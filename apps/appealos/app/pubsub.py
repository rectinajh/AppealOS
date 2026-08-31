"""Pub/Sub push helpers for the AppealOS platform-event consumer."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

LOGGER = logging.getLogger("appealos.pubsub")

PUBSUB_VERIFY_OIDC = os.getenv("PUBSUB_VERIFY_OIDC", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
PUBSUB_AUDIENCE = os.getenv("PUBSUB_AUDIENCE", "").strip()


class PubSubMessageError(ValueError):
    pass


def decode_push_message(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Return (decoded platform event, pubsub message id) from a push envelope."""
    message = payload.get("message")
    if not isinstance(message, dict):
        raise PubSubMessageError("Push payload is missing message")
    message_id = str(message.get("messageId") or "")
    raw = message.get("data")
    if not message_id:
        raise PubSubMessageError("Push message is missing messageId")
    if not isinstance(raw, str) or not raw:
        raise PubSubMessageError("Push message is missing base64 data")
    try:
        data_bytes = base64.b64decode(raw.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise PubSubMessageError("Push message data is not valid base64") from exc
    try:
        event = json.loads(data_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PubSubMessageError(f"Invalid platform-event JSON: {exc}") from exc
    if not isinstance(event, dict):
        raise PubSubMessageError("Platform event is not a JSON object")
    return event, message_id


def verify_push_token(authorization_header: Optional[str]) -> None:
    """Validate a Pub/Sub push OIDC token when configured.

    Local smoke runs keep OIDC off. Deployments should set PUBSUB_VERIFY_OIDC=true
    and PUBSUB_AUDIENCE to the AppealOS service URL.
    """
    if not PUBSUB_VERIFY_OIDC:
        return

    from google.auth.transport import requests as google_requests  # type: ignore
    from google.oauth2 import id_token  # type: ignore

    if not PUBSUB_AUDIENCE:
        raise PubSubMessageError("PUBSUB_AUDIENCE is required when OIDC verification is enabled")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise PubSubMessageError("Missing bearer token on Pub/Sub push")
    token = authorization_header[len("Bearer ") :]
    try:
        id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=PUBSUB_AUDIENCE,
        )
    except Exception as exc:  # pragma: no cover - depends on GCP token
        raise PubSubMessageError(f"Pub/Sub OIDC verification failed: {exc}") from exc
