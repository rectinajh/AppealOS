"""AppealOS rescue runtime FastAPI service.

Exposes a deterministic demo controller and a real Google ADK root agent.
The controller calls the ADK/Gemini engine for interpretation/drafting and
MockDrop for external writes; it never lets the model authorize actions.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from functools import lru_cache, wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List, Optional

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import (
    ADKEngine,
    ClaimDraftList,
    EvidenceRelevance,
    NoticeExtraction,
    claims_instruction,
    notice_instruction,
    relevance_instruction,
)
from .domain import (
    ALLOWED_CLAIM_TYPES,
    ALLEGATION_TYPE,
    DETERMINISTIC_DEADLINE,
    DEVICE_LOG_SHA256,
    EVIDENCE_ARTIFACTS,
    POLICY_PROFILE,
    RIDER_ACCOUNT_ID,
    REQUIRED_DEVICE_LOG_FIELDS,
    SUPPLEMENT_TEMPLATE,
    SYNTHETIC_NOTICE,
    AnalysisConsent,
    AppealMandate,
    DemoCase,
    evidence_inventory,
)
from .gemini import GEMINI_MODEL_ID
from .mockdrop import MOCKDROP_BASE_URL, MockDropClient
from .pubsub import PubSubMessageError, decode_push_message, verify_push_token
from .store import STORE_BACKEND, CaseStore, build_store

LOGGER = logging.getLogger("appealos")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
            }:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


handler = logging.StreamHandler()
handler.setFormatter(JsonLogFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])


class NoticeRequest(BaseModel):
    case_id: str
    notice_text: str = SYNTHETIC_NOTICE


class ConsentRequest(BaseModel):
    case_id: str
    artifact_ids: List[str] = Field(default_factory=list)


class CaseRequest(BaseModel):
    case_id: str


def serialized_workflow(method):
    """Serialize case mutations inside the single-instance demo runtime."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._workflow_lock:
            return method(self, *args, **kwargs)

    return wrapped


