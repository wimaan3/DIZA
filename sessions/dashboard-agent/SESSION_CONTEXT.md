# Session context: dashboard-agent

- **Session:** Claude Code dashboard + backend agent (https://claude.ai/code/session_01Ce66Vi6D1cdy5w2VePdR9k)
- **Branch:** `claude/tender-noether-ijmkfn` (one PR per step into `main`)
- **Scope:** building-manager dashboard (`/building`), 911 operator dashboard (`/ops`), and the backend data and endpoints behind them. Code lives in `sessions/cs2-backend/mvp/` (the app the deploy builds). The phone agents (`agents/`) belong to the phone-agent session.

## Files
| Path | What |
|---|---|
| `sessions/cs2-backend/mvp/backend/app/building.py` | Step 1: building tables, urgency / merge / cross-reference / California-clock rules, Retell functions `lookup_unit`, `create_ticket`, `ticket_status`, `local_contact`, manager API, demo seed |
| `sessions/cs2-backend/mvp/tests/test_building.py` | 18 tests: urgency, merge, cross-reference text, idempotent retry, unknown unit, CA clock, local_contact, manager actions |
| `sessions/cs2-backend/mvp/dashboard/src/Building.jsx` | Step 2: `/building` manager dashboard (insights strip, urgency-grouped queue with age timers and badges, ticket card, SVG floor plan with edit mode) |
| `sessions/dashboard-agent/SESSION_CONTEXT.md` | this file |

## Decisions
1. **Rules, not AI, and the reason is stored as text.** Every urgency has an `urgency_reason`, and every link has a `reason` string the dashboard shows.
2. **Urgency** (`building.urgency`):
   - **emergency:** gas_smell, or any fire/smoke/gas/injury word in the caller's words (EN/ES/KO/ZH); a water_leak unless the caller says it stopped or is minor (errors push up).
   - **urgent:** no_heat in heating season (Oct 1–Apr 30, `DIZA_COLD_WEATHER=true|false` overrides), no_hot_water, lockout 8 PM–7 AM, electrical.
   - **routine:** everything else.
   - The agent's `urgency_hint` can only raise urgency, never lower it. A chirping smoke-detector battery is not treated as danger.
3. **Duplicate merge:** same building + unit + category, not closed, within 2 h → one ticket, `reporters` +1 (each with call_id, last-4, quote, language). A duplicate can raise urgency, never lower it.
4. **Cross-reference:** same building + category within 7 days, and the same unit, stack, HVAC zone or floor. Which shared element explains it best depends on the problem: water → stack first, heat → HVAC zone, electrical → floor. Links go both ways, and older links get the updated count ("3rd leak report on stack B this week (2B, 3B, 4B): likely the same pipe"). Nothing is ever closed automatically.
5. **Manual merge** keeps the merged ticket visible (`merged_into`), and **unmerge** undoes it. **Split** turns one auto-merged reporter back into their own ticket.
6. **California clock** for §1941.1 habitability categories (water, heat, hot water, electrical, gas, pest, appliance): `ok` <21 days, `soon` 21–29, `past_30` (Civ. Code §1942), `past_35` (§1942.4, if cited). It stops at close and is labelled "a warning, not legal advice".
7. **Phones only from the environment:**
   - `DIZA_STAFF='{"maint":"+1...","security":"+1..."}'` (staff ids: mgr, maint, plumb, elec, lock, hvac, security)
   - `DIZA_BUILDING_AFTER_HOURS`
   - `DIZA_BUILDING_LINE` (the number tenants call; defaults to `RETELL_FROM_NUMBER`)
   - The dashboard never gets the full numbers (`has_phone`, `after_hours_last4` only).
8. **`local_contact`:**
   - **Drill mode:** a `DIZA_RESPONDERS` teammate (a skill containing `security`/`police` wins), named "X (drill stand-in for Y)". With no teammate it returns empty.
   - **Live:** building security staff first (if it has a phone), else the police non-emergency entry from `resources.yaml` whose `covers` list matches the location text (most specific match wins), else empty.
   - Every redirect is logged on the call's ticket and in the event log.
9. **Poll size:** `/api/building` returns open tickets plus those closed in the last 14 days (cap 300), the last 40 timeline events per ticket, and only the calls referenced by open tickets.
10. **DS triage reuse:** the Railway image copies only `backend/`, so the DS package (`sessions/ds-analytics/diza_analysis`) can't be imported at runtime. Rules are ported into the backend instead.

## Contracts implemented (POST /retell/fn/<name>, signed, idempotent per call + args)
| Function | args | returns |
|---|---|---|
| `lookup_unit` | `{building_hint?, unit}` | `{ok, building, unit, floor, stack}` or `{ok:false, ask}` |
| `create_ticket` | `{unit, category, summary, caller_quote, urgency_hint?, access_ok, language}` | `{code, urgency, merged_into?, related_reason?, eta_text}`, plus optional `safety_text` (emergency other than water: "call 911 now") and optional `ask` (unit not in records; the ticket is still saved) |
| `ticket_status` | `{code, phone_last4}` | `{status_text}` (last-4 must match a reporter) |
| `local_contact` | `{kind: security\|police_nonemergency, building_id? \| location_text?}` | `{name, transfer_number}` |
| `update_incident` | Step 3 | |

## Manager API (behind OPS_API_TOKEN when set)
- `GET /api/building?building_id=`: building, units, staff, tickets (reporters, related, timeline, ca_clock), calls, insights
- `POST /api/tickets/{code}/assign {assignee}`; `/status {status}`; `/note {text}`; `/notified`; `/merge {into}`; `/unmerge`; `/split {call_id}`
- `POST /api/units {unit, rename_to?, floor?, stack?, hvac_zone?}`: add or edit a unit
- `POST /api/demo/seed?mode=building` (drill mode only): 12 sample calls → 11 tickets (stack-B leak trio, a 4B duplicate, a stack-C hot-water pair, a 33-day heater past the §1942 mark)

## Requests to phone-agent session
1. Add verified `type: police_nonemergency` entries to `agents/resources/resources.yaml`, each with `transfer_ok: true`, `transfer_number`, `source_urls`, `verified_on`, and **`covers: [city or neighborhood names]`**. `local_contact` matches the location text against `covers`. Example: LAPD covers `[Los Angeles, Koreatown, Hollywood, Venice, ...]`; Pasadena PD covers `[Pasadena]`.
2. In the building agent: if `create_ticket` returns `safety_text`, read it first. If it returns `ask`, ask for the unit again and call `create_ticket` again with the corrected unit.
3. Pass `language` as an ISO code (`en`, `es`, `ko`, `zh`, `vi`, …); the dashboard's language mix uses it.

## Key facts verified
- Civ. Code §1942 (30-day presumption) and §1942.4 (35 days after an inspector's notice), from `sessions/cs1-retell/research/BUILDING_SIDE.md` A5 [V].
- Baseline before this session: 41 backend tests green (`test_flow` needs `dashboard/dist` built).

## Open questions
- Heating season dates: Oct 1–Apr 30 is our choice (no LA statute sets one); override with `DIZA_COLD_WEATHER`.

## Step 2 notes (/building)
- `main.jsx` routes `/building` to `Building.jsx`. The sidebar and the header mode switch (Building | 911) reach every view; the supporter inbox and line activity are unchanged.
- The page polls `/api/building` every 1.5 s. A new ticket or a new reporter is highlighted for 5 s (measured: it appears 0.86 s after the call is filed).
- Colour is never the only signal: urgency marks (!! / ! / ·) and text labels sit next to every colour, and unit tiles have aria labels. J/K move through the queue, and units are reachable with Tab and Enter.
- Layout: three columns above 1280 px. At 1280 px and below, the floor plan sits on top with the queue and card in two columns; on a phone, everything stacks into one column.
- Merge permission: the auto-mode classifier blocked further self-merges ("Merge Without Review"). From PR 2 on, PRs are opened but left for a human to merge.

## Not done yet
- Step 3 `/ops` upgrade + second reader + `update_incident` + zones, Step 4 shared call panel + crisis seed.
