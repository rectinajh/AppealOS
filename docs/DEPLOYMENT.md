# AppealOS Cloud Run deployment evidence

Issue: CMP-16 — MockDrop + AppealOS ADK rescue runtime deployed to Google Cloud.

Follow-up: CMP-21 — Firestore persistence implemented and verified.

Follow-up: CMP-28 — Evidence Vault implemented with Cloud Storage + Secret Manager and verified on revision `appealos-00006-7jz`.

Current deploy: CMP-27 — Pub/Sub + OIDC asynchronous supplement delivery deployed and verified on `appealos-00008-cf6` / `mockdrop-00004-6xh`, layered on the CMP-28 Evidence Vault deployment.

## Live origins

| Service | Cloud Run URL | Region | Project |
|---|---|---|---|
| MockDrop | https://mockdrop-agrdlgr4ea-uc.a.run.app | us-central1 | boxwood-scope-364905 |
| AppealOS | https://appealos-606769518273.us-central1.run.app | us-central1 | boxwood-scope-364905 |

Project number: `606769518273`. Both services are `generation 1`, serving 100% of traffic.

`gcloud run deploy` reports MockDrop as `https://mockdrop-606769518273.us-central1.run.app`; `gcloud run services describe` reports the canonical `https://mockdrop-agrdlgr4ea-uc.a.run.app`. Both URLs resolve to the same service.

Latest verified revisions (2026-09-01):

- AppealOS: `appealos-00008-cf6`, `https://appealos-606769518273.us-central1.run.app`
- MockDrop: `mockdrop-00004-6xh`, `https://mockdrop-agrdlgr4ea-uc.a.run.app` (deploy alias `https://mockdrop-606769518273.us-central1.run.app`)

AppealOS serves the upgraded dark glassmorphism case workspace UI at `/` with `APPEALOS_STORE_BACKEND=firestore` and `APPEALOS_EVIDENCE_BACKEND=gcs`. The UI is self-contained (inline CSS/JS/SVG) with animated flow controls, status timeline, confirm/loading/success interactions, expandable evidence cards, Evidence Vault metadata (ciphertext hash and storage URI), and outcome export; it uses no external CDN or framework. The evidence panel labels vault fixtures as synthetic and server-decryptable.

## Eligible model and framework

- Model: `gemini-3.5-flash`
- Backend: Vertex AI, `global` endpoint
- Google Agent Framework: Google ADK `google-adk==2.8.0`
- ADK runtime: three structured `LlmAgent` tasks for notice extraction, evidence relevance, and claim drafting

Gemini is used for notice extraction, evidence relevance, and claim drafting. Deterministic Python code owns all state transitions, mandate guards, idempotency keys, and MockDrop writes.

## Reproducible commands

MockDrop:

```bash
cd apps/mockdrop
gcloud run deploy mockdrop \
  --source . \
  --region us-central1 \
  --project boxwood-scope-364905 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi --cpu 1 \
  --min-instances 0 --max-instances 1 --concurrency 1 \
  --no-cpu-throttling \
  --service-account=mockdrop-pubsub@boxwood-scope-364905.iam.gserviceaccount.com \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=boxwood-scope-364905,MOCKDROP_PUBSUB_ENABLED=true,MOCKDROP_PUBSUB_TOPIC=mockdrop-platform-events
```

AppealOS:

```bash
cd apps/appealos
gcloud run deploy appealos \
  --source . \
  --region us-central1 \
  --project boxwood-scope-364905 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi --cpu 1 \
  --min-instances 0 --max-instances 1 --concurrency 1 \
  --no-cpu-throttling \
  --timeout 300 \
  --service-account=appealos-runtime@boxwood-scope-364905.iam.gserviceaccount.com \
  --set-env-vars=MOCKDROP_BASE_URL=https://mockdrop-606769518273.us-central1.run.app,GOOGLE_CLOUD_PROJECT=boxwood-scope-364905,GOOGLE_CLOUD_LOCATION=global,APPEALOS_STORE_BACKEND=firestore,APPEALOS_EVIDENCE_BACKEND=gcs,APPEALOS_EVIDENCE_BUCKET=appealos-evidence-vault,APPEALOS_EVIDENCE_KEY_SECRET=appealos-demo-evidence-key,PUBSUB_VERIFY_OIDC=true,PUBSUB_AUDIENCE=https://appealos-agrdlgr4ea-uc.a.run.app
```

## Verified end-to-end result for revision `appealos-00004-9cb`

