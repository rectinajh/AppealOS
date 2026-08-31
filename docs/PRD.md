# AppealOS Runtime Product Requirements

**Status:** Approved for implementation

**Version:** 0.1

**Target:** All Things Agentic Hackathon MVP

**Primary track:** The Taskmaster
**Data policy:** Synthetic fixtures only

## 1. Product summary

AppealOS is a user-owned appeal workflow runtime. It turns a platform suspension into an executable `AppealCase` that joins the notice, allegation, deadline, user-directed evidence, policy rules, scoped authorization, external actions, platform receipts, and final outcome.

The long-term category covers anyone governed by a platform algorithm. The MVP proves one complete case for a fictional delivery rider suspended for abnormal location activity.

## 2. Problem

Automated platform decisions can remove a person's ability to work, sell, create, or participate. The affected person often receives a short notice and a generic appeal form, while the information needed to respond is fragmented across email, help pages, receipts, device logs, and account history.

The current process fails because it has no durable case state:

- users cannot see which facts or policies matter;
- deadlines and supplement requests are easy to miss;
- the same context must be reconstructed repeatedly;
- platform acknowledgements are easily confused with decisions;
- users cannot tell which evidence an automated helper disclosed;
- rejection produces no portable record for a human escalation.

## 3. Product principles

1. **User direction before Agent action.** Analysis and disclosure require separate permissions.
2. **Facts before rhetoric.** Every drafted claim carries citations and a confidence result.
3. **Minimum disclosure.** A mandate limits artifact IDs, fields, time range, bytes, recipient, and action count.
4. **State over chat.** The primary interface is a case workspace and action timeline.
5. **Receipts before celebration.** Submission, acknowledgement, decision, and restored access are distinct.
6. **Failure is still an outcome.** Rejection must create a clear record, not a false success screen.
7. **No cryptographic theater.** The MVP calls its export hash-consistent, not immutable or independently authentic.

## 4. Users

### 4.1 Long-term users

- delivery riders and rideshare drivers;
- independent marketplace sellers;
- creators whose content or monetization is suspended;
- developers whose platform or API accounts are disabled;
- worker centers, creator associations, unions, and legal-aid organizations supporting those users.

### 4.2 MVP persona

**Rider R-2048** works through the fictional MockDrop platform. MockDrop suspends the account for abnormal location activity. The rider has one delivery receipt, one GPS trace, and one device log that together show a cellular-network handoff during a legitimate delivery.

## 5. Jobs to be done

When a platform suspends my account, I want to understand the allegation, assemble only the relevant facts, authorize a bounded response, and keep the process moving until I receive a clear outcome, so I can recover access or escalate without rebuilding the case from scratch.

## 6. Goals and non-goals

### Goals

- Prove an Agent can execute a multi-step appeal after one scoped mandate.
- Prove a real write to a separately deployed simulated platform.
- Preserve citation, authorization, action, and receipt history.
- Handle one asynchronous evidence request without another prompt when it is inside the mandate.
- Verify `ACTIVE` through a direct status call after approval.
- Make every safety limitation visible to judges and users.

### Non-goals

- Real DoorDash, Uber, TikTok, Amazon, GitHub, or other platform integration.
- Legal advice, legal representation, or guaranteed reinstatement.
- General-purpose browser automation or arbitrary email submission.
- Multiple platforms, policies, allegation types, languages, or jurisdictions.
- Production identity, multitenancy, billing, mobile apps, or organization workspaces.
- Blockchain or Filecoin anchoring.
- A zero-knowledge or exclusively user-held encryption design.
- Free-form real-user evidence uploads in the public MVP.

## 7. Binding MVP scenario

1. Reset MockDrop so Rider R-2048 is `SUSPENDED` for `ABNORMAL_LOCATION`.
2. Select the packaged synthetic suspension notice.
3. Gemini extracts the allegation, incident window, deadline, and missing procedural records into a typed result.
4. The user grants an `AnalysisConsent` for three named synthetic artifacts.
5. AppealOS constructs a timeline from one delivery receipt, one GPS trace, and one device log.
6. The Agent matches the timeline to one frozen MockDrop policy profile.
7. AppealOS generates structured claim units with artifact spans and policy citations.
8. The user approves an `AppealMandate` covering one recipient, the named claims, the three evidence rules, one supplement cycle, polling, verification, and a 72-hour expiry.
9. The Agent submits the initial appeal to MockDrop using authenticated HTTP and an idempotency key.
10. MockDrop accepts the appeal, returns a durable receipt, and publishes one supplement request through Pub/Sub.
11. AppealOS recognizes that the requested device log and explanation template are already authorized, then submits the supplement automatically.
12. MockDrop changes the appeal to `APPROVED` and the rider account to `ACTIVE`.
13. AppealOS performs a separate account-status request and closes the case only after directly observing `ACTIVE`.
14. The user downloads a redacted, hash-consistent `DueProcessAuditExport`.

## 8. Functional requirements

Priority definitions:

- **P0:** required for the four-minute deployed demonstration.
- **P1:** required for the full 48-hour build but may be deferred from the rescue build.
- **P2:** post-hackathon.

