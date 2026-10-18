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
| `sessions/cs2-backend/mvp/backend/app/regions.py` | Country table (emergency numbers per service, map centre, geocoder area, UI language), caller country from calling code, agent variables |
| `sessions/cs2-backend/mvp/dashboard/src/i18n.js` | Dashboard text in English / 中文 / Español (English sentence = key; falls back to English) |
| `sessions/cs2-backend/mvp/tests/test_regions.py` | 6 tests |

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

9. **Global (hackathon twist):** one setting per deployment, `DIZA_COUNTRY` (+ optional `DIZA_AREA`, `DIZA_UI_LANGUAGE`).
   - The emergency number follows where the line runs, not the caller's phone (a +86 tourist in LA still needs 911). The caller's country code is only a language hint (`caller_country`).
   - `/retell/inbound` sets `emergency_number`, `crisis_line_*`, `service_area` and `country` per call. The prompts already use `{{emergency_number}}`, so no agent edit is needed.
   - Countries with separate numbers are spoken in full ("119 for fire, 120 for an ambulance, or 110 for police").
   - Crisis lines are set only where verified (US/CA 988). Elsewhere the agent gives the emergency number, never a US hotline.
   - The dashboard has a language switch (region default, remembered per browser) and a region badge with the local numbers. Caller quotes and transcripts are never translated.
   - The geocoder biases to the region's area and country; the Census geocoder is used only in the US.
   - Not translated yet: backend-generated text (reasons, timeline, AI summaries), the `/building` page (other session), and the `/text` and `/l` pages beyond the emergency number.

## Pitch notes: "how would firefighters in China use it?"
- **What stays:** the rules engine (ranking, second reader, merge, checklist) and the dashboard. Both are model-agnostic and run on any server.
- **What changes per country (config, not code):** emergency numbers by service (CN 119 fire, 120 ambulance, 110 police), map centre, geocoder area, and the default dashboard language. The second reader already has Chinese danger words.
- **What a China deployment must swap:**
  - Telephony: a local carrier or SIP trunk. Retell numbers are US/CA.
  - Voice/LLM: an in-country model (e.g. Qwen), because US model APIs aren't available there.
  - Hosting: in-country servers. PIPL limits sending personal data abroad.
  - Maps: Chinese basemaps (Amap, Baidu) use the GCJ-02 offset, so raw GPS lands a few hundred metres off unless converted.
- **One line:** "The AI that listens is replaceable; the rules that rank and the screen that shows them travel unchanged."

## Key facts verified
- Emergency numbers: Wikipedia "List of emergency telephone numbers", read 2026-10-18 [S]. Before live use in a country, check the national government page.
- Retell has no live web search during calls. Knowledge-base URLs auto-refresh every 24 h, with up to 500 URLs per KB plus auto-crawl ([docs](https://docs.retellai.com/build/knowledge-base), read 2026-10-18).
- Live check of the geocoder: Kansas City → 39.10, −94.58; Wichita → 37.69, −97.34; Tulsa → 36.16, −95.99; Venice and Altadena still resolve in LA.

## Requests to phone-agent session
1. **Wire `update_incident`** (`{field, value}`, field in location, callback, relationship, what, people, hazards, access_needs). It returns `{ok, missing:[…]}`; ask next for the first item in `missing`. Call it as each fact comes in, so the operator's card fills live.
2. **When a caller names several places,** pass them all in `location_text` ("Kansas City, Wichita, and Tulsa"). The backend splits them into one card per place.
3. **Knowledge base:** add official pages as auto-refreshing URL sources (LA County emergency, Ready.gov, Caltrans road status, LADWP/SCE outage pages; equivalents per country later). This expands answers with no new API key. A paid search API is only needed for questions those pages don't cover.

## Open questions
- Web search beyond the knowledge base: which provider (needs a key on Railway), or not at all?

## Not done yet
- Translating backend-generated text; more dashboard languages (ko, vi, fa, hy, tl); a GCJ-02 conversion for a China basemap; per-country offline maps (LA only).
