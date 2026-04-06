from datetime import date as DateType
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

import rate_limit
from models import AUTO_HIDE_THRESHOLD, Post, PostCreate, PostOut, ReportOut
from database import get_session

router = APIRouter(prefix="/posts", tags=["posts"])

POST_VISIBILITY_HOURS = 24

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two coordinates"""
    RADIUS_EARTH = 6371
    # Convert coordinates from degrees to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * RADIUS_EARTH * asin(sqrt(a))


@router.get("/", response_model=list[PostOut])
async def get_posts(
    lat: float,
    lng: float,
    radius: float = 10.0,
    date: DateType | None = None,
    session: AsyncSession = Depends(get_session)
):
    """
    Get visable posts within radius (km)
    - Without date: show post within the latest 24 hors
    - With date(YYYY-MM-DD): show posts within that spefic date (00:00-23:59 UTC)
    """
    if date is None:
        cutoff_start = datetime.utcnow() - timedelta(hours=POST_VISIBILITY_HOURS)
        cutoff_end = datetime.utcnow()
    else:
        cutoff_start = datetime(date.year, date.month, date.day, 0, 0, 0)
        cutoff_end = datetime(date.year, date.month, date.day, 23, 59, 59)
    
    stmt = select(Post).where(
        Post.is_deleted == False,
        Post.is_hidden == False,
        Post.created_at >= cutoff_start,
        Post.created_at <= cutoff_end
    )
    
    result = await session.exec(stmt)
    posts = result.all()
    return [p for p in posts if haversine(lat, lng, p.lat, p.lng) <= radius]


@router.post("/", response_model=PostOut, status_code=201)
async def create_post(
    data: PostCreate,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    ip = request.client.host
    allowed, msg = rate_limit.check_rate_limit(ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)
    
    post = Post(
        title=data.title,
        content=data.content,
        category=data.category,
        lat=data.lat,
        lng=data.lng
    )

    session.add(post)
    await session.commit()
    await session.refresh(post)
    rate_limit.record_post(ip)
    return post

@router.post("/{post_id}/report", response_model=ReportOut)
async def report_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    post = await session.get(Post, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="Post not found.")
    
    post.report_count += 1

    if post.report_count >= AUTO_HIDE_THRESHOLD:
        post.is_hidden = True
    
    session.add(post)
    await session.commit()
    return ReportOut(message="Thank you for your report.", auto_hidden=post.is_hidden)



    