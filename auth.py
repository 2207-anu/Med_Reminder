import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt

from config import ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_HOURS
from db_postgres import login_user, register_user

COOKIE_NAME = "medremind_token"


def valid_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def create_access_token(user: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return {
        "id": int(payload["sub"]),
        "email": payload["email"],
        "full_name": payload["full_name"],
        "role": payload["role"],
    }


def get_optional_user(token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> dict | None:
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return {
        "id": int(payload["sub"]),
        "email": payload["email"],
        "full_name": payload["full_name"],
        "role": payload["role"],
    }


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access only")
    return user


def authenticate(email: str, password: str) -> dict:
    return login_user(email, password)


def signup(full_name: str, email: str, password: str, role: str = "admin") -> dict:
    return register_user(full_name, email, password, role=role)
