import base64
import datetime as dt
import hashlib
import unittest

from fastapi import HTTPException

from app.domain import (
    DEVICE_LOG_SHA256,
    EVIDENCE_ARTIFACTS,
    AnalysisConsent,
    AppealMandate,
    DemoCase,
    sha256_canonical,
)
from app.main import DemoService
from app.store import InMemoryCaseStore
from app.vault import (
    EVIDENCE_CASE_ID,
    EVIDENCE_MIME_TYPE,
    EVIDENCE_SCHEMA_VERSION,
    EvidenceIntegrityError,
    FixtureEvidenceVault,
    _verify_envelope,
    build_aad,
)


class FixtureVaultTest(unittest.TestCase):
    def test_fixture_vault_returns_verified_plaintext_and_hashes(self):
        vault = FixtureEvidenceVault()
        artifact = vault.read_verified("device-log")
        self.assertTrue(artifact["verified"])
        self.assertEqual(artifact["plaintextSha256"], DEVICE_LOG_SHA256)
        self.assertEqual(
            sha256_canonical(artifact["plaintext"]),
            DEVICE_LOG_SHA256,
        )

    def test_fixture_vault_lists_all_three_artifacts(self):
        vault = FixtureEvidenceVault()
        ids = {item["artifactId"] for item in vault.list_artifacts()}
        self.assertEqual(ids, set(EVIDENCE_ARTIFACTS))

    def test_verify_envelope_rejects_aad_mismatch(self):
        plaintext_sha256 = sha256_canonical(EVIDENCE_ARTIFACTS["device-log"]["plaintext"])
        ciphertext = b"tampered-ciphertext"
        envelope = {
            "schemaVersion": EVIDENCE_SCHEMA_VERSION,
            "caseId": EVIDENCE_CASE_ID,
            "artifactId": "device-log",
            "mimeType": EVIDENCE_MIME_TYPE,
            "plaintextSha256": plaintext_sha256,
            "ciphertextSha256": hashlib.sha256(ciphertext).hexdigest(),
            "aadCanonical": "wrong-aad",
            "ciphertextB64": base64.b64encode(ciphertext).decode(),
        }
        with self.assertRaises(EvidenceIntegrityError):
            _verify_envelope(envelope, "device-log")

    def test_verify_envelope_accepts_expected_envelope_shape(self):
        plaintext_sha256 = sha256_canonical(EVIDENCE_ARTIFACTS["device-log"]["plaintext"])
        ciphertext = b"ciphertext-bytes"
        envelope = {
            "schemaVersion": EVIDENCE_SCHEMA_VERSION,
            "caseId": EVIDENCE_CASE_ID,
            "artifactId": "device-log",
            "mimeType": EVIDENCE_MIME_TYPE,
            "plaintextSha256": plaintext_sha256,
            "ciphertextSha256": hashlib.sha256(ciphertext).hexdigest(),
            "aadCanonical": build_aad("device-log", plaintext_sha256),
            "ciphertextB64": base64.b64encode(ciphertext).decode(),
        }
        _verify_envelope(envelope, "device-log")


class TamperedDeviceLogVault(FixtureEvidenceVault):
    def read_verified(self, artifact_id):
        if artifact_id == "device-log":
            raise EvidenceIntegrityError("synthetic tamper: ciphertext hash mismatch")
        return super().read_verified(artifact_id)


class FakeMockDrop:
    def submit_supplement(self, **kwargs):
        return {
            "appeal": {"appealId": kwargs["appeal_id"], "status": "APPROVED"},
            "account": {"accountId": "rider-r-2048", "status": "ACTIVE"},
            "receipt": {"receiptId": "receipt-supplement", "idempotencyKey": kwargs["idempotency_key"]},
        }


class QuarantineWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryCaseStore()
        self.service = DemoService(
            adk=object(),
            mockdrop=FakeMockDrop(),
            store=self.store,
            vault=TamperedDeviceLogVault(),
        )

    def _authorized_supplement_case(self):
        now = dt.datetime.now(dt.timezone.utc)
        case = DemoCase()
        case.consent = AnalysisConsent.create(case.caseId, list(EVIDENCE_ARTIFACTS), now)
        case.mandate = AppealMandate(
            mandateId="mandate-1",
            caseId=case.caseId,
            destinationAdapter="mockdrop",
            destinationAccountId=case.accountId,
            approvedClaimIds=["claim-1"],
            allowedActions=["SUBMIT", "SUPPLEMENT", "POLL", "VERIFY"],
            approvedArtifactIds=list(EVIDENCE_ARTIFACTS),
            allowedSupplementTemplate="DEVICE_NETWORK_HANDOFF_V1",
            maxSupplementCycles=1,
            supplementCyclesUsed=0,
            approvedAt=now.isoformat(),
            expiresAt=(now + dt.timedelta(hours=1)).isoformat(),
        )
        case.appealId = "appeal-1"
        case.record("SUPPLEMENT_REQUESTED", "PLATFORM", {}, "SUPPLEMENT_REQUESTED")
        return case

    def test_tampered_device_log_is_quarantined_and_blocks_disclosure(self):
        case = self._authorized_supplement_case()
        self.store.save(case)

        with self.assertRaises(HTTPException) as raised:
            self.service.supplement(case.caseId)

        self.assertIn("integrity failure", raised.exception.detail)
        restored = self.store.get(case.caseId)
        self.assertIn("device-log", restored.quarantinedArtifactIds)
        self.assertIn(
            "EVIDENCE_QUARANTINED",
            [event["type"] for event in restored.timeline],
        )

        with self.assertRaises(HTTPException) as again:
            self.service.supplement(case.caseId)
        self.assertIn("quarantined", again.exception.detail)


if __name__ == "__main__":
    unittest.main()
