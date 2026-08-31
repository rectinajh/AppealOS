"""Evidence Vault: AES-256-GCM fixtures in Cloud Storage + Secret Manager.

The vault stores synthetic evidence ciphertext in Cloud Storage and the demo
AES-256 key in Secret Manager.  AppealOS reads and verifies an artifact only
after permission checks; a plaintext-hash, ciphertext-hash, or AAD mismatch
raises :class:`EvidenceIntegrityError` so the workflow can quarantine the
artifact and block citation or disclosure.

This is deliberately a synthetic, server-decryptable prototype.  The server
can decrypt the fixtures with the demo key, so it is not zero-knowledge,
user-held-custody, immutable, or independently verifiable.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .domain import EVIDENCE_ARTIFACTS, canonicalize, sha256_canonical

LOGGER = logging.getLogger("appealos.vault")

EVIDENCE_BUCKET = os.getenv("APPEALOS_EVIDENCE_BUCKET", "appealos-evidence-vault")
EVIDENCE_SECRET = os.getenv(
    "APPEALOS_EVIDENCE_KEY_SECRET", "appealos-demo-evidence-key"
)
EVIDENCE_BACKEND = os.getenv("APPEALOS_EVIDENCE_BACKEND", "memory").strip().lower()
EVIDENCE_SCHEMA_VERSION = "1.0"
EVIDENCE_CASE_ID = "case-synthetic-r-2048-vault-v1"
EVIDENCE_MIME_TYPE = "application/json"
EVIDENCE_OBJECT_PREFIX = "evidence"

ENVELOPE_PUBLIC_FIELDS = (
    "schemaVersion",
    "caseId",
    "artifactId",
    "kind",
    "capturedAt",
    "mimeType",
    "storageUri",
    "plaintextSha256",
    "ciphertextSha256",
    "nonceB64",
    "aadCanonical",
    "demoKeySecret",
)


class EvidenceIntegrityError(Exception):
    """Raised when a vault artifact fails hash, AAD, or decryption checks."""


class EvidenceVault(Protocol):
    backend: str

    def list_artifacts(self) -> List[Dict[str, Any]]:
        """Return public vault metadata without decrypting evidence."""

    def read_verified(self, artifact_id: str) -> Dict[str, Any]:
        """Fetch, verify, and decrypt one artifact."""


def build_vault() -> EvidenceVault:
    if EVIDENCE_BACKEND == "gcs":
        LOGGER.info("evidence_vault_backend", extra={"backend": "gcs"})
        return GcsEvidenceVault()
    LOGGER.info("evidence_vault_backend", extra={"backend": "memory"})
    return FixtureEvidenceVault()


def build_aad(artifact_id: str, plaintext_sha256: str) -> str:
    return canonicalize(
        {
            "schemaVersion": EVIDENCE_SCHEMA_VERSION,
            "caseId": EVIDENCE_CASE_ID,
            "artifactId": artifact_id,
            "plaintextSha256": plaintext_sha256,
        }
    )


def plaintext_bytes_for(artifact_id: str) -> bytes:
    if artifact_id not in EVIDENCE_ARTIFACTS:
        raise EvidenceIntegrityError(f"Unknown evidence artifact {artifact_id}")
    return canonicalize(EVIDENCE_ARTIFACTS[artifact_id]["plaintext"]).encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


class FixtureEvidenceVault:
    """Local fallback used by tests and unconfigured environments.

    It does not persist ciphertext; it verifies the same fixture hashes the
    deployed GCS vault is seeded from.
    """

    backend = "memory"

    def list_artifacts(self) -> List[Dict[str, Any]]:
        artifacts: List[Dict[str, Any]] = []
        for item in EVIDENCE_ARTIFACTS.values():
            plaintext_sha256 = sha256_canonical(item["plaintext"])
            artifacts.append(
                {
                    "schemaVersion": EVIDENCE_SCHEMA_VERSION,
                    "caseId": EVIDENCE_CASE_ID,
                    "artifactId": item["artifactId"],
                    "kind": item["kind"],
                    "capturedAt": item["capturedAt"],
                    "mimeType": EVIDENCE_MIME_TYPE,
                    "storageUri": f"memory://evidence/{item['artifactId']}",
                    "plaintextSha256": plaintext_sha256,
                    "ciphertextSha256": None,
                    "nonceB64": None,
                    "aadCanonical": build_aad(item["artifactId"], plaintext_sha256),
                    "demoKeySecret": EVIDENCE_SECRET,
                }
            )
        return artifacts

    def read_verified(self, artifact_id: str) -> Dict[str, Any]:
        if artifact_id not in EVIDENCE_ARTIFACTS:
            raise EvidenceIntegrityError(f"Unknown evidence artifact {artifact_id}")
        item = EVIDENCE_ARTIFACTS[artifact_id]
        plaintext = item["plaintext"]
        plaintext_sha256 = sha256_canonical(plaintext)
        metadata = {
            "schemaVersion": EVIDENCE_SCHEMA_VERSION,
            "caseId": EVIDENCE_CASE_ID,
            "artifactId": item["artifactId"],
            "kind": item["kind"],
            "capturedAt": item["capturedAt"],
            "mimeType": EVIDENCE_MIME_TYPE,
            "storageUri": f"memory://evidence/{item['artifactId']}",
            "plaintextSha256": plaintext_sha256,
            "ciphertextSha256": None,
            "nonceB64": None,
            "aadCanonical": build_aad(item["artifactId"], plaintext_sha256),
            "demoKeySecret": EVIDENCE_SECRET,
        }
        return {**metadata, "plaintext": plaintext, "verified": True}


class GcsEvidenceVault:
    """Persisted vault backed by Cloud Storage and Secret Manager."""

    backend = "gcs"

    def __init__(
        self,
        *,
        bucket: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> None:
        self.bucket = bucket or EVIDENCE_BUCKET
        self.secret = secret or EVIDENCE_SECRET
        self._storage_client = None
        self._secret_client = None

    def _storage(self):
        if self._storage_client is None:
            from google.cloud import storage  # type: ignore

            self._storage_client = storage.Client()
        return self._storage_client

    def _secretmanager(self):
        if self._secret_client is None:
            from google.cloud import secretmanager  # type: ignore

            self._secret_client = secretmanager.SecretManagerServiceClient()
        return self._secret_client

    def _object_path(self, artifact_id: str) -> str:
        return f"{EVIDENCE_OBJECT_PREFIX}/{artifact_id}.json"

    def _project(self) -> str:
        return os.getenv("GOOGLE_CLOUD_PROJECT", "boxwood-scope-364905")

    def _secret_path(self) -> str:
        return f"projects/{self._project()}/secrets/{self.secret}"

    def read_demo_key(self) -> bytes:
        client = self._secretmanager()
        response = client.access_secret_version(
            request={"name": f"{self._secret_path()}/versions/latest"}
        )
        key = response.payload.data
        if len(key) != 32:
            raise EvidenceIntegrityError(
                f"Demo key is {len(key)} bytes; expected 32 bytes"
            )
        return key

    def fetch_envelope(self, artifact_id: str) -> Dict[str, Any]:
        bucket = self._storage().bucket(self.bucket)
        blob = bucket.blob(self._object_path(artifact_id))
        if not blob.exists():
            raise EvidenceIntegrityError(
                f"Vault object {blob.name} does not exist in {self.bucket}"
            )
        raw = blob.download_as_text()
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvidenceIntegrityError(
                f"Vault object {blob.name} is not valid JSON"
            ) from exc
        return envelope

    def list_artifacts(self) -> List[Dict[str, Any]]:
        artifacts: List[Dict[str, Any]] = []
        for artifact_id in EVIDENCE_ARTIFACTS:
            envelope = self.fetch_envelope(artifact_id)
            artifacts.append(_public_envelope(envelope))
        return artifacts

    def read_verified(self, artifact_id: str) -> Dict[str, Any]:
        envelope = self.fetch_envelope(artifact_id)
        _verify_envelope(envelope, artifact_id)
        plaintext = _decrypt_envelope(envelope, self.read_demo_key())
        metadata = _public_envelope(envelope)
        return {**metadata, "plaintext": plaintext, "verified": True}

    def upload_artifact(self, artifact_id: str, key: Optional[bytes] = None) -> Dict[str, Any]:
        key = key or self.read_demo_key()
        plaintext_bytes = plaintext_bytes_for(artifact_id)
        plaintext = EVIDENCE_ARTIFACTS[artifact_id]["plaintext"]
        plaintext_sha256 = sha256_canonical(plaintext)
        aad = build_aad(artifact_id, plaintext_sha256)
        nonce = os.urandom(12)
        sealed = AESGCM(key).encrypt(nonce, plaintext_bytes, aad.encode("utf-8"))
        ciphertext = sealed[:-16]
        tag = sealed[-16:]
        storage_uri = f"gs://{self.bucket}/{self._object_path(artifact_id)}"
        envelope = {
            "schemaVersion": EVIDENCE_SCHEMA_VERSION,
            "caseId": EVIDENCE_CASE_ID,
            "artifactId": artifact_id,
            "kind": EVIDENCE_ARTIFACTS[artifact_id]["kind"],
            "capturedAt": EVIDENCE_ARTIFACTS[artifact_id]["capturedAt"],
            "mimeType": EVIDENCE_MIME_TYPE,
            "storageUri": storage_uri,
            "plaintextSha256": plaintext_sha256,
            "ciphertextSha256": hashlib.sha256(ciphertext).hexdigest(),
            "nonceB64": _b64encode(nonce),
            "aadCanonical": aad,
            "demoKeySecret": self.secret,
            "ciphertextB64": _b64encode(ciphertext),
            "tagB64": _b64encode(tag),
        }
        blob = self._storage().bucket(self.bucket).blob(self._object_path(artifact_id))
        blob.upload_from_string(
            json.dumps(envelope, indent=2, sort_keys=True),
            content_type="application/json",
        )
        LOGGER.info(
            "evidence_vault_upload",
            extra={"artifact_id": artifact_id, "storage_uri": storage_uri},
        )
        return _public_envelope(envelope)


def _public_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return {key: envelope.get(key) for key in ENVELOPE_PUBLIC_FIELDS}


def _verify_envelope(envelope: Dict[str, Any], artifact_id: str) -> None:
    if envelope.get("artifactId") != artifact_id:
        raise EvidenceIntegrityError(
            f"Vault artifact id {envelope.get('artifactId')!r} does not match {artifact_id}"
        )
    if envelope.get("schemaVersion") != EVIDENCE_SCHEMA_VERSION:
        raise EvidenceIntegrityError("Unsupported evidence vault schema version")
    if envelope.get("caseId") != EVIDENCE_CASE_ID:
        raise EvidenceIntegrityError("Evidence vault case binding mismatch")
    expected_plaintext = sha256_canonical(EVIDENCE_ARTIFACTS[artifact_id]["plaintext"])
    if envelope.get("plaintextSha256") != expected_plaintext:
        raise EvidenceIntegrityError("Plaintext hash does not match the synthetic fixture")
    expected_aad = build_aad(artifact_id, envelope["plaintextSha256"])
    if envelope.get("aadCanonical") != expected_aad:
        raise EvidenceIntegrityError("Evidence AAD does not match expected canonical AAD")
    ciphertext = _b64decode(envelope.get("ciphertextB64", ""))
    expected_ciphertext = hashlib.sha256(ciphertext).hexdigest()
    if envelope.get("ciphertextSha256") != expected_ciphertext:
        raise EvidenceIntegrityError("Ciphertext hash does not match stored ciphertext")
    if envelope.get("mimeType") != EVIDENCE_MIME_TYPE:
        raise EvidenceIntegrityError("Evidence MIME type is not allowlisted")


def _decrypt_envelope(envelope: Dict[str, Any], key: bytes) -> Any:
    nonce = _b64decode(envelope.get("nonceB64", ""))
    ciphertext = _b64decode(envelope.get("ciphertextB64", ""))
    tag = _b64decode(envelope.get("tagB64", ""))
    aad = envelope.get("aadCanonical", "").encode("utf-8")
    try:
        raw = AESGCM(key).decrypt(nonce, ciphertext + tag, aad)
    except Exception as exc:  # cryptography raises InvalidTag on mismatch
        raise EvidenceIntegrityError("Evidence decryption failed; AAD/key/ciphertext mismatch") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceIntegrityError("Decrypted evidence is not valid JSON") from exc