class DemoService:
    def __init__(
        self,
        *,
        adk: Optional[ADKEngine] = None,
        mockdrop: Optional[MockDropClient] = None,
        store: Optional[CaseStore] = None,
    ) -> None:
        self.adk = adk or ADKEngine()
        self.mockdrop = mockdrop or MockDropClient()
        self.store = store or build_store()
        self._workflow_lock = threading.RLock()

    # ------------------------------------------------------------------
    # ADK/Gemini helpers
    # ------------------------------------------------------------------
    def extract_notice(self, notice_text: str) -> NoticeExtraction:
        return self.adk.run_structured(
            "notice",
            notice_instruction(),
            NoticeExtraction,
            notice_text,
        )

    def assess_relevance(
        self,
        notice_text: str,
        allowed_artifact_ids: List[str],
    ) -> EvidenceRelevance:
        inventory = [
            artifact
            for artifact in evidence_inventory()
            if artifact["artifactId"] in allowed_artifact_ids
        ]
        prompt = (
            "Allegation context:\n"
            f"{notice_text}\n\n"
            "User-authorized synthetic evidence inventory:\n"
            f"{json.dumps(inventory, indent=2)}\n\n"
            "Return one relevance item per artifact id."
        )
        return self.adk.run_structured(
            "relevance",
            relevance_instruction(),
            EvidenceRelevance,
            prompt,
        )

    def draft_claims(
        self,
        notice_text: str,
        allowed_artifact_ids: List[str],
    ) -> ClaimDraftList:
        authorized_evidence = {
            artifact_id: EVIDENCE_ARTIFACTS[artifact_id]
            for artifact_id in allowed_artifact_ids
        }
        prompt = (
            "Notice:\n"
            f"{notice_text}\n\n"
            "User-authorized evidence artifacts:\n"
            f"{json.dumps(authorized_evidence, indent=2)}\n\n"
            "Policy profile:\n"
            f"{json.dumps(POLICY_PROFILE, indent=2)}"
        )
        return self.adk.run_structured(
            "claims",
            claims_instruction(),
            ClaimDraftList,
            prompt,
        )

    # ------------------------------------------------------------------
    # Deterministic validators
    # ------------------------------------------------------------------
    @staticmethod
    def validate_notice(extracted: NoticeExtraction) -> Dict[str, Any]:
        if extracted.platform.strip().lower() != "mockdrop":
            raise HTTPException(status_code=422, detail="Notice platform must be mockdrop")
        if extracted.account_id.strip() != RIDER_ACCOUNT_ID:
            raise HTTPException(status_code=422, detail="Notice account id is not the synthetic rider")
        if extracted.allegation.strip().upper() != ALLEGATION_TYPE:
            raise HTTPException(status_code=422, detail="Notice allegation is not ABNORMAL_LOCATION")
        return {
            "platform": "mockdrop",
            "account_id": RIDER_ACCOUNT_ID,
            "allegation": ALLEGATION_TYPE,
            "deadline_text": extracted.deadline_text,
            "model_deadline_at": extracted.deadline_at,
            "authoritative_deadline_at": DETERMINISTIC_DEADLINE,
        }

    @staticmethod
    def validate_claims(
        claims: List[Any],
        allowed_artifact_ids: List[str],
    ) -> List[Dict[str, Any]]:
        if not claims:
            raise HTTPException(status_code=422, detail="Gemini produced no claims")
        allowed_artifacts = set(allowed_artifact_ids)
        allowed_clauses = set(POLICY_PROFILE["clauses"])
        validated: List[Dict[str, Any]] = []
        for index, claim in enumerate(claims):
            claim_type = claim.claim_type
            if claim_type not in ALLOWED_CLAIM_TYPES:
                raise HTTPException(status_code=422, detail=f"Unsupported claim type {claim_type}")
            artifact_ids = list(dict.fromkeys(claim.evidence_artifact_ids))
            if not artifact_ids or not set(artifact_ids).issubset(allowed_artifacts):
                raise HTTPException(status_code=422, detail="Claim cites an unapproved artifact")
            clause_ids = list(claim.policy_clause_ids)
            if clause_ids and not set(clause_ids).issubset(allowed_clauses):
                raise HTTPException(status_code=422, detail="Claim cites an unknown policy clause")
            if not 0 <= float(claim.confidence) <= 1:
                raise HTTPException(status_code=422, detail="Claim confidence must be between 0 and 1")
            text = claim.text.strip()
            if not text or len(text) > 2000:
                raise HTTPException(status_code=422, detail="Claim text must contain 1 to 2000 characters")
            validated.append(
                {
                    "claimId": f"claim-{index + 1}",
                    "claimType": claim_type,
                    "text": text,
                    "evidence": [{"artifactId": artifact_id} for artifact_id in artifact_ids],
                    "policyClauseIds": clause_ids,
                    "confidence": float(claim.confidence),
                    "validator": "CITATION_VALID",
                }
            )
        return validated

    @staticmethod
    def validate_relevance(
        relevance: EvidenceRelevance,
        allowed_artifact_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Reject relevance output that escapes or incompletely covers consent."""
        expected = set(allowed_artifact_ids)
        item_ids = [item.artifact_id for item in relevance.items]
        if len(item_ids) != len(set(item_ids)) or set(item_ids) != expected:
            raise HTTPException(
                status_code=422,
                detail="Gemini relevance output must cover each authorized artifact exactly once",
            )
        if any(not item.reason.strip() for item in relevance.items):
            raise HTTPException(status_code=422, detail="Gemini relevance reasons cannot be empty")
        return [item.model_dump() for item in relevance.items]

    # ------------------------------------------------------------------
    # Demo workflow steps
    # ------------------------------------------------------------------
    def _save(self, case: DemoCase) -> None:
        self.store.save(case)

    def require_case(self, case_id: str) -> DemoCase:
        case = self.store.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Case {case_id} was not found")
        return case

    @serialized_workflow
    def reset(self) -> Dict[str, Any]:
        account = self.mockdrop.reset()["account"]
        case = DemoCase()
        case.record("DEMO_RESET", "SYSTEM", {"account": account}, "NOTICE_RECEIVED")
        self._save(case)
        return {
            "case": case.to_dict(),
            "account": account,
            "mockdrop_base_url": MOCKDROP_BASE_URL,
        }

    @serialized_workflow
    def notice(self, case_id: str, notice_text: str) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "NOTICE_RECEIVED":
            raise HTTPException(status_code=409, detail=f"Expected NOTICE_RECEIVED, got {case.state}")
        extracted = self.extract_notice(notice_text)
        parsed = self.validate_notice(extracted)
        case.deadlineSourceText = notice_text
        case.deadlineAt = DETERMINISTIC_DEADLINE
        case.record(
            "PARSE_SUCCEEDED",
            "AGENT",
            {"extracted": extracted.model_dump(), "validated": parsed},
            "PARSED",
        )
        self._save(case)
        return {"case": case.to_dict(), "parsed": parsed}

    @serialized_workflow
    def consent(self, case_id: str, artifact_ids: List[str]) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "PARSED":
            raise HTTPException(status_code=409, detail=f"Expected PARSED, got {case.state}")
        try:
            consent = AnalysisConsent.create(case.caseId, artifact_ids, _utcnow())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        case.consent = consent
        case.record(
            "ANALYSIS_CONSENT_APPROVED",
            "USER",
            {"consentId": consent.consentId, "artifactIds": consent.artifactIds},
            "CONSENTED",
        )
        self._save(case)
        return {"case": case.to_dict(), "consent": consent.__dict__}

    @serialized_workflow
    def mandate(self, case_id: str) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "CONSENTED" or case.consent is None:
            raise HTTPException(status_code=409, detail="Analysis consent is required before mandate")
        if not case.consent.is_active():
            raise HTTPException(status_code=409, detail="Analysis consent has expired")
        notice_text = case.deadlineSourceText or SYNTHETIC_NOTICE
        relevance = self.assess_relevance(notice_text, case.consent.artifactIds)
        validated_relevance = self.validate_relevance(relevance, case.consent.artifactIds)
        claims_draft = self.draft_claims(notice_text, case.consent.artifactIds)
        claims = self.validate_claims(claims_draft.claims, case.consent.artifactIds)
        case.claims = claims
        mandate = AppealMandate(
            mandateId=f"mandate-{uuid.uuid4()}",
            caseId=case.caseId,
            destinationAdapter="mockdrop",
            destinationAccountId=case.accountId,
            approvedClaimIds=[claim["claimId"] for claim in claims],
            allowedActions=["SUBMIT", "SUPPLEMENT", "POLL", "VERIFY"],
            approvedArtifactIds=case.consent.artifactIds,
            allowedSupplementTemplate=SUPPLEMENT_TEMPLATE,
            maxSupplementCycles=1,
            supplementCyclesUsed=0,
            approvedAt=_utcnow().isoformat(),
            expiresAt=(_utcnow() + _timedelta(hours=1)).isoformat(),
        )
        case.mandate = mandate
        case.record(
            "MANDATE_APPROVED",
            "USER",
            {"mandateId": mandate.mandateId, "approvedClaimIds": mandate.approvedClaimIds},
            "MANDATE_APPROVED",
        )
        self._save(case)
        return {
            "case": case.to_dict(),
            "relevance": validated_relevance,
            "claims": claims,
            "mandate": {
                "mandateId": mandate.mandateId,
                "allowedActions": mandate.allowedActions,
                "approvedArtifactIds": mandate.approvedArtifactIds,
                "allowedSupplementTemplate": mandate.allowedSupplementTemplate,
                "maxSupplementCycles": mandate.maxSupplementCycles,
            },
        }

    @serialized_workflow
    def submit(self, case_id: str) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "MANDATE_APPROVED" or case.mandate is None:
            raise HTTPException(status_code=409, detail="An active mandate is required before submit")
        if not case.mandate.allows(
            "SUBMIT",
            destination_adapter=case.platform,
            destination_account_id=case.accountId,
        ):
            raise HTTPException(
                status_code=409,
                detail="Mandate is expired or does not authorize this submit destination",
            )
        claim_ids = [claim["claimId"] for claim in case.claims]
        if set(claim_ids) != set(case.mandate.approvedClaimIds):
            raise HTTPException(status_code=409, detail="Case claims differ from the approved mandate")
        response = self.mockdrop.submit_appeal(
            case_id=case.caseId,
            account_id=case.accountId,
            allegation_type=case.allegationType,
            claim_ids=claim_ids,
            idempotency_key=f"appealos:{case.caseId}:submit",
        )
        case.appealId = response["appeal"]["appealId"]
        receipt = response["receipt"]
        case.platformReceipts.append(receipt)
        case.record("APPEAL_SUBMITTED", "AGENT", {"receipt": receipt, "replayed": response.get("replayed", False)}, "ACKNOWLEDGED")
        case.record(
            "SUPPLEMENT_REQUESTED",
            "PLATFORM",
            {"outboundEvent": response.get("outboundEvent")},
            "SUPPLEMENT_REQUESTED",
        )
        self._save(case)
        return {"case": case.to_dict(), "appeal": response["appeal"], "receipt": receipt}

    @serialized_workflow
    def supplement(self, case_id: str) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "SUPPLEMENT_REQUESTED" or case.mandate is None:
            raise HTTPException(status_code=409, detail=f"Expected SUPPLEMENT_REQUESTED, got {case.state}")
        if case.consent is None or not case.consent.is_active():
            raise HTTPException(status_code=409, detail="Analysis consent is missing or expired")
        if not case.consent.allows_artifact("device-log"):
            raise HTTPException(status_code=409, detail="Consent does not authorize device-log disclosure")
        if not case.mandate.can_supplement(
            "device-log",
            SUPPLEMENT_TEMPLATE,
            destination_adapter=case.platform,
            destination_account_id=case.accountId,
        ):
            raise HTTPException(
                status_code=409,
                detail="Mandate does not authorize this supplement artifact, template, or destination",
            )
        if case.appealId is None:
            raise HTTPException(status_code=409, detail="Appeal has not been submitted")
        response = self.mockdrop.submit_supplement(
            appeal_id=case.appealId,
            artifact_sha256=DEVICE_LOG_SHA256,
            template=SUPPLEMENT_TEMPLATE,
            disclosed_fields=REQUIRED_DEVICE_LOG_FIELDS,
            idempotency_key=f"appealos:{case.caseId}:supplement",
        )
        case.mandate.supplementCyclesUsed += 1
        receipt = response["receipt"]
        case.platformReceipts.append(receipt)
        case.record(
            "SUPPLEMENT_SUBMITTED",
            "AGENT",
            {"receipt": receipt, "replayed": response.get("replayed", False)},
            "SUPPLEMENTED",
        )
        event_type = "DECISION_APPROVED" if response["appeal"]["status"] == "APPROVED" else "DECISION_REJECTED"
        next_state = "DECIDED_APPROVED" if event_type == "DECISION_APPROVED" else "DECIDED_REJECTED"
        case.record(
            event_type,
            "PLATFORM",
            {"appeal": response["appeal"], "account": response.get("account"), "outboundEvent": response.get("outboundEvent")},
            next_state,
        )
        self._save(case)
        return {"case": case.to_dict(), "appeal": response["appeal"], "account": response.get("account")}

    @serialized_workflow
    def verify(self, case_id: str) -> Dict[str, Any]:
        case = self.require_case(case_id)
        if case.state != "DECIDED_APPROVED":
            raise HTTPException(status_code=409, detail=f"Expected DECIDED_APPROVED, got {case.state}")
        if case.mandate is None or not case.mandate.allows(
            "VERIFY",
            destination_adapter=case.platform,
            destination_account_id=case.accountId,
        ):
            raise HTTPException(status_code=409, detail="Mandate does not authorize account verification")
        account = self.mockdrop.get_account(case.accountId)["account"]
        if account.get("status") != "ACTIVE":
            raise HTTPException(status_code=409, detail=f"MockDrop account is {account.get('status')}, not ACTIVE")
        case.record(
            "ACCOUNT_STATUS_ACTIVE",
            "SYSTEM",
            {"account": account, "verifiedBy": "GET /v1/accounts"},
            "ACCOUNT_ACTIVE",
        )
        self._save(case)
        return {"case": case.to_dict(), "account": account}

    @serialized_workflow
    def execute_authorized(self, case_id: str) -> Dict[str, Any]:
        """Finish or resume the platform workflow after explicit approval."""
        case = self.require_case(case_id)
        resumable_states = {
            "MANDATE_APPROVED",
            "SUPPLEMENT_REQUESTED",
            "DECIDED_APPROVED",
            "ACCOUNT_ACTIVE",
        }
        if case.state not in resumable_states:
            raise HTTPException(
                status_code=409,
                detail="Explicit consent and mandate approval are required before execution",
            )

        steps: Dict[str, Any] = {}
        if case.state == "MANDATE_APPROVED":
            submitted = self.submit(case_id)
            steps["submit"] = {
                "appealId": submitted["appeal"]["appealId"],
                "appealStatus": submitted["appeal"]["status"],
            }
            case = self.require_case(case_id)
        if case.state == "SUPPLEMENT_REQUESTED":
            supplemented = self.supplement(case_id)
            steps["supplement"] = {
                "appealStatus": supplemented["appeal"]["status"],
                "accountStatus": supplemented["account"]["status"],
            }
            case = self.require_case(case_id)
        if case.state == "DECIDED_APPROVED":
            verified = self.verify(case_id)
            steps["verify"] = verified["account"]
            case = self.require_case(case_id)
        if case.state != "ACCOUNT_ACTIVE":
            raise HTTPException(status_code=409, detail=f"Execution paused in {case.state}")
        return {
            "steps": steps,
            "case": case.to_dict(),
            "final_state": case.state,
        }

    @serialized_workflow
    def handle_platform_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        external_event_id = str(event.get("externalEventId") or "")
        case_id = str(event.get("caseId") or "")
        if not external_event_id or not case_id:
            raise HTTPException(status_code=422, detail="Platform event requires externalEventId and caseId")
        if self.store.is_external_event_processed(external_event_id):
            return {"accepted": True, "duplicate": True, "externalEventId": external_event_id}
        event_type = str(event.get("type") or "")
        supported_types = {
            "SUPPLEMENT_REQUESTED",
            "DECISION_APPROVED",
            "DECISION_REJECTED",
        }
        if event_type not in supported_types:
            raise HTTPException(status_code=422, detail="Unsupported platform event type")

        case = self.require_case(case_id)
        if event.get("accountId") != case.accountId or event.get("appealId") != case.appealId:
            raise HTTPException(status_code=409, detail="Platform event does not match the appeal case")
        if event_type == "SUPPLEMENT_REQUESTED":
            if case.state == "ACCOUNT_ACTIVE":
                result = {"appealStatus": "APPROVED", "finalState": case.state}
            elif case.state == "DECIDED_APPROVED":
                verified = self.verify(case_id)
                result = {
                    "appealStatus": "APPROVED",
                    "finalState": verified["case"]["state"],
                }
            else:
                supplemented = self.supplement(case_id)
                verified = self.verify(case_id)
                result = {
                    "appealStatus": supplemented["appeal"]["status"],
                    "finalState": verified["case"]["state"],
                }
        else:
            expected_state = (
                "ACCOUNT_ACTIVE" if event_type == "DECISION_APPROVED" else "DECIDED_REJECTED"
            )
            if case.state != expected_state:
                raise HTTPException(
                    status_code=409,
                    detail=f"Decision event arrived before case reached {expected_state}",
                )
            result = {"finalState": case.state}
        if not self.store.mark_external_event_processed(external_event_id):
            return {"accepted": True, "duplicate": True, "externalEventId": external_event_id}
        return {
            "accepted": True,
            "duplicate": False,
            "externalEventId": external_event_id,
            **result,
        }


def _utcnow():
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc)


def _timedelta(**kwargs):
    import datetime as _dt

    return _dt.timedelta(**kwargs)


@lru_cache
def get_service() -> DemoService:
    return DemoService()


app = FastAPI(title="AppealOS Runtime", version="0.2.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> Dict[str, Any]:
    try:
        adk_version = version("google-adk")
    except PackageNotFoundError:  # pragma: no cover - only for partial local installs
        adk_version = "unavailable"
    return {
        "status": "ok",
        "service": "appealos",
        "revision": os.getenv("K_REVISION", "local"),
        "geminiModel": GEMINI_MODEL_ID,
        "googleAdkVersion": adk_version,
        "storeBackend": STORE_BACKEND,
        "pubsubOidcVerification": os.getenv("PUBSUB_VERIFY_OIDC", "false").lower() == "true",
    }


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return health()


@app.post("/demo/reset")
def demo_reset() -> Dict[str, Any]:
    return get_service().reset()


@app.post("/demo/notice")
def demo_notice(request: NoticeRequest) -> Dict[str, Any]:
    return get_service().notice(request.case_id, request.notice_text)


@app.post("/demo/consent")
def demo_consent(request: ConsentRequest) -> Dict[str, Any]:
    return get_service().consent(request.case_id, request.artifact_ids)


@app.post("/demo/mandate")
def demo_mandate(request: CaseRequest) -> Dict[str, Any]:
    return get_service().mandate(request.case_id)


@app.post("/demo/submit")
def demo_submit(request: CaseRequest) -> Dict[str, Any]:
    return get_service().submit(request.case_id)


@app.post("/demo/supplement")
def demo_supplement(request: CaseRequest) -> Dict[str, Any]:
    return get_service().supplement(request.case_id)


@app.post("/demo/verify")
def demo_verify(request: CaseRequest) -> Dict[str, Any]:
    return get_service().verify(request.case_id)


@app.post("/demo/run")
def demo_run(request: CaseRequest) -> Dict[str, Any]:
    return get_service().execute_authorized(request.case_id)


@app.get("/demo/case")
def demo_case(case_id: str) -> Dict[str, Any]:
    return get_service().require_case(case_id).to_dict()


@app.get("/demo/case/{case_id}")
def demo_case_by_id(case_id: str) -> Dict[str, Any]:
    return get_service().require_case(case_id).to_dict()


@app.get("/demo/case/{case_id}/verify-timeline")
def verify_case_timeline(case_id: str) -> Dict[str, Any]:
    case = get_service().require_case(case_id)
    return {
        "caseId": case.caseId,
        "verified": case.verify_timeline(),
        "eventCount": len(case.timeline),
        "headHash": case.timeline[-1].get("eventHash") if case.timeline else None,
    }


@app.post("/events/pubsub")
def platform_event(
    payload: Dict[str, Any] = Body(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    try:
        verify_push_token(authorization)
        event, message_id = decode_push_message(payload)
    except PubSubMessageError as exc:
        status_code = 401 if "token" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    result = get_service().handle_platform_event(event)
    return {**result, "pubsubMessageId": message_id}


@app.get("/demo/evidence")
def demo_evidence() -> Dict[str, Any]:
    return {
        "model": "gemini-3.5-flash",
        "project": os.getenv("GOOGLE_CLOUD_PROJECT", "boxwood-scope-364905"),
        "location": os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
        "mockdrop_base_url": MOCKDROP_BASE_URL,
        "evidence_inventory": evidence_inventory(),
        "policy_profile": POLICY_PROFILE,
    }
