# DIZA: pitch, solution, and how it meets the hackathon brief

- **Session:** cs1-retell, 2026-10-17. Built on `REFOCUS.md`, `research/EXISTING_INFRASTRUCTURE.md` and `research/OPERATOR_WORKFLOW.md` (in progress).
- **Verification:** numbers come from `research/OPERATOR_WORKFLOW.md` and `research/EXISTING_INFRASTRUCTURE.md`. [V] means a primary source; check the URL there before putting a number on a slide.

---

## One line (Devpost)

**DIZA turns a flood of emergency calls into ranked, located, multilingual incident cards for the human on duty, and turns residents' reports into early evidence for evacuation alerts.** The AI only listens and asks. Rules and people decide.

Lens: **Resilience Comms (Retell AI)**. The track's seat is *the overnight supervisor of a call line*.

---

## The 5-minute pitch (hub format: problem → working thing → twists → next)

### 0:00–0:30 · The problem
> "January 7th, 2025, Eaton fire. The first 911 calls reporting fire west of Lake Avenue came in around 10:50 pm. The evacuation alert for west Altadena went out at 3:25 am. [V: McChrystal / Citygate reviews] Those first reports weren't confirmed, and that's the point: nobody could tell, in that flood, which calls agreed with each other.
>
> On a normal day, LAPD answers only 57% of 911 calls within 15 seconds; the standard is 90%. [V: LAPD, 2024] When a call-taker finally picks up, they re-ask everything, wait 49 seconds on average for an interpreter [V], and in the Palisades fire they grouped 160+ evacuation calls into one incident by hand. [V: LAPD after-action]
>
> Our track asks the overnight supervisor: *'a surge of calls no one can verify, too few people to answer them. Residents are your earliest sensor and your biggest flood.'* We built the tool for that person."

### 0:30–3:00 · Show it working (live, phone on speaker)
1. **The surge is on.** Two teammates are the operators, both "busy" on the console.
2. **A judge calls in Spanish:** "There's smoke, my grandmother can't walk, I'm not sure of the address."
   - DIZA answers instantly, in Spanish: "A dispatcher will be with you. I'm getting your details so they can send help faster."
   - It texts a location link. The judge taps it, and **the pin drops at their exact GPS spot.**
   - The incident card fills in live: location ✓ (GPS ±10 m), callback ✓, *trapped / wheelchair*. **The card jumps to the top of the queue** and shows the reasons it's ranked there.
3. **Two more callers** (teammates, one in Korean) report smoke on the same street.
   - The console links them as one incident, three independent callers. **Every call stays its own record.**
   - Rule fires: **"3 independent reports of fire in zone ⟨X⟩ in 6 minutes. No evacuation order on file."** A pre-drafted alert appears for a human to approve.
4. **The operator clicks "Take call."** Their phone rings with a whisper: "Spanish-speaking caller, grandmother in a wheelchair, smoke at Lake and Woodbury, GPS verified." The human starts with everything already known.
5. **The supervisor approves the alert.** Voice calls go out in Spanish, Korean and English, to landlines too, with a "say help or press 1" reply. Anyone who says "help" becomes a new card.

