"""Tests for Web Admin Authentication (Login, Session Token, Protected Routes)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.core.config import settings
from app.core.security import create_session_token, verify_session_token
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db_session

auth_test_app = create_app()

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


auth_test_app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[User.__table__])
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[User.__table__])


@pytest.mark.asyncio
async def test_admin_login_success():
    """Verify that valid username and password return an access token."""
    transport = ASGITransport(app=auth_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["access_token"]
        assert data["username"] == settings.ADMIN_USERNAME

        # Verify token cryptographically
        verified_user = verify_session_token(data["access_token"])
        assert verified_user == settings.ADMIN_USERNAME


@pytest.mark.asyncio
async def test_admin_login_invalid_password():
    """Verify that invalid password returns 401 Unauthorized."""
    transport = ASGITransport(app=auth_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": "wrong_password_999"},
        )
        assert res.status_code == 401
        assert "Noto'g'ri login" in res.json()["detail"]


@pytest.mark.asyncio
async def test_session_token_authenticates_admin_endpoints():
    """Verify that the generated session token authorizes protected admin endpoints."""
    token = create_session_token(username=settings.ADMIN_USERNAME)
    transport = ASGITransport(app=auth_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check /auth/me
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_me.status_code == 200
        assert res_me.json()["authenticated"] is True

        # Check /crm/leads
        res_leads = await client.get(
            "/api/v1/crm/leads",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_leads.status_code == 200


@pytest.mark.asyncio
async def test_tampered_session_token_rejected():
    """Verify that tampering with token payload or signature is rejected."""
    token = create_session_token(username=settings.ADMIN_USERNAME)
    parts = token.split(".")
    tampered_token = f"{parts[0]}.forgedsignature123"

    assert verify_session_token(tampered_token) is None

    # Test rejection in production environment
    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    try:
        transport = ASGITransport(app=auth_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {tampered_token}"},
            )
            assert res.status_code == 401
    finally:
        settings.ENVIRONMENT = original_env
