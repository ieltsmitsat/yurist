"""Tests for Instagram Meta Webhook HMAC-SHA256 signature verification (Phase 2)."""

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.core.config import settings
from app.core.redis import InMemoryRedisClient
from app.services.instagram.security import generate_meta_hub_signature, verify_meta_hub_signature


def test_generate_and_verify_meta_signature() -> None:
    secret = "meta_test_secret_key_123"
    body = b'{"object":"instagram","entry":[]}'

    sig = generate_meta_hub_signature(body, secret)
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64  # 'sha256=' + 64 hex characters

    # Valid check
    assert verify_meta_hub_signature(body, sig, secret) is True

    # Tampered payload check
    tampered_body = b'{"object":"instagram","entry":[],"tampered":true}'
    assert verify_meta_hub_signature(tampered_body, sig, secret) is False

    # Wrong secret check
    assert verify_meta_hub_signature(body, sig, "wrong_secret") is False

    # Malformed headers
    assert verify_meta_hub_signature(body, "invalid_sig_without_prefix", secret) is False
    assert verify_meta_hub_signature(body, None, secret) is False
    assert verify_meta_hub_signature(body, sig, "") is False


@pytest.mark.asyncio
async def test_webhook_signature_enforcement() -> None:
    app = create_app()
    mock_redis = InMemoryRedisClient()
    secret = "super_secret_meta_key"

    payload_dict = {
        "object": "instagram",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "sec_user_1"},
                        "message": {"text": "Salom, yuridik savol bor"},
                    }
                ]
            }
        ],
    }
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    valid_signature = generate_meta_hub_signature(raw_bytes, secret)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch.object(settings, "INSTAGRAM_APP_SECRET", secret),
            patch("app.api.v1.instagram.get_redis_client", return_value=mock_redis),
        ):
            # 1. Missing signature header -> 403 Forbidden
                resp_missing = await client.post(
                    "/api/v1/instagram/webhook",
                    content=raw_bytes,
                    headers={"Content-Type": "application/json"},
                )
                assert resp_missing.status_code == 403
                assert "X-Hub-Signature-256" in resp_missing.json()["detail"]

                # 2. Tampered / invalid signature -> 403 Forbidden
                resp_invalid = await client.post(
                    "/api/v1/instagram/webhook",
                    content=raw_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
                    },
                )
                assert resp_invalid.status_code == 403

                # 3. Valid signature -> 200 OK
                resp_valid = await client.post(
                    "/api/v1/instagram/webhook",
                    content=raw_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Hub-Signature-256": valid_signature,
                    },
                )
                assert resp_valid.status_code == 200
                assert resp_valid.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_production_fail_closed_without_secret() -> None:
    app = create_app()
    raw_bytes = b'{"object":"instagram","entry":[]}'

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch.object(settings, "INSTAGRAM_APP_SECRET", ""),
            patch.object(settings, "ENVIRONMENT", "production"),
        ):
            resp = await client.post(
                "/api/v1/instagram/webhook",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            # In production, must fail-closed if app secret is not configured
            assert resp.status_code == 403
            assert "not configured" in resp.json()["detail"].lower()