The current source requires an explicit `case_id`, separate consent, and mandate approval before `/demo/run`. The full approved workflow was run against the live URL and produced `final_state: ACTIVE` with nine timeline events and hash-chain integrity `true`.

`POST /demo/run` on revision `appealos-00004-9cb` returned `final_state: ACCOUNT_ACTIVE` with this timeline:

```text
DEMO_RESET
PARSE_SUCCEEDED
ANALYSIS_CONSENT_APPROVED
MANDATE_APPROVED
APPEAL_SUBMITTED
SUPPLEMENT_REQUESTED
SUPPLEMENT_SUBMITTED
DECISION_APPROVED
ACCOUNT_STATUS_ACTIVE
```

The submitted appeal reaches `SUPPLEMENT_REQUESTED`; the authorized device-log supplement moves the appeal to `APPROVED` and the direct account-status verification confirms `ACTIVE`.

## Deploy log excerpts

MockDrop:

```text
Building using Dockerfile and deploying container to Cloud Run service [mockdrop] in project [boxwood-scope-364905] region [us-central1]
Building and deploying new service...
Validating configuration.................done
Uploading sources........................done
Building Container........................................................................................done
Setting IAM Policy..................................done
Creating Revision..................................................done
Routing traffic.....done
Service [mockdrop] revision [mockdrop-00003-77m] has been deployed and is serving 100 percent of traffic.
Service URL: https://mockdrop-606769518273.us-central1.run.app
```

AppealOS:

```text
Building using Dockerfile and deploying container to Cloud Run service [appealos] in project [boxwood-scope-364905] region [us-central1]
Building and deploying new service...
Validating configuration................done
Uploading sources........................done
Building Container........................................................................................done
Setting IAM Policy........................done
Creating Revision.................................................................................done
Routing traffic.....done
Service [appealos] revision [appealos-00004-9cb] has been deployed and is serving 100 percent of traffic.
Service URL: https://appealos-606769518273.us-central1.run.app
```

## Runtime log evidence

The AppealOS Cloud Run logs include, per demo run:

```json
{"timestamp":"2026-08-31T18:33:13Z","level":"INFO","logger":"appealos.gemini","message":"gemini_client_ready","model":"gemini-3.5-flash","project":"boxwood-scope-364905","location":"global","auth":"vertex_ai"}
{"timestamp":"2026-08-31T18:33:13Z","level":"INFO","logger":"appealos.adk","message":"adk_run_start","task":"notice","model":"gemini-3.5-flash"}
{"timestamp":"2026-08-31T18:33:13Z","level":"INFO","logger":"google_adk.google.adk.models.google_llm","message":"Sending out request, model: gemini-3.5-flash, backend: GoogleLLMVariant.VERTEX_AI, stream: False"}
{"timestamp":"2026-08-31T18:33:18Z","level":"INFO","logger":"google_adk.google.adk.models.google_llm","message":"Response received from the model."}
```

## Evidence Vault (CMP-28)

The synthetic Evidence Vault is now deployed on revision `appealos-00006-7jz`.

- Cloud Storage bucket: `gs://appealos-evidence-vault` (`evidence/{artifactId}.json`)
- Secret Manager secret: `appealos-demo-evidence-key` (32-byte demo AES key; value not committed, logged, or exposed by `/demo/evidence/vault`)
- Three artifacts: `delivery-receipt`, `gps-trace`, `device-log`
- Each envelope records `kind`, `capturedAt`, `mimeType`, `plaintextSha256`, `ciphertextSha256`, `nonceB64`, `aadCanonical`, and `storageUri`
- AppealOS decrypts in memory only after permission checks and verifies plaintext hash, ciphertext hash, and canonical AAD before citation or disclosure

Boundaries stated honestly:

- The fixtures are **synthetic** and **server-decryptable** with the demo key.
- The Vault is not zero-knowledge, not user-held custody, not immutable, and not independently verifiable.
- Managed Python does not guarantee secure memory erasure.

Least-privilege service identity:

- Cloud Run runtime service account: `appealos-runtime@boxwood-scope-364905.iam.gserviceaccount.com`
- Secret Manager access is scoped to `appealos-demo-evidence-key` (`roles/secretmanager.secretAccessor`)
- Cloud Storage access is scoped to the bucket (`roles/storage.objectViewer`)
- The service account also has project-level `roles/datastore.user` (Firestore), `roles/aiplatform.user` (Vertex AI), and `roles/logging.logWriter`

Live verification on `appealos-00006-7jz`:

