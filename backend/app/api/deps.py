from typing import Optional
from fastapi import Header, HTTPException
from app.config.settings import settings
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.system_state_repository import SystemStateRepository
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone


ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_current_user(x_user_token: str = Header(None)) -> dict:
    if not x_user_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = decode_token(x_user_token)
    return payload


def get_admin_user(x_user_token: str = Header(None)) -> dict:
    user = get_current_user(x_user_token)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in settings.admin_emails_list
