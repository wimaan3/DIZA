# Build prompt: DIZA final direction (for one Claude Code agent)

Paste everything below the line into a Claude Code session that has the `wimaan3/DIZA` repo checked out and `RETELL_API_KEY` in the repo-root `.env`.

---

You are the single build agent for team DIZA (USC InnovateLA hackathon, Resilience Comms track, sponsored by Retell AI). Build the final product end to end on top of what already exists. Work carefully: the live phone line and the deployed site are used in a live demo.

## 0. Read first (in this order), then summarize back what you learned in 10 lines before coding
1. `AGENTS.md` (repo rules: write in your own `sessions/<name>/` folder for notes, PRs to `main`, no secrets, never push directly to `main`).
2. `sources/participant-hub-gdoc.txt` and `sources/README.md`: judging criteria, track brief, deliverables, deadlines.
3. The proposal doc's final section, mirrored in `sessions/cs1-retell/PITCH.md` and `sessions/cs1-retell/REFOCUS.md`. The **final direction is in section 1 below** and wins over older text.
4. Research (sources for every number we pitch):
   - `sessions/cs1-retell/research/OPERATOR_WORKFLOW.md`: 911 workflow, bottlenecks, LA fire findings
   - `sessions/cs1-retell/research/EXISTING_INFRASTRUCTURE.md`: NENA 2026, alerts, legal, competitors
   - `sessions/cs1-retell/research/WELFARE_CHECKS.md`: background only
   - `sessions/cs1-retell/research/BUILDING_SIDE.md`: building and hotel evidence (if present)
5. Code map:
   - **Agents (Retell config as code):** `agents/`
     - `push.py --env staging` creates or updates every agent and binds the phone number. `tools.json` holds the tools. Prompts are in `prompts/*.md`. `retell.ids.json` holds the IDs. Each agent has `*.llm.json` and `*.agent.json`.
     - `safety_check.py` runs playground tests. `contract_check.py` runs signed backend checks.
   - **Backend (FastAPI + SQLite):** `sessions/cs2-backend/mvp/backend/app/`
     - `main.py`: reports, triage, clustering, webhooks, call log, geocoding.
     - `retell_fns.py`: Retell function endpoints.
     - `locate.py`: GPS links. `textline.py`: web chat. `alerts.py`, `resources.py`.
   - **Dashboard (React + Vite + Leaflet):** `sessions/cs2-backend/mvp/dashboard/src/`.
   - **Tests:** `sessions/cs2-backend/mvp/tests/`. Run each with `python -m unittest tests.<name>` from `mvp/`.
   - **Deterministic triage and clustering (DS):** `sessions/ds-analytics/diza_analysis/`, `triage.py` and `zones.py`.
   - **Deploy:** Railway builds `sessions/cs1-retell/deploy/Dockerfile` from `main` (see `railway.json`). The live site is https://diza-production.up.railway.app with SQLite on the `/data` volume. Every merge to `main` redeploys. Agents do **not** redeploy on merge: run `push.py` after backend changes are live.

## 1. The final direction (build exactly this)

**One AI intake engine, two customers, two modes. The AI only gathers and asks; plain rules rank, merge and route; humans decide.**

| | Building mode (everyday customer) | 911 mode (crisis customer) |
|---|---|---|
| Who decides | Building manager, hotel front desk or night manager | 911 dispatcher / overnight supervisor |
| Who calls | Tenants and guests: "sink is leaking in 4B", "AC broken in 412", "noise next door", "locked out", "need towels" | The public during a disaster surge (fire, flood, earthquake) |
| AI asks | Only what's missing: unit/room, issue, urgency, permission to enter, callback; then reads back and files a ticket | In order: "Are you in danger right now?" (yes, help or keypad 1 → human now) → location (read back; GPS link if unsure) → callback → on scene or calling for someone? → what, how many, hurt or trapped → hazards and access needs → "anything else?" |
| Rules do | Urgency (water, gas, no heat, lockout, safety = high), cross-reference by unit, floor or building system ("3rd leak on floor 4 this week, likely same pipe"), merge duplicates, route to staff or vendor | Priority with stated reasons, duplicate merge (every call kept), agency for the location, completeness check |
| Human does | Assign, comment, close on the dashboard | Take call (warm transfer with whispered summary), dispatch outside DIZA |
| Never | Promise a repair time the manager didn't set | Dispatch, decide who gets help, drop or downgrade a call, claim help is on the way |

**Redirect to local police (non-emergency) or security, in both modes:**
- **Who gets what:**
  - Danger now → always "hang up and call 911", never a police or security transfer.
  - A safety matter that isn't an emergency → with the caller's consent, warm-transfer to the right local line, with a whispered summary:
    - noise or a disturbance in progress with no threat
    - a suspicious person who isn't acting
    - a theft or vandalism that already happened
    - a lockout at night
- **The right line:**
  - Building mode: the building's own security or on-call staff first, then the police non-emergency line for the building's jurisdiction.
  - 911 mode: the police non-emergency line for the *incident location's* jurisdiction. The rules engine picks it from the geocoded location, so out-of-area callers get the right department.
