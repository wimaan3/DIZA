# DIZA — local operations MVP

Runnable subset of the supplied CS2 backend/dashboard contracts. Python FastAPI, SQLite, React/Vite. This is a demonstration, not an emergency dispatch service.

## Run

From this folder:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd dashboard
npm ci
npm run build
cd ..
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ops and http://127.0.0.1:8000/supporter. Environment variables are read from the process; `.env` is an example only and is not automatically loaded.

## Demo flow

1. Select **Simulate surge**: 12 reports at Building A, including 2 individual assistance requests. All are labeled simulated.
2. Select a P1 report. Read the supporting quote and unknowns, then **Offer to eligible responder**.
3. Open Supporter inbox, select Alex, and accept or decline. Declining offers to a backup. Waiting 30 seconds expires the offer and tries the backup automatically.
4. Accept as Sam, then mark completed. Completion is responder-reported; caller confirmation is not collected.
5. Add an immediate-danger report. It stays in the urgent supervisor path and is never assigned to a general helper or treated as a normal callback.

Offers are visible in the app only. No outbound calls, texts, or emergency dispatch occur. Background expiration resumes from persistent timestamps after a restart. All responders are fictional demo identities.

## What is implemented

- Persistent reports, requests, responder reservations, attempts, audit history.
- Idempotent report submissions and transactional assignment/acceptance.
- Conservative exact location/category grouping within 10 minutes, retaining individual reports.
- Rule-based severity from explicit structured flags. No AI model inference or clinical triage validation.
- Live polling console, supporter inbox, simulator and responsive layout.
- Retell signed inbound/report/webhook endpoints. Lifecycle webhooks currently acknowledge receipt only; no live transcript UI.

## Retell connection (not yet live-tested)

Set `RETELL_API_KEY` to the webhook-enabled key and expose only the Retell paths through HTTPS. Configure a custom `submit_report` function using wrapped payload `{call:{call_id},args:{...}}` (not args-only) and URL `/retell/fn/submit_report`. Fields: `hazard`, `location_text`, `summary`, `evidence`, `unknowns`, `language`, `immediate_danger`, `needs_assistance`. `injured_or_trapped` is conservatively treated as an immediate-danger flag for compatibility. Use actual JSON booleans. Save partial reports during the call, not just post-call. Configure `/retell/inbound` and `/retell/webhook` as appropriate. SDK signature verification checks the raw body.

Unconfigured Retell endpoints fail closed with 503. Real phone operation requires an account, agent, telephone setup, reachable HTTPS endpoint, and a real integration test. Do not claim these are connected based on the local simulator.

## Retell functions (backend/app/retell_fns.py)

All 00_CONTRACTS functions answer at `/retell/fn/<name>` with the contract's response shapes, signature-checked, idempotent per call + arguments (Retell retries once). Nothing dials, texts or dispatches; each request becomes a case (`D-1234`) a person must act on, visible in `/api/state` → `cases` and the event log.

- `flag_urgent` creates a P0 report that is escalated to the supervisor and never offered to helpers.
- `route_to_human` picks the available responder with the most matching skills/language (`lang:es`) from `DIZA_RESPONDERS` (env only), never a `volunteer` for P0/P1, marks them busy, and frees them on the call's `call_ended` webhook. Nobody available → `oncall_number: ""` + `fallback: callback`.
- `submit_report`: free-text hazards map to the category enum (so grouping works), vulnerability or people at risk raise severity to P1, and `cluster_match` is only set when other reports share the cluster.
- Forms use `agents/forms/*.yaml` (`FORMS_DIR`). `lookup_info` logs knowledge gaps; `send_link` returns `sent: false` (no SMS provider yet).
- Check against the agents with `python agents/contract_check.py --base-url http://127.0.0.1:8000 --key <key>` (in wimaan3/DIZA#2).

## Deliberate scope differences

SQLite replaces Supabase for runnable local storage. `backend/db/schema.sql` is a draft Postgres migration, not an active adapter. No magic-link authentication, role isolation, photos, calendars, check-ins, public status page, automatic external notifications, or official public alert publishing. Supporter selection is a demo control, not authentication.

Keep this app bound to localhost and use synthetic data. `OPS_API_TOKEN` optionally protects `/api/*`, but is not a production per-user authorization system. Do not publish real caller data or expose the demo role selector as a production app. `DRILL_MODE=false` disables simulator/report-entry/reset endpoints, not demo role selection.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover report idempotency, separate individual requests in a grouped incident, assignment contention, acceptance, timeout escalation, unavailable responders, and Retell failing closed.
