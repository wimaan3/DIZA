# Session context: elder-care

- **Session:** Codex implementation of DIZA Care for an elderly residential care home.
- **Branch:** `codex/elder-care-dual-use`.
- **Scope:** combined care-home staff workflow for urgent response, daily care, and shared facilities incidents, with persistent records, check-ins, audit history, an optional signed voice adapter, and a container deployment handoff.

## Files in this folder

| File | Contents |
| --- | --- |
| `app.py` | FastAPI care API, SQLite storage, role-aware workflow rules, check-ins, signed voice functions, and original-engine mounting |
| `facility.py` | Adapter reusing Imaan's building rules and ticket helpers for care-home rooms, shared repairs, role-aware actions, and room editing |
| `web/index.html` | Staff workspace entry point |
| `web/app.js` | Daily and urgent queues, resident roster, check-ins, request dialogs, assignment and care outcomes |
| `web/style.css` | Responsive staff dashboard, visible focus states, and accessible text contrast |
| `web/facility.js`, `web/facility.css` | Combined room map, facilities queue, original reports, call context, vendor coordination, and repair dialogs |
| `tests/test_care.py` | Care backend workflow and integration checks |
| `tests/test_facility.py` | Shared care/repair transactions, grouping, role enforcement, conservative permissions, version checks, and upgrade compatibility |
| `tests/care.spec.js` | Browser workflows, mobile checks, accessibility scans, and connection recovery |
| `tests/facility.spec.js` | Room filtering, repair assignment and outcomes, merge/unmerge/split, transcript links, room editing, and combined-workspace accessibility |
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
12. The user then requested combining Imaan's workflow with the care-home workflow.
Imaan is `wimaan3`; the relevant sources are building backend PR #24, dashboard PR #25, and security PR #27.
13. The feature branch incorporates current main, including the existing building dashboard and newer operations endpoints.
14. Physical repairs share tickets, while resident care requests retain independent acceptance and resolution.
Repair completion never silently closes resident care.
15. Shared facilities incidents use the existing `building.file_ticket`, urgency, cross-reference, timeline, and insights helpers directly.
Care-home room records and facility tickets live in the care database, preserving separation from the legacy apartment/disaster data.
16. Facilities and care leads coordinate repairs; nurse/care-lead acceptance still governs urgent resident requests.
Merge/unmerge/split preserve original reports, caller context, and escalated urgency.
17. Maintenance review targets are demo operational thresholds, and tenancy-law clocks are excluded from care-home policy.
18. Existing demo data is upgraded in place, with original request IDs and retry behavior preserved.

## Key facts verified

- Existing app entry point and operations contracts: `sessions/cs2-backend/mvp/backend/app/main.py` and `sessions/cs2-backend/mvp/README.md`.
- Existing building operations and role workflow: `sessions/cs2-backend/mvp/backend/app/building.py`.
- Current deployment wiring: root `railway.json` and `sessions/cs1-retell/deploy/Dockerfile`.
- Repository branch, review, and session-folder rules: root `AGENTS.md`.
- Synthetic roster, role restrictions, urgency safeguards, and transaction behavior: this session's backend tests.
- Responsive layouts, visible original quotes, browser workflow, and accessibility: this session's browser tests and rendered screenshots.
- The existing 60 backend tests pass when run one file per process in an isolated checkout.
Their combined discovery runner has pre-existing environment-state collisions between modules.
- Rebased onto `425b6db`, which added security briefing support, and verified its 6 additional tests in an isolated process.
The integrated container was rebuilt and checked against that revision.
- Initial care validation: 17 backend tests and 9 Chromium browser tests passed, including axe checks with zero violations on the tested screens and dialog.
- The integrated Docker image builds successfully and serves the care workspace, original operations/supporter/text screens, original APIs, and signed voice endpoints.
- Combined-workflow validation: 30 backend tests and 16 Chromium browser tests pass.
The tested care screens, combined room workspace, and request/assignment dialogs have zero axe violations.
- The latest isolated main export (`cfc6e82`) passes all 85 existing backend tests, run one file per process.
- A copy of the active local demo database was upgraded successfully, preserving all five original request IDs and adding the shared facilities records.
The upgraded demo contains eight care reports, three facilities tickets, and three labeled synthetic transcripts.
- The combined Docker image builds and passes HTTP checks for `/care`, `/building`, `/ops`, `/supporter`, `/text`, and the care/building/operations APIs.

## Open questions

- Facility-specific emergency procedure, escalation contacts, staff roster, operating policy, and resident import remain deployment inputs.
- A teammate from CS#2 must review the backend/dashboard PR before merge under the repository's review policy.

## Not done yet

- No production deployment or live Retell agent change.
- No real resident information imported.
- No individual authentication, production role authorization, clinical validation, staff paging, or emergency dispatch integration.
- No care-home human-transfer destination configured or live phone test performed.
- The care prompt and signed tool definitions are optional integration artifacts, not an activated voice agent.
