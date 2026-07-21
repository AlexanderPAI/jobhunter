from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connector import get_session
from backend.db.models import User
from backend.security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    user = await session.scalar(select(User).where(User.username == form.username))
    if (
        user is None
        or not user.is_active
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "username": user.username,
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "username": user.username}