- **Numbers come only from a verified allowlist,** never from the model:
  - extend `agents/resources/resources.yaml` with `type: police_nonemergency` / `security` entries, each with `transfer_number`, `transfer_ok: true`, `source_urls`, `verified_on` and the area it covers (city or campus); building security numbers live in the building record
  - seed only numbers you verify on the agency's official site that day (for example LAPD non-emergency on lapdonline.org; USC DPS 213-740-6000 is already verified)
- **Built on the existing transfer:** reuse `transfer_to_resource` (or add `transfer_to_police_nonemergency` / `transfer_to_security` with the same allowlist rule). The backend returns the number from a new function such as `local_contact(kind, location_text | building_id)`.
- **Drill mode:** the backend returns a teammate's number instead (`DIZA_RESPONDERS`), never the real department. The agent says which line it is connecting to.
- **Ticket trail:** every redirect is logged on the ticket or card ("transferred to LAPD non-emergency, 23:14") so the manager or operator sees it.
- **Tests:**
  - noise complaint → offered the security or police non-emergency transfer
  - "someone is breaking in right now" → the 911 instruction, no transfer
  - an out-of-area location → the right department
  - drill mode → the teammate's number

Two customers, same engine; **no data link between them** (team decision). 911 mode is positioned for the 911 **non-emergency and overflow line** (NENA-STA-020.2-2026 §5.6.2 endorses AI there); live 911 lines only where policy allows.

