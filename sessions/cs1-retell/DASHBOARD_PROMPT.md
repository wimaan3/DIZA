# Build prompt: DIZA operator & manager dashboard (for a separate coding agent)

Paste everything below the line into a Claude Code session with the `wimaan3/DIZA` repo checked out.

---

You are the dashboard and backend agent for team DIZA (USC InnovateLA hackathon, Resilience Comms track, sponsored by Retell AI). Build the dashboards that organize and cross-reference every call for **building managers** (everyday) and **911 operators** (crisis), plus the backend data and endpoints they need. A different session owns the phone agents (Retell prompts and tools in `agents/`). Don't edit `agents/` except where section 6 says so.

## 0. Read first, then summarize back in 10 lines before coding
- `AGENTS.md`: repo rules. Make notes in your own folder `sessions/dashboard-agent/`; no secrets.
- `sessions/cs1-retell/BUILD_PROMPT.md`: the overall plan. Its sections 1 and 2 (direction and safety rules) apply to you.
- `sessions/cs1-retell/research/BUILDING_SIDE.md` and `OPERATOR_WORKFLOW.md`: what managers and operators need, and why.
- Backend: `sessions/cs2-backend/mvp/backend/app/`
  - `main.py`: reports, triage, clustering, `calls` log, webhooks, geocoding, `/api/state`, pin placement.
  - `retell_fns.py`: Retell function endpoints, signed via `parse()`, idempotent via `once()`.
  - `locate.py`: GPS links. `alerts.py`. `resources.py`. `textline.py`.
- Dashboard: `sessions/cs2-backend/mvp/dashboard/src/`, React + Vite + Leaflet: `main.jsx`, `LiveMap.jsx`, `style.css`.
- Tests: `sessions/cs2-backend/mvp/tests/`. From `mvp/`, run `python -m unittest tests.test_retell_fns` and the others. 40+ tests must stay green.
- Deterministic triage and clustering from the data science work: `sessions/ds-analytics/diza_analysis/triage.py`, `zones.py`. Reuse them where they fit.
- Live site: https://diza-production.up.railway.app (Railway builds `main`, SQLite on the `/data` volume). The dashboard is served from the same container.

## 1. Product in one paragraph
One AI intake engine, two customers. **Building mode:** tenants call DIZA about problems ("leak in 4B", "no heat", "noise next door"). The AI files tickets; the manager sees them ranked, cross-referenced and assigned. **911 mode:** during a disaster surge, callers' reports become ranked, located, deduplicated incident cards; the operator takes calls and dispatches. The AI only gathers; **rules rank, merge and cross-reference; humans decide**. Keep every existing feature working and reachable: call log, live transcript, map, GPS links, alerts, the supporter inbox, the `/text` chat. Nothing gets deleted.

## 2. What already flows in (use it, don't rebuild it)
- `GET /api/state` (polled every 1.5 s) returns: `reports` (severity P0–P3, category, location, lat/lon, gps_accuracy, cluster_id, evidence, unknowns, source), `requests` (status, assignee), `responders`, `attempts`, `events` (timeline), `cases` (codes such as D-417, type, status), `calls` (direction, agent, caller_last4, status live/ended, duration, summary, sentiment, transcript: live for the 15 most recent), `kb_gaps`, `alerts`, `places`, `live`, `line_number`.
- Webhooks already log calls; `transcript_updated` streams live transcripts.
- Clustering: same location + category within 10 min share a `cluster_id`. P0 flags merge into the full report from the same call.
- `POST /api/reports/{id}/location` (place or drag a pin), `/api/responders/{id}/available`, `/api/requests/{id}/offer|decision`.
- The Retell function body is `{name, call:{call_id, from_number, to_number, direction}, args}` (or `chat` for text), signed with `X-Retell-Signature`. Copy the pattern of `simple()` / `once()` in `retell_fns.py`.

## 3. Build (one small PR per step into `main`; merge your own PR with a merge commit once all tests pass; never push directly to `main`)

