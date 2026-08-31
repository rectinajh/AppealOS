# AppealOS — Devpost Demo Storyboard (CMP-25 re-record, 3:44 target)

> Re-recorded against the CMP-25 deployment and live Cloud Run UI. The App-in-action segment now shows the current seven-step case workspace and the verified nine-event state chain. Problem/value, architecture, and closing slides are retained from the previous cut.

- Video: 1280×720 MP4 (H.264 + AAC mono), 30 fps
- Runtime: 3:44 (223.7 s), within 3:30–4:00
- Narration: English primary (macOS `Samantha` voice), external Simplified Chinese subtitles
- Live evidence: https://appealos-606769518273.us-central1.run.app (`appealos-00004-9cb`)
- MockDrop: https://mockdrop-606769518273.us-central1.run.app (`mockdrop-00002-l26`)
- App-in-action segment (1:12–2:40) is a real screen recording of the deployed Cloud Run UI

| # | Time | Visual | Narration (English) | On-screen text |
|---|------|--------|---------------------|----------------|
| 1 | 0:00–0:08 | Cover hero: AppealOS wordmark, "A digital advocate for an algorithmic world" | "Platforms already use algorithms to judge us. AppealOS gives ordinary people a tireless digital advocate of their own." | AppealOS · AppealOS Runtime |
| 2 | 0:08–0:38 | Problem card: suspended account notice, fragmented evidence, contextless form | "A rider, seller, creator, or developer can lose an account, income, or audience over an automated fraud signal — then has to reconstruct the allegation, policy, deadline, and evidence through a contextless form." | Problem: automated suspension + contextless appeal |
| 3 | 0:38–1:12 | Value proposition: scoped workflow, AnalysisConsent vs AppealMandate | "The missing product is not a better appeal-letter generator. It is a persistent workflow that reads the notice, inspects only user-approved evidence, builds a citation-backed timeline, then acts under one bounded mandate — and verifies a clear result." | Value: one case, scoped authority, verifiable outcome |
| 4 | 1:12–1:21 | Live UI — empty case workspace: flow controls, case summary, status timeline | "Here is the live case workspace, running on Cloud Run. A MockDrop rider has been suspended for abnormal location." | Live URL + case workspace |
| 5 | 1:21–1:28 | Live UI — `Reset case` creates `NOTICE_RECEIVED`; evidence panel shows three consent-gated artifacts | "Reset creates a fresh synthetic case and loads three consent-gated evidence artifacts." | Demo — notice + evidence consent |
| 6 | 1:28–1:38 | Live UI — `Parse notice` adds `PARSE_SUCCEEDED`; allegation/incident/deadline extracted | "AppealOS parses the notice, extracts the allegation, the incident window, and the deadline." | Demo — parse notice |
| 7 | 1:38–1:46 | Live UI — `Grant consent` (two-click confirm) adds `ANALYSIS_CONSENT_APPROVED` | "The user grants analysis consent first. Analysis builds the timeline and drafts claims without disclosing anything." | Demo — scoped analysis consent |
| 8 | 1:46–2:02 | Live UI — `Approve mandate` (two-click confirm) compiles grounded claims and approves one scoped Appeal Mandate | "Next, the agent compiles grounded claim units and asks for one scoped Appeal Mandate: a single recipient, named claims, allowed evidence, one supplement cycle, polling, verification, and a seventy-two-hour expiry." | Demo — grounded claims + mandate approval |
| 9 | 2:02–2:06 | Live UI reaches `MANDATE_APPROVED`; `Execute approved mandate` becomes enabled | "The mandate is approved. The agent is now cleared to execute." | Demo — one approval, ready to execute |
| 10 | 2:06–2:15 | Live UI — one `Execute approved mandate` click runs submit → supplement → verify | "One Execute click submits the appeal, answers the supplement request with the authorized device log, and verifies the account." | Demo — autonomous action loop |
| 11 | 2:15–2:23 | Live UI — nine-event status timeline ends with `DECISION_APPROVED` and `ACCOUNT_STATUS_ACTIVE` | "Every external write leaves a receipt. The timeline ends with DECISION_APPROVED and ACCOUNT_STATUS_ACTIVE." | Demo — verified outcome |
| 12 | 2:23–2:31 | Live UI — live log shows idempotent supplement replay; no duplicate platform write | "Replay of the supplement is idempotent, so no duplicate platform action is produced." | Demo — idempotent replay |
| 13 | 2:31–2:40 | Live UI — `Export outcome JSON` downloads the hash-chained, redacted audit export | "The user can download a redacted, hash-chained due-process export." | Demo — audit export |
| 14 | 2:40–3:07 | Updated in-code architecture Mermaid | "Under the hood: Cloud Run hosts the ADK runtime and UI, Gemini handles structured extraction and drafting, deterministic code enforces every mandate boundary, and Firestore holds recoverable case state. A Pub/Sub consumer exists in code; live event wiring is not claimed." | Architecture — implemented vs optional |
| 15 | 3:07–3:28 | GCP evidence: live Cloud Run service cards with new revisions and URLs, verified health and demo run | "Here is the deployed backend on Google Cloud. AppealOS and MockDrop run as separate Cloud Run services, each serving one hundred percent of traffic. The verified demo returned ACCOUNT_ACTIVE, with nine timeline events, timeline integrity verified, and Gemini ready on Vertex AI." | GCP evidence — live |
| 16 | 3:28–3:44 | Safety + synthetic-data disclaimer, close | "AppealOS is a synthetic proof of concept. It never promises reinstatement, and every claim stays inside user-approved scope. One approval. One authorized supplement. One verified outcome." | Synthetic data · no real platform integration |

## Recording notes

- Slides 1–3, 14, 16 are static/ken-burns slide cards retained from the previous cut.
- Slides 4–13 are a real 1280×720 screen recording of the deployed Cloud Run UI, captured with headless Chrome via Playwright.
- The new App-in-action flow is `Reset case` → `Parse notice` → `Grant consent` (two-click confirm) → `Approve mandate` (two-click confirm) → one `Execute approved mandate` click → `Export outcome JSON`.
- Key states shown in the status timeline: `NOTICE_RECEIVED`, `PARSED`, `CONSENTED`, `MANDATE_APPROVED`, `ACKNOWLEDGED`, `SUPPLEMENT_REQUESTED`, `SUPPLEMENTED`, `DECIDED_APPROVED`, `ACCOUNT_ACTIVE`.
- CMP-25 verified timeline: `DEMO_RESET` → `PARSE_SUCCEEDED` → `ANALYSIS_CONSENT_APPROVED` → `MANDATE_APPROVED` → `APPEAL_SUBMITTED` → `SUPPLEMENT_REQUESTED` → `SUPPLEMENT_SUBMITTED` → `DECISION_APPROVED` → `ACCOUNT_STATUS_ACTIVE`; `timelineIntegrity.verified=true`.
- `submission/screenshots/` contains live UI captures: `01-case-workspace.png`, `02-claims-and-mandate.png`, `03-action-timeline.png`, `04-outcome-export.png`, `05-live-log.png`.
- GCP slide now shows the CMP-25 revisions: `appealos-00004-9cb` and `mockdrop-00002-l26`, with both services serving 100% traffic.
