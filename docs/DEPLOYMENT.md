# AppealOS Cloud Run deployment evidence

Issue: CMP-16 — MockDrop + AppealOS ADK rescue runtime deployed to Google Cloud.

## Live origins

| Service | Cloud Run URL | Region | Project |
|---|---|---|---|
| MockDrop | https://mockdrop-agrdlgr4ea-uc.a.run.app | us-central1 | boxwood-scope-364905 |
| AppealOS | https://appealos-agrdlgr4ea-uc.a.run.app | us-central1 | boxwood-scope-364905 |

Project number: `606769518273`. Both services are `generation 1`, serving 100% of traffic.

## Eligible model and framework

- Model: `gemini-3.5-flash`
- Backend: Vertex AI, `global` endpoint
- Google Agent Framework: Google ADK `google-adk==2.8.0`
- ADK root agent: `appeal_runtime_agent`

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
  --min-instances 0 --max-instances 1 \
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
  --min-instances 0 --max-instances 1 \
  --no-cpu-throttling \
  --timeout 300 \
  --set-env-vars=MOCKDROP_BASE_URL=https://mockdrop-agrdlgr4ea-uc.a.run.app,GOOGLE_CLOUD_PROJECT=boxwood-scope-364905,GOOGLE_CLOUD_LOCATION=global
```

## Verified end-to-end result

`POST /demo/run` on the deployed AppealOS returns `final_state: ACCOUNT_ACTIVE` with the required timeline:

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
Service [mockdrop] revision [mockdrop-00001-bf7] has been deployed and is serving 100 percent of traffic.
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
Service [appealos] revision [appealos-00001-vvd] has been deployed and is serving 100 percent of traffic.
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

## Not implemented / planned

- Firestore persistence for both services (both currently use in-memory demo state).
- Pub/Sub event publication and OIDC service-to-service enforcement.
- Encrypted Evidence Vault, Cloud Storage, Secret Manager, Cloud Scheduler reconciler.
- Real-platform adapters; the public MVP is synthetic MockDrop data only.

Do not cite these planned components as implemented in Devpost.
