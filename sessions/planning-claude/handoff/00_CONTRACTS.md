# 00 · Shared contracts (all four people and agents code against this)

Every handoff doc points here. **Change a contract only by telling the team in the stand-up and editing this file on your branch + PR.**

## Repo layout on `main` (CS#2 creates it first)
```
backend/            FastAPI app (CS#2)
  app/main.py, app/retell/, app/twilio/, app/scheduler/, app/routing/, app/public/
  app/triage/       ← DS python package lives here (imported, not a service)
agents/             Retell agent + LLM JSON, push/pull scripts, prompts/*.md (CS#1)
  forms/            form schemas *.yaml (biomech writes, CS#1/CS#2 consume)
config/             zones.yaml, lexicon.yaml, pools.yaml, skills.yaml, settings.yaml (DS + biomech)
analysis/           notebooks, metrics snapshots, eval runner, public-data loaders (DS)
sim/                surge simulator, drill cards + drill page content (DS + CS#2)
dashboard/          React (Vite): supervisor console/Ops Wall, supporter app, public status page (CS#2)
evals/cases/        golden test cases *.yaml (DS + biomech)
docs/               deck assets, TWISTS.md, TOOLS.md, Devpost text (biomech)
.env.example        never commit .env
```

## Branches
- Personal branches: `cs1/*`, `cs2/*`, `ds/*`, `bio/*`
- **`main` = real app, via small PRs only.** Reviewers: CS#2 for backend/dashboard, CS#1 for agents, DS for config/analysis.
- Session notes go in `sessions/<you>/` on your own branch (see AGENTS.md).

## Environment variables (`.env.example`)
```
RETELL_API_KEY=            RETELL_WEBHOOK_KEY=        RETELL_FROM_NUMBER=
RETELL_AGENT_INBOUND_EN_ES=  RETELL_AGENT_CRISIS=  RETELL_AGENT_CHECKIN=  RETELL_AGENT_WELFARE=
RETELL_KB_CAMPUS=  RETELL_KB_RESOURCES=  RETELL_KB_POLICY=
TWILIO_ACCOUNT_SID=  TWILIO_AUTH_TOKEN=  TWILIO_SMS_FROM=
SUPABASE_URL=  SUPABASE_SERVICE_KEY=  SUPABASE_ANON_KEY=
PUBLIC_BASE_URL=           GOOGLE_CALENDAR_CREDENTIALS_JSON=
ANTHROPIC_API_KEY=         # backend LLM jobs (FAQ drafting, summaries), optional
MODE=staging|prod          DRILL_MODE=true|false
```

## Enums
- `severity`: `P0 | P1 | P2 | P3`
- `category`: `fire | smoke | gas | flood | power | medical | mental_health | safety_crime | infrastructure | info | logistics | volunteer_offer | other`
- `zone_level`: `normal | watch | ask | crisis`
- `request_status`: `new | offered | accepted | in_progress | done | cancelled | escalated`
- `responder_status`: `off | available | busy | pending_verification`
- `pool`: `trained_responder | trained_listener | general_helper | bilingual_helper`
- `skills`: `medical | mental_health | evac_logistics | safety_escort | housing | facilities | academics | tech | driver | general` + `lang:<code>`
- `outcome`: `ai_resolved | human_transferred | callback_queued | safety_911_988 | abandoned | voicemail`

## Supabase tables (CS#2 creates in `backend/db/schema.sql`; Realtime ON for the ★ tables)
```sql
residents(id uuid pk, name, phone, phone_hash, language, zone_id, lat, lon, needs text[],
  contact_name, contact_phone, consent_checkin bool, consent_analytics bool default true,
  share_status_with text[], do_not_call bool default false, created_at)
responders(id uuid pk, name, phone, languages text[], skills text[], pools text[],
  status responder_status, active_calls int, calls_this_shift int, verified bool, area_zone_id)   ★
zones(id text pk, name, polygon jsonb, level zone_level, level_changed_at, evidence jsonb,
  auto_action_at timestamptz)                                                                     ★
calls(id uuid pk, retell_call_id text unique, direction, agent, from_hash, from_masked, language,
  zone_id, started_at, ended_at, disconnection_reason, severity, category, priority int,
  outcome, routed_to uuid, drill_code, feature_consent bool, consent_analytics bool, summary)    ★
call_events(id bigserial pk, call_id uuid, ts, type, payload jsonb, keyword_hits text[])         ★
reports(id uuid pk, call_id, hazard, location_text, lat, lon, zone_id, people_at_risk int,
  vulnerability text[], cluster_id, photo_ids uuid[], verified bool default false, ts)          ★
clusters(id uuid pk, zone_id, category, lat, lon, distinct_callers int, photo_count int,
  status, first_seen, last_seen)                                                                 ★
requests(id uuid pk, code text unique, type, form jsonb, status request_status, pool,
  caller_hash, caller_phone, assignee_id, link_token, created_at, updated_at)                    ★
ladder_tasks(id uuid pk, resident_id, reason, step int, due_at, status, last_result)            ★
photos(id uuid pk, request_code, storage_path, exif_stripped bool, blurred bool,
  vision_tags jsonb, reviewed bool, created_at)
kb_items(id uuid pk, kb text, question, answer, source, approved_by, approved_at, expires_at,
  retell_source_id)                                                                              ★
kb_gaps(id uuid pk, call_id, question_text, cluster_key, status, created_at)                    ★
labels(call_id uuid, urgent bool, right_skill bool, resolved bool, labeled_by, ts)
drill_cards(code text pk, role_text, language, expected jsonb)
eval_runs(id, prompt_version, case_id, passed bool, scores jsonb, ts)
-- analytics schema (DS): analytics.calls_anon, analytics.reports_anon (no names, no phones, zone-level only)
```

