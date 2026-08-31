# AppealOS ADK runtime

Python FastAPI service for a bounded, user-owned appeal workflow over **Gemini 3.5 Flash** and **Google ADK 2.8.0**.

Gemini/ADK performs three structured reasoning tasks: notice extraction, evidence relevance, and grounded claim drafting. Deterministic domain code owns consent, mandate authorization, state transitions, idempotency keys, MockDrop writes, and final account verification.

## What is implemented

- Real Vertex AI calls to `gemini-3.5-flash` through Google ADK `LlmAgent` runners.
- Explicit `AnalysisConsent` followed by a destination-, action-, artifact-, cycle-, and expiry-scoped `AppealMandate`.
- One authorized execution call that submits the appeal, answers one approved supplement request, and directly verifies `ACTIVE`.
- Firestore case recovery by `caseId`, with an in-memory local fallback.
- Hash-chained timeline events plus a deterministic integrity-verification endpoint.
- Synthetic Evidence Vault backed by Cloud Storage + Secret Manager with plaintext/ciphertext hash and AAD verification before citation/disclosure.
- Idempotent Pub/Sub push consumer at `POST /events/pubsub`; OIDC verification is env-gated.
- A typed HTTP adapter to MockDrop and a single-page case workspace at `/`.
- No arbitrary URL, shell, filesystem, email, recipient, or real-platform tool.

The current hosted revision is `appealos-00006-7jz` at https://appealos-606769518273.us-central1.run.app/. Check `/health` for the deployed revision, model, ADK version, storage backend, Evidence Vault backend, and Pub/Sub OIDC status.

## Run locally

Prerequisites: Python 3.12+ and `gcloud` authenticated to a project with Vertex AI enabled.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MOCKDROP_BASE_URL=https://mockdrop-606769518273.us-central1.run.app
# Optional: use the deployed Evidence Vault instead of the local fixture fallback.
export APPEALOS_EVIDENCE_BACKEND=gcs
export APPEALOS_EVIDENCE_BUCKET=appealos-evidence-vault
export APPEALOS_EVIDENCE_KEY_SECRET=appealos-demo-evidence-key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080/. The UI stores only the synthetic `caseId` in local storage so it can reload a Firestore-backed case after a Cloud Run restart.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Single-page case workspace |
| `GET` | `/health`, `/healthz` | Runtime evidence and health |
| `POST` | `/demo/reset` | Reset MockDrop and create a synthetic case |
| `POST` | `/demo/notice` | ADK/Gemini notice extraction; requires `case_id` |
| `POST` | `/demo/consent` | Grant selected-artifact analysis consent |
| `POST` | `/demo/mandate` | Draft claims and approve the bounded mandate |
| `POST` | `/demo/run` | Execute submit → supplement → verify after approval |
| `POST` | `/demo/submit`, `/demo/supplement`, `/demo/verify` | Individually test deterministic workflow steps |
| `GET` | `/demo/case/{case_id}` | Reload a persisted case |
| `GET` | `/demo/case/{case_id}/verify-timeline` | Verify its event hash chain |
| `GET` | `/demo/evidence` | Inspect synthetic evidence metadata and policy |
| `GET` | `/demo/evidence/vault` | Inspect non-secret Evidence Vault metadata |
| `POST` | `/events/pubsub` | Consume an idempotent MockDrop platform event |

`/demo/run` does **not** create consent or approve a mandate. The human boundary is explicit: reset → parse → select evidence and consent → approve mandate → execute.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MOCKDROP_BASE_URL` | `http://localhost:8080` | Fixed MockDrop origin |
| `MOCKDROP_API_TOKEN` | empty | Optional MockDrop bearer token |
| `GOOGLE_CLOUD_PROJECT` | `boxwood-scope-364905` | Vertex AI / Firestore project |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI location |
| `GEMINI_MODEL_ID` | `gemini-3.5-flash` | Gemini model |
| `GEMINI_API_KEY` | empty | Optional Developer API key; otherwise Vertex AI ADC |
| `APPEALOS_STORE_BACKEND` | `memory` | `memory` or `firestore` |
| `APPEALOS_EVIDENCE_BACKEND` | `memory` | `memory` or `gcs` |
| `APPEALOS_EVIDENCE_BUCKET` | `appealos-evidence-vault` | Cloud Storage bucket for encrypted fixtures |
| `APPEALOS_EVIDENCE_KEY_SECRET` | `appealos-demo-evidence-key` | Secret Manager demo key name |
| `PUBSUB_VERIFY_OIDC` | `false` | Require a verified bearer token on Pub/Sub pushes |
| `PUBSUB_AUDIENCE` | empty | Expected Cloud Run audience when OIDC is enabled |

## Tests

```bash
python -m unittest -v
```

The suite (37 tests) covers consent and mandate boundaries, destination/artifact enforcement, autonomous execution, case recovery, Pub/Sub decoding, Evidence Vault hash/AAD verification, tamper quarantine, and hash-chain tamper detection.
