# 03 · Data science: triage brain, data, evals, numbers

> **Paste to your AI agent:** "You are the data scientist for team DIZA at the InnovateLA Dual-Use Hackathon (Resilience Comms / Retell AI). Read `sessions/planning-claude/handoff/03_DS_TRIAGE_DATA_EVALS.md` and `00_CONTRACTS.md` in https://github.com/wimaan3/DIZA (branch `claude/relaxed-goodall-tmz8gz`), then the referenced docs. Build a pure-Python package at `backend/app/triage/` with unit tests, configs in `config/`, analysis in `analysis/`, simulator/drill content in `sim/`, eval cases in `evals/cases/`. Work on `ds/<topic>` branches, notes in `sessions/ds-analytics/` with a SESSION_CONTEXT.md. No real personal data in git. Do the tasks in priority order and meet the acceptance criteria."

**Read first:**
- `00_CONTRACTS.md`
- `TRIAGE.md`
- `EVALS.md`
- `REACH.md`
- `SYSTEM_SPEC.md` §2.4, §2.7, §3
- `PLAN.md` (call analytics, mode switching, skills routing)
- `CALL_SCHEDULE.md` (role cards)
- `DECK.md` (numbers needed)

**Mission:**
- decide who needs a person right now
- detect when a zone is in crisis
- match callers to the right helper
- prove it with numbers

## Tasks

### P0: tonight → M0/M1
- [ ] **Synthetic data** (`analysis/synth.py` → seed SQL/CSV):
  - ~500 residents across `altadena`, `usc_campus`, `san_pedro_wilmington`
  - language mix weighted by **Census ACS** (language spoken at home by tract), age 65+ share, needs (mobility, oxygen, dialysis, lives alone), contacts, consent flags
  - 8–12 responders with pools, skills, languages
- [ ] **`config/zones.yaml`** (polygons; GeoHub or hand-drawn), **`config/settings.yaml`** thresholds.
- [ ] **`config/lexicon.yaml` v0:** tiers P0 / P1 / BOOST / P2 / P3 × EN + ES (biomech adds the medical and vulnerability phrases); context guards (negation, test/drill, hearsay, figurative).
- [ ] **Package `backend/app/triage/`** (pure functions + pytest):
  - `lexicon_hits`
  - `classify`: lexicon + fields; LLM call optional
  - `score_priority`: **escalate-only**; P0 can never be lowered
  - `allowed_pools`: P0 → []
  - `match_responder`: skill + language − load − fatigue
- **Accept:** tests pass, including "no smoke here" (no P1), "fire alarm test" (downgraded), "me quiero morir" (P0, never downgraded), wheelchair (boost + `evac_logistics` skill).

### P1: Sat morning → M2
- [ ] **`detect_zone_level` + `cluster_reports`:**
  - DBSCAN on (lat, lon, time)
  - **distinct callers** (phone hash) per category per window
  - volume z-score vs. baseline
  - official feed match (NWS / CAL FIRE / USGS loaders)
  - hoax resistance: rate-limit per number, location agreement
  - Returns level + evidence JSON for the banner
- [ ] **Everyday baseline from public data:** load **MyLA311** service requests (data.lacity.org) → volume and topics by area and hour. That's the real "Tuesday" baseline for the Watch trigger.
- [ ] **`semantic_answer`** (answer cache): embed approved Q&A (sentence-transformers); return a hit ≥ threshold, zone-tagged, expiring when the zone level changes.
- [ ] **Drill content:**
  - role cards (`sim/cards.yaml` → `drill_cards`)
  - mix: 60% everyday / 25% crisis / 10% duplicates / 5% hoax; ~30% non-English
  - unique codes; `expected` labels = ground truth
  - drill page copy
- [ ] **Golden eval set** `evals/cases/*.yaml` (~40):
  - P0 ×8, hazard ×8, everyday actions ×12, language ×6, adversarial/compliance ×6
  - expected function calls, labels, forbidden phrases
  - Give CS#1 the Retell batch-test format.
- [ ] **Anonymization pipeline:**
  - `anonymize_row`
  - `analytics.*` tables: salted phone hash, names dropped, transcript PII scrubbed (regex + optional LLM), zone-level location only
  - k ≥ 5 for anything public or exported
  - respects `consent_analytics=false`

### P1: after each flood (12:30 · 3:30 · 8:00)
- [ ] **Failure mining** (`analysis/failures.py`):
  - severity mismatch vs. card
  - missed P0
  - repeated questions
  - "person!" requests
  - early hangups
  - form incomplete
  - Output → 15-min team triage → new eval cases.
- [ ] **Metrics snapshot** → `analysis/snapshots/<flood>.json`:
  - calls, peak concurrent
  - AI-resolved %, time-to-human P0/P1
  - P0 recall, severity accuracy
  - routing match %
  - non-EN/ES %
  - registry reached within 15 min, reached via contact
  - busy/abandoned
- [ ] **Judge calibration:** 40 human labels (10 each teammate) vs. the LLM judge; report agreement per criterion.
- [ ] **Scoreboard v1 → v2 → v3** into `eval_runs` (CS#2 shows it).

### P1: Sat afternoon
- [ ] **Topic mining** on real calls (embeddings + HDBSCAN/BERTopic); **KB gap clustering** → drafts for the approval queue.
- [ ] **Lexicon learning:** terms frequent in true-urgent calls but missing from the lexicon → suggestions for human approval; before/after recall.
- [ ] **Reach analysis** with ACS: tracts where EN/ES alerts miss people vs. who our line served.
- [ ] **All deck numbers** in `docs/numbers.md` (problem stats + our live stats + cost per resident/month), handed to biomech by **6 PM**.

### P2
- [ ] Acoustic flags from `recording_multi_channel_url` (librosa speech rate, pauses, pitch; **YAMNet** alarms/sirens/cough) → escalate-only flags + personal baselines (with biomech).
- [ ] Photo vision tags (smoke/flood) as corroboration evidence (with CS#2).
- [ ] Weekly "Community Pulse" digest generator (anonymized).

## Demo / event duties
- Sunday Q&A owner for metrics and methodology.
- Live numbers on the slide come from your snapshot.

## Hand-offs
- **You need:** CS#2 tables + data access; CS#1 transcripts / post-call fields; biomech medical lexicon + labels.
- **You give:** package, configs, seed data, eval cases, snapshots, `docs/numbers.md`.
