"""Authentication endpoints for Web Admin Dashboard."""

import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_session_token, verify_admin_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=LoginResponse)
async def admin_login(payload: LoginRequest) -> dict[str, Any]:
    """Authenticate administrator with login and password and return session token."""
    username = payload.username.strip()
    password = payload.password.strip()

    valid_username = hmac.compare_digest(username, settings.ADMIN_USERNAME)
    valid_password = hmac.compare_digest(password, settings.ADMIN_PASSWORD)

    if not valid_username or not valid_password:
        logger.warning("Failed admin login attempt for username: %s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Noto'g'ri login yoki parol kiritildi",
        )

    expires_in = settings.ADMIN_TOKEN_EXPIRE_DAYS * 86400
    token = create_session_token(username=username, expires_in_seconds=expires_in)
    logger.info("Admin user '%s' logged in successfully", username)

    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "username": username,
    }


@router.get("/me")
async def get_current_admin_info(_: bool = Depends(verify_admin_access)) -> dict[str, Any]:
    """Verify session validity and return current admin identity."""
    return {
        "ok": True,
        "username": settings.ADMIN_USERNAME,
        "authenticated": True,
    }


@router.post("/logout")
async def admin_logout() -> dict[str, bool]:
    """Client logout confirmation."""
    return {"ok": True}
