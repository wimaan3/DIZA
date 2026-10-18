# Session context: ops-agent

- **Session:** Claude Code, 911 operator dashboard (`/ops`) + its backend (https://claude.ai/code/session_014uLShQafuyJtC3oWCMN9BW)
- **Branch:** `claude/jolly-euler-c7h43c` (one PR per step into `main`; the user allowed self-merge on 2026-10-18)
- **Scope:** Step 3 of `sessions/cs1-retell/DASHBOARD_PROMPT.md` (`/ops` upgrade), the Railway outage, location bugs. Code lives in `sessions/cs2-backend/mvp/`. The phone agents (`agents/`) belong to the phone-agent session; requests for it are listed below.

## Files
| Path | What |
|---|---|
| `sessions/cs2-backend/mvp/backend/app/ops.py` | `GET /api/ops`: ranked queue, second reader, checklist, corroboration, load metrics; operator actions; zones; `update_incident`; crisis seed |
| `sessions/cs2-backend/mvp/backend/app/resources.py` | `place_list()` (one call naming several places), geocoding LA first, then anywhere |
| `sessions/cs2-backend/mvp/backend/app/main.py` | `split_report()`: one card and pin per named place, geocoded in parallel |
| `sessions/cs2-backend/mvp/dashboard/src/Ops.jsx` | `/ops` UI: load strip, Urgent / Not urgent lanes, incident card, trend charts, wall view |
| `sessions/cs2-backend/mvp/dashboard/src/LiveMap.jsx` | Map: severity pins, zones and polygon drawing, unlocated list, offline fallback |
| `sessions/cs2-backend/mvp/dashboard/src/offline-la.json` | Offline basemap: LA-area freeways + city/CDP outlines, US Census TIGERweb (public domain), lazy-loaded |
| `sessions/cs2-backend/mvp/tests/test_ops.py` | 12 tests |

## Decisions
1. **Rules, not AI**, with every reason on screen.
   - Score = severity base (P0 100, P1 70, P2 40, P3 10)
     - plus danger words in the caller's own words: trapped +40, breathing/unconscious +35, weapon +30, bleeding/injured +20
     - plus vulnerability +10 each (max 2), 3+ people +10, extra independent callers +5 each (max 15).
   - Sort: P0 pinned, then score, then oldest.
2. **Second reader:** EN/ES/KO/ZH/VI/RU/HY/FA/TL word lists plus sound-alikes ("has a kite" → knife, "pulled a gone" → gun), with simple EN/ES negation ("no one is trapped").
   - Flags only when the AI's severity is lower, or its category differs (unless the card is already P0).
   - It raises the shown priority until a person reviews the card; it never lowers anything.
   - The other dashboard session (PR #32) added: a second-reader P0 is escalated to the supervisor, and "lowering" is judged against the shown severity.
3. **Never hidden:**
   - Merge only re-groups (both reports stay listed), and unmerge undoes it.
   - Unlocated reports are listed with "place on map".
   - Corroboration is shown, never used to filter.
4. **Several places in one call** ("Kansas City, Wichita, and Tulsa") become one card per place, each with the same priority and its own request.
   - Never split: intersections, addresses, or "City, State".
5. **Geocoding** (bug from the user's test call): LA County first, then anywhere. A town the caller named beats an LA street with the same name ("Tulsa" St → Tulsa, OK).
6. **Load metrics** are measured from stored calls. The one estimate (20 s per checklist answer the AI already collected) is labelled on screen.
7. **Severity colours:** one hue, dark → light (P0 #7d1d10, P1 #c0442a, P2 #e8956b, P3 #b9c0b6). The old orange/olive pair failed the colour-blind check. The P0–P3 text always sits next to the colour.
8. **Railway outage 2026-10-18** was a malformed `DIZA_RESPONDERS` env var, not code. Fixed by PR #26 (other session).
   - The variable is still malformed (logs: "read 4 entries one by one"). The user needs to fix its value in Railway.

## Key facts verified
- Retell has no live web search during calls. Knowledge-base URLs auto-refresh every 24 h, with up to 500 URLs per KB plus auto-crawl ([docs](https://docs.retellai.com/build/knowledge-base), read 2026-10-18).
- Live check of the geocoder: Kansas City → 39.10, −94.58; Wichita → 37.69, −97.34; Tulsa → 36.16, −95.99; Venice and Altadena still resolve in LA.

## Requests to phone-agent session
1. **Wire `update_incident`** (`{field, value}`, field in location, callback, relationship, what, people, hazards, access_needs). It returns `{ok, missing:[…]}`; ask next for the first item in `missing`. Call it as each fact comes in, so the operator's card fills live.
2. **When a caller names several places,** pass them all in `location_text` ("Kansas City, Wichita, and Tulsa"). The backend splits them into one card per place.
3. **Knowledge base:** add official pages as auto-refreshing URL sources (LA County emergency, Ready.gov, Caltrans road status, LADWP/SCE outage pages; equivalents per country later). This expands answers with no new API key. A paid search API is only needed for questions those pages don't cover.

## Open questions
- Web search beyond the knowledge base: which provider (needs a key on Railway), or not at all?

## Not done yet
- Global support: country from the caller's number, emergency number per country (not hard-coded 911), dashboard text in other languages.
