# AppealOS — Devpost Demo Storyboard (4:00 target)

- Video: 1280×720 MP4 (H.264 + AAC)
- Narration: English primary (macOS `Samantha` placeholder voice for now), optional Simplified Chinese subtitles
- Runtime budget: 3:30–4:00
- GCP evidence slots: reserved and replaceable once CMP-16 provides `.run.app` URL + Cloud Run / Vertex AI / Console evidence

| # | Time | Visual | Narration (English) | On-screen text |
|---|------|--------|---------------------|----------------|
| 1 | 0:00–0:08 | Cover hero: AppealOS wordmark, "A digital advocate for an algorithmic world" | "Platforms already use algorithms to judge us. AppealOS gives ordinary people a tireless digital advocate." | AppealOS · AppealOS Runtime |
| 2 | 0:08–0:38 | Problem card: suspended account notice, fragmented evidence, contextless form | "A rider, seller, creator, or developer can lose an account, income, or audience over an automated fraud signal — then has to reconstruct the allegation, policy, deadline, and evidence through a contextless form." | Problem: automated suspension + contextless appeal |
| 3 | 0:38–1:08 | Value proposition: scoped workflow, AnalysisConsent vs AppealMandate | "The missing product is not a better appeal-letter generator. It is a persistent workflow that reads the notice, inspects only user-approved evidence, builds a citation-backed timeline, then acts under one bounded mandate — and verifies a clear result." | Value: one case, scoped authority, verifiable outcome |
| 4 | 1:08–1:28 | UI screenshot 1 — case workspace: allegation, deadline, 3 evidence artifacts, consent | "Here is the case workspace. A MockDrop rider is suspended for abnormal location. AppealOS extracts the allegation and deadline, and shows exactly three synthetic evidence artifacts before any disclosure." | Demo — notice + evidence consent |
| 5 | 1:28–1:50 | UI screenshot 2 — grounded claims + Appeal Mandate preview | "The agent compiles grounded claim units with citations, then asks for one scoped Appeal Mandate: one recipient, named claims, allowed evidence, one supplement, polling, verification, 72-hour expiry." | Demo — grounded claims + mandate approval |
| 6 | 1:50–2:18 | MockDrop terminal + timeline: submit appeal, receive supplement request, auto-supplement | "After one approval, AppealOS submits to MockDrop through a typed adapter, receives an asynchronous supplement request for the device log, and supplies it automatically because it is already inside the mandate." | Demo — local MockDrop end-to-end |
| 7 | 2:18–2:36 | UI screenshot 3 — live action timeline + receipts | "Every external write produces a durable receipt. Replaying the supplement event causes no duplicate platform action." | Demo — receipts before celebration |
| 8 | 2:36–2:52 | UI screenshot 4 — outcome: ACCOUNT_ACTIVE + Due Process Audit Export | "Only after a separate status call returns ACTIVE does AppealOS close the case — and the user downloads a redacted, hash-consistent audit export." | Demo — verified outcome + export |
| 9 | 2:52–3:12 | Architecture diagram (final SVG/PNG) | "Under the hood: Cloud Run hosts the ADK runtime and UI, Gemini handles structured extraction and drafting, deterministic code enforces mandates and idempotency, Firestore holds case state, and Pub/Sub carries the supplement event from MockDrop." | Architecture — Google Cloud |
| 10 | 3:26–3:42 | GCP evidence: live Cloud Run service cards (`.run.app` URLs + revisions + 100% traffic), verified end-to-end timeline, Vertex AI runtime logs | "Here is the deployed backend on Google Cloud. AppealOS and MockDrop run as separate Cloud Run services, each serving one hundred percent of traffic. The verified demo returned ACCOUNT_ACTIVE, with Gemini ready on Vertex AI and the request path logged end-to-end." | GCP evidence — live (CMP-16) |
| 11 | 3:42–3:58 | Safety + synthetic-data disclaimer, close | "AppealOS is a synthetic proof of concept. It never promises reinstatement, and every claim stays inside user-approved scope. One approval. One authorized supplement. One verified outcome." | Synthetic data · no real platform integration |

## Recording notes

- Slides 1–3, 9–11 are static/ken-burns slide cards rendered from HTML/CSS.
- Slides 4–8 use `submission/screenshots/*.png` with subtle zoom/pan.
- GCP segment (slide 10) now uses live Cloud Run evidence from CMP-16: `.run.app` service URLs, deployed revisions, the verified `ACCOUNT_ACTIVE` timeline, and Vertex AI runtime log excerpts from `docs/DEPLOYMENT.md`.
- If engineering deploys before deadline, replace the local MockDrop terminal shots (slide 6) with the deployed `.run.app` sequence and re-render only affected segments.