## 2. Non-negotiable safety rules (911 mode, and danger in building mode)
- **Errors only push up.** A call is "urgent until reviewed"; only a human can lower priority. Silence, whispers, hang-ups and unclear answers default to urgent.
- **Danger fast path:** any danger signal (direct yes, "help", keypad 1, words like stab, fire, trapped, can't breathe, gas, in EN/ES/KO/ZH) stops intake and connects a human now. If no human is free: "Hang up and call 911 now (or text 911)", and the card stays at the top. In building mode, a gas smell, fire, smoke or someone hurt always gets "call 911 now" first, and the ticket is marked emergency.
- **Caller's words are never lost:** the raw transcript and exact quotes sit on every card. A **second reader** (fixed rules over the raw transcript, not the AI summary) flags a card red if it finds danger words the AI's card missed.
- **No hallucinated facts:** the AI states only what the caller said, our database returns, or approved fixed text. Critical lines (danger question, 911 instruction, handoff) are fixed text. Use Retell Conversation Flow nodes or static `begin_message` + strict prompt wording, whichever you can verify works. Temperature stays 0.1 and `tool_call_strict_mode` stays on.
- **Retell keyword boosting** for danger words in 4 languages on 911-mode agents (verify the field name against Retell's API before using it).
- **Drill mode stays on** (`DRILL_MODE=true`): transfers go to teammates' phones (`DIZA_RESPONDERS` on Railway), never to real 911 or 988.
- Never commit keys or personal phone numbers. Ask the user before anything that spends money (buying numbers, raising concurrency) or deletes Retell agents.

## 3. Build plan (in order; one small PR per step into `main`; tests green before each PR)

1. **Building data model + tickets (backend).**
   - Tables:
     - `buildings` (id, name, type apartment/hotel, address, lat, lon)
     - `units` (building_id, unit/room, floor, plus optional system tags like riser or HVAC zone)
     - `staff` (name, role, phone, skills)
     - `tickets` (code, building, unit, category, urgency, summary, caller quote, access permission, status new/assigned/in_progress/closed, assignee, related_ticket_ids, created/updated)
   - Retell functions (same signed `{name, call, args}` body as existing ones, idempotent via `once()`): `create_ticket`, `lookup_unit` (validates the unit exists and gives its floor and system), `ticket_status` (by code + callback last-4).
   - Rules:
     - urgency map
     - cross-reference: same building and (same unit or same floor or same system tag) and the same category within 7 days, linked with a human-readable reason
     - duplicate merge: same unit + category within 2 h means one ticket with several reporters
   - Seed one demo apartment building (~24 units, 4 floors) and one demo hotel (~40 rooms), with fake staff. No real phone numbers in git; staff phones come from an env var like `DIZA_RESPONDERS`.
   - Tests: urgency, cross-reference reason text, merge, idempotent retries, invalid unit asks again.
2. **Building-mode agent (Retell).**
   - New agent `building` (+ optional per-language variants, or a language switch like the existing KO/ZH swaps). Prompt in `agents/prompts/building.md` + `_shared_rules.md` danger rules.
   - Tools: `lookup_unit`, `create_ticket`, `ticket_status`, `route_to_human` (urgent → on-duty staff), `local_contact` + transfer to security or police non-emergency (see section 1), `text_caller` (ticket code), `end_call`.
   - Push with `push.py`. Add `safety_check.py` cases:
     - a leak → `create_ticket` with high urgency
     - gas smell → "call 911" first and an emergency ticket
     - "is someone coming to fix it today?" → no promised time
     - Spanish and Korean requests
     - an unknown unit → asks again
3. **911-mode intake agent.**
   - Rewrite `inbound`, `crisis`, `inbound_ko`, `inbound_zh` prompts to intake-only, in the order in section 1. Never deflect; always end in a human handoff or a priority callback.
   - Add fields as they're confirmed via an `update_incident` function, so the card fills live.
   - Non-emergency police matters: offer the transfer to the incident jurisdiction's police non-emergency line (section 1).
   - Danger fast path and fixed-text critical lines.
   - Add `safety_check.py` cases:
     - misheard words: "someone with a kite is coming at me", "he has a gone"
     - silence
     - keypad 1
     - "send SWAT" with no detail (must stay urgent, flag unverified)
     - Spanish trapped
     - Korean P0
4. **Dashboard: one HUD, two modes** (mode switch in the header; URL `/building` and `/ops`).
   - **Building view:**
     - tickets grouped by urgency with age timers
     - unit/floor filter
     - cross-reference badge ("3 related on floor 4")
     - merged reporters count
     - assign to staff (dropdown), status changes
     - transcript and quote on the card
   - **911 view:**
     - queue sorted by priority, then wait, with reasons
     - age timers turning red
     - card with completeness checklist (location ✓, callback ✓, …), exact quotes, live transcript, agency, corroboration (independent callers count, on scene vs third party, GPS match)
     - map (existing LiveMap)
     - Take call / Callback / Merge / Mark reviewed buttons
     - hotkeys J/K, T, M, 1–4, C
   - Remove leftovers that don't serve these two views from the main nav (services desk, alerts, volunteer inbox). Keep the code.
5. **Second reader + misheard-word tests (backend).** Rules over raw transcripts (EN/ES/KO/ZH word lists + sound-alikes), and a red mismatch flag on the card. Unit tests.
6. **Demo kit.**
   - `scripts/replay_surge.py`: pushes a recorded 50-caller surge through the same signed endpoints, as a backup if the live audience call-in fails.
   - Printable scenario cards: tenant cards for act 1, fire cards for act 2 in EN/ES/KO/ZH, each written for about a 60-second call.
   - A rehearsal checklist.
7. **Docs and deliverables (in `sessions/<your-folder>/`):**
   - a demo script (5 minutes, see below)
   - Devpost text: name, lens, one line, responsible-use note
   - a poster outline
   - an updated `SESSION_CONTEXT.md`

   Don't change other sessions' folders.

## 4. Demo the build must support (5 minutes)
1. **Problem (30 s):** both customers share one bottleneck: too many reports, too few people. LAPD answered 57% of 911 calls within 15 s in 2024 (standard 90%). The October 2026 UL Research Institutes report found that in the LA fires, "calls came in faster than dispatch could manage or assign them". Building numbers come from `BUILDING_SIDE.md`.
2. **Ordinary Tuesday (90 s):** three judges call as tenants about the same leak in different words and languages. The building view merges them into one ticket, "floor 4, likely same pipe", ranked above a towel request. The manager assigns a plumber in one click; the tenant gets a texted ticket code.
3. **Crisis (2 min):** switch to 911 mode. The audience calls in from fire cards. Cards rank themselves with reasons, duplicates merge, the map fills. A teammate operator presses Take call on a P0 and their phone rings with the whispered summary.
4. **Twists (40 s):** funding (subscriptions; FEMA UASI/EMPG; NSF SBIR Phase I), global (hotels are international; region variables for 999/112), poster.
5. **Close (20 s):** never automated: dispatch, decisions, dropping a call. Next step: a pilot with one building and one 911 non-emergency line.

## 5. Capacity and ops facts (keep the demo inside them)
- Retell concurrency 20, burst 60. Beyond that, callers queue or fail. Ask the user to set a fallback number, and put a QR/web fallback on the scenario cards.
- Backend load test: 60 simultaneous calls, 0 errors, p95 under 1.9 s. Keep handlers sync (thread pool) and the single uvicorn worker (SQLite).
- Cost: about $0.10–0.15/min plus $0.10/min in burst. Remind the user to turn on Retell auto-recharge.

## 6. How to work
- Branch per step (`cs1/<step>`), `git pull --rebase origin main` before pushing, PR into `main` with a short summary + test results.
- Do not merge PRs yourself unless the user explicitly tells you to; then merge with a merge commit.
- After a backend PR is merged and the site has redeployed (check a new endpoint answers), run `python agents/push.py --env staging` with `PUBLIC_BASE_URL=https://diza-production.up.railway.app`, then `python agents/contract_check.py`, then `python agents/safety_check.py`. All must pass.
- Verify Retell API field names in the docs or the CLI's bundled schema before using new ones. Don't guess.
- Report progress to the user after each step in 3–5 lines: what changed, test results, what's next. Flag anything you couldn't verify.
- Keep scope tight: if something isn't in section 3, don't build it. Write it under "later" in your session notes.
