# Session context: planning-claude

- **Session:** Claude Code planning session (https://claude.ai/code/session_01NYBe2Xjj43hYTW7eJNMXKM)
- **Branch:** `claude/relaxed-goodall-tmz8gz`
- **Scope:** strategy + architecture planning for the Resilience Comms track (Retell AI). No app code yet.

## Files in this folder
| File | Contents |
|---|---|
| `PLAN.md` | Master plan: requirements checklist, scorecard strategy, Retell prize checklist, prior art, product concept, zone escalation ladder, skills routing, flood handling, campus drill, call analytics, agent actions, architecture, never-automate rules, roles, timeline, pitch, twist prep |
| `SETUP.md` | Accounts and infra: Retell (KYC, number, agent type, functions, transfer, outbound, webhooks), SMS limits, Twilio/Supabase/hosting, build-vs-reuse |
| `TRIAGE.md` | Keyword tiers (P0–P3 + vulnerability boosters), context guards, per-call label schema, cross-call crisis detection thresholds, routing map |
| `WORKFLOW.md` | End-to-end flows (inbound, outbound, escalation, supporter, learning loop) + team process (branches, stand-ups, twist protocol) |
| `RETELL_GUIDE.md` | Retell MCP server, CLI/SDK, agents-in-git push script, agent swap between agents, knowledge base split, high-leverage settings, simulation testing |
| `COMPLIANCE.md` | Laws and rules (recording consent, TCPA/AI voice, 988, no false dispatch, privacy, accessibility) and where each is enforced: prompt / backend / KB |
| `INTAKE.md` | Forms engine (slot-filling with clarifying questions), case files attached to routed profiles, sandbox "service world" (clinic / 311 / utility) vs. real supporters, production adapters (FHIR, Open311) |
| `EVALS.md` | Light eval flywheel: golden set from role cards, code checks first + calibrated LLM-as-judge, team as humans in the loop, one wheel spin per flood, scoreboard + publish gate |
| `DEMO.md` | 5-min pitch beat sheet, 3-min demo-floor version, setup, backups, rehearsal, Q&A prep |
| `OPS_WALL.md` | Real-time big-screen visualization (panels, data sources, Supabase realtime, replay mode, privacy masking) + live audience-call demo script and safeguards (concurrency, room noise, cell signal, planted calls, simulator top-up) |
| `CALL_SCHEDULE.md` | Open Line hours, flood drill windows, role cards, pre-flight checklist, announcement copy |

## Decisions made (with the user)
1. **Track:** Resilience Comms (Retell AI). **Use Retell** and target its prize explicitly.
2. **Team:** CS, CS, data science, biomech. Roles in PLAN.md §8.
3. **Concept:**
   - One Retell agent with two lives: ordinary-day check-ins + concerns line; crisis-night surge triage.
   - Second customer: home-care agency / council office / **USC** (campus concerns line).
4. **Dual-use framing:**
   - Lead with the everyday LA + crisis story. The hub explicitly says dual-use ≠ weapons.
   - The roster scores "everyday LA **and national resilience**", so use the military/national angle as an expansion slide.
5. **Voice intent:** transcript + keywords live; acoustic and physiological flags (breathlessness, slurring, alarms) **after the call**, since Retell has no server-side live audio. **Signals only escalate, never de-escalate.**
6. **Mode switching:**
   - Per-zone ladder: normal → watch (auto) → ask (auto) → crisis (**human declares**) → stand-down (**human only**).
   - Dead-man's switch: if nobody acknowledges within ~5 min, the system calls only the highest-risk residents. Never sends public alerts.
7. **Skills-based routing** (biomech's idea): responder profiles (skills, languages, load); never wait for a specialist on a critical call.
8. **AI disclosure:**
   - **No upfront AI disclaimer in the crisis greeting** (user's call).
   - The agent never claims to be human and never implies dispatch.
   - The campus test line includes a recording-consent line (California all-party consent).
9. **Flood handling:** the AI answers in parallel; duplicate clustering with "we already know" greetings; callbacks instead of hold; overflow fallback; hoax rate-limits.
10. **Live campus test:** Open Line (Sat 11 AM–9 PM, Sun 9 AM–3:30 PM) + flood drills (Sat 12:30, **3:30**, 8:00 PM; Sunday demo floor) with role cards for ground truth. Safety path: P0 → 911/988, never to volunteers.
11. **Agent actions:** create_request, request_escort, reminders/callbacks, book_appointment, enroll_checkin, notify_contact, check_status, lookup_info, send_summary. Confirm before acting; never claim agency dispatch; no writes into real USC/city systems.
12. **Call analytics loop:** baselines → Watch trigger; topic mining → knowledge base; triage calibration; routing stats; failure mining → prompt fixes; weekly "Community Pulse" digest.
14. **Branches:** one per person or agent; `main` = real app only (via PR).
15. **Retell structure:** per-language everyday agents + a crisis agent connected by Agent Transfer; 3 knowledge bases (campus-faq, la-resources, line-policy); live data via functions, not the KB; agents versioned in git and pushed by script; coding agents use the Retell MCP with manual approval.
16. **Intake:** real structured intake via form schemas + clarifying questions; real for our supporters (Google Calendar); third parties (clinics, 311, utility) are a sandbox we control. No submitting into real external systems.
17. **Caching:** answer cache (KB + semantic cache in `lookup_info`, zone-tagged expiry) + function TTL caches + static prompts; Anthropic prompt caching only for our own backend LLM calls.
18. **Evals:** light flywheel, not full AI-eng stack. Code checks first, LLM-as-judge for fuzzy criteria (calibrated vs. 40 human labels), P0 recall + safety = 100% hard gates, one wheel spin per flood (v1→v3).
19. **Live audience calls in the pitch** + an **Ops Wall** real-time dashboard; planted P0 call; simulator top-up stated honestly; replay mode as backup.
13. **Keyword triage:** 3 layers (live lexicon + LLM context + cross-call counts by distinct callers per zone).

## Key facts verified
- **Retell:**
  - Single Prompt agent (multi-prompt deprecated)
  - KYC is required before numbers, outbound or SMS
  - 20 free concurrent calls
  - ~$0.10/min
  - transfer number can be a dynamic variable
  - whisper brief supported
  - batch calls have no retries
  - recordings and word timings available after the call
  - live audio only in a browser
  - transfers don't work on web calls
- **SMS** from our own number needs A2P 10DLC (2–3 weeks), so this weekend we use the Twilio trial (5 verified numbers) or voice/email confirmations.
- **Hosting:** Render free tier cold starts (~1 min) exceed Retell's 10 s webhook timeout.
- **Pitch stats** (sourced in PLAN.md):
  - Eaton fire: 14+ resident reports; west Altadena order at 3:25 AM; 17 of 19 deaths in the west
  - Jan 9 2025: false alert to ~10M phones
  - wireless alerts only in EN/ES; 12k+ Asian Americans couldn't understand them

## Open questions (not yet answered)
- How and where twist responses are submitted; twist texts arrive via the app/WhatsApp
- "Deck Rules" section in the hub is blank: slide limits?
- Demo video length; does the repo need to be public?
- How the $10 Retell hackathon credits are applied
- Organizer OK to announce the drill on their WhatsApp channel
- "Harbor Night in the Extended Card" is referenced in the problem statement but isn't in any doc we have

## Not done yet
- No code scaffolded. Next proposed step: Supabase schema, FastAPI endpoints for Retell functions and webhooks, agent prompts as files + push script, lexicon file, simulator + drill cards, dashboard skeleton.
