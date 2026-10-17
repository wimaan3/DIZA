# Build plan: who builds what, in what order

**Milestones (whole team):**
| ID | When | Definition of done |
|---|---|---|
| **M0 thin slice** | Fri 11:30 PM | Call the number → agent intake → `submit_report` → row appears on the dashboard |
| **M1 internal test** | Sat 10 AM | Transfer with whisper, outbound check-in, one form, ES agent, P0 safety path, all working |
| **M2 P0 freeze** | Sat 2 PM | Everything in PLAN §0-G P0 works on `main`; only fixes after this |
| **M3 video** | Sat 4 PM | Demo video recorded during the Surge Drill |
| **M4 submitted** | Sat 9 PM | Devpost complete (hard deadline 10 PM) |

## Interfaces to agree TONIGHT (15 min, before splitting up)

**Supabase tables (CS#2 creates; everyone codes against them):**
```
residents(id, name, phone, language, zone_id, lat, lon, needs[], contact_name, contact_phone,
          consent_checkin, do_not_call)
responders(id, name, phone, languages[], skills[], status, active_calls, calls_this_shift)
calls(id, retell_call_id, direction, agent, from_masked, language, zone_id, started_at, ended_at,
      disconnection_reason, severity, category, priority, outcome, routed_to, drill_code, feature_consent)
call_events(id, call_id, ts, type, payload jsonb, keyword_hits[])
reports(id, call_id, hazard, location_text, lat, lon, zone_id, people_at_risk, vulnerability[], cluster_id, ts)
clusters(id, zone_id, category, lat, lon, distinct_callers, status)
zones(id, name, polygon, level, level_changed_at, evidence jsonb)
requests(id, code, type, form jsonb, status, caller_phone, assignee_id, created_at)
ladder_tasks(id, resident_id, step, due_at, status)
labels(call_id, urgent, right_skill, resolved, labeled_by)
drill_cards(code, role_text, language, expected jsonb)
```

**Retell function contracts (CS#1 + CS#2):**
- `submit_report`
- `route_to_human` → `{oncall_number, responder_name, brief, match_reason}`
- `schedule_callback`
- `lookup_info`
- `start_form` / `fill_form` / `submit_form`
- `create_request`
- `request_escort`
- `set_reminder`
- `enroll_checkin`
- `notify_contact`
- `check_status`
- `opt_out`
- `flag_urgent`

**DS functions the backend imports:**
- `score_priority(label) -> int`
- `detect_zone_level(zone_id) -> (level, evidence)`
- `match_responder(needs, language) -> ranked list`
- `lexicon_hits(text, lang) -> hits`

## CS#1: Retell lead
| When | Task | Priority |
|---|---|---|
| Fri now | Retell account + **KYC**, top up, invite team, buy a 626 number, burst on, fallback number | P0 |
| Fri → 11:30 PM | `inbound` Single Prompt agent v0 (EN+ES) → `submit_report` via ngrok; test by web call, then phone | P0 (M0) |
| Overnight | `route_to_human` + warm transfer to `{{oncall_number}}` with whisper; `crisis` agent + agent swap; P0 safety path (911/988) | P0 |
| Overnight | `checkin-outbound` agent; voicemail handling; `enroll_checkin`, `notify_contact` | P0 |
| Sat AM | Form functions + actions; boosted keywords; drill-code handling; recording notice; `feature_consent` | P0/P1 |
| Sat AM | `pull.py` / `push.py` (agents in git) + staging/prod tags | P1 |
| Sat 10:30 AM | Retell info session (one question: live-call update + transfer reliability) | — |
| Sat PM | KO/ZH agents; keypad-only path ("press 1"); `update-live-call` push on P0 misses | P1/P2 |

## CS#2: backend + Ops Wall
| When | Task | Priority |
|---|---|---|
| Fri now | Repo scaffold on `main` (backend/, dashboard/, agents/, analysis/, sim/), Supabase schema above, `.env.example` | P0 |
| Fri → 11:30 PM | FastAPI: `/retell/inbound` webhook, `/retell/functions/submit_report`, `/retell/webhook` (signature verify), ngrok static domain; minimal dashboard list | P0 (M0) |
| Overnight | All function endpoints (stubs → real); scheduler (APScheduler): callbacks, check-ins, ladder; routing plumbing using DS `match_responder` | P0 |
| Overnight | Supporter mobile web app: on/off duty, accept request, one-tap rating | P0 |
| Sat AM | Ops Wall panels (map, tiles, call cards with transcript ticker, flow, actions, responders, zone banner + Declare) over Supabase Realtime | P0/P1 |
| Sat PM | Drill Mode, replay mode, phone-number masking; deploy to Railway/Fly; simulator (`sim/`) posting 200 reports | P1 |
| Optional | Use **IBM Bob** for the backend tests + scheduler and log how (Devpost) | P2 |

## DS: triage brain + evidence
| When | Task | Priority |
|---|---|---|
| Fri → 11:30 PM | Synthetic data: 500 residents (Altadena + campus + **San Pedro/Wilmington** config), 8 responders, zone polygons; `lexicon.yaml` v0 (EN/ES) | P0 |
| Overnight | `score_priority`, `lexicon_hits`, `match_responder` | P0 |
| Sat AM | `detect_zone_level`: DBSCAN clusters + distinct-caller counts + volume z-score → WATCH/ASK | P1 |
| Sat AM | Drill cards (+codes, ground truth) + drill page content; golden eval set (~40 cases) | P1 |
| After each flood | Failure mining → new eval cases → metrics snapshot (`analysis/snapshots/`) | P1 |
| Sat PM | Topic clustering of real calls; scoreboard v1→v3; **all numbers for the deck** | P1 |
| Stretch | Acoustic features (librosa + YAMNet) on recordings, with biomech | P2 |

## Biomech: domain, people, story
| When | Task | Priority |
|---|---|---|
| Fri now | Help desk: Harbor Night card, deck rules, twist submission, drill OK; confirm the USC student + team locked; Devpost project skeleton; `TOOLS.md` | P0 |
| Fri → Sat AM | Medical + vulnerability lexicon (real phrasing); form schemas (medical appointment, evacuation assistance); responder skill taxonomy + fatigue rules | P0 |
| Twists | Owns TWISTS.md write-ups (with whoever changed the code) | P0 |
| Sat AM | Recruit 6–8 supporters + callers; posters/QR; Instagram Story; organizer approval; book mentors (Nemani, Frazzini, McEwen, Kumar) | P1 |
| Sat PM | **Deck, demo video edit, Devpost write-up, responsible-use note, Q&A doc**; presenter | P0 |
| Stretch | Physiological voice-marker spec + thresholds (breathlessness, slurring, cough) with DS | P2 |

## Daily rhythm
- **Stand-ups:** Fri 11 PM · Sat 9 AM · 1 PM · 5 PM · 8:30 PM. Each person says done / next / blocked.
- **Twists** (11:30 PM, 4:30 AM, 7:00 AM): 15-min huddle; one build change; TWISTS.md entry.
- **Floods:** 12:30 PM · 3:30 PM · 8:00 PM. Pre-flight check, flood, snapshot, fixes.
- **Sleep shifts:** CS#1 + DS 12:30–4:30 AM; CS#2 + biomech 4:45–8:45 AM.
- **Merge rule:** `main` always demos. Small PRs; CS#2 reviews backend PRs, CS#1 reviews agent PRs.
