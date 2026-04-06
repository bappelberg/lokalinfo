from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Comment, CommentCreate, CommentOut, CommentVote, Post, VoteOut

router = APIRouter(prefix="/posts", tags=["comments"])


@router.get("/{post_id}/comments", response_model=list[CommentOut])
async def get_comments(
    post_id: UUID,
    sort: str = "popular",
    session: AsyncSession = Depends(get_session),
):
    post = await session.get(Post, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="Post not found.")

    stmt = select(Comment).where(
        Comment.post_id == post_id,
        Comment.is_deleted == False,
    )
    result = await session.exec(stmt)
    comments = list(result.all())

    top = [c for c in comments if c.parent_id is None]
    replies = [c for c in comments if c.parent_id is not None]

    if sort == "newest":
        top.sort(key=lambda c: c.created_at, reverse=True)
    else:
        top.sort(key=lambda c: c.upvote_count - c.downvote_count, reverse=True)

    replies.sort(key=lambda c: c.created_at)
    return top + replies


@router.post("/{post_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    post_id: UUID,
    data: CommentCreate,
    session: AsyncSession = Depends(get_session),
):
    post = await session.get(Post, post_id)
    if not post or post.is_deleted:
        raise HTTPException(status_code=404, detail="Post not found.")

    if data.parent_id:
        parent = await session.get(Comment, data.parent_id)
        if not parent or parent.is_deleted or parent.post_id != post_id:
            raise HTTPException(status_code=404, detail="Parent comment not found.")

    comment = Comment(post_id=post_id, parent_id=data.parent_id, content=data.content)
    post.comment_count += 1
    session.add(comment)
    session.add(post)
    await session.commit()
    await session.refresh(comment)
    return comment


@router.post("/{post_id}/comments/{comment_id}/upvote", response_model=VoteOut)
async def upvote_comment(
    post_id: UUID,
    comment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    comment = await session.get(Comment, comment_id)
    if not comment or comment.is_deleted or comment.post_id != post_id:
        raise HTTPException(status_code=404, detail="Comment not found.")
    ip = request.client.host
    existing = await session.get(CommentVote, (comment_id, ip))
    if existing is None:
        comment.upvote_count += 1
        session.add(CommentVote(comment_id=comment_id, ip=ip, direction="up"))
        new_direction = "up"
    elif existing.direction == "up":
        comment.upvote_count -= 1
        await session.delete(existing)
        new_direction = None
    else:
        comment.downvote_count -= 1
        comment.upvote_count += 1
        existing.direction = "up"
        session.add(existing)
        new_direction = "up"
    session.add(comment)
    await session.commit()
    return VoteOut(upvote_count=comment.upvote_count, downvote_count=comment.downvote_count, direction=new_direction)


@router.post("/{post_id}/comments/{comment_id}/downvote", response_model=VoteOut)
async def downvote_comment(
    post_id: UUID,
    comment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    comment = await session.get(Comment, comment_id)
    if not comment or comment.is_deleted or comment.post_id != post_id:
        raise HTTPException(status_code=404, detail="Comment not found.")
    ip = request.client.host
    existing = await session.get(CommentVote, (comment_id, ip))
    if existing is None:
        comment.downvote_count += 1
        session.add(CommentVote(comment_id=comment_id, ip=ip, direction="down"))
        new_direction = "down"
    elif existing.direction == "down":
        comment.downvote_count -= 1
        await session.delete(existing)
        new_direction = None
    else:
        comment.upvote_count -= 1
        comment.downvote_count += 1
        existing.direction = "down"
        session.add(existing)
        new_direction = "down"
    session.add(comment)
    await session.commit()
    return VoteOut(upvote_count=comment.upvote_count, downvote_count=comment.downvote_count, direction=new_direction)
