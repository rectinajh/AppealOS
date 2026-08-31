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

    def test_consent_rejects_empty_artifact_scope(self):
        now = dt.datetime.now(dt.timezone.utc)
        with self.assertRaises(ValueError):
            AnalysisConsent.create("case-1", [], now)

    def test_consent_deduplicates_scope_and_expires(self):
        now = dt.datetime.now(dt.timezone.utc)
        consent = AnalysisConsent.create("case-1", ["gps-trace", "gps-trace"], now)
        self.assertEqual(consent.artifactIds, ["gps-trace"])
        self.assertTrue(consent.is_active(now))
        self.assertFalse(consent.is_active(now + dt.timedelta(hours=2)))

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
        self.assertFalse(
            mandate.can_supplement(
                "device-log",
                "DEVICE_NETWORK_HANDOFF_V1",
                now=dt.datetime.now(dt.timezone.utc),
            )
        )

    def test_mandate_rejects_wrong_destination_and_artifact(self):
        now = dt.datetime.now(dt.timezone.utc)
        mandate = AppealMandate(
            mandateId="mandate-1",
            caseId="case-1",
            destinationAdapter="mockdrop",
            destinationAccountId="rider-r-2048",
            approvedClaimIds=["claim-1"],
            allowedActions=["SUBMIT", "SUPPLEMENT"],
            approvedArtifactIds=["gps-trace"],
            allowedSupplementTemplate="DEVICE_NETWORK_HANDOFF_V1",
            maxSupplementCycles=1,
            supplementCyclesUsed=0,
            approvedAt=now.isoformat(),
            expiresAt=(now + dt.timedelta(minutes=10)).isoformat(),
        )
        self.assertFalse(
            mandate.allows(
                "SUBMIT",
                destination_adapter="other-platform",
                destination_account_id="rider-r-2048",
                now=now,
            )
        )

    def test_expired_mandate_blocks_actions(self):
        now = dt.datetime.now(dt.timezone.utc)
        mandate = AppealMandate(
            mandateId="mandate-1",
            caseId="case-1",
            destinationAdapter="mockdrop",
            destinationAccountId="rider-r-2048",
            approvedClaimIds=["claim-1"],
            allowedActions=["SUBMIT"],
            approvedArtifactIds=["gps-trace"],
            allowedSupplementTemplate="DEVICE_NETWORK_HANDOFF_V1",
            maxSupplementCycles=1,
            supplementCyclesUsed=0,
            approvedAt=(now - dt.timedelta(hours=2)).isoformat(),
            expiresAt=(now - dt.timedelta(hours=1)).isoformat(),
        )
        self.assertFalse(
            mandate.allows(
                "SUBMIT",
                destination_adapter="mockdrop",
                destination_account_id="rider-r-2048",
                now=now,
            )
        )
        self.assertFalse(
            mandate.can_supplement(
                "device-log",
                "DEVICE_NETWORK_HANDOFF_V1",
                destination_adapter="mockdrop",
                destination_account_id="rider-r-2048",
                now=now,
            )
        )


if __name__ == "__main__":
    unittest.main()
