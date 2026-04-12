from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import LoginRequest, User, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.exec(
        select(User).where(or_(User.email == body.email, User.username == body.username))
    )
    taken = existing.first()
    if taken:
        if taken.email == body.email:
            raise HTTPException(status_code=400, detail="E-post är redan registrerad")
        raise HTTPException(status_code=400, detail="Användarnamnet är taget")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=ph.hash(body.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.exec(
        select(User).where(or_(User.email == body.identifier, User.username == body.identifier))
    )
    user = result.first()
    if not user:
        raise HTTPException(status_code=401, detail="Fel inloggningsuppgifter")

    try:
        ph.verify(user.hashed_password, body.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Fel inloggningsuppgifter")

    if ph.check_needs_rehash(user.hashed_password):
        user.hashed_password = ph.hash(body.password)
        session.add(user)
        await session.commit()

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role,
    }
