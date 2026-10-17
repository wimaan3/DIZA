# Retell features we use, and the demo that shows them

Status as of Sat Oct 17 morning. ✅ = configured on our agents in the DIZA workspace (defined in `agents/`, pushed by `push.py`).

| Retell capability | How we use it | Status |
|---|---|---|
| Phone number, inbound + outbound agents | +1 978-915-3497 → inbound `diza-inbound-en-es`, outbound `diza-checkin-outbound` | ✅ (points at drafts until first publish) |
| Agents per job ("nodes"/scenarios) | 7 single-prompt agents: inbound EN/ES, crisis, Korean, Chinese, check-in, welfare, **alert**. Handed off live with **Agent Transfer** (same call, full context). We chose Single Prompt + agent swaps over Conversation Flow nodes: crisis calls don't follow a script, and each agent stays short and testable. | ✅ |
| Functions / custom functions → our API | 21 custom functions (report, flag urgent, route to human, callbacks, forms, escort, appointments, status, opt-out, lookup…) → `/retell/fn/*` | ✅ agent side · backend in PR #4 |
| "Store fields as variables" | `route_to_human` fills `{{oncall_number}}`, `{{responder_name}}`, `{{brief}}`; `lookup_info` fills `{{resource_transfer_number}}` | ✅ |
| Dynamic variables through the whole call | caller name, language, zone, zone level, known incidents, drill mode, alert text… set by the inbound webhook or the batch call | ✅ |
| Transfer to a human immediately | "person" / press 0 → `route_to_human` → transfer | ✅ |
| **Warm transfer with a brief** | private whisper to the human: "Caller Maria, Spanish. Smoke next door, uses a wheelchair. You got this because you speak Spanish and do evacuation help." | ✅ (needs phone call, not web call) |
| Transfer to 988 / resource lines | 988 → teammate stand-in during drills; resource lines only from the allowlist, never in drill mode | ✅ |
| Knowledge bases | `line-policy`, `la-resources`, `campus-faq`, `guides` (all sourced) | ✅ |
| FAQ answering | inbound agent + KBs + `lookup_info` (live/nearest place) + supervisor-approved answers | ✅ |
| Calendar / CRM integrations | `book_appointment` goes through our backend. Option: swap to Retell's built-in Cal.com tool for real bookings (needs a Cal.com account) | backend ✅ · Cal.com optional |
| **Event → automatic call/text** ("mark it ready → call the right people") | supervisor approves an alert → backend starts a **batch call** → per-person outcomes → retry no-answers | ✅ agent + `send_alert.py` · backend in PR #4 |
| **Batch calling from a CSV** | `send_alert.py --alert X.yaml --contacts team.csv` (dry run by default) | ✅ |
| Voicemail detection | outbound agents leave a message; alert voicemail carries the alert | ✅ |
| Post-call analysis | severity, category, people at risk, vulnerability, outcome; alerts: heard / safe / needs help | ✅ |
| PII scrubbing, 7-day retention | on every agent | ✅ |
| Multilingual | EN/ES, Korean, Chinese lines; per-call language override on alert calls | ✅ |
| Concurrency + burst | 20 at once, burst to 60; batch reserves 8 slots for inbound | ✅ |
| **Live monitoring: listen in / take over** | Retell dashboard live calls; API `listen-live-call`, `take-over-live-call` for our console | ⬜ show from Retell dashboard in the demo; console buttons are a CS#2 stretch |
| Inbound webhook (per-caller context, language routing) | contract + agent ready; backend returns `call_inbound` | backend in PR #4 |
| Simulation tests | `safety_check.py` (13 cases, 4 languages) via the playground API | ✅ |
| SMS | needs A2P 10DLC (2–3 weeks) → demo uses Twilio trial to team phones | ⬜ |

## The core use case (what the demo must prove)
**"On the Line": a surge nobody can verify, too few people. Who needs a person now? What's never automated? What if they don't pick up?**

1. **Flood of calls, answered instantly in their language.** 3 teammates call at once (EN, ES, KO). Duplicates hear "we already have 3 reports of smoke near Lake Ave."
2. **The right caller reaches a human first.** Planted P0 ("my grandma is trapped") → 911 instruction + flag on the console. Wheelchair + smoke → **warm transfer** to the matched teammate's phone; the room hears the **whisper brief** on speakerphone.
3. **Never automated.** A supervisor (not the AI) **approves the alert** on the console → one click → **batch alert calls** to opted-in people. The agent reads the approved text word for word and never says "all clear".
4. **Two-way, not a blast.** One recipient says "I use a wheelchair, I can't leave" → intake → callback/transfer. Tally updates live: reached / voicemail / needs help.
5. **Nobody picks up?** No-answers → **retry** → then a human. Show the retry button.
6. **Ordinary Tuesday.** Same line: "where's the nearest cooling center?" → real library 0.6 mi away + "confirm with 211"; Korean caller gets a step-by-step guide.

## Recommended to win (in order)
1. Backend live at a public URL (blocks everything else) → first real call.
2. Twist responses as commits + safety-check proof (Best Shift Adapter).
3. Console: alert panel (draft → approve → live tally) and the call queue with "why ranked here".
4. Record the demo video the moment step 1–3 work; keep it as the backup.
5. Pitch numbers: calls answered, % handled without a person, duplicates merged, time to a human, % reached by alert.