- `GET /health` returned `evidenceVaultBackend: gcs`
- `GET /demo/evidence/vault` returned `status: ok` and all three artifact records with no secret value
- `POST /demo/run` completed `Reset → … → ACCOUNT_ACTIVE` with nine timeline events and `timelineIntegrity.verified: true`
- Tampering the `device-log` `ciphertextSha256` in Cloud Storage caused `POST /demo/mandate` to return `409 Evidence integrity failure ... Ciphertext hash does not match stored ciphertext`, recorded `EVIDENCE_QUARANTINED`, and blocked further citation
- The valid device-log object was restored after the controlled tamper test

## Firestore persistence (CMP-21)

AppealOS has a durable case store in `apps/appealos/app/store.py`. With `APPEALOS_STORE_BACKEND=firestore` the runtime persists one `cases/{caseId}` document and an ordered `cases/{caseId}/events/{eventId}` subcollection; the in-memory store remains the local default. This backend is deployed on revision `appealos-00004-9cb`.

Firestore layout:

```text
cases/{caseId}                                  case, consent, mandate, claims, receipts
cases/{caseId}/events/{eventId}                 ordered timeline events
processed_platform_events/{externalEventId}     Pub/Sub consumer dedupe
```

Verification performed on `boxwood-scope-364905` using a temporary collection:

- `DemoCase → to_persistable → save → get → from_persistable` round trip preserved mandate, receipts, and timeline order.
- `mark_external_event_processed` created the dedupe record once and rejected the duplicate.
- The verification documents were deleted afterwards; no demo data was left behind.

Deploy with:

```bash
gcloud run services update appealos   --project boxwood-scope-364905   --region us-central1   --set-env-vars=APPEALOS_STORE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=boxwood-scope-364905
```

## Pub/Sub supplement delivery (CMP-21 → deployed in CMP-27)

MockDrop publishes `SUPPLEMENT_REQUESTED` and decision events through `apps/mockdrop/src/pubsub.js` when `MOCKDROP_PUBSUB_ENABLED=true` and `MOCKDROP_PUBSUB_TOPIC` is set. AppealOS exposes `POST /events/pubsub` in `apps/appealos/app/pubsub.py` and `apps/appealos/app/main.py`; it decodes the push message, deduplicates on `externalEventId`, reloads the case from Firestore, submits the allowed supplement, then verifies `ACTIVE` with a direct `GET /v1/accounts`.

Status: deployed to Cloud Run on 2026-09-01 and wired to the live `mockdrop-platform-events` topic with OIDC push verification (`PUBSUB_VERIFY_OIDC=true` + `PUBSUB_AUDIENCE=https://appealos-agrdlgr4ea-uc.a.run.app`).

## Not implemented / planned

- Firestore persistence for MockDrop (its API still uses the in-memory store; AppealOS Firestore is deployed and verified).
- Cloud Scheduler reconciler.
- Real-platform adapters; the public MVP is synthetic MockDrop data only.

Do not cite MockDrop Firestore as implemented in Devpost. Deployed Pub/Sub/OIDC is verified and may be cited.

## CMP-24 UI refresh verification

On 2026-09-01 the workspace was redeployed as revision `appealos-00003-hwk`.

- `GET /` returned HTTP 200 and the new `<title>AppealOS · Case Workspace</title>` page containing `flow-progress` and `confirm-mode` markers.
- `POST /demo/run` returned `final_state=ACCOUNT_ACTIVE` with 9 timeline events.

## CMP-25 latest-source redeploy verification

On 2026-09-01 the repository `main` HEAD `6b891aa` was redeployed after a focused review.

- MockDrop revision: `mockdrop-00003-77m` at `https://mockdrop-agrdlgr4ea-uc.a.run.app` (deploy alias `https://mockdrop-606769518273.us-central1.run.app`).
- AppealOS revision: `appealos-00004-9cb` at `https://appealos-606769518273.us-central1.run.app`.
- AppealOS `GET /health` returned `{"status":"ok","revision":"appealos-00004-9cb","storeBackend":"firestore","pubsubOidcVerification":false}`.
- MockDrop `GET /health` returned `{"status":"ok","service":"mockdrop"}` on the Cloud Run revision; `/healthz` remains local-only because Cloud Run intercepts that path.
- `GET /` returned HTTP 200 and `<title>AppealOS · Case Workspace</title>`.
- `POST /demo/run` returned `final_state=ACCOUNT_ACTIVE` with nine timeline events and `timelineIntegrity.verified=true`.

Optimizations applied before deploy:

