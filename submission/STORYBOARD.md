# AppealOS — Devpost Demo Storyboard (replacement recording, 3:58 target)

> The checked-in MP4 predates the one-approved-execution UI. Re-record the app-in-action segment from the award-readiness revision before final upload; do not present the old manual supplement click as autonomous execution.

- Video: 1280×720 MP4 (H.264 + AAC mono)
- Narration: English primary (macOS `Samantha` voice), optional Simplified Chinese subtitles
- Runtime: 3:58 (within 3:30–4:00)
- Live evidence: AppealOS case workspace deployed at https://appealos-606769518273.us-central1.run.app
- App-in-action segment (1:12–2:57) is a real screen recording of the deployed Cloud Run UI, not wireframes/screenshots

| # | Time | Visual | Narration (English) | On-screen text |
|---|------|--------|---------------------|----------------|
| 1 | 0:00–0:08 | Cover hero: AppealOS wordmark, "A digital advocate for an algorithmic world" | "Platforms already use algorithms to judge us. AppealOS gives ordinary people a tireless digital advocate of their own." | AppealOS · AppealOS Runtime |
| 2 | 0:08–0:38 | Problem card: suspended account notice, fragmented evidence, contextless form | "A rider, seller, creator, or developer can lose an account, income, or audience over an automated fraud signal — then has to reconstruct the allegation, policy, deadline, and evidence through a contextless form." | Problem: automated suspension + contextless appeal |
| 3 | 0:38–1:12 | Value proposition: scoped workflow, AnalysisConsent vs AppealMandate | "The missing product is not a better appeal-letter generator. It is a persistent workflow that reads the notice, inspects only user-approved evidence, builds a citation-backed timeline, then acts under one bounded mandate — and verifies a clear result." | Value: one case, scoped authority, verifiable outcome |
| 4 | 1:12–1:19 | Live UI — `Reset` creates case `NOTICE_RECEIVED`; case summary + three synthetic evidence cards visible | "Here is the live case workspace, running on Cloud Run. A MockDrop rider is suspended for abnormal location." | Live URL + case workspace |
| 5 | 1:19–1:30 | Live UI — `Parse notice` extracts allegation/incident/deadline; evidence cards remain consent-gated | "AppealOS extracts the allegation, the incident window, and the deadline, and shows exactly three synthetic evidence artifacts: a delivery receipt, a GPS trace, and a device log." | Demo — notice + evidence consent |
| 6 | 1:30–2:03 | Live UI — `Grant consent`, then `Approve mandate`; timeline shows `ANALYSIS_CONSENT_APPROVED` and `MANDATE_APPROVED` | "The user grants analysis consent first. Next, the agent compiles grounded claim units and asks for one scoped Appeal Mandate: one recipient, named claims, allowed evidence, one supplement, polling, verification, 72-hour expiry." | Demo — grounded claims + mandate approval |
| 7 | 2:03–2:31 | Live UI — one `Execute approved mandate` click; timeline adds submit, supplement request, supplement, and decision receipts | "After one approval, AppealOS submits through a typed adapter. MockDrop requests a device log; because that artifact and one supplement cycle are already inside the mandate, AppealOS answers without a second approval." | Demo — one approval, autonomous action loop |
| 8 | 2:31–2:57 | Live UI reaches `ACCOUNT_ACTIVE`; `Export outcome JSON` downloads the hash-chained case | "Every external write leaves a receipt. Only after a separate account-status call returns ACTIVE does AppealOS close the case. Its event hash chain makes later local tampering detectable." | Demo — verified outcome + audit export |
| 9 | 2:57–3:12 | Updated in-code architecture Mermaid | "Under the hood: Cloud Run hosts the ADK runtime and UI, Gemini handles structured extraction and drafting, deterministic code enforces every mandate boundary, and Firestore holds recoverable case state. A Pub/Sub consumer exists in code; live event wiring is not claimed." | Architecture — implemented vs optional |
| 10 | 3:26–3:42 | GCP evidence: live Cloud Run service cards (`.run.app` URLs + revisions + 100% traffic), verified end-to-end timeline, Vertex AI runtime logs | "Here is the deployed backend on Google Cloud. AppealOS and MockDrop run as separate Cloud Run services, each serving one hundred percent of traffic. The verified demo returned ACCOUNT_ACTIVE, with Gemini ready on Vertex AI and the request path logged end-to-end." | GCP evidence — live |
| 11 | 3:42–3:58 | Safety + synthetic-data disclaimer, close | "AppealOS is a synthetic proof of concept. It never promises reinstatement, and every claim stays inside user-approved scope. One approval. One authorized supplement. One verified outcome." | Synthetic data · no real platform integration |

## Recording notes

- Slides 1–3, 9–11 are static/ken-burns slide cards retained from the previous cut.
- Slides 4–8 are now a real 1280×720 screen recording of the deployed Cloud Run UI, captured with headless Chrome via Playwright.
- The replacement recording must follow `Reset` → `Parse notice` → `Grant consent` → `Approve mandate` → one `Execute approved mandate` click → `Export outcome JSON`.
- Key states shown in the status timeline: `NOTICE_RECEIVED`, `PARSED`, `CONSENTED`, `MANDATE_APPROVED`, `ACKNOWLEDGED`, `SUPPLEMENT_REQUESTED`, `SUPPLEMENTED`, `DECIDED_APPROVED`, `ACCOUNT_ACTIVE`.
- Regenerate the middle narration and app recording after deploying the award-readiness revision.
- `submission/screenshots/` now contains live UI captures: `01-case-workspace.png`, `02-claims-and-mandate.png`, `03-action-timeline.png`, `04-outcome-export.png`, `05-live-log.png`.
