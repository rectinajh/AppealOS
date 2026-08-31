import datetime as dt
import unittest
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.agent import ClaimDraftList, ClaimUnit, EvidenceRelevance, EvidenceRelevanceItem
from app.domain import (
    EVIDENCE_ARTIFACTS,
    SUPPLEMENT_TEMPLATE,
    AnalysisConsent,
    AppealMandate,
    DemoCase,
)
from app.main import DemoService, app
from app.store import InMemoryCaseStore


class FakeMockDrop:
    def reset(self):
        return {"account": {"accountId": "rider-r-2048", "status": "SUSPENDED"}}

    def submit_appeal(self, *, case_id, account_id, allegation_type, claim_ids, idempotency_key):
        return {
            "appeal": {"appealId": "appeal-1", "status": "SUPPLEMENT_REQUESTED"},
            "receipt": {"receiptId": "receipt-submit", "idempotencyKey": idempotency_key},
            "outboundEvent": {
                "externalEventId": "external-supplement-1",
                "type": "SUPPLEMENT_REQUESTED",
                "caseId": case_id,
                "accountId": account_id,
                "appealId": "appeal-1",
            },
        }

    def submit_supplement(self, *, appeal_id, artifact_sha256, template, disclosed_fields, idempotency_key):
        return {
            "appeal": {"appealId": appeal_id, "status": "APPROVED"},
            "account": {"accountId": "rider-r-2048", "status": "ACTIVE"},
            "receipt": {"receiptId": "receipt-supplement", "idempotencyKey": idempotency_key},
            "outboundEvent": {"type": "DECISION_APPROVED"},
        }

    def get_account(self, account_id):
        return {"account": {"accountId": account_id, "status": "ACTIVE"}}


class CapturingADK:
    def __init__(self):
        self.prompts = {}

    def run_structured(self, task, instruction, output_schema, prompt):
        self.prompts[task] = prompt
        if task == "relevance":
            return EvidenceRelevance(
                items=[
                    EvidenceRelevanceItem(
                        artifact_id="gps-trace",
                        relevant=True,
                        reason="The trace contains the network handoff.",
                    )
                ]
            )
        if task == "claims":
            return ClaimDraftList(
                claims=[
                    ClaimUnit(
                        claim_type="OBSERVED_EVENT",
                        text="The GPS trace records the handoff.",
                        evidence_artifact_ids=["gps-trace"],
                        policy_clause_ids=["POLICY-LOCATION-1"],
                        confidence=0.97,
                    )
                ]
            )
        raise AssertionError(f"Unexpected task {task}")


class EscapingRelevanceADK(CapturingADK):
    def run_structured(self, task, instruction, output_schema, prompt):
        if task == "relevance":
            return EvidenceRelevance(
                items=[
                    EvidenceRelevanceItem(
                        artifact_id="device-log",
                        relevant=True,
                        reason="Not authorized for this case.",
                    )
                ]
            )
        return super().run_structured(task, instruction, output_schema, prompt)


def authorized_case(*, artifact_ids=None, state="MANDATE_APPROVED"):
    now = dt.datetime.now(dt.timezone.utc)
    artifacts = artifact_ids or list(EVIDENCE_ARTIFACTS)
    case = DemoCase()
    case.consent = AnalysisConsent.create(case.caseId, artifacts, now)
    case.claims = [
        {
            "claimId": "claim-1",
            "claimType": "OBSERVED_EVENT",
            "text": "The active delivery overlaps the network handoff.",
            "evidence": [{"artifactId": artifacts[0]}],
            "policyClauseIds": ["POLICY-LOCATION-1"],
            "confidence": 0.98,
            "validator": "CITATION_VALID",
        }
    ]
    case.mandate = AppealMandate(
        mandateId="mandate-1",
        caseId=case.caseId,
        destinationAdapter="mockdrop",
        destinationAccountId=case.accountId,
        approvedClaimIds=["claim-1"],
        allowedActions=["SUBMIT", "SUPPLEMENT", "POLL", "VERIFY"],
        approvedArtifactIds=artifacts,
        allowedSupplementTemplate=SUPPLEMENT_TEMPLATE,
        maxSupplementCycles=1,
        supplementCyclesUsed=0,
        approvedAt=now.isoformat(),
        expiresAt=(now + dt.timedelta(hours=1)).isoformat(),
    )
    case.record("MANDATE_APPROVED", "USER", {}, state)
    return case


class AuthorizedWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryCaseStore()
        self.service = DemoService(
            adk=object(),
            mockdrop=FakeMockDrop(),
            store=self.store,
        )

    def test_one_approved_execution_reaches_active(self):
        case = authorized_case()
        self.store.save(case)

        result = self.service.execute_authorized(case.caseId)

        self.assertEqual(result["final_state"], "ACCOUNT_ACTIVE")
        restored = self.store.get(case.caseId)
        self.assertEqual(restored.state, "ACCOUNT_ACTIVE")
        self.assertEqual(restored.mandate.supplementCyclesUsed, 1)
        self.assertEqual(
            [event["type"] for event in restored.timeline][-5:],
            [
                "APPEAL_SUBMITTED",
                "SUPPLEMENT_REQUESTED",
                "SUPPLEMENT_SUBMITTED",
                "DECISION_APPROVED",
                "ACCOUNT_STATUS_ACTIVE",
            ],
        )

    def test_authorized_execution_resumes_after_submit(self):
        case = authorized_case()
        self.store.save(case)
        self.service.submit(case.caseId)

        result = self.service.execute_authorized(case.caseId)

        self.assertEqual(result["final_state"], "ACCOUNT_ACTIVE")
        self.assertNotIn("submit", result["steps"])
        self.assertIn("supplement", result["steps"])

    def test_completed_execution_is_idempotent(self):
        case = authorized_case()
        self.store.save(case)
        self.service.execute_authorized(case.caseId)

        replay = self.service.execute_authorized(case.caseId)

        self.assertEqual(replay["final_state"], "ACCOUNT_ACTIVE")
        self.assertEqual(replay["steps"], {})

    def test_pubsub_supplement_event_executes_and_deduplicates(self):
        case = authorized_case()
        self.store.save(case)
        submitted = self.service.submit(case.caseId)
        event = {
            "externalEventId": "external-supplement-1",
            "type": "SUPPLEMENT_REQUESTED",
            "caseId": case.caseId,
            "accountId": case.accountId,
            "appealId": submitted["appeal"]["appealId"],
        }

        first = self.service.handle_platform_event(event)
        replay = self.service.handle_platform_event(event)

        self.assertEqual(first["finalState"], "ACCOUNT_ACTIVE")
        self.assertFalse(first["duplicate"])
        self.assertTrue(replay["duplicate"])

    def test_pubsub_supplement_event_is_state_idempotent_after_execution(self):
        case = authorized_case()
        self.store.save(case)
        completed = self.service.execute_authorized(case.caseId)
        event = {
            "externalEventId": "external-supplement-late-1",
            "type": "SUPPLEMENT_REQUESTED",
            "caseId": case.caseId,
            "accountId": case.accountId,
            "appealId": completed["case"]["appealId"],
        }

        result = self.service.handle_platform_event(event)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["finalState"], "ACCOUNT_ACTIVE")
        restored = self.store.get(case.caseId)
        self.assertEqual(
            [item["type"] for item in restored.timeline].count("SUPPLEMENT_SUBMITTED"),
            1,
        )

    def test_concurrent_pubsub_delivery_advances_case_once(self):
        case = authorized_case()
        self.store.save(case)
        submitted = self.service.submit(case.caseId)
        event = {
            "externalEventId": "external-concurrent-1",
            "type": "SUPPLEMENT_REQUESTED",
            "caseId": case.caseId,
            "accountId": case.accountId,
            "appealId": submitted["appeal"]["appealId"],
        }

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(self.service.handle_platform_event, [event, event]))

        self.assertEqual(sum(result["duplicate"] for result in results), 1)
        restored = self.store.get(case.caseId)
        self.assertEqual(restored.state, "ACCOUNT_ACTIVE")
        self.assertEqual(
            [item["type"] for item in restored.timeline].count("SUPPLEMENT_SUBMITTED"),
            1,
        )

    def test_pubsub_decision_event_is_acknowledged_after_verified_state(self):
        case = authorized_case()
        self.store.save(case)
        completed = self.service.execute_authorized(case.caseId)
        event = {
            "externalEventId": "external-decision-1",
            "type": "DECISION_APPROVED",
            "caseId": case.caseId,
            "accountId": case.accountId,
            "appealId": completed["case"]["appealId"],
        }

        result = self.service.handle_platform_event(event)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["finalState"], "ACCOUNT_ACTIVE")

    def test_supplement_cannot_disclose_unapproved_device_log(self):
        case = authorized_case(artifact_ids=["gps-trace"], state="SUPPLEMENT_REQUESTED")
        case.appealId = "appeal-1"
        self.store.save(case)

        with self.assertRaises(HTTPException) as raised:
            self.service.supplement(case.caseId)

        self.assertIn("device-log", raised.exception.detail)

    def test_execute_rejects_case_before_mandate_approval(self):
        case = DemoCase()
        case.record("PARSE_SUCCEEDED", "AGENT", {}, "PARSED")
        self.store.save(case)
        with self.assertRaises(HTTPException) as raised:
            self.service.execute_authorized(case.caseId)
        self.assertIn("mandate approval", raised.exception.detail)

    def test_mandate_sends_only_consented_evidence_to_gemini(self):
        capturing_adk = CapturingADK()
        service = DemoService(
            adk=capturing_adk,
            mockdrop=FakeMockDrop(),
            store=self.store,
        )
        now = dt.datetime.now(dt.timezone.utc)
        case = DemoCase()
        case.consent = AnalysisConsent.create(case.caseId, ["gps-trace"], now)
        case.record("ANALYSIS_CONSENT_APPROVED", "USER", {}, "CONSENTED")
        self.store.save(case)

        service.mandate(case.caseId)

        self.assertIn('"artifactId": "gps-trace"', capturing_adk.prompts["relevance"])
        self.assertNotIn('"artifactId": "device-log"', capturing_adk.prompts["relevance"])
        self.assertIn('"gps-trace": {', capturing_adk.prompts["claims"])
        self.assertNotIn('"device-log": {', capturing_adk.prompts["claims"])

    def test_mandate_rejects_relevance_outside_consent_scope(self):
        service = DemoService(
            adk=EscapingRelevanceADK(),
            mockdrop=FakeMockDrop(),
            store=self.store,
        )
        now = dt.datetime.now(dt.timezone.utc)
        case = DemoCase()
        case.consent = AnalysisConsent.create(case.caseId, ["gps-trace"], now)
        case.record("ANALYSIS_CONSENT_APPROVED", "USER", {}, "CONSENTED")
        self.store.save(case)

        with self.assertRaises(HTTPException) as raised:
            service.mandate(case.caseId)

        self.assertIn("exactly once", raised.exception.detail)

    def test_pubsub_event_rejects_case_binding_mismatch(self):
        case = authorized_case()
        self.store.save(case)
        submitted = self.service.submit(case.caseId)
        event = {
            "externalEventId": "external-mismatch-1",
            "type": "SUPPLEMENT_REQUESTED",
            "caseId": case.caseId,
            "accountId": "another-account",
            "appealId": submitted["appeal"]["appealId"],
        }
        with self.assertRaises(HTTPException) as raised:
            self.service.handle_platform_event(event)
        self.assertIn("does not match", raised.exception.detail)

    def test_pubsub_decision_retries_until_verified_state(self):
        case = authorized_case()
        self.store.save(case)
        submitted = self.service.submit(case.caseId)
        event = {
            "externalEventId": "external-decision-early",
            "type": "DECISION_APPROVED",
            "caseId": case.caseId,
            "accountId": case.accountId,
            "appealId": submitted["appeal"]["appealId"],
        }
        with self.assertRaises(HTTPException) as raised:
            self.service.handle_platform_event(event)
        self.assertIn("arrived before", raised.exception.detail)

    def test_case_can_be_resumed_by_id_in_new_service_instance(self):
        case = authorized_case()
        self.store.save(case)
        restarted = DemoService(adk=object(), mockdrop=FakeMockDrop(), store=self.store)
        self.assertEqual(restarted.require_case(case.caseId).mandate.mandateId, "mandate-1")

    def test_pubsub_route_is_exposed(self):
        self.assertIn("/events/pubsub", {route.path for route in app.routes})

    def test_health_exposes_runtime_evidence(self):
        response = TestClient(app).get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["geminiModel"], "gemini-3.5-flash")
        self.assertEqual(response.json()["googleAdkVersion"], "2.8.0")

    def test_pubsub_route_rejects_invalid_envelope(self):
        response = TestClient(app).post("/events/pubsub", json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
