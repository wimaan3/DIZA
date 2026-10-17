# 01 · CS#1: Retell voice agents (everything inside Retell)

> **Paste to your AI agent:** "You are building the Retell AI voice agents for team DIZA at the InnovateLA Dual-Use Hackathon (Resilience Comms track). Read `sessions/planning-claude/handoff/01_CS1_RETELL_AGENT.md` and `00_CONTRACTS.md` in https://github.com/wimaan3/DIZA (branch `claude/relaxed-goodall-tmz8gz`), then the referenced docs. Work on branch `cs1/<topic>`, put code in `agents/`, keep notes in `sessions/cs1-retell/` with a SESSION_CONTEXT.md, open small PRs to `main`. Never commit keys. Use the Retell MCP/CLI but keep git as the source of truth. Do the tasks in priority order and check off acceptance criteria."

**Read first:**
- `00_CONTRACTS.md`
- `RETELL_GUIDE.md` (MCP, CLI, agent swap, KB, settings, capacity)
- `SETUP.md` §1
- `TRIAGE.md`
- `COMPLIANCE.md`
- `SYSTEM_SPEC.md` Layer 1
- `INTAKE.md`
- `PLAN.md` (never-automate rules, disclosure decision)

**Mission:** an agent that answers every caller instantly, in their language, does real tasks, finds who needs a person right now, and never does what must not be automated.

## Tasks

### P0: tonight → M0 (Fri 11:30 PM)
- [ ] Retell account (one owner), **KYC** done, ~$30 top-up, teammates invited. Ask organizers how the $10 hackathon credits apply.
- [ ] Buy a **626** number (provider twilio). **Burst concurrency ON.** Set the number's **fallback number** (CS#2's Twilio voicemail line) and `reserved_inbound_concurrency` = 8.
- [ ] Hook up the MCP for your coding agent: `claude mcp add --transport http retell https://mcp.retellai.com --header "Authorization: Bearer $RETELL_API_KEY"`. **Approve each `invoke_api_endpoint` by hand.**
- [ ] `inbound` Single Prompt agent v0 (EN+ES), LLM GPT-4.1-mini or Claude Haiku, structured output, low temperature; `submit_report` wired to CS#2's ngrok URL.
- **Accept:** a web call and a phone call create a row in `reports` and show on the dashboard.

### P0: overnight → M1 (Sat 10 AM)
- [ ] **Prompts in git:** `agents/prompts/{inbound,crisis,checkin,welfare,volunteer}.md` + `agents/*.agent.json`, `*.llm.json`; `agents/pull.py` and `agents/push.py` (update LLM/agent → create version → publish → move `prod` tag; `staging` tag with test transfer numbers).
- [ ] **Inbound webhook variables:** use `{{zone_level}}`, `{{known_incidents}}`, `{{caller_name}}`, `{{language}}`, `{{drill_mode}}`. The greeting branches:
  - normal: everyday greeting
  - watch/ask/crisis: "If you're calling about {{known_incidents}}: we know…"
  - **No upfront AI disclaimer in the crisis greeting.** The drill/test line says: "This call is recorded for a USC student project."
- [ ] **Crisis agent + Agent Transfer (`agent_swap`)** both ways; post-call analysis runs on the crisis agent.
- [ ] **P0 safety path:** on any P0 phrase, call `flag_urgent`, give 911/988, offer a transfer. **Never to volunteers.** Self-harm → offer the 988 transfer.
- [ ] **`route_to_human`** → warm transfer to `{{oncall_number}}` ("Store Fields as Variables"):
  - whisper debrief: "Caller {{caller_name}}, {{language}}. {{brief}}. You got this because {{match_reason}}."
  - agentic warm transfer, ring ~20 s, then retry next / callback
- [ ] **`checkin-outbound` agent:**
  - identifies the service at the start ("This is the … check-in line")
  - "say stop anytime" → `opt_out`
  - voicemail detection: leave a short message
  - "I smell smoke" → swap to crisis
- [ ] `welfare-outbound` agent (crisis call-down, short, gets needs + safe/not safe).
- [ ] Functions wired: `schedule_callback`, `lookup_info`, `create_request`, `set_reminder`, `enroll_checkin` (pending consent), `notify_contact` (consent first), `check_status`, `opt_out`.
- **Accept:**
  - Transfer with whisper works on a real phone.
  - An outbound check-in reaches a teammate.
  - "I want to hurt myself" → 988 offered, no volunteer transfer.
  - "Are you a real person?" → truthful.
  - "Is someone coming?" → no false dispatch.

### P0/P1: Sat morning → M2 (2 PM)
- [ ] **Forms loop:** `start_form` / `fill_form` / `submit_form`, with read-back + "yes" before submit. Forms (from biomech):
  - medical appointment (sandbox clinic)
  - evacuation assistance
  - maintenance
  - escort
  - lost item
  - shelter need
- [ ] **Volunteer intake:** `register_volunteer` → "pending until a coordinator verifies you".
- [ ] **Never-share rule:** never reveal another person's info or status unless `share_status_with` includes the caller (backend enforces).
- [ ] `send_link` (status / photo upload link), `record_consent` (analytics opt-out; `feature_consent` question at the end of drill calls only).
- [ ] `book_appointment` (Google Calendar via the backend), `request_escort`.
- [ ] **Drill mode:** ask for the drill code first if `{{drill_mode}}`; pass it into `submit_report`.
- [ ] **Settings:**
  - boosted keywords (humo, fuego, atrapado, oxígeno, Altadena, Lake Ave, campus building names, shelter names)
  - denoising: remove-noise + **background speech** for floods
  - interruption sensitivity ~0.75
  - reminder ~8 s
  - long silence on crisis → flag for callback
  - `user_dtmf_options`: press 0 = person, press 1 = someone hurt
  - `pii_config` on
  - retention 7 days
- [ ] **Knowledge bases:**
  - create `campus-faq`, `la-resources`, `line-policy` (content from DS + biomech)
  - `agents/kb_add.py` pushes approved `kb_items` via `add-knowledge-base-sources`
  - live data stays in functions, not the KB
- [ ] **Retell simulation tests:** batch tests from `evals/cases/` (mock functions → staging) as a **gate inside `push.py`**. P0 + safety must be 100%.
- [ ] Go to the **Retell session 10:30 AM** (ask: is `update-live-call` reliable for forcing a transfer, and what does a caller hear at the concurrency limit?).

### P1/P2: Sat afternoon
- [ ] Per-language agents: **KO, ZH** (then HY/TL if time), routed via `override_agent_id` from the inbound webhook; "para español / 한국어" swaps.
- [ ] Keypad-only "network degraded" mode (prompt variant + `{{degraded}}` variable) → twist-ready.
- [ ] Backend `update-live-call` push on a missed P0 (with CS#2).
- [ ] Stretch: sandbox-clinic receptionist agent; our agent phones it to book on a caller's behalf.

## Demo / event duties
- Before each flood: balance ≥ $30, burst on, `get-concurrency` OK, staging/prod tags right, run the safety test.
- Sunday: run the phones (planted P0 call, speakerphone for the whisper, Korean enrollment moment).
- Twists: implement the agent-side change; commit = proof; give biomech the diff + the test result.

## Hand-offs
- **You need:**
  - CS#2: endpoints + ngrok/Railway URL, Twilio fallback number
  - DS: lexicon and eval cases
  - biomech: form YAMLs, KB content, medical phrases
- **You give:** agent IDs + KB IDs → `.env` (shared privately, not in git); prompt versions for the scoreboard.
