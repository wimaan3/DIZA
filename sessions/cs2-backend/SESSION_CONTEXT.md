# CS#2 backend session

Owner: CS#2 (ZoeCreates), assisted by Codex.
Branch: `cs2/local-operations-mvp`.

## Files
- `mvp/backend/`: FastAPI, local SQLite, partial signed Retell endpoints, draft Postgres schema.
- `mvp/dashboard/`: React/Vite operations console and demo supporter inbox.
- `mvp/tests/`: nine tests covering assignment, timeout, deduplication, signed callbacks, and page routing.
- `mvp/README.md`: setup, simulation walkthrough, integration limitations.

## Decisions
Preserve this prototype in our own session folder. It is not the shared contract implementation and must not replace other teams' code. No direct push to main; code PR requires teammate review. Supabase migration and CS#1 payload alignment remain follow-up work.

## Verified facts
Local frontend production build passed and nine backend tests passed. The operations page was verified in the local browser after fixing its static asset path. No real telephone call has been integration-tested. Reference requirements: `sessions/planning-claude/handoff/00_CONTRACTS.md` and `02_CS2_BACKEND_DASHBOARDS.md`; repository rules: `AGENTS.md`.

## Not done
MD2 M0 is NOT complete. No live Supabase/Realtime, ngrok, Retell transfer/outbound, Twilio, magic-link login, role authorization, public status page, photos, calendars, welfare scheduler, complete Ops Wall, replay, cloud deployment, or full function contract coverage. Notifications only appear in the local supporter inbox. All example responders are fictional. No production use or real personal data.

## Next integration steps
Read remaining referenced specs; align with CS#1 tool schemas; implement the agreed top-level app skeleton and Supabase adapter in small PRs; connect a public callback URL and validate a real call-to-report workflow. External credentials must stay outside Git.
