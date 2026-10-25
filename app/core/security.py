"""Security dependencies, authentication, and session management for Yurist REST API."""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
bearer_security = HTTPBearer(auto_error=False)


def create_session_token(username: str, expires_in_seconds: int = 7 * 86400) -> str:
    """Create a cryptographically signed HMAC-SHA256 session token."""
    payload = {
        "sub": username,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
    }
    encoded_payload = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )

    secret = (settings.ADMIN_SESSION_SECRET or settings.BOT_TOKEN).encode("utf-8")
    signature = hmac.new(secret, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{encoded_payload}.{signature}"


def verify_session_token(token: str) -> str | None:
    """Verify signed session token. Returns username if valid, None otherwise."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        encoded_payload, signature = parts
        secret = (settings.ADMIN_SESSION_SECRET or settings.BOT_TOKEN).encode("utf-8")
        expected_sig = hmac.new(secret, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add back padding if missing
        pad_len = 4 - (len(encoded_payload) % 4)
        if pad_len and pad_len != 4:
            encoded_payload += "=" * pad_len

        raw_json = base64.urlsafe_b64decode(encoded_payload.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw_json)

        if not isinstance(payload, dict):
            return None

        exp = payload.get("exp")
        if not isinstance(exp, (int, float)) or exp < time.time():
            return None

        return str(payload.get("sub", ""))
    except Exception as e:  # noqa: BLE001
        logger.debug("Session token verification failed: %s", e)
        return None


async def verify_admin_access(
    x_admin_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_security)] = None,
) -> bool:
    """Verify administrator and lawyer access for /api/v1 management endpoints.

    Authenticates via:
    - Web Session Token (from login page via Bearer or X-Admin-Key)
    - Programmatic API Key (ADMIN_API_KEY)
    """
    token: str | None = None
    if x_admin_key:
        token = x_admin_key.strip()
    elif bearer and bearer.credentials:
        token = bearer.credentials.strip()

    # 1. Check if token matches ADMIN_API_KEY
    if token and settings.ADMIN_API_KEY and hmac.compare_digest(token, settings.ADMIN_API_KEY):
        return True

    # 2. Check if token is a valid signed session token
    if token and verify_session_token(token):
        return True

    # In production, require either valid session token or valid API key
    if settings.ENVIRONMENT.lower() == "production":
        logger.warning("Unauthorized admin access attempt in production.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kirish taqiqlangan: avtorizatsiyadan o'ting",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development/test mode: if ADMIN_API_KEY is configured, enforce it
    if settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing administrative credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
