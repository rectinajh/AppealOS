"""Pub/Sub push helpers for the AppealOS platform-event consumer."""

from __future__ import annotations

import base64
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
    if isinstance(raw, str):
        data_bytes = base64.b64decode(raw.encode("ascii"))
    else:
        data_bytes = base64.b64decode(raw)
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

    from google.oauth2 import id_token  # type: ignore

    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise PubSubMessageError("Missing bearer token on Pub/Sub push")
    token = authorization_header[len("Bearer ") :]
    try:
        id_token.verify_oauth2_token(token, None, audience=PUBSUB_AUDIENCE)
    except Exception as exc:  # pragma: no cover - depends on GCP token
        raise PubSubMessageError(f"Pub/Sub OIDC verification failed: {exc}") from exc