**On screen at the end:** *intake done before a human picked up: N seconds · interpreter wait: 0 s (vs 49 s average) · 3 independent callers linked in the time a call-taker spends on one.* (N comes from the demo's own timestamps.)

### 3:00–4:00 · How it holds up (twists, below)
Funding pathway · works in other countries · the poster.

### 4:00–5:00 · What never gets automated, what's next, why it can ship
- **Never automated:** dispatching, deciding who gets help, issuing an alert, or ending an emergency call. The AI gathers. Rules rank. People decide.
- **Why it can ship:** it uses a phone number and a browser. There's no app to install and no new hardware. NENA's 2026 call-processing standard explicitly endorses AI platforms that support 911 operations (§5.6.2, verified).
- **Next:** a pilot with one LA-area emergency communications center or a campus department (USC DPS), funded by UASI/EMPG (customer side) and NSF SBIR (R&D side).

---

## The solution

### Who it's for
| Person | The moment they decide | What DIZA gives them |
|---|---|---|
| **911 call-taker / call-line operator** (primary) | All lines are busy and the queue is growing | A queue ranked by rules, a pre-filled card, a whispered handoff |
| **Overnight supervisor / emergency manager** | "Do we warn this neighborhood now?" | Clustered, independent ground reports for zones with no order yet, plus an alert draft to approve |
| **Caller** | "Is anyone going to answer?" | Answered in their language right away, never dropped, location captured |

### What each part does
| Part | Job | Built? |
|---|---|---|
| **AI intake (Retell voice agents)** | Answers instantly in EN/ES/KO/ZH. Asks in NENA order: location → callback → **on scene or calling for someone else?** → what → people → hazards/access needs. (The relationship question separates on-scene callers from relatives far away, the Palisades duplicate problem.) Reads location back. Sends a GPS link when the caller is unsure. **Decides nothing.** | ✅ agents, location link, live transcript; prompt rewrite to intake-only ⏳ |
| **Rules engine (backend, no LLM)** | Priority score with stated reasons · on-scene vs third-party flag · jurisdiction (incident location → agency + transfer number, so a caller in Boston reporting LA gets the LA agency) · duplicate clustering (each call kept) · zone with no order → alert evidence · completeness check | ✅ triage (DS), clustering, geocoding · ⏳ jurisdiction, completeness, "no order" rule |
| **Automatic official context** | For each incident location: NWS alerts, evacuation zone, nearest shelter, attached automatically. No one types it in | ✅ shelters/resources · ⏳ NWS feed |
| **Operator console** | Queue by priority then wait time · live card + transcript · map · "Take call" (warm transfer + whisper) · priority callback when nobody is free | ✅ console, map, transcript, transfer · ⏳ queue sort, completeness, Take-call button |
| **Approved alerts** | Human approves the exact text → batch voice calls in each person's language → replies become cards | ✅ built and safety-railed |

### What we cut (on purpose)
The services desk, forms, check-in calls, community Q&A, the volunteer inbox and the web chat are all in git and out of the pitch. One problem, one pipeline.

---

## How it meets the judging criteria

| Criterion (1–5 each) | Our evidence |
|---|---|
| **Dual-use fit** *(decides ties)* | **Ordinary Tuesday:** the same intake runs a center's **non-emergency and overflow line** every day: noise complaints, welfare questions, out-of-area transfers, callers in Korean at 3 AM. NENA §5.6.2 describes exactly this use. **Crisis day:** the same tool absorbs the surge and feeds alerts. Second customer: **USC DPS / a campus safety line**, every night. |
| **Technical execution** | It's live: a real phone number, 9 Retell agents, a deployed backend, a live map, live transcripts, GPS links, warm transfer with whisper, batch alert calls. Tests: 36 backend, 17 safety cases. |
| **Feasibility + impact** | No app, no hardware: a phone line and a browser. **LAPD's own plan asks for this:** AI as "a tool for PSRs … not an automated call-taking service," with who/what/where summaries and two-way translation [V]. 86% of 911 staff are comfortable with AI assistance, but only 4% use call screening (2025 national survey [V]). **Impact:** callers who'd wait (43% of LAPD 911 calls miss the 15-second standard) are answered at once; the interpreter wait drops from 49 s to 0; duplicate grouping is automatic instead of manual. |
| **Adapting to twists** | See below. Each twist changed the build, not just the slides. |
| **Demo + pitch** | A judge's own phone call drives the demo. Nothing is canned. |

### Retell track criteria (Resilience Comms)
| Retell asks | DIZA |
|---|---|
| A working voice/text flow with Retell agents | Inbound intake, language agents, warm transfer, outbound alert batch calls, an SMS tool, a chat agent |
| Works when **networks are weak** | Plain voice calls, so it works from landlines and basic phones with no data. Alerts go out as voice calls, not app pushes. GPS link is optional: spoken location always works. *Limit:* it can't fix downed towers. |
| Works when **people speak different languages** | EN/ES/KO/ZH natively. Wireless Emergency Alerts only come in English and Spanish (verified), so Korean and Mandarin speakers are reached here and nowhere else |
| **Who it reaches that today's alerts miss** | Non-English speakers, landline-only and older residents (no smartphone push), and people who can't get through to a busy line |
| Everyday use that still works in a crisis | The non-emergency/overflow line every day; surge intake on crisis day |

### The track's three questions, answered
- **"How do you tell who needs a person right now?"** Stated rules, not AI judgment: P0 words, trapped, injured, vulnerability, wait time. The card shows why.
- **"What must never be automated?"** Dispatch, alert approval, deciding who gets help, ending an emergency call.
- **"What happens when someone doesn't pick up?"** Alerts retry no-answers (up to 3) and mark voicemail and unreachable separately. Dropped intake calls get a priority callback card. Nobody falls through silently.

### The three kickoff tests
- **Ordinary day:** who pays on a calm Tuesday? The communications center or campus, for its non-emergency/overflow line.
- **3 AM, network down, staff gone:** the AI still answers, gathers and queues. With no humans, every caller gets a priority callback code, and the supervisor sees the whole picture on arrival.
- **Travel / a tenth of the budget:** a phone number and a browser, about $0.10–0.15 per minute, region settings per country (twist 2).

---

## Twists

| Twist | What changed in the **build** | Proof |
|---|---|---|
| **1 · Funding pathway** | Costed the pilot. Mapped the buyer (a communications center or emergency-management office) to the money: **FEMA UASI/EMPG** (customer-funded pilot), and **NSF SBIR Phase I** (up to $305K; next deadline Mar 4, 2027) for the R&D risk. **I-Corps** for discovery interviews with LA 911/EOC staff. | `twists/FUNDING.md` (sources) |
| **2 · Go global** | Agents run on **region variables**: emergency number, crisis line, info line, service area, language. One config switches the US to the UK (999), the EU (112) or Korea (112/119) without code changes. Telephony abroad goes through Retell SIP trunks. Countries where it **can't** work as-is: China (licensing and data law) and languages Retell doesn't support (Yoruba, Hausa). | `twists/GLOBAL.md`, region vars in `agents/*.llm.json` |
| **3 · Poster** | One-page poster built from the pipeline diagram, the demo screenshot and three numbers. Due with Devpost at 10 PM. | *to make* |

---

## Competitors (from the research; the gap is plausible, not proven)
- **Non-emergency lines only:** Aurelian, Hyper (now Motorola), Axon's agent work.
- **Assist after a human answers:** Prepared/Axon (transcription, translation), Carbyne (location and video links), RapidSOS (location and data).
- **What no one does that we found:** gathering and verifying intake while the caller is still in the queue, plus linking independent callers into evidence for an alert decision.

## Biggest risk (say it before a judge does)
Whether Cal OES or agency policy allows any automated answer **on 911 lines themselves** is unverified. Our deployment path doesn't depend on it:
1. Start on the **non-emergency and overflow line**, which NENA §5.6.2 explicitly endorses.
2. Run as an **assist** for call-takers: summaries, translation, duplicate linking, jurisdiction lookup.
3. Add intake during the 911 queue only where policy approves it.

## Corrections to our earlier docs
- The "38-year-old" system in the LA fire reviews is **LASD's dispatch (CAD) software**, not a network [V].
- Early 911 reports in Altadena included invalid addresses and undamaged homes. DIZA shows **how many independent callers agree**; it never claims a fire exists.
- `planning-claude/REACH.md` says Genasys "needs a smartphone app". Wrong: it also sends SMS and voice.

## Responsible-use note (Devpost requires one)
DIZA never dispatches emergency services and never decides who gets help. A human approves every alert, and every alert names its target zone; the January 2025 LA County false alert to about 10 million phones (secondary sources) is why. Calls carry a California recording notice. Location comes only from what the caller says, or from a link they choose to tap. Transcripts are PII-scrubbed and kept 7 days. Drill mode is on for the hackathon: transfers go to teammates, never to real 911 or 988.

## Open before submission
- Re-check every slide number against the source URLs in the research files.
- Build the ⏳ items in this order: intake-only prompt → queue sort + completeness → "no order yet" cluster rule → jurisdiction → NWS context.
- Record a backup demo video. Make the poster.
