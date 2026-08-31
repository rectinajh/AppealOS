# Changelog

All notable changes to AppealOS are documented in this file.

## [0.2.0.0] - 2026-09-01

### Added

- Durable case recovery by `case_id`, including a hash-chained event timeline and an integrity-verification endpoint.
- A Pub/Sub push consumer with strict envelope decoding, optional Google OIDC verification, case binding, and external-event deduplication.
- One-click execution of an explicitly approved mandate: submit the appeal, answer one bounded supplement request, and verify account recovery.
- Runtime evidence in the health response for the Gemini model, Google ADK version, Cloud Run revision, store backend, and Pub/Sub OIDC mode.
- Thirty-one Python tests and seven Node HTTP tests covering authorization, recovery, concurrency, idempotency, Pub/Sub, and tamper detection.

### Changed

- Gemini receives only user-consented evidence; deterministic validators reject unsupported claims and relevance output outside that scope.
- Consent and mandates now enforce expiry, destination, artifact, action, template, and supplement-cycle constraints at every external write.
- The case workspace persists the active case identifier and resumes a partially completed authorized workflow after refresh or retry.
- CI installs the pinned AppealOS runtime and exercises the complete Python test suite instead of domain-only tests.
- Submission documentation now distinguishes implemented behavior, code-complete cloud wiring, historical deployment evidence, and planned production controls.

### Security

- Serialized all mutating demo workflows and constrained the documented Cloud Run deployment to one instance with one concurrent request.
- Rejected empty consent scopes, malformed Pub/Sub payloads, mismatched platform events, and expired or destination-mismatched mandates.
