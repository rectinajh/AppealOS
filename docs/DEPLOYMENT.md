# AppealOS Cloud Run deployment evidence

Issue: CMP-16 — MockDrop + AppealOS ADK rescue runtime deployed to Google Cloud.

Follow-up: CMP-21 — Firestore persistence implemented and verified; Pub/Sub supplement delivery implemented behind flags, not yet deployed.

Current deploy: CMP-25 — latest `6b891aa` source redeployed to Cloud Run after review and optimization.

## Live origins

| Service | Cloud Run URL | Region | Project |
|---|---|---|---|
| MockDrop | https://mockdrop-agrdlgr4ea-uc.a.run.app | us-central1 | boxwood-scope-364905 |
| AppealOS | https://appealos-606769518273.us-central1.run.app | us-central1 | boxwood-scope-364905 |

Project number: `606769518273`. Both services are `generation 1`, serving 100% of traffic.

`gcloud run deploy` reports MockDrop as `https://mockdrop-606769518273.us-central1.run.app`; `gcloud run services describe` reports the canonical `https://mockdrop-agrdlgr4ea-uc.a.run.app`. Both URLs resolve to the same service.

Latest verified revisions (2026-09-01):

- AppealOS: `appealos-00004-9cb`, `https://appealos-606769518273.us-central1.run.app`
- MockDrop: `mockdrop-00003-77m`, `https://mockdrop-agrdlgr4ea-uc.a.run.app` (deploy alias `https://mockdrop-606769518273.us-central1.run.app`)

AppealOS serves the upgraded dark glassmorphism case workspace UI at `/` with `APPEALOS_STORE_BACKEND=firestore`. The UI is self-contained (inline CSS/JS/SVG) with animated flow controls, status timeline, confirm/loading/success interactions, expandable evidence cards, and outcome export; it uses no external CDN or framework.

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
  --no-cpu-throttling
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
  --set-env-vars=MOCKDROP_BASE_URL=https://mockdrop-606769518273.us-central1.run.app,GOOGLE_CLOUD_PROJECT=boxwood-scope-364905,GOOGLE_CLOUD_LOCATION=global,APPEALOS_STORE_BACKEND=firestore
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

## Pub/Sub supplement delivery (CMP-21)

MockDrop publishes `SUPPLEMENT_REQUESTED` and decision events through `apps/mockdrop/src/pubsub.js` when `MOCKDROP_PUBSUB_ENABLED=true` and `MOCKDROP_PUBSUB_TOPIC` is set. AppealOS exposes `POST /events/pubsub` in `apps/appealos/app/pubsub.py` and `apps/appealos/app/main.py`; it decodes the push message, deduplicates on `externalEventId`, reloads the case from Firestore, submits the allowed supplement, then verifies `ACTIVE` with a direct `GET /v1/accounts`.

Status: code complete and covered by local unit tests; not yet deployed to Cloud Run and not yet wired to the live `mockdrop-platform-events` topic. OIDC push verification is optional via `PUBSUB_VERIFY_OIDC=true` + `PUBSUB_AUDIENCE`; it remains planned for the deployed revision.

## Not implemented / planned

- Firestore persistence for MockDrop (its API still uses the in-memory store; AppealOS Firestore is deployed and verified).
- Deployed Pub/Sub delivery and OIDC service-to-service enforcement.
- Encrypted Evidence Vault, Cloud Storage, Secret Manager, Cloud Scheduler reconciler.
- Real-platform adapters; the public MVP is synthetic MockDrop data only.

Do not cite deployed Pub/Sub/OIDC or MockDrop Firestore as implemented in Devpost.

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

Pub/Sub topic wiring and OIDC enforcement remain planned, not deployed.
