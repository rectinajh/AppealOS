import datetime as dt
import unittest

from app.domain import (
    DEVICE_LOG_FIXTURE,
    DEVICE_LOG_SHA256,
    EVIDENCE_ARTIFACTS,
    AnalysisConsent,
    AppealMandate,
    canonicalize,
    sha256_canonical,
)


class DeviceLogFixtureTest(unittest.TestCase):
    def test_device_log_hash_matches_mockdrop(self):
        self.assertEqual(sha256_canonical(DEVICE_LOG_FIXTURE), DEVICE_LOG_SHA256)

    def test_canonicalization_matches_mockdrop_js_vector(self):
        self.assertEqual(
            canonicalize({"b": 2, "a": [1, {"c": 3}]}),
            '{"a":[1,{"c":3}],"b":2}',
        )


class ConsentMandateGuardTest(unittest.TestCase):
    def test_consent_rejects_unknown_artifact(self):
        now = dt.datetime.now(dt.timezone.utc)
        with self.assertRaises(ValueError):
            AnalysisConsent.create("case-1", ["not-an-artifact"], now)

    def test_mandate_blocks_second_supplement_cycle(self):
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        mandate = AppealMandate(
            mandateId="mandate-1",
            caseId="case-1",
            destinationAdapter="mockdrop",
            destinationAccountId="rider-r-2048",
            approvedClaimIds=["claim-1"],
            allowedActions=["SUBMIT", "SUPPLEMENT", "POLL", "VERIFY"],
            approvedArtifactIds=list(EVIDENCE_ARTIFACTS),
            allowedSupplementTemplate="DEVICE_NETWORK_HANDOFF_V1",
            maxSupplementCycles=1,
            supplementCyclesUsed=1,
            approvedAt=now,
            expiresAt=now,
        )
        self.assertFalse(mandate.can_supplement())


if __name__ == "__main__":
    unittest.main()
