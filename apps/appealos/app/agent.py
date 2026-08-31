"""Google ADK root agent used by the AppealOS rescue runtime.

The root agent is `appeal_runtime_agent`.  Specialized single-turn ADK agents
perform structured extraction/drafting, and deterministic domain code performs
every state transition and external write.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Type, TypeVar

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from .domain import (
    EVIDENCE_ARTIFACTS,
    POLICY_PROFILE,
)
from .gemini import GEMINI_MODEL_ID, build_vertex_client

LOGGER = logging.getLogger("appealos.adk")

T = TypeVar("T", bound=BaseModel)


class NoticeExtraction(BaseModel):
    platform: str
    account_id: str
    allegation: str
    deadline_text: str
    deadline_at: str


class EvidenceRelevanceItem(BaseModel):
    artifact_id: str
    relevant: bool
    reason: str


class EvidenceRelevance(BaseModel):
    items: List[EvidenceRelevanceItem]


class ClaimUnit(BaseModel):
    claim_id: str = Field(default="")
    claim_type: str
    text: str
    evidence_artifact_ids: List[str]
    policy_clause_ids: List[str] = Field(default_factory=list)
    confidence: float


class ClaimDraftList(BaseModel):
    claims: List[ClaimUnit]


def _lookup_evidence_fixture(artifact_id: str) -> Dict[str, Any]:
    """Read-only tool: expose one synthetic fixture by its fixed allowlisted id."""
    artifact = EVIDENCE_ARTIFACTS.get(artifact_id)
    if artifact is None:
        return {"error": f"unknown artifact {artifact_id}"}
    return {
        "artifactId": artifact["artifactId"],
        "kind": artifact["kind"],
        "capturedAt": artifact["capturedAt"],
        "plaintext": artifact["plaintext"],
    }


def _lookup_policy_clause(clause_id: str) -> Dict[str, str]:
    """Read-only tool: expose one frozen synthetic policy clause."""
    clause = POLICY_PROFILE["clauses"].get(clause_id)
    if clause is None:
        return {"error": f"unknown policy clause {clause_id}"}
    return {"clauseId": clause_id, "text": clause}


class ADKEngine:
    """Thin wrapper that runs structured ADK agents over Gemini 3.5+."""

    def __init__(self) -> None:
        self.model = Gemini(model=GEMINI_MODEL_ID, client=build_vertex_client())
        self.session_service = InMemorySessionService()
        self._agents: Dict[str, LlmAgent] = {}

    @property
    def root_agent(self) -> LlmAgent:
        """The single ADK root agent for the rescue runtime."""
        return LlmAgent(
            name="appeal_runtime_agent",
            description=(
                "AppealOS root agent. It interprets notices and drafts claims "
                "only; deterministic code authorizes actions and writes state."
            ),
            model=self.model,
            instruction=(
                "You are the AppealOS reasoning engine. You may only inspect "
                "the three fixed synthetic evidence artifacts and the frozen "
                "policy profile. Never authorize actions, compute deadlines, "
                "or declare an account active."
            ),
            tools=[_lookup_evidence_fixture, _lookup_policy_clause],
        )

    def _agent_for(
        self,
        task: str,
        instruction: str,
        output_schema: Type[T],
    ) -> LlmAgent:
        if task not in self._agents:
            self._agents[task] = LlmAgent(
                name=f"appeal_{task}",
                description=f"AppealOS structured task: {task}",
                model=self.model,
                instruction=instruction,
                output_schema=output_schema,
            )
        return self._agents[task]

    def run_structured(
        self,
        task: str,
        instruction: str,
        output_schema: Type[T],
        prompt: str,
    ) -> T:
        """Run one single-turn ADK agent and parse its structured JSON output."""
        agent = self._agent_for(task, instruction, output_schema)
        runner = Runner(
            app_name="appealos",
            agent=agent,
            session_service=self.session_service,
            auto_create_session=True,
        )
        session_id = f"{task}-{uuid.uuid4()}"
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
        LOGGER.info(
            "adk_run_start",
            extra={"task": task, "model": GEMINI_MODEL_ID, "session_id": session_id},
        )
        events = list(
            runner.run(user_id="synthetic-owner", session_id=session_id, new_message=content)
        )
        LOGGER.info(
            "adk_run_end",
            extra={"task": task, "model": GEMINI_MODEL_ID, "event_count": len(events)},
        )

        text = self._last_model_text(events, agent.name)
        payload = json.loads(_strip_code_fence(text))
        return output_schema.model_validate(payload)

    @staticmethod
    def _last_model_text(events: List[Any], author: str) -> str:
        collected: List[str] = []
        for event in events:
            if getattr(event, "author", None) != author:
                continue
            content = getattr(event, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", []) or []:
                text = getattr(part, "text", None)
                if text:
                    collected.append(text)
        if not collected:
            raise RuntimeError(f"ADK agent {author} produced no text output")
        return collected[-1]


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def notice_instruction() -> str:
    return (
        "Extract the suspension notice into the requested schema. "
        "Use only the provided text. Do not invent account identifiers."
    )


def relevance_instruction() -> str:
    return (
        "Assess each synthetic evidence artifact for the ABNORMAL_LOCATION "
        "allegation. Return one relevance item per artifact id exactly."
    )


def claims_instruction() -> str:
    return (
        "Draft grounded claim units from the supplied evidence and policy. "
        "Only cite artifact ids from the supplied inventory and clause ids "
        "from the supplied policy profile. Use claim_id '', claim_type from "
        "OBSERVED_EVENT, CAUSAL_EXPLANATION, or POLICY_REQUEST, confidence "
        "between 0 and 1, and only supported evidence_artifact_ids."
    )
