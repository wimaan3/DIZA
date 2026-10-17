# Deck, video and the things we must say

**Yes, we need a deck.**
- Devpost requires a **pitch deck** + **demo video** (Round 1 is judged from these alone).
- Finalists submit a final deck by **Sun 9 AM** for the 5-min pitch.
- The "Deck Rules" section in the hub is blank; ask the help desk. Plan for **~10 slides, 16:9, readable from the back row.**

## Slide outline (maps to the hub's pitch order: problem → working thing → twist → next)
| # | Slide | Content | Metric / proof on it |
|---|---|---|---|
| 1 | **Title** | DIZA + one-liner + Resilience Comms × Retell + team (4 names, roles) | QR "call it yourself" |
| 2 | **The night nobody listened** (problem, 0:30) | Altadena: residents called, the west side was warned at 3:25 AM; the false alert to 10M phones 2 days later | 14+ reports · 3:25 AM · 17 of 19 deaths · ~10M false-alert phones |
| 3 | **Seat · moment · rungs** | Overnight supervisor of a community call line · 2 AM fire night (or Harbor Night) · we live on **ASK + HAND TO A PERSON** | — |
| 4 | **Live demo** (switch to the Ops Wall) | Audience calls, surge, transfer with whisper, Declare | live counters |
| 5 | **How it decides who needs a person** | P0–P3 + vulnerability → priority → skills routing; never-wait-for-a-specialist rule | P0 recall 100% · routing match % · time-to-human P0 |
| 6 | **When nobody picks up** | Callback ladder (resident) · next responder (human) · dead-man's switch (supervisor) | % of high-risk residents reached in 15 min · reached via a contact |
| 7 | **What it never automates** | Public alerts, declaring/ending a crisis, P0 to volunteers, claiming dispatch, claiming to be human | safety evals 100% |
| 8 | **Twists: it changed the build** | 3 rows: twist → change → proof (commit/clip) | before → after numbers |
| 9 | **Tuesday: who pays** (dual-use) | Second customer + day: *council district senior-services line, every Tuesday 10 AM*; live pilot: USC campus line this weekend; national-resilience expansion (base family lines, VA check-ins) | real calls this weekend · cost per resident/month |
| 10 | **Reach + feasibility + ask** | Who today's alerts miss vs. us (any phone, 10+ languages, outbound-first, familiar number); stack is off-the-shelf; Open311/FHIR adapters; next: a pilot with a council office or 211LA | languages served · non-EN/ES % · $/call |
| Appx | Architecture · eval scoreboard v1→v3 · responsible use · tools list | for Q&A and Devpost | |

## Numbers we must have (DS owns; fill from real drills)

**Problem (sourced, in PLAN.md):**
- 14+ reports; west Altadena warned at 3:25 AM; 17/19 deaths in the west; median victim age 77; ≥1/3 had mobility impairments
- ~10M phones got the false alert
- 12k+ Asian Americans couldn't understand alerts
- alerts go out in EN/ES only
- 82% of 911 centers struggle to staff

**Ours, from the live weekend:**
- real calls handled · peak concurrent · busy signals (target 0)
- % resolved by AI alone · median time-to-human for P0/P1
- P0 recall (100%) · severity accuracy vs. role cards · routing skill-match %
- calls in languages other than EN/ES (count, %)
- registry high-risk residents reached within 15 min of Declare · reached via a contact
- forms completed / avg turns · actions done (escorts, reminders, enrollments)
- eval scoreboard v1 → v3

**Cost and feasibility:**
- ~$0.10–0.15 per call-minute all-in (Retell)
- **a weekly 2-min check-in ≈ $0.80–1.20 per resident per month**
- 20 concurrent calls standard, 60 in burst (~2,400 calls/hour)
- built in 24 h on off-the-shelf parts

## Lines we must say (judges listen for these)
1. **Second customer + day:** "A council district's senior-services line uses DIZA every Tuesday at 10 AM. On fire night, the same line, list and number are already in place."
2. **The rungs:** "We live on two rungs: *ask* and *hand to a person*."
3. **The three questions, one sentence each:**
   - Who needs a person: "Anyone with a life-safety word, a vulnerability, or a cluster behind them, ranked, and sent to the *right* human, not the next free one."
   - What's never automated: "Public alerts, declaring a crisis, and anything life-or-death goes to a trained human or 911/988, never a bot or a volunteer."
   - Nobody picks up: "We widen the circle: text, retry, their daughter, their neighbour, then a human at the door. Nobody is silently dropped."
4. **Pre-emptive:** "We build the list on Tuesday so Friday night is a phone call, not a search."
5. **The automation framing:** "Automated alerts misfire and systems go quiet. We corroborate before anyone broadcasts, and we treat silence as a signal."
6. **Reach:** "Today's alerts reach people with a smartphone who read English or Spanish and are awake. We reach the 81-year-old on a landline who speaks Korean, at 3 AM."
7. **Which way we lean (the kickoff deck asks this):** "We lean everyday-first. That's deliberate: the everyday use is what keeps the crisis tool alive."
8. **Honesty:** say "plus 150 simulated" during the flood; "SMS in production needs A2P registration".

## Demo video (Devpost, 2–3 min; check the length limit)
- 0:00–0:15 problem (slide 2 voiceover)
- 0:15–1:45 the Surge Drill recording:
  - Instagram/campus callers
  - Ops Wall
  - P0 transfer with whisper
  - Declare
  - ladder reaches the daughter
  - Korean check-in enrollment
- 1:45–2:15 twists + scoreboard
- 2:15–2:45 Tuesday customer + reach + ask
- Captions on (judges watch muted). Only clips with `feature_consent = yes`.

## Devpost write-up sections
- Name + lens (**Resilience Comms**) + one line
- Inspiration (Altadena)
- What it does (both lives)
- How we built it (Retell agents, swap, functions, Supabase, …)
- Twists (link TWISTS.md)
- Results (the numbers above)
- Challenges
- What's next (pilot)
- **Responsible use (2 lines):**
  - **Misuse risks:** hoax floods could fake an emergency, and the vulnerable-resident registry is a sensitive list.
  - **How we limit it:** corroboration from independent callers, human approval for any alert or crisis declaration, opt-in consent, short data retention, and P0 calls never handled by volunteers.
- **Tools used:**
  - Retell AI (+ underlying LLM), Twilio, Supabase, FastAPI, React/Leaflet
  - scikit-learn, librosa/YAMNet if used
  - Claude Code, IBM Bob if used
- Team (all 4)
- Repo link
