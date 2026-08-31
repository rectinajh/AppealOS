import base64
import json
import unittest

from app.domain import (
    EVIDENCE_ARTIFACTS,
    AnalysisConsent,
    AppealMandate,
    DemoCase,
)
from app.pubsub import PubSubMessageError, decode_push_message
from app.store import InMemoryCaseStore


def make_case():
    case = DemoCase()
    case.record("DEMO_RESET", "SYSTEM", {"account": {"accountId": case.accountId}})
    case.consent = AnalysisConsent(
        consentId="consent-1",
        caseId=case.caseId,
        artifactIds=list(EVIDENCE_ARTIFACTS),
        purposes=["TIMELINE", "POLICY_MATCH", "DRAFT_CLAIMS"],
        allowGeminiProcessing=True,
        approvedAt="2026-08-18T00:00:00+00:00",
        expiresAt="2026-08-18T01:00:00+00:00",
    )
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
        approvedAt="2026-08-18T00:00:00+00:00",
        expiresAt="2026-08-18T01:00:00+00:00",
    )
    case.platformReceipts.append({"receiptId": "receipt-1"})
    case.record("MANDATE_APPROVED", "USER", {}, "MANDATE_APPROVED")
    return case


class DemoCaseRoundTripTest(unittest.TestCase):
    def test_persistable_round_trip_preserves_mandate_and_events(self):
        case = make_case()
        restored = DemoCase.from_persistable(case.to_persistable())
        self.assertEqual(restored.caseId, case.caseId)
        self.assertEqual(restored.mandate.mandateId, "mandate-1")
        self.assertEqual(restored.mandate.allowedSupplementTemplate, "DEVICE_NETWORK_HANDOFF_V1")
        self.assertEqual(len(restored.timeline), len(case.timeline))
        self.assertEqual(restored.platformReceipts[0]["receiptId"], "receipt-1")

    def test_in_memory_store_round_trip(self):
        store = InMemoryCaseStore()
        case = make_case()
        store.save(case)
        restored = store.get(case.caseId)
        self.assertEqual(restored.mandate.mandateId, "mandate-1")
        self.assertEqual(len(restored.timeline), 2)


class PubSubDecodeTest(unittest.TestCase):
    def test_decode_supplement_event(self):
        event = {
            "externalEventId": "event-1",
            "type": "SUPPLEMENT_REQUESTED",
            "caseId": "case-1",
            "appealId": "appeal-1",
            "accountId": "rider-r-2048",
        }
        encoded = base64.b64encode(json.dumps(event).encode()).decode()
        payload = {"message": {"messageId": "msg-1", "data": encoded}}
        decoded, message_id = decode_push_message(payload)
        self.assertEqual(message_id, "msg-1")
        self.assertEqual(decoded["type"], "SUPPLEMENT_REQUESTED")

    def test_decode_rejects_invalid_json(self):
        encoded = base64.b64encode(b"not-json").decode()
        payload = {"message": {"messageId": "msg-1", "data": encoded}}
        with self.assertRaises(PubSubMessageError):
            decode_push_message(payload)


if __name__ == "__main__":
    unittest.main()
