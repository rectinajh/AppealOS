# AppealOS ADK rescue runtime

Python FastAPI service that runs the AppealOS binding demo and a real Google ADK root agent (`appeal_runtime_agent`) over **Gemini 3.5 Flash**.

Deterministic domain code owns every state transition, mandate guard, idempotency key, and external MockDrop write. Gemini/ADK is called only for notice extraction, evidence relevance, and claim drafting.

## Hosted workspace

Deployed case workspace: https://appealos-agrdlgr4ea-uc.a.run.app/

## What is implemented

- FastAPI service with a single ADK root agent (`google-adk==2.8.0`).
- Real Vertex AI calls to `gemini-3.5-flash` at the `global` endpoint.
- End-to-end flow: reset → notice → consent → mandate → submit → supplement → verify `ACTIVE`.
- Deterministic notice validation, citation validation, mandate scope, supplement cycle guard, and direct account-state verification.
- Typed HTTP adapter for the deployed/local MockDrop service.
- JSON stdout logs recording every Gemini/ADK call and MockDrop HTTP request.
- A polished, dark glassmorphism single-page case workspace UI at `/` with an animated status timeline, two-step confirm states, loading/success motion, expandable evidence cards, and outcome export. No external CDN or framework is used, so the workspace works offline from the Cloud Run origin.

## Run locally

Prerequisites: Python 3.12+ and `gcloud` authenticated to a project with Vertex AI enabled.

```bash
cd apps/appealos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Use the deployed MockDrop (recommended):
export MOCKDROP_BASE_URL=https://mockdrop-agrdlgr4ea-uc.a.run.app
# Optional for local MockDrop instead:
# export MOCKDROP_BASE_URL=http://localhost:8080

python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Then open the case workspace at http://localhost:8080/ or run the full binding demo:

```bash
curl -X POST http://localhost:8080/demo/run -H 'content-type: application/json'
```

Expected final state: `ACCOUNT_ACTIVE`.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Single-page case workspace UI |
| `GET` | `/health`, `/healthz` | Health check |
| `POST` | `/demo/reset` | Reset synthetic rider and case |
| `POST` | `/demo/notice` | ADK/Gemini notice extraction |
| `POST` | `/demo/consent` | Grant scoped analysis consent |
| `POST` | `/demo/mandate` | Draft claims and approve appeal mandate |
| `POST` | `/demo/submit` | Submit the initial appeal to MockDrop |
| `POST` | `/demo/supplement` | Submit the authorized device-log supplement |
| `POST` | `/demo/verify` | Directly verify MockDrop account is `ACTIVE` |
| `POST` | `/demo/run` | Run the entire binding flow in one request |
| `GET` | `/demo/case` | Read current case state and timeline |
| `GET` | `/demo/evidence` | Read model/evidence config and MockDrop URL |

## Env vars

| Variable | Default | Purpose |
|---|---|---|
| `MOCKDROP_BASE_URL` | `http://localhost:8080` | MockDrop origin |
| `MOCKDROP_API_TOKEN` | empty | Optional bearer token for MockDrop writes |
| `GOOGLE_CLOUD_PROJECT` | `boxwood-scope-364905` | Vertex AI project |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI region |
| `GEMINI_MODEL_ID` | `gemini-3.5-flash` | Eligible Gemini model |
| `GEMINI_API_KEY` | empty | Optional Gemini Developer API key; otherwise Vertex AI ADC/gcloud auth |