### Step 1: Building data model and ticket API
- **Tables:**
  - `buildings`: id, name, address, lat, lon, manager_name, after_hours_phone (from env or seed, never a real number in git)
  - `units`: building_id, unit, floor, stack/riser, hvac_zone, tenant_language (optional)
  - `staff_vendors`: name, role (manager, maintenance, plumber, electrician, locksmith, security), phone from env, skills
  - `tickets`: code (T-1234), building_id, unit, category (water_leak, no_heat, no_hot_water, electrical, gas_smell, lockout, pest, appliance, noise, security, other), urgency (emergency, urgent, routine), summary, caller_quote, language, access_ok, reporters (count + call_ids), status (new, assigned, in_progress, waiting_tenant, closed), assignee, created, updated, first_human_action_at, closed_at, related (ticket codes + reason), timeline
- **Retell function endpoints** (contracts in section 6; same signing and idempotency as existing ones): `lookup_unit`, `create_ticket`, `ticket_status`, `local_contact`.
- **Rules (deterministic, unit-tested):**
  - **Urgency:** gas_smell, fire, smoke and water actively leaking → emergency. No heat in cold weather, no hot water, lockout at night and electrical hazards → urgent. Everything else → routine.
  - **Duplicate merge:** same unit and category within 2 h → one ticket, reporters +1.
  - **Cross-reference:** same building and same category within 7 days, and (same unit, or same stack/riser, or same floor, or same hvac_zone). Link the tickets with a human-readable reason, e.g. "3rd leak report on stack B this week (4B, 5B, 6B): likely the same pipe". Never auto-close a linked ticket; a human decides.
  - **California clocks:** show days since first notice for habitability categories, flagging 30 days (Civ. Code §1942) and 35 days (§1942.4), as a warning, not legal advice.
- **Seed:** one demo LA apartment building (about 24 units, 4 floors, stacks A–F) and fake staff and vendors.
- **Tests:** urgency, merge, cross-reference reason text, idempotent retries, unknown unit, the California clock.

### Step 2: Manager dashboard (`/building`)
- **Queue:** grouped by urgency, sorted by age. Age timers turn red past targets (emergency 1 h, urgent 24 h, routine 7 days). Badges for the reporters count and cross-reference ("3 related, stack B").
- **Ticket card:**
  - caller quote(s) and language
  - transcript (from `calls`)
  - unit/floor/stack, access permission
  - a timeline of every call, assignment and status change
  - related tickets with reasons
  - California clock
- **Actions:** assign to staff or vendor (dropdown), change status, add a note, merge or unmerge, mark the tenant notified.
- **Building map (ours, no map provider):** an SVG floor-plan grid drawn from `units`. Each unit is coloured by its worst open ticket. Cross-referenced units are joined by a line and the stack is highlighted. Click a unit to filter. Edit mode adds or renames units and sets stack and zone.
- **Insights strip:** open tickets by urgency, median time to first human action, duplicates merged this week, top repeat problems (by stack or zone), language mix.
- **Real time:** a new call shows up within 2 s, highlighted for 5 s.

### Step 3: Operator dashboard (`/ops`), upgrading what exists
- **Queue:** sorted by priority, then wait time. Each card shows its priority reasons ("trapped +40, wheelchair +10, waiting 2:10"). Age timers turn red. Life-threatening (P0) cards stay pinned at the top. **Errors only push up:** only a human action ("mark reviewed", with a reason) can lower a priority, and the action is logged.
- **Incident card:**
  - a completeness checklist (location verified, callback, on scene or third party, what, people, hazards, access needs)
  - exact caller quotes and the live transcript, with danger words highlighted
  - GPS accuracy and the agency for the location (if the backend provides it)
  - a corroboration panel: independent callers (distinct numbers), on scene vs third party, GPS vs stated address, callback answered. Show it; never hide a card because corroboration is low.
  - a timeline
