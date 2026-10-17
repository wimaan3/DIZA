# 04 · Biomech: domain safety, people ops, twists, pitch and every deliverable

> **Paste to your AI agent:** "You support the biomech/domain lead of team DIZA at the InnovateLA Dual-Use Hackathon (Resilience Comms / Retell AI). Read `sessions/planning-claude/handoff/04_BIO_DOMAIN_OPS_STORY.md` and `00_CONTRACTS.md` in https://github.com/wimaan3/DIZA (branch `main`), then the referenced docs. Produce form schemas (`agents/forms/`), medical/vulnerability lexicon additions (`config/lexicon.yaml` via PR to DS), KB content, skill taxonomy, and all hackathon deliverables in `docs/` (deck, video script, Devpost text, TWISTS.md, TOOLS.md, Q&A). Work on `bio/<topic>` branches, notes in `sessions/bio-domain/` with a SESSION_CONTEXT.md. Verify every phone number and statistic with a source. Meet the acceptance criteria."

**Read first:**
- `00_CONTRACTS.md`
- `REQUIREMENTS_TRACE.md`
- `DECK.md`
- `DEMO.md`
- `COMPLIANCE.md`
- `REACH.md`
- `INTAKE.md`
- `CALL_SCHEDULE.md`
- `TWISTS_TEMPLATE.md`
- `SYSTEM_SPEC.md`
- `sources/README.md`

**Mission:** make it medically and humanly credible, get real people calling and helping, and turn the build into a submission that wins Round 1 (judged from Devpost only) and a 5-minute pitch.

## Tasks

### P0: tonight (now → 11:30 PM)
- [ ] **Help desk questions** (write answers into `sessions/bio-domain/SESSION_CONTEXT.md`):
  - where twist responses are submitted
  - deck rules (blank in the hub)
  - demo video length
  - does the repo need to be public
  - the **Harbor Night Extended Card** (get the text → `sources/harbor-night.md`)
  - OK to announce the drill on WhatsApp
  - how the $10 Retell credits apply
- [ ] Confirm the team is locked in the portal, lens = **Resilience Comms**, **≥1 USC student**. Complete all profiles (+10 fun).
- [ ] **Devpost** project created, all 4 joined, lens set; `docs/TOOLS.md` started (Retell, model, Twilio, Supabase, FastAPI, React/Leaflet, scikit-learn, Claude Code, IBM Bob if used).
- [ ] **Decide with the team** the headline second customer. Recommended: *council district senior-services line, every Tuesday 10 AM*; USC campus line = live pilot.

### P0: overnight → M1
- [ ] **Form schemas** `agents/forms/*.yaml` (format in INTAKE.md):
  - `medical_appointment` (sandbox clinic; `safety_check` for urgent symptoms)
  - `evacuation_assistance` (mobility, oxygen/power-dependent devices, pets, people count, transport)
  - `maintenance_request`, `escort_request`, `lost_item`, `shelter_need`, `checkin_enrollment` (pending consent), `volunteer_registration`
- [ ] **Medical + vulnerability lexicon** (PR to DS): the phrases people actually say, EN + ES (+ KO/ZH if you can get help):
  - "can't catch my breath", "my sugar is low", "face is drooping", "chest feels tight", "he's not waking up"
  - oxygen / dialysis / ventilator / CPAP / wheelchair / walker / bedbound
- [ ] **Skill taxonomy + pools + fatigue rules** → `config/skills.yaml`, `config/pools.yaml` (with DS): which categories each pool may take; max concurrent per responder; rotate heavy calls.
- [ ] **KB content** (Markdown, sourced, phone numbers **verified**):
  - `campus-faq`
  - `la-resources`: 911, 988, 211 LA, 711 relay, USC DPS + counseling 24/7, LA County APS, CA child abuse hotline, county emergency site, Red Cross shelters
  - `line-policy`: what the line can and can't do, not 911, privacy
  - preparedness guides (go-bag, evacuation) in EN/ES
- [ ] **Twist write-ups:** for each twist (11:30 PM · 4:30 AM · 7:00 AM), run the 15-min huddle, then fill `docs/TWISTS.md` with whoever changed code: what changed, why, proof (commit, test, clip, metric). **Submit before the 6-h mark.**

### P1: Saturday morning
- [ ] **People ops:**
  - recruit **6–8 supporters** (skills + languages; trained-listener and medical people where possible) and drill callers
  - put the roster into the supporter app
  - brief supporters on P0 → 911/988 and never-share rules
- [ ] **Promotion:**
  - posters + QR in RTH 526
  - Instagram Story (18+, "help us stress-test at 3:30")
  - announcement copy from `CALL_SCHEDULE.md`
  - organizer OK before using their WhatsApp channel
- [ ] **Mentors** (non-judges): Abhi Nemani (govtech / what a city buys), Alison Frazzini (county), Justin McEwen (national resilience), Ayush Kumar (AI agents). One decision question each.
- [ ] **Consent tracking:** drill-call `feature_consent` list; only those clips get used.

### P0: Saturday afternoon → M3/M4 (the submission IS the Round 1 score)
- [ ] **Deck** (10 slides per DECK.md):
  - title + QR
  - Altadena problem
  - seat / moment / **rungs = ASK + HAND TO A PERSON**
  - live demo
  - who needs a person
  - when nobody picks up
  - never automated
  - twists
  - Tuesday customer
  - reach + feasibility + ask
  - Appendix: architecture, scoreboard, responsible use.
- [ ] **Demo video** (2–3 min, captions on) cut from the **3:30 Surge Drill** recording: Instagram/campus callers, Ops Wall, P0 whisper transfer, Declare, ladder reaching the daughter, Korean enrollment, twists + scoreboard, Tuesday customer.
- [ ] **Devpost write-up:**
  - name + lens + one line ("DIZA: the everyday community call line that becomes a 3 AM crisis line, triaging every caller, in their language, to the right human first.")
  - inspiration, what it does, how built, twists, **results (DS numbers)**, challenges, next
  - **responsible-use 2 lines**
  - tools list
  - team, repo
- [ ] Say the required lines (DECK.md "Lines we must say"): second customer + day, two rungs, the three answers, pre-emptive, the automation framing, reach, which way we lean, honesty about simulated calls.
- [ ] **Submit by 9 PM** (hard 10 PM). Then rehearse at 9 PM.

### Sunday
- [ ] 8 AM rehearsal; cell-signal test in Ginsburg Hall; confirm the demo in the app **by 9 AM**; finalist deck by 9 AM.
- [ ] **Q&A doc** (`docs/QA.md`):
  - false positives, hoax floods
  - privacy/consent
  - cost (~$1/resident/month)
  - why not 911
  - AI failure → fallback
  - A2P SMS timeline
  - HIPAA
  - how a city buys it (Open311, pilot)
  - volunteers' safety/vetting
- [ ] **Present** the pitch. Run the audience call-in ("phones out, scan, call at zero").

### P2
- [ ] Physiological voice-marker spec (breathlessness, slurring/dysarthria, cough, tremor) with thresholds + sources → DS for acoustic flags.
- [ ] National-resilience appendix slide (base family-support lines, VA check-ins, Guard surge lines).

## Hand-offs
- **You need:**
  - DS: numbers by 6 PM, scoreboard
  - CS#1/CS#2: twist diffs, screenshots, the drill recording
- **You give:** forms, lexicon additions, KB content, skills/pools, roster, all deliverables.
