# DIZA — Triage: keywords → severity → crisis detection → routing

Keyword spotting alone is brittle. "Fire" could be a fire, a fire alarm test, "you're fired", or slang. A caller who says "no smoke here" mentions smoke. So we run **three layers**. Keywords give speed and recall, the LLM gives context, and cross-call counts decide whether a crisis is happening.

## Layer 1: live, per call (the seconds that matter)

**Where it runs:**
1. **In the agent prompt.** The agent is told to call `flag_urgent` / `route_to_human` the moment it hears a Tier 0/1 phrase.
2. **In the backend, independently.**
   - Retell's `transcript_updated` webhook streams each turn, and every function call carries the transcript so far.
   - The backend runs the lexicon on it and **flags the call on the dashboard even if the agent misses it**, so a supporter can jump in or call back.
   - Unverified: whether the backend can *force* a mid-call transfer through Retell's API. Treat it as no, and rely on the prompt + dashboard.

**Lexicon tiers** (`triage/lexicon.yaml`, versioned, so a twist can add terms in one commit):

| Tier | Meaning | Examples (EN / ES) | Action |
|---|---|---|---|
| **P0: life safety now** | someone may die or be hurt in minutes | can't breathe, not breathing, unconscious, trapped, bleeding a lot, chest pain, overdose, gun, being attacked, kill myself / no puedo respirar, atrapado, inconsciente, sangrando, me quiero morir | **Immediately give 911/988 + offer transfer.** Never to a volunteer. **Can never be downgraded.** |
| **P1: active hazard** | a danger that is also a *crisis signal* for the zone | fire, smoke, flames, smell gas, explosion, water rising, flooding, power lines down, building collapsed, evacuate, earthquake damage / humo, fuego, incendio, huele a gas, inundación | Human queue at top priority + counts toward zone crisis detection |
| **Vulnerability boosters** | raise priority, choose skills | wheelchair, oxygen, dialysis, ventilator, bedridden, alone, elderly, baby, can't drive, blind, deaf, no power + medical device, pets / silla de ruedas, oxígeno, sola, bebé | +priority; adds a `mobility` or `medical` skill to routing |
| **P2: needs a person soon** | distress without immediate danger | scared, panicking, can't reach my mom, nowhere to go, lost, stuck outside | Human or callback within ~20 min |
| **P3: routine** | AI can resolve | housing, heater, lost ID, escort, dining, class, printing, Wi-Fi | AI action + confirmation code |

**Context guards** (handled by the LLM, never by deleting keywords):
- Negations: "no smoke", "not trapped"
- Tests and drills: "fire alarm test", unless the caller has a drill code
- Hearsay: "I saw on the news", "my friend in Pasadena said"
- Figurative use: "this class is killing me", "fire mixtape"

**Rule: context can downgrade P1–P3, never P0.** When unsure, escalate.

**Other languages:** a hand-written lexicon for EN + ES (+ KO/ZH if time). The LLM classifier covers everything else; it reads the original language.

## Layer 2: per-call classification (in `submit_report` + post-call analysis)

The agent and the backend produce a structured label for every call:
```json
{
  "category": "fire | smoke | gas | flood | power | medical | mental_health | safety_crime | infrastructure | info | logistics | other",
  "severity": "P0 | P1 | P2 | P3",
  "hazard_here_now": true,
  "location": "...", "zone": "...",
  "people_at_risk": 2,
  "vulnerability": ["mobility", "oxygen"],
  "language": "es",
  "skills_needed": ["evac_logistics", "spanish"],
  "keyword_hits": ["humo", "silla de ruedas"],
  "confidence": 0.82
}
```

**Priority score** = severity base + vulnerability boosts + acoustic flags (escalate only) + cluster corroboration − nothing else. Callers are sorted by this score, not by arrival time.

## Layer 3: across calls (is this a crisis?)

For each zone, in 5-min and 15-min windows, compare against the everyday baseline:
- number of **distinct callers** with P1 hits in the same category (distinct numbers, so one person calling 10 times doesn't count 10 times)
- call-volume z-score vs. the same hour on an ordinary day
- spatial clustering of reported locations (DBSCAN)
- an official feed match (NWS / CAL FIRE / USGS / utility outage), if available

| Signal | Zone moves to |
|---|---|
| ≥ 3 distinct callers, same P1 category, within 10 min, OR volume z ≥ 3 | **WATCH** (auto) |
| ≥ 6 distinct callers, OR WATCH + an official feed, OR the cluster keeps growing over 2 windows | **ASK** (auto): corroboration calls to neighbours |
| a human taps Declare | **CRISIS** |

- Thresholds are config values. DS tunes them on drill data: "how many callers before we were sure?"
- **Hoax resistance:** count distinct numbers only, rate-limit each number, and require location agreement.

## Routing: from label to the right human

```
category + vulnerability + language → required skills
  medical / P0-medical      → medical (nurse/EMT)   [P0 still gets 911 first]
  mental_health             → mental_health listener [P0 → 988]
  fire/smoke/flood + mobility → evac_logistics
  safety_crime / escort     → safety
  housing / infrastructure  → facilities / housing
  info / logistics          → AI resolves (no human)
+ language match, if any
→ match score over available supporters (skill + language − load − fatigue)
→ no match in 20 s → any human → callback queue
```

## Dashboard
- **Live transcript ticker** with keyword hits highlighted by tier colour
- **Trending terms per zone** ("humo ×7 in the last 10 min, Altadena West") next to the zone-level banner
- Each queue item shows *why* it's ranked there: hits, boosters, cluster size

## Learning (DS)
- Measure the lexicon's **precision and recall per tier** against drill cards and supporter labels. **The P0 recall target is ~100%.**
- **Topic mining → new terms.** Words common in true-urgent calls but missing from the lexicon become suggested terms for human approval.
- **Before/after numbers for the pitch:** "after Flood #1 we added 9 terms; urgent recall went from X% to Y%."

## Owners
- **CS#1:** prompt trigger rules, `flag_urgent` function, P0 safety path
- **CS#2:** `transcript_updated` scanning, dashboard ticker and trending panel
- **DS:** lexicon file, classifier eval, crisis-detection thresholds, routing map
- **Biomech:** the medical and vulnerability lexicon (clinical phrasing callers actually use, e.g. "can't catch my breath", "my sugar is low", "face is drooping"), plus the acoustic escalation flags