## Retell → backend endpoints (CS#2 implements, CS#1 configures in Retell)
All POST, JSON, **verify `X-Retell-Signature` on the raw body**, respond in < 2 s (functions) / < 10 s (webhooks).

| Endpoint | Purpose | Returns |
|---|---|---|
| `/retell/inbound` | inbound call webhook | `{override_agent_id?, dynamic_variables:{caller_name, language, zone_id, zone_level, known_incidents, is_registered, drill_mode}}` (**strings only**) |
| `/retell/webhook` | call_started / call_ended / call_analyzed / transcript_updated / transfer_* | 204 |
| `/retell/fn/submit_report` | `{hazard, location_text, people_at_risk, injured_or_trapped, vulnerability[], language, drill_code?}` | `{report_id, cluster_match:"we already know about…"|"", severity, priority}` |
| `/retell/fn/flag_urgent` | `{reason, keyword}` | `{instruction}` (P0 path text) |
| `/retell/fn/route_to_human` | `{needs[], language, severity, summary}` | `{oncall_number, responder_name, brief, match_reason}` or `{oncall_number:"", fallback:"callback"}` |
| `/retell/fn/schedule_callback` | `{reason, preferred_time?}` | `{code, eta_text}` |
| `/retell/fn/lookup_info` | `{question, zone_id?}` | `{answer, source, confidence}` or `{answer:"", gap_logged:true}` |
| `/retell/fn/start_form` | `{form_type}` | `{case_code, next_fields:[{name, ask}]}` |
| `/retell/fn/fill_form` | `{case_code, fields:{}}` | `{missing:[], invalid:[], complete:bool, readback}` |
| `/retell/fn/submit_form` | `{case_code, confirmed:true}` | `{code, pool, status, next_step_text}` |
| `/retell/fn/create_request` | `{type, details, location_text}` | `{code, pool, eta_text}` |
| `/retell/fn/request_escort` | `{from, to, time}` | `{code, eta_text}` |
| `/retell/fn/set_reminder` | `{when, message}` | `{code, scheduled_for}` |
| `/retell/fn/book_appointment` | `{with_skill, preferred_times}` | `{code, slot}` |
| `/retell/fn/enroll_checkin` | `{person_name, person_phone, language, needs[], frequency, enrolled_by}` | `{code, status:"pending_consent"}` |
| `/retell/fn/notify_contact` | `{contact_name, contact_phone, message, consent:true}` | `{code, status}` |
| `/retell/fn/check_status` | `{code, phone_last4}` | `{status_text, link?}` |
| `/retell/fn/register_volunteer` | `{name, skills[], languages[], availability, area}` | `{code, status:"pending_verification"}` |
| `/retell/fn/send_link` | `{code}` | `{sent:bool, spoken_short_url}` |
| `/retell/fn/opt_out` | `{scope:"calls"|"analytics"|"all"}` | `{ok}` |
| `/retell/fn/record_consent` | `{feature_consent?, analytics_consent?}` | `{ok}` |
| `/twilio/sms` · `/twilio/mms` | inbound SMS/MMS → report / photo on the case | TwiML |

## DS python API (`backend/app/triage/`, pure functions, unit-tested)
```python
lexicon_hits(text: str, lang: str) -> list[Hit]            # Hit(term, tier: "P0"|"P1"|"BOOST"|"P2"|"P3", lang)
classify(transcript: str, fields: dict) -> Label            # severity, category, vulnerability, skills_needed, confidence
score_priority(label: Label, acoustic_flags: list[str] = []) -> int   # escalate-only
match_responder(skills: list[str], language: str, severity: str, pools_allowed: list[str]) -> list[Candidate]
allowed_pools(category: str, severity: str) -> list[str]     # P0 → [] (911/988 only)
detect_zone_level(zone_id: str, now) -> tuple[str, dict]     # level, evidence
cluster_reports(zone_id: str) -> list[Cluster]
semantic_answer(question: str, zone_id: str|None) -> Answer|None    # answer cache
anonymize_row(row: dict) -> dict
```

## Config files
- `config/zones.yaml`: zones with polygons. Sets: `altadena`, `usc_campus`, `san_pedro_wilmington` (Harbor Night).
- `config/lexicon.yaml`: tiers × languages
- `config/pools.yaml`, `config/skills.yaml`: pools ↔ skills ↔ allowed categories/severities
- `config/settings.yaml`: thresholds (`watch_distinct_callers: 3`, `ask_distinct_callers: 6`, `window_min: 10`, `deadman_min: 5`, `transfer_ring_s: 20`, `k_anon: 5`, `public_delay_min: 10`)
- `agents/forms/*.yaml`: form schemas (see INTAKE.md)

## Milestones
- **M0** Fri 11:30 PM thin slice
- **M1** Sat 10 AM internal test
- **M2** Sat 2 PM P0 freeze
- **M3** Sat 4 PM video
- **M4** Sat 9 PM Devpost submitted (hard deadline 10 PM)

**Floods:** 12:30 · 3:30 · 8:00 PM Sat; Sunday demo floor.

**Twists:** 11:30 PM · 4:30 AM · 7:00 AM, each answered within 6 h.
