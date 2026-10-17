# DIZA refocus: one problem, one pipeline

- **Session:** cs1-retell, 2026-10-17. Written after the mentor review.
- **Status:** superseded by `PITCH.md` for the pitch; this file keeps the reasoning.

## 1. What the mentor said, and where we push back

| Mentor point | Verdict | Why / what we do |
|---|---|---|
| "When someone says emergency, we want real help to come, not an AI rerouting us." | **Agree on the goal. The mechanism has to change.** | Only a 911 center (PSAP) can send police, fire or EMS. A separate number can never make help come. So DIZA must sit **inside the 911 workflow, as the operator's tool**, not beside it as a line that says "call 911". The caller always ends with a human dispatcher. |
| "Don't filter callers. Every call should reach the operator." | **Agree.** | The AI never decides whether someone gets help. It can't end, deflect or downgrade a call. It only gathers and organizes while the caller waits. Every call ends in a warm transfer or a priority callback from a human. |
| "A caller in Boston wants help sent to LA: how?" | **Real problem; we can solve it deterministically.** | 911 routes by the *caller's* phone location, so a Boston caller reaches a Boston PSAP, which must find the right LA agency and its 10-digit number by hand. DIZA: geocode the **incident** location, find the responsible agency from city/county boundaries, and show its transfer number on the card. |
| "Remove friction: populate the knowledge base automatically." | **Agree, aimed at the operator.** | Not general Q&A. For each incident location, automatically pull official context: NWS alerts, evacuation zone, nearest open shelter, prior reports nearby. No one types it in. |
| "Pick one real problem." | **Agree.** | Below. Everything that doesn't serve it is cut from the demo. The code stays in git. |
| "A deterministic tool for the operator as the core; AI only gathers information." | **Agree. This is the design.** | The LLM handles conversation and extraction only. Priority, jurisdiction, duplicates and completeness are plain rules anyone can audit. |

## 2. The problem

> During a disaster surge like the January 2025 LA fires, **callers wait or hang up** because every 911 call-taker is busy. When a call-taker does pick up, they re-ask where, who and what (LAPD: 57% of 911 calls answered within 15 s vs a 90% standard; interpreter connects in 49 s on average), often through an interpreter or for a location in another jurisdiction. Today the waiting caller gets hold music or a busy signal, and that waiting time is wasted.

**Our claim:** DIZA turns queue time into intake time. Every caller is answered at once, in their language, and when a human picks up, the incident card is already filled in, verified, ranked and routed.

## 3. The one pipeline (demo this end to end)

```
Caller dials (demo: our number = the 911 center's overflow line)
  │  answered instantly, in EN/ES/KO/ZH. "A dispatcher will be with you; I'm getting your details so they can send help faster."
  ▼
AI intake (Retell): gathers in NENA order, decides nothing
  1. Location: say + read back; if unsure → GPS link by text
  2. Callback number (from caller ID, confirmed)
  3. What is happening
  4. People / injuries / trapped
  5. Hazards + access needs (wheelchair, oxygen, language)
  │  each answer → update_incident() → incident card fills in live
  ▼
Deterministic engine (backend, no LLM)
  • priority score (rules: P0 words, injuries, trapped, vulnerability, wait time)
  • jurisdiction: incident location → agency + transfer number (fixes Boston→LA)
  • duplicates: same place + type within N min → linked, each call kept
  • context: NWS alert / evac zone / nearest shelter for that location
  • completeness: required fields ✓ → "ready for dispatch"
  ▼
Operator console (dashboard)
  queue sorted by priority, then wait time · prefilled card · live transcript (translated)
  [Take call] → warm transfer with a whispered summary · [Call back] · [Mark duplicate] · [Copy to CAD]
  ▼
Human dispatcher sends help (outside DIZA)
```

## 4. Keep / change / cut (using what we already have)

| Already built | Fate |
|---|---|
| Inbound + crisis agents, KO/ZH agents, `flag_urgent`, `submit_report` | **Keep, then merge into one intake role.** Rewrite prompts: never "hang up and call 911"; always "a dispatcher will take over". |
| `route_to_human` + warm transfer with whisper | **Keep: this is the operator handoff.** |
| Location link (GPS), geocoding, live map | **Keep: location is step 1.** |
| Live transcript, call log | **Keep: the operator sees the call before taking it.** |
| Clustering / incident rings, DS `zones.py` DBSCAN | **Keep: duplicate detection.** |
| DS `triage.py` (deterministic P0–P3) | **Keep: swap in as the priority engine.** |
| Dashboard (report list, briefing, map) | **Change:** rename to Operator console, add a completeness checklist, jurisdiction, context, and sort by priority × wait |
| Callback codes (`schedule_callback`) | **Keep as priority callback** when no operator is free |
| `text_caller` | **Keep** for the GPS link only |
| Services desk, forms, check-ins, welfare calls, alert batch calls, volunteer inbox, KB Q&A, `/text` chat | **Cut from the demo and pitch.** The code stays; don't spend more time on it |

## 5. New work (small, concrete)

1. `update_incident` function: the agent writes each field as it's confirmed. The card fills in live.
2. Jurisdiction resolver: Census geocoder `geographies` → city/county → agency table (LAPD, LAFD, LASD, Pasadena, Glendale, Burbank, Santa Monica, USC DPS, …) with non-emergency/transfer numbers from official sites. Out-of-area callers get the right agency.
3. Auto context: NWS `api.weather.gov/alerts/active?point=lat,lon` and a nearest-shelter lookup, attached to the card.
4. Priority = DS triage severity + rule boosts + wait time. Show the reasons on the card ("trapped +40, wheelchair +10, waiting 2:10").
5. Console changes: completeness checklist, "ready for dispatch" state, jurisdiction + transfer number, context chips, Take call / Call back.
6. Prompt rewrite: intake only, NENA order, never deflect, always hand off.

## 6. Demo (3 minutes)

1. Two operators on the console (teammates). A surge is on, so both are "busy".
2. A judge calls in Spanish: "Smoke, my grandmother can't walk, I'm not sure of the address." The AI answers instantly in Spanish, sends the GPS link, and the pin drops. The card fills in live: location ✓ (GPS ±10 m), callback ✓, trapped / wheelchair, priority jumps to the top, jurisdiction LAFD, red-flag warning attached.
3. A second caller from a "Boston" number reports a fire at the same street. It's linked as a duplicate, jurisdiction resolves to the LA agency, and the transfer number is on the card.
4. An operator frees up, clicks **Take call**, and their phone rings with a whisper: "Spanish-speaking caller, grandmother in a wheelchair, smoke at Lake and Woodbury, GPS verified." They're talking to the caller with everything already known.
5. Closing number: seconds of intake done before the human picked up (from demo timestamps).

## 7. Honest limits (say them)

- DIZA doesn't dispatch and isn't CAD. It hands off to the 911 center's people and CAD.
- A real deployment needs the PSAP to route overflow to DIZA. In the demo, our number stands in for that line.
- Carrier location (ANI/ALI) never reaches us; GPS comes only with the caller's consent through the link.
