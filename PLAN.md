# DIZA — Game Plan (InnovateLA Dual-Use Hackathon, Resilience Comms × Retell AI)

> Working name. Rename freely.
> Submit on Devpost by **Sat 10 PM** (aim for 9 PM). Devpost links lock **Sun 11 AM**.

## 1. What we're actually being asked

- **Seat:** the overnight supervisor of a call line.
  - A surge of calls and alerts nobody can verify, and too few people to answer them.
  - *"Residents are your earliest sensor and your biggest flood."*
- **Kickoff one-liner:** *"In a crisis, call lines flood faster than people can answer. How do we get the right callers to a human first?"*
- **Three questions we must answer explicitly:**
  1. How do you tell who needs a person right now?
  2. What must **never** be automated?
  3. What happens when someone doesn't pick up?
- **The response ladder:** watch → ask → slow → hold → hand to a person. Our build lives on **watch + ask + hand to a person**. Elegant beats loud: no "alert everyone".
- **Dual-use here does NOT mean military vs. civilian.** The organizers say explicitly: *"it does not mean weapons. It means a tool worth owning before the emergency."*
  - Score it as **ordinary Tuesday + crisis night**, with the same tool already in place.
  - Defense, VA and base family lines are a market-expansion slide, not the core.
- **The kickoff deck's three tests:**
  - **Ordinary day:** who pays on a calm Tuesday?
  - **Crisis:** what does it do at 3 AM with the network down and staff gone?
  - **Travel:** does it work on a tenth of the budget?
  - Say out loud which way we lean before a judge does.

### Who's judging and mentoring (from the roster PDF): pitch to *them*

- **City people are on the jury:**
  - Betty Lieu (Torrance councilmember)
  - Brad Waller (Redondo Beach Mayor Pro Tem)
  - Andy Wilson (ex-vice mayor, USC)
  - Krystal Ayala (SCAG regional planning)
  - an ex-White House judge
  - **Sell to them:** "your council office can run this for your seniors on Tuesday" is a pitch they can picture buying.
- **Defense and federal people are on the jury too:**
  - Matthew Finney (Accenture Federal, Data & AI)
  - a special-ops veteran
  - ex-Navy EOD Josh Duntz
  - Mert Turna (YC)
  - Tariq Nazar (Mithrandir Dynamics)
  - The roster's own scorecard phrases dual-use as *"Does it serve everyday LA **and national resilience** at once?"*
  - **So** the military and national angle earns a strong slide: the same stack serves base family-support lines, VA wellness check-ins, or a FEMA or National Guard surge line. Keep the core story LA everyday + crisis.