### FR-01: Demo reset and ownership — P0

The user can start from a known synthetic case without receiving a shared secret.

Acceptance criteria:

- The browser calls only AppealOS `POST /demo/reset`.
- AppealOS resets its prior case and calls MockDrop server-to-server.
- A random owner token is stored in a secure HTTP-only cookie; only its hash is persisted.
- MockDrop ends the reset in `SUSPENDED` with a monotonically increasing account version.

### FR-02: Structured notice intake — P0

The system parses only the allowlisted synthetic notice fixture.

Acceptance criteria:

- The result includes allegation type, source text, source timezone, normalized UTC deadline, incident window, and confidence.
- A missing or conflicting allegation/deadline produces `NEEDS_USER_REVIEW`.
- Notice text is treated as untrusted data and cannot cause a tool call.

### FR-03: Analysis consent — P0

The user must authorize internal evidence processing separately from platform disclosure.

Acceptance criteria:

- Consent names artifact IDs and purposes: timeline, policy match, and draft claims.
- Consent records approval and expiry.
- Consent alone cannot invoke MockDrop or disclose evidence.
- Revocation blocks new internal artifact reads.

### FR-04: Evidence Vault prototype — P0

The case contains exactly one delivery receipt, one GPS trace, and one device log.

Acceptance criteria:

- Each artifact has a kind, capture time, plaintext hash, ciphertext hash, nonce, AAD, MIME type, and storage URI.
- Ciphertext is stored in Cloud Storage; the synthetic demo key is stored in Secret Manager.
- The UI labels the Vault as synthetic and server-decryptable.
- A hash mismatch quarantines the artifact and blocks citation or disclosure.

### FR-05: Citation-backed timeline — P0

AppealOS must produce ordered facts without claiming semantic certainty it cannot prove.

Acceptance criteria:

- Every claim references an artifact ID, plaintext hash, and exact source span.
- Deterministic code validates citation integrity only.
- Causal claims and low-confidence semantic claims require user confirmation.
- Product copy uses “verified” only for hashes, authorization guards, receipts, and external state.

### FR-06: Versioned policy profile — P0

The case uses one frozen MockDrop policy profile.

Acceptance criteria:

- The profile records version, capture time, source URL, source hash, jurisdiction label, and clause IDs.
- Every policy statement in the appeal points to a clause ID.
- Policy text is untrusted input, not Agent instruction.

### FR-07: Appeal Mandate — P0

The user can issue one bounded external-action authorization.

Acceptance criteria:

- The mandate names case, owner, destination adapter/account, approved claim IDs, actions, artifact IDs, evidence rules, supplement template, supplement limit, expiry, and stop conditions.
- Evidence rules use closed kinds plus field, time, byte, and redaction constraints.
- New claims, recipients, evidence classes, or expired authority require a new mandate.
- The UI states that revocation cannot recall an in-flight or accepted remote request.

### FR-08: Initial appeal submission — P0

The Agent can perform a real external write after mandate approval.

Acceptance criteria:

- Only the allowlisted MockDrop method and path are callable.
- The request uses Cloud Run OIDC and a stored idempotency key.
- The accepted response becomes a durable `PlatformReceipt` before the case advances.
- The accepted receipt produces separate `APPEAL_SUBMITTED` and `PLATFORM_ACKNOWLEDGED` events.

### FR-09: Asynchronous supplement — P0

The Agent can react to one Pub/Sub supplement event without another user prompt when it fits the mandate.

Acceptance criteria:

- The topic accepts publishes only from the MockDrop service identity.
- AppealOS validates Pub/Sub OIDC, message age, case/account binding, external event ID, and platform sequence.
- Replaying the same event does not produce another platform supplement.
- Any mismatch in artifact, field, time, bytes, template, cycle, or expiry moves the case to `NEEDS_USER_APPROVAL`.

### FR-10: Decision and status verification — P0

The product cannot equate approval text with restored access.

Acceptance criteria:

- `DECIDED_APPROVED` and `ACCOUNT_ACTIVE` are different states.
- A direct MockDrop account-status call must return `ACTIVE` before closure.
- Verification retries at most three times.
- Exhaustion produces a terminal unresolved failure, not success.

### FR-11: Action timeline — P0

The case page shows what happened, who acted, and what proved it.

Acceptance criteria:

- Each event records type, actor, time, correlation ID, case version, sequence, predecessor hash, and event hash.
- Platform writes link to receipt IDs and request/response hashes.
- Operational states distinguish pending, dispatching, succeeded, retryable failure, and terminal failure.
- The timeline never exposes raw evidence, keys, tokens, or complete model prompts.

### FR-12: Due Process Audit Export — P0

The user can download a canonical JSON case record.

Acceptance criteria:

- The export contains allegation, policy profile, redacted artifacts, claim units, mandate digest, events, platform receipts, final state, and chain root.
- It excludes raw evidence, coordinates, device identifiers, owner token, encryption key, secrets, and complete prompts.
- The UI describes it as hash-consistent under a trusted service boundary, not signed, immutable, or independently authentic.

