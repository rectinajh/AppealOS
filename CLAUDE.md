## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec

## AppealOS project context

AppealOS Runtime is a user-owned appeal workflow Agent for people affected by algorithmic platform suspensions.

Authoritative project documents:

- `README.md` — public project entry point and current implementation status.
- `docs/PRD.md` — product scope, P0/P1 requirements, and acceptance criteria.
- `docs/TECHNICAL_DESIGN.md` — proposed architecture, contracts, state machine, security, and delivery plan.

Implementation rules:

- The public MVP uses synthetic MockDrop data only.
- Do not claim a proposed component is implemented until its deployed verification passes and README is updated.
- Keep Gemini interpretation separate from deterministic authorization, state transitions, and side effects.
- Preserve the distinction between `AnalysisConsent` and `AppealMandate`.
- Never equate submission, acknowledgement, approval, and `ACCOUNT_ACTIVE`.