- **Finney's talk is titled "The Great Inversion":** *"AI made building cheap. Knowing which problem to solve is now the scarce skill."* Lead the pitch with the **problem choice** (Altadena), not the tech.
- **Mentors to book first (Saturday):**
  1. **Abhi Nemani** (LA's first Chief Data Officer, govtech): procurement, and what a city would actually buy.
  2. **Alison Frazzini** (LA County Chief Sustainability Office): county emergency context.
  3. **Justin McEwen** (FedTech, USAF): the national-resilience framing.
  4. **Ayush Kumar** (AWS, AI agents): the agent architecture.
- **Avoid lobbying judges as mentors.** Sobti, Turna and Nazar also mentor, and judges who mentored us carry less weight.

## 2. Scorecard → how we win each line

| Criterion (1–5) | Our answer |
|---|---|
| Dual-use fit (tie-breaker!) | **Name the second customer and the day.** Every Tuesday at 10 AM, a home-care agency or senior-housing operator runs multilingual wellness check-in calls to its residents. On crisis night the same agent, number and resident list become the surge line and the evacuation call-down list. |
| Technical execution | A real Retell phone number judges can call. Live dashboard. Real outbound callbacks, SMS fallback and warm transfer. |
| Feasibility & impact | Retell and Twilio are off-the-shelf. Pilot with a home-care agency, 211LA or a council office. Metric: time-to-human for the highest-risk callers, and % of registry residents reached. |
| Adapting to twists | Every twist changes the **build**, not just the slides. Log each one in `TWISTS.md` (what changed, why, proof). This also enters us for *Best Shift Adapter*. |
| Demo & pitch | Working thing first: a judge calls the number live in Spanish or Korean and their call pops onto the board. |

## 3. Retell prize checklist (judged with Retell)

- **Working voice + text flow:** inbound voice agent, outbound callback agent, SMS fallback and inbound SMS reports.
- **Weak networks:**
  - Plain voice calls and SMS work on landlines, flip phones and one bar of signal. No app required.
  - If the AI or the backend goes down, calls fall back to a plain recorded message and voicemail.
- **Different languages:**
  - Retell supports Spanish, Korean, Mandarin, Cantonese, Armenian, Tagalog, Vietnamese, Farsi, Russian and Japanese.
  - Show at least one live non-English call.
  - Deepgram and Soniox can switch language mid-call. Armenian and Tagalog run on Azure, one language per call.
- **Reaches who today's alerts miss:**
  - Wireless emergency alerts go out only in English and Spanish. A UCLA study found 12,000+ Asian Americans in the 2025 evacuation zones couldn't understand them.
  - Eaton fire victims had a median age of 77, and about a third had mobility impairments.
  - We **call** people on a registry instead of hoping they read a text.
- **Dual-use:** the Tuesday check-in service (above).
- **Use Retell features visibly:**
  - warm transfer with a **whisper briefing** to the human
  - agentic warm transfer: if the human doesn't answer, the call returns to the AI
  - batch outbound calls
  - voicemail detection
  - SMS during a call
  - post-call analysis fields (urgency, hazard, location, needs)
  - custom functions
- **Go to Retell's 10:30 AM Saturday session** with one specific question. Ask the Retell people for feedback on the demo.
- Use the $10 credits early. Buy or claim the number tonight.

## 4. Prior art: what to harvest and where the gap is

| Existing | Steal | Gap we own |
|---|---|---|
| **Aurelian** (YC; AI on 911 non-emergency lines) | Narrow scope plus "detect emergency → human" | Inbound only. No outbound calls, no corroboration. |
| **Hyper** (police non-emergency AI) | An allowlist of what the AI may handle; texting a link mid-call | Police only |
| **Carbyne** (911 triage) | **Cluster duplicate calls**, then tell callers "we already know about the fire at X" | Locked inside the 911 stack; ignores people who never call |
| **CheckWellCall / SeaVoice / Joy Calls** | Scheduled AI wellness calls (our Tuesday use) | Not connected to emergencies or evacuation zones |
| **Everbridge / Genasys / NotifyLA** | Evacuation-zone IDs; "reply YES" confirmations | One-way or fixed replies; no callback ladder; English and Spanish only |
| **LA County SNAP registry** | Opt-in list of vulnerable residents | Static list that nobody calls |
| **New Orleans 311 bot** | What *not* to do: it hides that it's an AI | We always disclose |

**Repos to fork:**
- [retell-custom-llm-python-demo](https://github.com/RetellAI/retell-custom-llm-python-demo)
- [retell-custom-llm-node-demo](https://github.com/RetellAI/retell-custom-llm-node-demo)
- Ushahidi's data model, for crowd reports on a map

**Hackathon projects to beat:** AeroRescue, Sentinel (won 1st at AI Tinkerers), Lifeline, VozGuard. None of them used Retell, and none did corroboration or a callback ladder.

**Our five gaps:**
1. **Corroborate before broadcast.** Cluster resident reports by place and time. Require N independent reports, then the AI asks registry neighbours nearby. Then one human taps approve. The AI never broadcasts.
2. **Callback ladder for no-answer.** Call → SMS → retry → emergency contact or neighbour → flag for a human welfare check. Retell has no built-in retries; we build them.
3. **Use the vulnerable-resident registry.** It's called every week, so it is current on the night.
4. **Languages and old phones.** Voice and SMS, pre-approved translated message templates.
5. **Hard "never automate" rules** (section 7).

**Opening story for the pitch (sourced):**
- In the Eaton fire, dispatch got at least 14 resident fire reports while no alert went out for west Altadena.
- West Altadena's first evacuation order came at 3:25 AM; east Altadena's came at 6:48 PM the evening before.
- 17 of the 19 deaths were in the west.
- Two days later, a false evacuation alert went to ~10M phones across LA County.

Residents *were* the sensor; nobody was listening. And the blunt tool, alerting everyone, misfired.

## 5. The product: one agent, two lives

**Tuesday (paid, everyday):** "DIZA Check-in"
- Weekly or daily multilingual wellness calls to opted-in residents: seniors, people with mobility or medical needs. The customer is a home-care agency, senior-housing operator or council office.
- The agent learns each person's baseline: language, how they usually sound, meds, mobility, emergency contact.
- It doubles as the non-emergency overflow line for the same customer.

**Crisis night (same number, same list):** "DIZA Surge"
1. **Watch:**
   - Every inbound call and SMS becomes a structured report (hazard, location, people, mobility, medical) via Retell functions and post-call analysis.
   - Reports are clustered by location and time.
2. **Acknowledge:** callers whose report matches a known cluster hear "we already know about the fire near X; here's what to do." That frees the line.
3. **Ask:**
   - When a new cluster forms but isn't verified, the agent places a few short outbound calls or texts to registry residents nearby: "Do you see smoke on your street?"
   - This turns corroboration into minutes, not hours.
4. **Hand to a person:**
   - The priority queue decides who gets the one human supervisor first.
   - The warm transfer whispers a 10-second brief: "Spanish speaker, 81, oxygen-dependent, smoke in the house, address confirmed."
   - The supervisor approves any public alert with one tap. The AI only drafts it.
5. **No-answer ladder:** registry residents inside the affected zone get called. If there's no answer: SMS → retry at +5 min → emergency contact → flagged red for a human welfare check.

**Voice-intent layer (data science + biomech): our differentiator**
- **Text signals (live):** intent, urgency and keywords (trapped, can't breathe, chest pain, child alone) from the transcript.
- **Acoustic/physiological signals:**
  - breathlessness and coughing (smoke inhalation)
  - slurred or slow speech (stroke, low blood sugar)
  - panic markers: speech rate, pause ratio, pitch variability
  - background sounds: smoke alarm, siren, crying (YAMNet audio classifier)
- **Rule: signals can only escalate, never de-escalate.** No one is deprioritized by a model.
- **Feasibility check (do first):** can we get live audio from Retell mid-call?
  - **Fallback A:** score from transcript timing during the call.
  - **Fallback B:** run full acoustic analysis on the recording right after the call (post-call webhook). It feeds the callback and priority queue.
  - The Tuesday check-ins also give a **personal baseline**. "Mrs. Kim sounds more breathless than her last 6 calls" is far stronger than a population model, and it's a great dual-use line.

## 6. Architecture (keep it boring)

```
Phone (voice/SMS) ──► Retell agent (multi-prompt, functions, transfer, SMS)
                          │  function calls + webhooks (call_ended, post-call analysis)
                          ▼
                   FastAPI backend (Python) ── SQLite/Postgres
                   ├─ /report  (structured reports)
                   ├─ clustering + corroboration engine (DS)
                   ├─ priority scorer (text + acoustic flags)
                   ├─ callback ladder scheduler (Retell create-phone-call + SMS)
                   └─ WebSocket ──► Supervisor dashboard (React + Leaflet map)
                                     priority queue · clusters · ladder status · [Approve alert]
Simulator script ──► /report  (floods 200 synthetic multilingual calls for the demo)
Audio worker ──► pulls recording URL → librosa features + YAMNet → escalate flags
```

- Hosting: Render, Railway or Fly for the backend. ngrok while developing.
- Synthetic data: ~500 fake registry residents across Altadena and Northeast LA. Language mix from census figures (Spanish, Armenian, Korean, Tagalog, Mandarin). Mobility and medical flags. Emergency contacts.
- **IBM Bob bonus:** use IBM Bob for part of the backend or tests and write up how on Devpost. It's an extra prize shot for little cost.

## 7. Never-automate rules (also the Responsible-use note)

- The AI never sends a public alert or declares an area safe. A human approves every alert.
- The AI never closes, deprioritizes or voicemails-out a call that mentions trapped people, a medical emergency, a child alone, or self-harm. Those go to a human immediately, or the caller is told to dial 911.
- Voice and physiology signals can only **raise** priority.
- The AI always discloses that it is an AI. Nobody is ever stuck in a loop: "press 0 / say 'person'" works at any time.
- Registry is **opt-in** and minimal: name, language, address, needs, contact. Retention limits, no selling, and the resident can delete their data.
- **Misuse and mitigation (2 lines for Devpost):**
  - Risk: hoax or swatting floods could fake a cluster. Mitigation: corroboration requires independent sources plus human approval.
  - Risk: the registry is a sensitive list. Mitigation: opt-in, encrypted, role-based access, used only for safety calls.

## 8. Roles (CS ×2, data science, biomech)

| Person | Owns | Concrete deliverables |
|---|---|---|
| **CS #1 — Voice/Retell lead** | Everything inside Retell | Phone number; inbound agent (multi-prompt: intake → match cluster → escalate); outbound check-in and callback agents; custom functions → backend; warm and agentic transfer with whisper; SMS; language setup; voicemail handling; Retell fallback message. Attends the Retell session at 10:30 AM. |
| **CS #2 — Backend + dashboard** | Data flow and the screen judges see | FastAPI, DB, webhooks; callback-ladder scheduler; WebSocket; dashboard (queue, map, clusters, ladder, approve button); deploy; demo simulator; IBM Bob write-up. |
| **Data science** | Triage brain | Synthetic LA registry and call dataset; clustering (DBSCAN on location and time) and corroboration threshold; priority score (transcript fields + acoustic flags); acoustic features (librosa) + YAMNet alarm and cough detection; pitch metrics (time-to-human, % reached, simulated vs. baseline). |
| **Biomech** | Human-body signals + the story | Spec which physiological voice markers matter and why (breathing rate and breathlessness, dysarthria and slurred speech, cough, vocal tremor), with thresholds and sources. Helps DS validate on recorded samples. Designs the registry fields for mobility and medical needs. **Also owns** the pitch deck, demo video, Devpost page, `TWISTS.md`, responsible-use note, mentor bookings, sourced stats. |

Everyone: the **twist huddle** (15 min after each twist) and rehearsing the demo.

## 9. Timeline (PT)

| When | Goal |
|---|---|
| **Fri now → 9 PM** | Lock team in portal (track: Resilience Comms; help with: domain/emergency-mgmt, policy, pitch). Ensure one USC student is on the team (needed for the incubator). Claim Retell credits and phone number. Start IBM Bob trial. Repo scaffold. |
| **9 PM → 11:30 PM** | **Thin slice end-to-end:** call the number → agent intakes in English and Spanish → function posts report → it appears on the dashboard. Nothing else matters until this works. |
| **11:30 PM Twist 1** | Huddle 15 min → decide the build change → log it in `TWISTS.md` → respond by 5:30 AM. |
| **Overnight shifts** | CS#1 and DS sleep 12:30–4:30. CS#2 and Biomech sleep 4:45–8:45. Someone is always awake for the twists at 4:30 AM and 7:00 AM. |
| **Sat 4:30 AM Twist 2 / 7:00 AM Twist 3** | Same drill; responses due 10:30 AM and 1:00 PM. |
| **Sat morning** | Clustering + "we already know" acknowledgement; outbound callback ladder; registry; second language live. Book mentors (emergency management, 911, Retell). |
| **10:30 AM** | Retell session (CS#1 + one more). |
| **Sat 2 PM** | **Feature freeze.** Acoustic layer is in, or it ships as post-call only. |
| **2–6 PM** | Polish dashboard, simulator, hardening, record backup demo video. |
| **6–9 PM** | Deck, Devpost write-up (name + lens + one line, deck, video, repo, teammates, responsible-use, tools used, IBM Bob), final video. **Submit by 9 PM.** |
| **Sun 9 AM** | Finalist deck due / confirm demo in the app (no confirmation = no judge feedback). |
| **Sun 12 PM** | Demo floor (if not finalist): 3-minute live demo, QR code "call it yourself" for People's Choice. |

## 10. The 5-minute pitch (Round 2) / 3-minute demo

1. **0:00–0:30 Problem.** Altadena: 14 resident reports, alert hours late, 17 of 19 deaths in the west. Two days later, ~10M phones get a false alert. "Residents were the sensor. Nobody was listening, and the loud button misfired."
2. **0:30–2:30 Show it.**
   - A judge calls the number and speaks Spanish or Korean; their pin pops onto the map.
   - The simulator floods 200 calls and they collapse into 3 clusters.
   - The agent texts two neighbours to corroborate. The supervisor taps approve.
   - Mrs. Kim (registry, 81, oxygen) doesn't pick up → SMS → her daughter is called → flagged red. The live warm transfer plays the whisper brief on speaker.
3. **2:30–3:30 Twists.** "Here's what changed in the build after each twist, and why." Show the diffs.
4. **3:30–4:30 Tuesday + next.**
   - "Every Tuesday at 10 AM, this same agent checks in on 500 residents in six languages. That's why it's current on fire night."
   - Who pays: a home-care agency, senior housing or council office. Pilot path via 211LA.
   - Travel test: voice and SMS only, works on flip phones and on a tenth of the budget.
5. **4:30–5:00 Never-automate rules + ask.**

**Backup:** a pre-recorded video of the full flow on a laptop, in case Wi-Fi or a phone dies.

## 11. Likely twists → pre-built switches

Build these as config flags so a twist means flipping a flag plus a small diff:
- **Cell or data network degraded** → SMS-only and landline mode; shorter calls; text-first callbacks.
- **Zero human staff** → AI holds a numbered queue and promises a callback time; priority callbacks when a human logs in.
- **A false or erroneous alert went out** (the prompt's theme) → correction call-down to the affected list, plus a "did you evacuate because of the alert?" check.
- **Our own automation misbehaves or goes quiet** (the core prompt!) → heartbeat monitor on Retell and the backend; auto-failover to a recorded message + voicemail + SMS intake; supervisor alarm.
- **Language surge** (e.g., an Armenian-speaking area) → route to a language-specific agent.
- **Hoax or flood attack** → corroboration threshold rises; one number's repeat calls get collapsed.
- **Power outage** → callers' phones are dying; keep calls under 60 seconds and prioritise SMS confirmations.

## 12. Easy points we shouldn't leave on the table

- Complete portal profile (+10 Most Fun Team points); play the Midnight Games (Sat 10:30 PM).
- Bring friends Sunday for People's Choice; QR code on the table.
- Judges who mentored us carry less weight, so seek mentors for the *questions*, not for lobbying.
- List every tool used (rule 4). Add the 2-line misuse note (rule 7).