### FR-13: Eligible model and ADK proof — P0

The deployed system must prove hackathon technology compliance.

Acceptance criteria:

- `/health` reports the exact eligible Gemini 3.5+ model ID, endpoint, region, and ADK version.
- A stored smoke-test result proves structured output and one typed tool invocation.
- The system never silently falls back to an ineligible model.

### FR-14: Outbox and crash reconciliation — P1

The full build can recover work lost between Firestore commit, Pub/Sub publish, and worker completion.

Acceptance criteria:

- Action creation freezes `actionCaseVersion` and idempotency key.
- A reconciler republishes stale pending and expired leased actions.
- MockDrop can look up the original receipt by idempotency key.
- Operational events do not change the business case version or action idempotency key.

### FR-15: Retention cleanup — P1

Expired demo data can be cleaned without false exact-time promises.

Acceptance criteria:

- Cases have a Firestore TTL field and artifacts have a one-day Storage lifecycle rule.
- A scheduled idempotent job removes remaining subcollections, outbox records, buffered events, and exports.
- Documentation states that TTL and lifecycle deletion are asynchronous.

### FR-16: Rejected-case export — P1

A rejected appeal still produces a usable human escalation record.

Acceptance criteria:

- The rejection reason and receipt are preserved.
- The export avoids legal conclusions and guaranteed-remedy language.
- No external escalation occurs without a new recipient-specific mandate.

## 9. State and outcome requirements

The UI must distinguish:

- `NOTICE_RECEIVED`
- `NEEDS_USER_REVIEW`
- `PARSED`
- `DRAFT_READY`
- `AWAITING_MANDATE`
- `SUBMISSION_PENDING`
- `ACKNOWLEDGED`
- `SUPPLEMENT_REQUESTED`
- `SUPPLEMENT_PENDING`
- `SUPPLEMENTED`
- `DECIDED_APPROVED`
- `DECIDED_REJECTED`
- `VERIFICATION_RETRY`
- `ACCOUNT_ACTIVE`
- `MANDATE_EXPIRED`
- `ACTION_FAILED_RETRYABLE`
- `ACTION_FAILED_TERMINAL`
- `ESCALATION_PACKET_READY`

The technical transition table is maintained in [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md#8-state-machine).

## 10. User experience requirements

### Main case workspace

The product uses one stateful case workspace rather than a generic dashboard or primary chat interface.

The information hierarchy is:

1. platform allegation, deadline, account state, and procedural gaps;
2. analysis consent, three evidence artifacts, and fact timeline;
3. policy match and grounded claim units;
4. Appeal Mandate preview and approval;
5. live action timeline and receipts;
6. explicit outcome and JSON export.

### Required empty and failure states

- fixture unavailable;
- model unavailable or ineligible;
- parse confidence too low;
- evidence hash mismatch;
- unsupported claim;
- mandate expired or revoked;
- supplement outside mandate;
- network timeout before known acceptance;
- duplicate Pub/Sub delivery;
- approval received but account remains suspended;
- rejected appeal.

## 11. Success metrics

### Hackathon proof metrics

- One approval triggers the initial write, one authorized supplement, tracking, and verification.
- The deployed MockDrop state changes from `SUSPENDED` to `ACTIVE` through authenticated external calls.
- Replaying the supplement event causes no duplicate platform action.
- Every claim has citation metadata and every external write has a receipt.
- The four-minute public video shows Gemini, ADK, Cloud Run, Pub/Sub, and the verified external state change.

### Product-learning metric

Show the deployed flow to a person who has experienced a platform restriction and ask: “At which exact step would you refuse to grant this Agent authority, and what evidence would you be unwilling to disclose?” The first post-hackathon revision must respond to that answer.

## 12. Release gates

The public demo cannot ship until:

- eligible Gemini access and ADK version are verified;
- both Cloud Run origins are deployed;
- the happy path passes from a fresh browser session;
- the supplement replay test passes;
- the expired-mandate test passes;
- no raw secrets or evidence appear in logs or exports;
- Devpost and README list only capabilities verified on the deployed revision;
- the video is no longer than four minutes;
- safety and synthetic-data statements are visible.

## 13. Delivery order

1. Prove MockDrop's manual `SUSPENDED → ACTIVE` API sequence.
2. Lock schemas, state reducer, mandate evaluator, and fixture hashes.
3. Verify the eligible Gemini model and ADK typed-tool smoke test.
4. Implement the P0 case workflow.
5. Connect the Pub/Sub supplement event and replay protection.
6. Build the approved three-stage UI.
7. Deploy and record the working path.
8. Add P1 reliability and cleanup only after the recorded P0 path is safe.

## 14. Open post-MVP questions

- Which first real group has the strongest lawful distribution path: delivery workers, sellers, creators, or developers?
- Which real platform exposes an appeal route that can be automated without violating terms or relying on fragile browser control?
- Should a worker center, creator association, or legal-aid partner maintain policy profiles?
- What signature or anchoring mechanism can add export authenticity without forcing users to understand wallets?
- Which production identity, residency, consent, and retention rules apply before real-case ingestion?