- **Second reader:** a backend rule scans raw transcripts for danger words (EN/ES/KO/ZH/VI/RU/HY/FA/TL lists, plus sound-alikes such as knife/kite and gun/gone). It flags a card red with "possible missed danger: caller said 'X'" when the AI's category or severity disagrees. Unit-tested.
- **Actions and hotkeys:**
  - J/K: move through the queue
  - T: take call (marks the operator as the claimed responder; the next `route_to_human` on that call returns them)
  - M: merge duplicates
  - 1–4: set priority (raising is free; lowering needs a reason)
  - C: callback
  - R: mark reviewed
- **Map (Leaflet, ours on top):**
  - our pins and incident rings
  - click to place and drag to correct (already built)
  - operator-drawn zones (polygon tool, saved via a new `/api/zones` endpoint)
  - a list of unlocated reports with "place on map"
  - an **offline fallback basemap** (a bundled GeoJSON of LA County city outlines and major roads) if tiles fail
- **Wall view** (`/ops?wall=1`): a big-screen layout for the live demo.

### Step 4: Shared pieces
- **Header mode switch** between Building and 911. The supporter inbox, alerts, line activity and `/text` stay reachable from a secondary menu.
- **One "call" panel** used by both views: caller last-4, language, agent, duration, summary, transcript, recording link if Retell provides one, and the tickets or incidents it created.
- **Demo seed/reset:** `POST /api/demo/seed?mode=building|crisis` loads realistic sample data. Reset already exists; only allowed in drill mode.
- **Accessibility:** keyboard-only use, visible focus, colour never the only signal, works at 1280 px and on a phone (manager on the go).

### Step 5: Verification before each merge
- All backend tests pass, plus your new ones.
- `npm run build` passes.
- Screenshot both dashboards with seeded data, using Playwright from `/opt/pw-browsers`. Look at them and fix anything that reads badly.
- After merge, wait for Railway to redeploy (check that a new endpoint answers) and check the live `/building` and `/ops` render.
- Report to the user in 3–5 lines per step: what changed, test results, the screenshot path, what's next.

## 4. Non-negotiables
- No AI in ranking, merging or cross-referencing: plain, explainable rules, with the reason shown on screen.
- Never drop or hide a report or ticket. Low confidence means "verify", not "remove".
- Caller numbers: show last-4 only on screen. Full numbers exist only in env and in transfers.
- Drill mode stays on. Never connect anything to real 911, police or 988.
- Never commit keys or real phone numbers.
- Keep handlers sync (FastAPI thread pool) and SQLite single-worker. The poll payload must stay small (cap list sizes; transcripts only for live and recent calls).

## 5. Out of scope for you
- Retell prompts, tools and voices (`agents/`). Request any change in your session notes and the phone-agent session makes it.
- Paid services, new phone numbers, Retell settings.

## 6. Contracts with the phone agents (implement exactly; the phone-agent session wires the tools)
All are `POST /retell/fn/<name>`, signed, body `{name, call|chat, args}`, idempotent per call + args, and must respond in under 2 s.

| Function | args | returns |
|---|---|---|
| `lookup_unit` | `{building_hint?, unit}` (building from the called number or hint) | `{ok, building, unit, floor, stack}` or `{ok:false, ask:"Which unit number is on your door?"}` |
| `create_ticket` | `{unit, category, summary, caller_quote, urgency_hint?, access_ok, language}` | `{code, urgency, merged_into?, related_reason?, eta_text:"The manager will review it; you'll get updates by text."}` (never a repair time) |
| `ticket_status` | `{code, phone_last4}` | `{status_text}` |
| `local_contact` | `{kind: "security"\|"police_nonemergency", building_id? \| location_text?}` | `{name, transfer_number}` from the verified allowlist (`agents/resources/resources.yaml` with `transfer_ok:true`, or building security in the DB); empty in drill mode unless `DIZA_RESPONDERS` provides a teammate |
| `update_incident` | `{field, value}` with field in location, callback, relationship, what, people, hazards, access_needs | `{ok, missing:[…]}`: updates the 911 card live |

If you need a contract change, write it in `sessions/dashboard-agent/SESSION_CONTEXT.md` under "Requests to phone-agent session" and keep the old shape working until it's wired.
