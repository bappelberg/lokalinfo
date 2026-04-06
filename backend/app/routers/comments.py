from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Comment, CommentCreate, CommentOut, Post, VoteOut

router = APIRouter(prefix="/posts", tags=["comments"])