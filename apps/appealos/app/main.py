"""AppealOS rescue runtime FastAPI service.

Exposes a deterministic demo controller and a real Google ADK root agent.
The controller calls the ADK/Gemini engine for interpretation/drafting and
MockDrop for external writes; it never lets the model authorize actions.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

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
from .mockdrop import MOCKDROP_BASE_URL, MockDropClient
from .store import build_store

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
    notice_text: str = SYNTHETIC_NOTICE


class ConsentRequest(BaseModel):
    artifact_ids: Optional[List[str]] = None


class DemoService:
    def __init__(self) -> None:
        self.adk = ADKEngine()
        self.mockdrop = MockDropClient()
        self.store = build_store()
        self.case: Optional[DemoCase] = None

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

    def assess_relevance(self, notice_text: str) -> EvidenceRelevance:
        prompt = (
            "Allegation context:\n"
            f"{notice_text}\n\n"
            "Synthetic evidence inventory:\n"
            f"{json.dumps(evidence_inventory(), indent=2)}\n\n"
            "Return one relevance item per artifact id."
        )
        return self.adk.run_structured(
            "relevance",
            relevance_instruction(),
            EvidenceRelevance,
            prompt,
        )

    def draft_claims(self, notice_text: str) -> ClaimDraftList:
        prompt = (
            "Notice:\n"
            f"{notice_text}\n\n"
            "Evidence artifacts:\n"
            f"{json.dumps(EVIDENCE_ARTIFACTS, indent=2)}\n\n"
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
            artifact_ids = list(claim.evidence_artifact_ids)
            if not artifact_ids or not set(artifact_ids).issubset(allowed_artifacts):
                raise HTTPException(status_code=422, detail="Claim cites an unapproved artifact")
            clause_ids = list(claim.policy_clause_ids)
            if clause_ids and not set(clause_ids).issubset(allowed_clauses):
                raise HTTPException(status_code=422, detail="Claim cites an unknown policy clause")
            if not 0 <= float(claim.confidence) <= 1:
                raise HTTPException(status_code=422, detail="Claim confidence must be between 0 and 1")
            validated.append(
                {
                    "claimId": f"claim-{index + 1}",
                    "claimType": claim_type,
                    "text": claim.text,
                    "evidence": [{"artifactId": artifact_id} for artifact_id in artifact_ids],
                    "policyClauseIds": clause_ids,
                    "confidence": float(claim.confidence),
                    "validator": "CITATION_VALID",
                }
            )
        return validated

    # ------------------------------------------------------------------
    # Demo workflow steps
    # ------------------------------------------------------------------
    def _save(self, case: DemoCase) -> None:
        self.store.save(case)

    def require_case(self) -> DemoCase:
        if self.case is None:
            raise HTTPException(status_code=409, detail="Run /demo/reset first")
        return self.case

    def reset(self) -> Dict[str, Any]:
        account = self.mockdrop.reset()["account"]
        self.case = DemoCase()
        self.case.record("DEMO_RESET", "SYSTEM", {"account": account}, "NOTICE_RECEIVED")
        self._save(self.case)
        return {
            "case": self.case.to_dict(),
            "account": account,
            "mockdrop_base_url": MOCKDROP_BASE_URL,
        }

    def notice(self, notice_text: str) -> Dict[str, Any]:
        case = self.require_case()
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

    def consent(self, artifact_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        case = self.require_case()
        if case.state != "PARSED":
            raise HTTPException(status_code=409, detail=f"Expected PARSED, got {case.state}")
        ids = artifact_ids or list(EVIDENCE_ARTIFACTS)
        consent = AnalysisConsent.create(case.caseId, ids, _utcnow())
        case.consent = consent
        case.record("ANALYSIS_CONSENT_APPROVED", "USER", {"consentId": consent.consentId}, "CONSENTED")
        self._save(case)
        return {"case": case.to_dict(), "consent": consent.__dict__}

    def mandate(self) -> Dict[str, Any]:
        case = self.require_case()
        if case.state != "CONSENTED" or case.consent is None:
            raise HTTPException(status_code=409, detail="Analysis consent is required before mandate")
        notice_text = case.deadlineSourceText or SYNTHETIC_NOTICE
        relevance = self.assess_relevance(notice_text)
        claims_draft = self.draft_claims(notice_text)
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
            "relevance": [item.model_dump() for item in relevance.items],
            "claims": claims,
            "mandate": {
                "mandateId": mandate.mandateId,
                "allowedActions": mandate.allowedActions,
                "approvedArtifactIds": mandate.approvedArtifactIds,
                "allowedSupplementTemplate": mandate.allowedSupplementTemplate,
                "maxSupplementCycles": mandate.maxSupplementCycles,
            },
        }

    def submit(self) -> Dict[str, Any]:
        case = self.require_case()
        if case.state != "MANDATE_APPROVED" or case.mandate is None:
            raise HTTPException(status_code=409, detail="An active mandate is required before submit")
        if not case.mandate.allows("SUBMIT"):
            raise HTTPException(status_code=409, detail="Mandate does not allow SUBMIT")
        response = self.mockdrop.submit_appeal(
            case_id=case.caseId,
            account_id=case.accountId,
            allegation_type=case.allegationType,
            claim_ids=[claim["claimId"] for claim in case.claims],
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

    def supplement(self) -> Dict[str, Any]:
        case = self.require_case()
        if case.state != "SUPPLEMENT_REQUESTED" or case.mandate is None:
            raise HTTPException(status_code=409, detail=f"Expected SUPPLEMENT_REQUESTED, got {case.state}")
        if not case.mandate.can_supplement():
            raise HTTPException(status_code=409, detail="Mandate does not allow another supplement")
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

    def verify(self) -> Dict[str, Any]:
        case = self.require_case()
        if case.state != "DECIDED_APPROVED":
            raise HTTPException(status_code=409, detail=f"Expected DECIDED_APPROVED, got {case.state}")
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

    def run_all(self) -> Dict[str, Any]:
        reset = self.reset()
        notice = self.notice(SYNTHETIC_NOTICE)
        consent = self.consent()
        mandate = self.mandate()
        submitted = self.submit()
        supplemented = self.supplement()
        verified = self.verify()
        return {
            "steps": {
                "reset": reset["account"],
                "notice": notice["parsed"],
                "consent": consent["consent"],
                "mandate": {
                    "mandate": mandate["mandate"],
                    "claims": mandate["claims"],
                    "relevance": mandate["relevance"],
                },
                "submit": {
                    "appealId": submitted["appeal"]["appealId"],
                    "appealStatus": submitted["appeal"]["status"],
                },
                "supplement": {
                    "appealStatus": supplemented["appeal"]["status"],
                    "accountStatus": supplemented["account"]["status"],
                },
                "verify": verified["account"],
            },
            "case": verified["case"],
            "final_state": verified["case"]["state"],
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


app = FastAPI(title="AppealOS Runtime", version="0.1.0-rescue")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "appealos"}


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return health()


@app.post("/demo/reset")
def demo_reset() -> Dict[str, Any]:
    return get_service().reset()


@app.post("/demo/notice")
def demo_notice(request: NoticeRequest) -> Dict[str, Any]:
    return get_service().notice(request.notice_text)


@app.post("/demo/consent")
def demo_consent(request: ConsentRequest) -> Dict[str, Any]:
    return get_service().consent(request.artifact_ids)


@app.post("/demo/mandate")
def demo_mandate() -> Dict[str, Any]:
    return get_service().mandate()


@app.post("/demo/submit")
def demo_submit() -> Dict[str, Any]:
    return get_service().submit()


@app.post("/demo/supplement")
def demo_supplement() -> Dict[str, Any]:
    return get_service().supplement()


@app.post("/demo/verify")
def demo_verify() -> Dict[str, Any]:
    return get_service().verify()


@app.post("/demo/run")
def demo_run() -> Dict[str, Any]:
    return get_service().run_all()


@app.get("/demo/case")
def demo_case() -> Dict[str, Any]:
    return get_service().require_case().to_dict()


@app.get("/demo/case/{case_id}")
def demo_case_by_id(case_id: str) -> Dict[str, Any]:
    case = get_service().store.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} was not found")
    return case.to_dict()


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
