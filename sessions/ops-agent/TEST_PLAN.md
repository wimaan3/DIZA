# How to test DIZA end to end (about 30 minutes)

Live site: https://diza-production.up.railway.app (drill mode: nothing ever reaches real 911).
Two people make it easier: one on the phone, one watching `/ops`.

## 0. Before you start (2 min)
- Open `/ops`. The sidebar should say "Live · connected to Retell" and show the line number.
- The **Team on call** panel (bottom of `/ops`) lists your teammates as Available, with their skills and languages.
- If yesterday's test calls clutter the queue: **Reset drill data** at the bottom of `/ops`. This wipes all calls and reports.

## 1. Automated checks (developers, 2 min)
```
cd sessions/cs2-backend/mvp/dashboard && npm ci && npm run build
cd .. && for t in tests/test_*.py; do PYTHONPATH=. python $t; done      # all should say OK
```

## 2. Dashboard with demo data (5 min, no phone needed)
1. `/ops` → **Load demo: falls & freeway crash**. 16 reports appear.
2. **Top tiles:** calls with no operator, peak answered at once, duplicates folded, time saved (estimate), call-to-card, outside 911.
3. **Urgent lane:** P0s on top, red timers.
   - "110 Fwy northbound at Exposition Blvd" shows **5 callers** and "Possible missed danger: caller said 'atrapada'".
4. Click that card and try the actions:
   - **T** take call
   - **2** (asks for a reason, because it lowers the priority)
   - **R** reviewed
   - **C** callback
   - **M** merge "Exposition Blvd and Figueroa St" into the crash

   Each action appears in the card's **Timeline**.
5. **Map:**
   - **Draw zone:** click 3+ corners, then Finish and save it.
   - Click "place on map" for "Location not given yet", then click the map. The pin appears.
   - **Offline map** toggles the outline map.
6. **Language:** header → 中文, then Español. The page switches; caller quotes stay in their original words.
7. `/ops?wall=1` on a big screen; `/building` → **Load demo week** (floor plan, tickets, J/K).

## 3. Real phone calls (15 min): call the line from your phone
Watch `/ops` while calling. A card should appear within seconds of the agent filing it.

| Say this | Expect on `/ops` |
|---|---|
| "My grandmother fell in the kitchen and can't get up, we're at Adams and Normandie" | P1 medical card, pinned in West Adams; the agent stays calm and asks the checklist questions |
| "There's a big crash on the 110 at Exposition, someone is trapped" (then call again from a second phone saying the same) | P0; the second call joins the same incident (2 callers) |
| "Elderly people fell in Kansas City, Wichita and Tulsa" | **Three** P0 cards, pinned in the right three cities |
| Say an emergency but no location, then give it later in the call | Card appears as "Location not given yet", then the pin appears once you say the address |
| "I want to talk to a person" (in Spanish or Korean too) | Warm transfer to a teammate who speaks that language; Timeline says why ("speaks Spanish, medical…") |
| Let that teammate **not answer** | After the agents are pushed (below): goes to their backup. Before: a callback is offered |
| "Where can my mom get a ride to dialysis?" | Answered from verified info; lands in **Not urgent** or nowhere; nobody paged |
| "Someone is breaking into the house next door" | Security briefing goes to whoever has the `security` skill (or a drill stand-in) |
| Anything else: fire, flood, gas smell, power out with oxygen | Any kind of report works; the demo is only sample data |

For each call, check on the card:
- **Completeness** checklist
- **Caller's words** with danger words highlighted
- **Transcript**
- the second-reader flag, if the AI under-rated it

## 4. Known setup items
- **Backup transfers** need the agents pushed once: `python agents/push.py --env prod` (phone-agent owner).
- **Teammates:** add `areas`, `hours`, `backup`, `languages` and skills (`security`, `facilities`, `safety`) to `DIZA_RESPONDERS` on Railway (see `backend/app/team.py` for the format).
- **Emergency numbers outside the US** come from a reference list; verify them before any non-US demo with `DIZA_COUNTRY`.
