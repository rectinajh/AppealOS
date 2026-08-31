"""Durable and in-memory case stores for the AppealOS demo runtime.

Firestore is the workflow authority in deployed environments.  Local smoke
tests and environments without GCP configuration default to the in-memory
store so the demo remains runnable without cloud setup.
"""

from __future__ import annotations

import copy
import datetime as _dt
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

from .domain import DemoCase

LOGGER = logging.getLogger("appealos.store")

STORE_BACKEND = os.getenv("APPEALOS_STORE_BACKEND", "memory").strip().lower()
FIRESTORE_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")
CASES_COLLECTION = os.getenv("FIRESTORE_CASES_COLLECTION", "cases")
EVENTS_COLLECTION = os.getenv("FIRESTORE_EVENTS_COLLECTION", "events")
PROCESSED_EVENTS_COLLECTION = os.getenv(
    "FIRESTORE_PROCESSED_EVENTS_COLLECTION", "processed_platform_events"
)


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


class CaseStore(Protocol):
    backend: str

    def save(self, case: DemoCase) -> None:
        """Persist the case snapshot and its ordered event timeline."""

    def get(self, case_id: str) -> Optional[DemoCase]:
        """Load a persisted case, including its event timeline."""

    def delete(self, case_id: str) -> None:
        """Remove a case and its events."""

    def is_external_event_processed(self, external_event_id: str) -> bool:
        """Return True when the external event id has already been consumed."""

    def mark_external_event_processed(self, external_event_id: str) -> bool:
        """Atomically record an external event id; return True when it is new."""


class InMemoryCaseStore:
    backend = "memory"

    def __init__(self) -> None:
        self.cases: Dict[str, DemoCase] = {}
        self.processed_event_ids: set[str] = set()

    def save(self, case: DemoCase) -> None:
        self.cases[case.caseId] = copy.deepcopy(case)

    def get(self, case_id: str) -> Optional[DemoCase]:
        case = self.cases.get(case_id)
        return copy.deepcopy(case) if case else None

    def delete(self, case_id: str) -> None:
        self.cases.pop(case_id, None)

    def is_external_event_processed(self, external_event_id: str) -> bool:
        return external_event_id in self.processed_event_ids

    def mark_external_event_processed(self, external_event_id: str) -> bool:
        if external_event_id in self.processed_event_ids:
            return False
        self.processed_event_ids.add(external_event_id)
        return True


class FirestoreCaseStore:
    """Persist the demo case as one document and events as a subcollection."""

    backend = "firestore"

    def __init__(self) -> None:
        # Imported lazily so local unit tests can run without GCP packages.
        try:
            from google.cloud import firestore  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "APPEALOS_STORE_BACKEND=firestore requires google-cloud-firestore"
            ) from exc

        kwargs: Dict[str, str] = {}
        if FIRESTORE_PROJECT:
            kwargs["project"] = FIRESTORE_PROJECT
        if FIRESTORE_DATABASE:
            kwargs["database"] = FIRESTORE_DATABASE
        self._client = firestore.Client(**kwargs)

    def _case_ref(self, case_id: str):
        return self._client.collection(CASES_COLLECTION).document(case_id)

    def _events_ref(self, case_id: str):
        return self._case_ref(case_id).collection(EVENTS_COLLECTION)

    def save(self, case: DemoCase) -> None:
        payload = case.to_persistable()
        events: List[Dict[str, Any]] = payload.pop("timeline", [])
        self._case_ref(case.caseId).set(payload, merge=False)

        batch = self._client.batch()
        for event in events:
            batch.set(self._events_ref(case.caseId).document(event["eventId"]), event)
        batch.commit()

    def get(self, case_id: str) -> Optional[DemoCase]:
        snapshot = self._case_ref(case_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        ordered_events = (
            self._events_ref(case_id)
            .order_by("caseVersion", direction="ASCENDING")
            .stream()
        )
        payload["timeline"] = [event.to_dict() for event in ordered_events]
        return DemoCase.from_persistable(payload)

    def delete(self, case_id: str) -> None:
        events = self._events_ref(case_id).stream()
        batch = self._client.batch()
        for event in events:
            batch.delete(event.reference)
        batch.delete(self._case_ref(case_id))
        batch.commit()

    def is_external_event_processed(self, external_event_id: str) -> bool:
        ref = self._client.collection(PROCESSED_EVENTS_COLLECTION).document(external_event_id)
        return ref.get().exists

    def mark_external_event_processed(self, external_event_id: str) -> bool:
        from google.api_core import exceptions as api_exceptions  # type: ignore

        ref = self._client.collection(PROCESSED_EVENTS_COLLECTION).document(external_event_id)
        try:
            ref.create(
                {
                    "externalEventId": external_event_id,
                    "createdAt": _utcnow(),
                }
            )
            return True
        except api_exceptions.AlreadyExists:
            return False


def build_store() -> CaseStore:
    if STORE_BACKEND == "firestore":
        LOGGER.info("store_backend", extra={"backend": "firestore"})
        return FirestoreCaseStore()
    LOGGER.info("store_backend", extra={"backend": "memory"})
    return InMemoryCaseStore()
