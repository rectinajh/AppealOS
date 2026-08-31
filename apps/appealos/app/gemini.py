"""Gemini 3.5+ client construction for the AppealOS rescue runtime.

The public MVP is allowed to use the synthetic fixtures only.  Gemini is used
for interpretation and drafting, never for authorization, state mutation, or
deadline computation.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
import subprocess

from google import genai
from google.oauth2.credentials import Credentials

LOGGER = logging.getLogger("appealos.gemini")

GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-3.5-flash")
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "boxwood-scope-364905")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TOKEN_TTL_MINUTES = 30


def _gcloud_access_token() -> str:
    """Return the current gcloud user credential for local development."""
    completed = subprocess.run(
        [
            "gcloud",
            "auth",
            "print-access-token",
            "--project",
            GCP_PROJECT,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _credentials():
    """Build short-lived credentials.

    Priority:
      1. explicit Gemini API key (Gemini Developer API, not Vertex AI)
      2. Application Default Credentials (Cloud Run service identity)
      3. local gcloud user credential (rescue development path)
    """
    if GEMINI_API_KEY:
        return None  # signal the client to use api_key

    # Cloud Run / Application Default Credentials first (service identity or
    # mounted service-account key), then local gcloud user credential.
    try:
        import google.auth

        credentials, _project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return credentials
    except Exception:
        pass

    token = _gcloud_access_token()
    return Credentials(
        token=token,
        expiry=_dt.datetime.utcnow() + _dt.timedelta(minutes=TOKEN_TTL_MINUTES),
    )


def build_vertex_client() -> genai.Client:
    """Create a Vertex AI client bound to the eligible Gemini model endpoint."""
    credentials = _credentials()
    kwargs = {
        "vertexai": True,
        "project": GCP_PROJECT,
        "location": GCP_LOCATION,
    }
    if GEMINI_API_KEY:
        kwargs = {"api_key": GEMINI_API_KEY}
    else:
        kwargs["credentials"] = credentials

    LOGGER.info(
        "gemini_client_ready",
        extra={
            "model": GEMINI_MODEL_ID,
            "project": GCP_PROJECT,
            "location": GCP_LOCATION,
            "auth": "api_key" if GEMINI_API_KEY else "vertex_ai",
        },
    )
    return genai.Client(**kwargs)
