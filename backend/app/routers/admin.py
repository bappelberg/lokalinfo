from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Post, PostAdminOut
from config import settings
from database import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

def verify_token(x_admin_token: str = Header(...)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid token.")
    
@router.get("/posts", response_model=list[PostAdminOut], dependencies=[Depends(verify_token)])
async def list_reported(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Post)
        .where(Post.report_count > 0, Post.is_deleted == False)
        .order_by(Post.report_count.desc())
    )
    result = await session.exec(stmt)
    return result.all()

@router.delete("/posts/{post_id}", dependencies=[Depends(verify_token)])
async def delete_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404)
    post.is_deleted = True
    session.add(post)
    await session.commit()
    return {"ok": True}

@router.post("/posts/{post_id}/restore", response_model=PostAdminOut, dependencies=[Depends(verify_token)])
async def restore_post(post_id: UUID, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404)
    post.is_hidden = False
    post.report_count = 0
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post
