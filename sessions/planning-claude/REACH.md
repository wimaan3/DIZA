# Reach: who today's alerts miss, and how DIZA reaches them

The Retell prize asks for **"Impact: who it reaches that today's alerts miss."** This doc is the answer. Every claim maps to something we build and something we measure.

## 1. What already exists (prior-art research)

| Existing | What it does | Who it misses |
|---|---|---|
| **Wireless Emergency Alerts / EAS** (government push to phones) | One-way broadcast to every phone in an area | Languages other than **EN/ES**. Sleepers (one-time alert). People outside a mis-drawn polygon. False alerts go to everyone: **~10M LA County phones on Jan 9, 2025** |
| **Genasys Protect / ALERT** (LA County vendor) | Zone alerts + app | Needs a smartphone app; **one-way**, residents can't report back |
| **NotifyLA** (City of LA on Nixle) | Opt-in SMS/email alerts | Few languages (the City Controller's audit urged pre-translated templates); you must sign up first |
| **Everbridge** (mass notification) | Alerts + "reply YES" confirmations | Fixed-choice replies only; first reply counts; **no follow-up when nobody answers** |
| **Aurelian / Hyper** (AI on 911/police non-emergency lines) | Inbound AI takes overflow calls, hands real emergencies to humans | **Inbound only.** Reaches only people who call. Nothing proactive, no corroboration. |
| **Carbyne** (911 AI triage) | Clusters duplicate calls, "we know about this event", live translation | Locked in the 911 stack; nothing for people who never call |
| **CheckWellCall / SeaVoice / Joy Calls** | Scheduled AI wellness calls to seniors | Not connected to emergencies or evacuation zones |
| **LA County SNAP registry** (access & functional needs) | Voluntary list of vulnerable residents | **Static list nobody calls**; Cal OES discourages registries partly because they go stale |
| **New Orleans 311 AI** | Answers info questions | Hides that it's AI, no tickets: a trust failure to avoid |

**The evidence this matters (sourced in PLAN.md):**
- **Eaton fire:** west Altadena's first evacuation order came at **3:25 AM**, vs. 6:48 PM the evening before in the east. **17 of 19 deaths were in the west.** Dispatch got **14+ resident fire reports** while no alerts went out for those hours.
- Victims' median age was **77**, and **≥1/3 had mobility impairments**.
- A UCLA study found **12,000+ Asian Americans** in evacuation zones couldn't understand EN/ES alerts.
- 82% of 911 centers struggle to fill openings.

## 2. The gaps we own (gap research → our build)

| Gap nobody covers | Our feature |
|---|---|
| **Nobody listens to residents as sensors.** 14 reports, no alert. | Cluster reports + count distinct callers + automatic WATCH/ASK + a human declares (TRIAGE.md) |
| **Nobody follows up on silence.** | Callback ladder: call → SMS → retry → emergency contact or neighbour → red flag for a human |
| **Registries are static and never called** | **Tuesday check-ins keep the list alive.** The same list becomes the crisis call-down. |
| **EN/ES only** | Per-language agents in 10+ LA languages (ES, KO, ZH, YUE, HY, TL, VI, FA, RU, JA) |
| **One-way or fixed replies** | Two-way conversation: report, ask, get a task done (forms, escort, reminders) |
| **AI lines are inbound-only** | Outbound-first: we call the people most likely to be missed |
| **Loud tools misfire** | Gentle rungs (watch, ask) are automatic; anything public needs a human |

## 3. How we build for reach (design rules)

1. **Works on any phone.**
   - Voice + keypad. Landlines and flip phones; no app, no data plan, no smartphone, no literacy needed.
   - Plain-language prompts; slower speech on request.
2. **We call them, not just wait for them.** Outbound welfare calls to the zone's registry, ordered by risk (oxygen, mobility, alone, age).
3. **Their language, by default.** The registry stores language; the inbound webhook routes to the matching agent; unknown callers can switch at any time ("para español", "한국어").
4. **The everyday line builds the crisis reach.**
   - Enrollment by self or **proxy** ("check on my grandma"), confirmed by her.
   - Weekly check-ins keep phone numbers, needs and contacts current.
   - **The number becomes familiar:** residents save it as a contact during check-ins, so on fire night it isn't an unknown number that phones silence or label as spam.
   - Our answer to "people don't pick up unknown callers" and to Cal OES's stale-registry worry.
5. **Reach through people who are already trusted.**
   - Enrollment comes through home-care agencies, council offices, senior housing, USC, 211LA and churches. Those are the Tuesday customers, so they bring their people.
   - The family-contact step reaches people through relatives.
6. **When nobody answers, widen the circle:** emergency contact → neighbour on the registry → human welfare-check flag. Never silently drop.
7. **Accessibility:** keypad-only path ("press 0"), 711 relay info, text/email alternatives, no time pressure, and silence treated as a risk signal, not a hang-up.
8. **No busy signals:** the AI answers in parallel, callbacks replace hold, and duplicate callers get the "we already know" announcement and are released fast.
9. **Travel test:** voice + SMS only, ~$0.10/min, no new hardware. Works where the budget is a tenth of LA's.

## 4. Reach metrics (on the Ops Wall + in the pitch)

| Metric | Shows |
|---|---|
| % of high-risk registry residents **reached within 15 min** of Declare (drill) | proactive reach |
| Residents reached **via a contact or neighbour** after no answer | the ladder working |
| Calls handled in languages other than EN/ES (count + %) | reach beyond WEA |
| Reports from residents that **arrived before** a cluster was confirmed | residents as sensors |
| Busy signals / abandoned calls during floods (target: 0) | capacity |
| Enrollments by proxy | trusted-network reach |

**Pitch line:** *"Today's alerts reach people with a smartphone who read English or Spanish and are awake. We reach the 81-year-old on a landline who speaks Korean, at 3 AM, and if she doesn't pick up, we call her daughter."*

## 5. Honest limits (say them before a judge does)
- We only call people who **opted in**. Everyone else reaches us inbound, or through a partner.
- Phones can silence unknown callers. Mitigation: a familiar number from the everyday check-ins, plus a "verified caller" (anti-spam) number registration in production.
- SMS needs A2P registration (2–3 weeks) in production.
- Voice can't reach people with no phone at all. That's door-knock territory, so the red flag goes to a human or CERT.
