from datetime import date as DateType
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

import rate_limit
from database import get_session
from models import AUTO_HIDE_THRESHOLD, Post, PostCreate, PostOut, PostVote, ReportOut, User, VoteOut
from utils import get_client_ip

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


@router.get("", response_model=list[PostOut])
async def get_posts(
    date: DateType | None = None,
    session: AsyncSession = Depends(get_session)
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if date is None:
        cutoff_start = now - timedelta(hours=POST_VISIBILITY_HOURS)
        cutoff_end = now
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
    return result.all()


@router.post("", response_model=PostOut, status_code=201)
async def create_post(
    data: PostCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_user_id: str | None = Header(default=None),
):
    ip = get_client_ip(request)
    allowed, msg = rate_limit.check_rate_limit(ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    user_id = None
    author_username = None
    author_avatar_url = None
    if x_user_id:
        try:
            uid = UUID(x_user_id)
            user = await session.get(User, uid)
            if user:
                user_id = user.id
                author_username = user.username
                author_avatar_url = user.avatar_url
        except ValueError:
            pass

    post = Post(
        title=data.title,
        content=data.content,
        category=data.category,
        lat=data.lat,
        lng=data.lng,
        image_url=data.image_url,
        user_id=user_id,
        author_username=author_username,
        author_avatar_url=author_avatar_url,
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
    
    post.report_count += 8

    if post.report_count >= AUTO_HIDE_THRESHOLD:
        post.is_hidden = True
    
    session.add(post)
    await session.commit()
    return ReportOut(message="Thank you for your report.", auto_hidden=post.is_hidden)


@router.post("/{post_id}/upvote", response_model=VoteOut)
async def upvote_post(post_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="Post not found.")
    ip = get_client_ip(request)
    existing = await session.get(PostVote, (post_id, ip))
    if existing is None:
        post.upvote_count += 1
        session.add(PostVote(post_id=post_id, ip=ip, direction="up"))
        new_direction = "up"
    elif existing.direction == "up":
        post.upvote_count -= 1
        await session.delete(existing)
        new_direction = None
    else:
        post.downvote_count -= 1
        post.upvote_count += 1
        existing.direction = "up"
        session.add(existing)
        new_direction = "up"
    session.add(post)
    await session.commit()
    return VoteOut(upvote_count=post.upvote_count, downvote_count=post.downvote_count, direction=new_direction)


@router.post("/{post_id}/downvote", response_model=VoteOut)
async def downvote_post(post_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="Post not found.")
    ip = get_client_ip(request)
    existing = await session.get(PostVote, (post_id, ip))
    if existing is None:
        post.downvote_count += 1
        session.add(PostVote(post_id=post_id, ip=ip, direction="down"))
        new_direction = "down"
    elif existing.direction == "down":
        post.downvote_count -= 1
        await session.delete(existing)
        new_direction = None
    else:
        post.upvote_count -= 1
        post.downvote_count += 1
        existing.direction = "down"
        session.add(existing)
        new_direction = "down"
    session.add(post)
    await session.commit()
    return VoteOut(upvote_count=post.upvote_count, downvote_count=post.downvote_count, direction=new_direction)

