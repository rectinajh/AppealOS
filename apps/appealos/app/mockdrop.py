"""Typed HTTP adapter for the deployed or local MockDrop service."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

MOCKDROP_BASE_URL = os.getenv(
    "MOCKDROP_BASE_URL", "http://localhost:8080"
).rstrip("/")
MOCKDROP_API_TOKEN = os.getenv("MOCKDROP_API_TOKEN", "")


class MockDropClient:
    def __init__(self, base_url: str = MOCKDROP_BASE_URL) -> None:
        self.base_url = base_url
        self.headers = {"content-type": "application/json"}
        if MOCKDROP_API_TOKEN:
            self.headers["authorization"] = f"Bearer {MOCKDROP_API_TOKEN}"

    def _post(
        self,
        path: str,
        body: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        headers = dict(self.headers)
        if idempotency_key:
            headers["idempotency-key"] = idempotency_key
        response = httpx.post(
            f"{self.base_url}{path}",
            json=body,
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        return response

    def _get(self, path: str) -> httpx.Response:
        response = httpx.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=20.0,
        )
        response.raise_for_status()
        return response

    def reset(self) -> Dict[str, Any]:
        return self._post("/v1/demo/reset", {}).json()

    def get_account(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/v1/accounts/{account_id}").json()

    def submit_appeal(
        self,
        *,
        case_id: str,
        account_id: str,
        allegation_type: str,
        claim_ids: list[str],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        return self._post(
            "/v1/appeals",
            {
                "caseId": case_id,
                "accountId": account_id,
                "allegationType": allegation_type,
                "claimIds": claim_ids,
            },
            idempotency_key=idempotency_key,
        ).json()

    def submit_supplement(
        self,
        *,
        appeal_id: str,
        artifact_sha256: str,
        template: str,
        disclosed_fields: list[str],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        return self._post(
            f"/v1/appeals/{appeal_id}/supplements",
            {
                "artifactSha256": artifact_sha256,
                "template": template,
                "disclosedFields": disclosed_fields,
            },
            idempotency_key=idempotency_key,
        ).json()

    def get_appeal(self, appeal_id: str) -> Dict[str, Any]:
        return self._get(f"/v1/appeals/{appeal_id}").json()
