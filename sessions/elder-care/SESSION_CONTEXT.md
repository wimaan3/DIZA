# Session context: elder-care

- **Session:** Codex implementation of DIZA Care for an elderly residential care home.
- **Branch:** `codex/elder-care-dual-use`.
- **Scope:** staff dashboard for urgent response and non-urgent daily care, with persistent records, check-ins, audit history, an optional signed voice adapter, and a container deployment handoff.

## Files in this folder

| File | Contents |
| --- | --- |
| `app.py` | FastAPI care API, SQLite storage, role-aware workflow rules, check-ins, signed voice functions, and original-engine mounting |
| `web/index.html` | Staff workspace entry point |
| `web/app.js` | Daily and urgent queues, resident roster, check-ins, request dialogs, assignment and care outcomes |
| `web/style.css` | Responsive staff dashboard, visible focus states, and accessible text contrast |
| `tests/test_care.py` | Care backend workflow and integration checks |
| `tests/care.spec.js` | Browser workflows, mobile checks, accessibility scans, and connection recovery |
| `playwright.config.js` | Isolated local browser-test server and temporary database |
| `package.json`, `package-lock.json` | Browser-test dependencies and scripts |
| `requirements.txt` | Reuses the existing backend's Python dependency versions |
| `agents/care-intake.md`, `agents/tools.json` | Opt-in care-home voice prompt and signed tool definitions |
| `Dockerfile`, `railway.json` | Integrated care and original-engine deployment configuration |
| `README.md` | Run instructions, configuration, demo limits, and deployment handoff |
| `.gitignore` | Local test artifacts and virtual environment exclusions |

## Decisions made

1. The user requested repurposing the app for an elderly care home, covering urgent and non-urgent needs, and asked for a pushed PR.
2. The user explicitly chose **staff dashboard only** when asked about a resident-facing screen.
3. All changes stay in this new session folder to respect the repository's isolation rule.
4. The care app mounts the original engine, preserving existing voice endpoints and built dashboards in the integrated Docker image.
5. Care-home records use a separate SQLite database so they stay separate from disaster/building incident records.
6. Urgent requests and medication questions require a nurse or care lead to accept responsibility.
7. Staff must explicitly accept, start care, and record an outcome before resolution.
8. Escalation is one-way; a non-clinical owner is released when a routine request becomes urgent.
9. Request updates use versions and SQLite write transactions to prevent stale or conflicting staff actions.
10. Check-in concerns create follow-up work atomically, and later check-ins never silently resolve those requests.
11. The live phone agents and shared root deployment configuration are unchanged; new signed care tools and a container configuration are included for review.

## Key facts verified

- Existing app entry point and operations contracts: `sessions/cs2-backend/mvp/backend/app/main.py` and `sessions/cs2-backend/mvp/README.md`.
- Existing building operations and role workflow: `sessions/cs2-backend/mvp/backend/app/building.py`.
- Current deployment wiring: root `railway.json` and `sessions/cs1-retell/deploy/Dockerfile`.
- Repository branch, review, and session-folder rules: root `AGENTS.md`.
- Synthetic roster, role restrictions, urgency safeguards, and transaction behavior: this session's backend tests.
- Responsive layouts, visible original quotes, browser workflow, and accessibility: this session's browser tests and rendered screenshots.
- The existing 60 backend tests pass when run one file per process in an isolated checkout.
Their combined discovery runner has pre-existing environment-state collisions between modules.
- Final care validation: 17 backend tests and 9 Chromium browser tests pass, including axe checks with zero violations on the tested screens and dialog.
- The integrated Docker image builds successfully and serves the care workspace, original operations/supporter/text screens, original APIs, and signed voice endpoints.

## Open questions

- Facility-specific emergency procedure, escalation contacts, staff roster, operating policy, and resident import remain deployment inputs.
- A teammate from CS#2 must review the backend/dashboard PR before merge under the repository's review policy.

## Not done yet

- No production deployment or live Retell agent change.
- No real resident information imported.
- No individual authentication, production role authorization, clinical validation, staff paging, or emergency dispatch integration.
- No care-home human-transfer destination configured or live phone test performed.
- The care prompt and signed tool definitions are optional integration artifacts, not an activated voice agent.
