# 02 · CS#2: Backend, systems and every screen

> **Paste to your AI agent:** "You are building the backend and all dashboards for team DIZA at the InnovateLA Dual-Use Hackathon (Resilience Comms / Retell AI). Read `sessions/planning-claude/handoff/02_CS2_BACKEND_DASHBOARDS.md` and `00_CONTRACTS.md` in https://github.com/wimaan3/DIZA (branch `claude/relaxed-goodall-tmz8gz`), then the referenced docs. First create the `main` app skeleton exactly as in the contracts (via PR). Work on `cs2/<topic>` branches, notes in `sessions/cs2-backend/` with a SESSION_CONTEXT.md. Never commit secrets. Python FastAPI + Supabase + React (Vite) + Leaflet. Do the tasks in priority order and meet the acceptance criteria."

**Read first:**
- `00_CONTRACTS.md`
- `SETUP.md` §1–3
- `WORKFLOW.md`
- `SYSTEM_SPEC.md` Layers 2–3
- `OPS_WALL.md`
- `INTAKE.md`
- `RETELL_GUIDE.md` §5, §9
- `COMPLIANCE.md`
- `CALL_SCHEDULE.md`

**Mission:** everything around the agent. Data, scheduling, routing plumbing, safety enforcement, and the three screens: supervisor console / Ops Wall, supporter app, public status page.

## Tasks

### P0: tonight → M0 (Fri 11:30 PM)
- [ ] **Create the `main` skeleton** (folders from the contracts, `.env.example`, README run steps) via PR. Add `docs/TWISTS.md` from `TWISTS_TEMPLATE.md`.
- [ ] Supabase project; `backend/db/schema.sql` (all tables + enums); Realtime on the ★ tables; storage bucket `photos` (private).
- [ ] FastAPI:
  - `/retell/inbound`, `/retell/webhook` with **signature verification on the raw body** (`retell-sdk`)
  - `/retell/fn/submit_report` (calls DS `lexicon_hits` / `classify` / `score_priority`, stubbed OK tonight)
- [ ] ngrok **static domain**; share the URL with CS#1.
- [ ] Minimal dashboard: a live list of reports via supabase-js.
- **Accept:** a real call → a row appears on screen in < 2 s.

### P0: overnight → M1 (Sat 10 AM)
- [ ] **All function endpoints** in the contracts (stubs → real). Respond in < 2 s; **cache** zone level / incidents / shelters in memory (TTL 30–60 s).
- [ ] **Safety enforcement in code** (not just the prompt):
  - P0 → `allowed_pools` = [] → 911/988 only
  - never-share check on `check_status`
  - volunteers get no address until `verified && accepted`
  - `opt_out` / `do_not_call` respected by the scheduler
  - calling window 8 AM–9 PM unless `emergency_purpose`
- [ ] **Routing:** `route_to_human` uses DS `match_responder` + `allowed_pools`; tracks ring timeout → next candidate → any human → `callback_queued`.
- [ ] **Scheduler (APScheduler):**
  - check-ins
  - reminders
  - callbacks
  - **no-answer ladder** (on `call_ended.disconnection_reason`: SMS → retry +5 min → contact → red flag)
  - **dead-man's switch** (zone at `ask` + no ack in `deadman_min` → welfare calls to the highest-risk residents only)
  - retries on outbound rejection
- [ ] **Twilio:**
  - fallback voice line (recorded message + voicemail → transcription → `requests` callback)
  - `/twilio/sms` + `/twilio/mms` (MMS photo → case)
  - outbound SMS (verified numbers only this weekend)
- [ ] **Supporter mobile web app (`/supporter`):**
  - login (magic link)
  - on/off duty, skills/languages
  - offered tasks (first accept wins)
  - case view after accepting
  - one-tap rating (urgent? right skill? resolved?)
  - **volunteer verification** screen for coordinators
- **Accept:** a full transfer with routing works; an unanswered outbound walks the ladder; a supporter accepts an escort and the caller's `check_status` shows it.

### P0/P1: Sat morning → M2 (2 PM)
- [ ] **Supervisor console / Ops Wall (`/ops`)**, per OPS_WALL.md:
  - zone banner with **Declare / Stand-down** + countdown
  - stat tiles (concurrency via `get-concurrency` poll every 2 s)
  - Leaflet map (pins by severity, cluster rings, zone polygons)
  - active call cards with a **live transcript ticker + keyword highlights** (`transcript_updated`)
  - call-flow breakdown
  - actions feed
  - trending terms
  - responders board
  - KB approval queue (`kb_gaps` → draft → approve → CS#1's `kb_add.py`)
  - **Public alert = draft export only**; no send path exists.
- [ ] **Projector privacy:** masked numbers, initials, regex PII scrub on the ticker.
- [ ] **Case pages + links:** `/s/<code>?t=<token>` shows status + photo upload. Tokens unguessable, 7-day expiry, own case only. Upload: size/type check, **EXIF strip**, store private.
- [ ] **Google Calendar** booking for `book_appointment` (team calendar).
- [ ] **Sandbox service world:** `/sandbox/clinic`, `/sandbox/311`, `/sandbox/utility` inboxes where a teammate accepts or proposes; status flows back. Adapter interface `submit(form) -> status`.
- [ ] Deploy the backend to **Railway/Fly** (not Render free); dashboard on Vercel.

### P1: Sat afternoon (before the 3:30 drill)
- [ ] **Public status page (`/status`):**
  - zone levels, **verified** incidents, open shelters, what to do
  - aggregates only (k ≥ 5); unverified items delayed `public_delay_min` + labelled
  - language toggle, text-only mode
  - case lookup by code + last 4 digits
  - banner "Not an official alert" + county link
  - **no pins, names, photos or transcripts**
- [ ] **Drill Mode** on `/ops` (countdown, counters) + **drill page** (QR → role card + code + number + web-call fallback button using Retell web SDK).
- [ ] **Replay mode:** replay any time window from `call_events` (backup demo).
- [ ] **Simulator `sim/surge.py`:** posts N synthetic reports/calls (multilingual) into the same pipeline; labelled "simulated".
- [ ] Quality tab: eval scoreboard (`eval_runs`).

### P2
- [ ] Face/plate blur + vision tags on photos (with DS); photo-corroboration count on clusters.
- [ ] Caller's own live "where did my call go" page from the drill code.
- [ ] Use **IBM Bob** for backend tests/scheduler and log how in `docs/TOOLS.md` (only if it's real).

## Demo / event duties
- Before each flood: backend warm, webhooks green, ≥ 4 supporters on duty, Drill Mode on, screen recording on (3:30 drill).
- Sunday: run the Ops Wall + simulator + replay backup.

## Hand-offs
- **You need:**
  - DS: triage package + configs + synthetic data
  - CS#1: agent IDs, function field names
  - biomech: form YAMLs, supporter roster
- **You give:** URLs, Twilio fallback number, Supabase keys (privately), `main` skeleton first.
