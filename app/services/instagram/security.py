"""Cybersecurity module for Instagram Meta Graph API Webhook signature verification.

Implements HMAC-SHA256 signature verification over raw request body matching
Meta's X-Hub-Signature-256 header using constant-time comparison.
"""

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def generate_meta_hub_signature(raw_body: bytes, app_secret: str) -> str:
    """Compute Meta-compatible sha256=<hex_digest> signature over raw body bytes."""
    if not app_secret:
        return ""
    digest = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify_meta_hub_signature(
    raw_body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """Verify Meta X-Hub-Signature-256 header using constant-time comparison.

    Meta sends: 'sha256=<64-char-hex-digest>' computed over raw payload bytes.
    """
    if not signature_header or not app_secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = generate_meta_hub_signature(raw_body, app_secret)
    is_valid = hmac.compare_digest(signature_header, expected_signature)
    if not is_valid:
        logger.warning("Meta webhook X-Hub-Signature-256 mismatch")
    return is_valid