- MockDrop no longer republishes an outbound Pub/Sub event when an idempotency key is replayed.
- AppealOS Pub/Sub supplement handling now acknowledges `SUPPLEMENT_REQUESTED` when the case is already `ACCOUNT_ACTIVE` and can resume from `DECIDED_APPROVED`, preventing retry-time 409 loops after a dedupe-write failure.
- MockDrop now exposes a Cloud Run-compatible `GET /health` endpoint (in addition to the local `/healthz` path).

Pub/Sub topic wiring and OIDC enforcement were deployed and verified in CMP-27.

## CMP-27 Pub/Sub + OIDC async supplement chain verification

On 2026-09-01 the previously code-complete Pub/Sub/OIDC path was enabled in production and verified end to end.

GCP resources:

- Topic: `projects/boxwood-scope-364905/topics/mockdrop-platform-events`
- Push subscription: `projects/boxwood-scope-364905/subscriptions/appealos-mockdrop-events-push`
- Push endpoint: `https://appealos-agrdlgr4ea-uc.a.run.app/events/pubsub`
- OIDC audience: `https://appealos-agrdlgr4ea-uc.a.run.app`
- Message ordering: enabled; ack deadline: `300s`; expiration: `never`

Least-privilege identities:

- `mockdrop-pubsub@boxwood-scope-364905.iam.gserviceaccount.com` — Cloud Run runtime for MockDrop, topic-scoped `roles/pubsub.publisher`.
- `appealos-pubsub-push@boxwood-scope-364905.iam.gserviceaccount.com` — used only by Pub/Sub push OIDC token minting; the Pub/Sub service agent holds `roles/iam.serviceAccountTokenCreator` on this SA.
- `appealos-runtime@boxwood-scope-364905.iam.gserviceaccount.com` — Cloud Run runtime for AppealOS, project-level `roles/datastore.user`, `roles/aiplatform.user`, and `roles/logging.logWriter`, plus scoped Secret Manager/Storage permissions from CMP-28.

Deployed revisions:

- MockDrop: `mockdrop-00004-6xh` at `https://mockdrop-606769518273.us-central1.run.app` with `MOCKDROP_PUBSUB_ENABLED=true` and `MOCKDROP_PUBSUB_TOPIC=mockdrop-platform-events`.
- AppealOS: `appealos-00008-cf6` at `https://appealos-606769518273.us-central1.run.app` with `PUBSUB_VERIFY_OIDC=true` and `PUBSUB_AUDIENCE=https://appealos-agrdlgr4ea-uc.a.run.app`.

Live async verification:

- AppealOS `GET /health` returned `pubsubOidcVerification:true`, `storeBackend:firestore`, and `revision:appealos-00008-cf6`.
- After `reset → notice → consent → mandate → submit`, the case moved from `SUPPLEMENT_REQUESTED` to `ACCOUNT_ACTIVE` without any direct `/demo/supplement` or `/demo/verify` call; the transition was triggered by the MockDrop-published Pub/Sub event.
- Final case `case-1033b50c-cb56-4c91-b646-7f3abd19c6e6` had nine timeline events (`... SUPPLEMENT_REQUESTED, SUPPLEMENT_SUBMITTED, DECISION_APPROVED, ACCOUNT_STATUS_ACTIVE`) and `timelineIntegrity.verified:true`.

OIDC and idempotency evidence:

- Unauthenticated `POST /events/pubsub` returned HTTP 401 with `Missing bearer token on Pub/Sub push`.
- Re-publishing the same `SUPPLEMENT_REQUESTED` event (`externalEventId=event-54808994-ab9e-4401-bccf-dcc22d867e65`) to the live topic left the case at nine timeline events and `ACCOUNT_ACTIVE`; no duplicate `SUPPLEMENT_SUBMITTED`/`DECISION_APPROVED` event was recorded.

## CMP-28 Evidence Vault verification

On 2026-09-01 the Evidence Vault was seeded, deployed, and verified as revision `appealos-00006-7jz`.

- Seeded `gs://appealos-evidence-vault/evidence/{delivery-receipt,gps-trace,device-log}.json`.
- Created Secret Manager secret `appealos-demo-evidence-key` and deployed the AppealOS runtime with scoped Storage/Secret Manager permissions.
- `POST /demo/run` returned `final_state=ACCOUNT_ACTIVE`; the case had nine timeline events, an empty quarantine list, and `timelineIntegrity.verified=true`.
- Controlled tamper test: replacing the device-log `ciphertextSha256` made `POST /demo/mandate` return HTTP 409 with `Evidence integrity failure for device-log: Ciphertext hash does not match stored ciphertext`; the case recorded `EVIDENCE_QUARANTINED` and `quarantinedArtifactIds: ["device-log"]`.
