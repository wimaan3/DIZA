# agents/: Retell voice agents (CS#1)

Git is the source of truth. Retell is a deploy target. Don't edit agents in the dashboard. If you do, run `pull.py` and copy the change back here.

## Layout
| Path | What |
|---|---|
| `prompts/_shared_rules.md` | Hard rules in **every** agent: P0 → 911, self-harm → 988, never claim to be human, no false dispatch, privacy, opt-out, "press 0" |
| `prompts/{inbound,crisis,checkin,welfare,volunteer}.md` | Per-agent prompts (`volunteer.md` is part of inbound) |
| `tools.json` | Every tool, one place. Custom functions point to `${BASE_URL}/retell/fn/<name>` (00_CONTRACTS.md) |
| `<name>.llm.json` | Model settings, `_prompt_files` (joined in order), `_tools` (names from tools.json), default dynamic variables |
| `<name>.agent.json` | Voice, language, webhook, speech settings, post-call analysis fields |
| `envs/{staging,prod}.json` | Per-env values. `${VARS}` are filled in from your shell or the repo-root `.env` |
| `retell.ids.json` | Agent, LLM and knowledge-base IDs (not secret; commit them) |
| `kb/*.md` + `kb_sync.py` | Knowledge bases `line-policy`, `la-resources`, `campus-faq`. Each `## ` section = one snippet. Numbers verified 2026-10-17 on official pages |
| `forms/*.yaml` | **Draft** form schemas for the `start_form`/`fill_form`/`submit_form` loop (biomech owns content) |
| `prompts/language_line.md` | Shared prompt for the Korean/Chinese lines |
| `remote/` | Snapshot of what's live, written by `pull.py`, for diffs |
| `CHANGELOG.md` | One line per prod publish |
| `safety_check.py` | Text-only safety regression (real person?, no false dispatch, 988, Spanish P0, prompt injection) |

## Agents
| Name | Retell name | Role | Swaps to |
|---|---|---|---|
| `inbound` | diza-inbound-en-es | Everyday line + first answer for every inbound call (EN+ES). Forms, escorts, appointments, volunteers | `crisis`, `inbound_ko`, `inbound_zh` |
| `crisis` | diza-crisis | Crisis intake: safe? what? where? who? vulnerability → `submit_report` → route | `inbound` (false alarm, never after a P0) |
| `inbound_ko` | diza-inbound-ko | Korean line; does its own crisis intake (no Korean crisis agent) | `inbound` (English/Spanish) |
| `inbound_zh` | diza-inbound-zh | Mandarin line; same design | `inbound` |
| `checkin` | diza-checkin-outbound | Outbound wellness check-in; names the service, "say stop anytime", voicemail message | `crisis` |
| `welfare` | diza-welfare-outbound | Outbound crisis call-down: safe / not safe, needs, can leave? | — |

## Run it
```bash
pip install -r agents/requirements.txt   # nothing to install today (stdlib only)
export RETELL_API_KEY=...                # or put it in the repo-root .env (git-ignored)
export PUBLIC_BASE_URL=https://<ngrok-or-railway-host>
export STAGING_CRISIS_LINE_NUMBER=+1...  # a teammate's phone. NEVER commit it
python agents/push.py --env staging --dry-run   # see the payloads
python agents/push.py --env staging             # update drafts (nothing published)
python agents/push.py --env prod                # update + publish + CHANGELOG line
python agents/pull.py                           # mirror live config into remote/
python agents/kb_sync.py                        # create/refresh knowledge bases from kb/*.md
python agents/safety_check.py                   # text safety tests on the drafts (a few cents); run before prod
```
Optional env vars: `RETELL_FROM_NUMBER` (bind the number: inbound → `inbound`, outbound → `checkin`, inbound webhook → `${BASE_URL}/retell/inbound`), `RETELL_FALLBACK_NUMBER` (CS#2's Twilio voicemail line), `PROD_CRISIS_LINE_NUMBER`.

**staging vs prod:** Retell has no API for version tags. Instead, `staging` edits only each agent's **draft**, and swaps point at `latest`. `prod` publishes, and swaps + the phone number point at `latest_published`. Test drafts in the dashboard or with a web call before running prod.

**Crisis line safety:** `transfer_to_crisis_line` dials `{{crisis_line_number}}`. During the hackathon it must be a **teammate's phone in both envs**, because drill callers role-play self-harm, and we must not send role-play calls to the real 988 Lifeline. The backend can also override it per call in the inbound webhook.

## For CS#2 (backend)
- **Inbound webhook response must be wrapped:** `{"call_inbound": {"override_agent_id": ..., "dynamic_variables": {...}, "metadata": {...}}}` (Retell docs: features/inbound-call-webhook). All dynamic-variable values must be strings.
- **Greeting:** the first line is fixed text, `{{recording_notice}} {{opening_line}}`. Default `opening_line` = "Thanks for calling the DIZA Community Line. How can I help?". For a zone at watch/ask/crisis, return `opening_line` like "If you're calling about the fire near Lake Ave: we know about it and we're tracking it. Are you safe right now?".
- Dynamic variables the prompts read: `caller_name, language, zone_id, zone_level, known_incidents, is_registered, drill_mode` (inbound webhook). Also `crisis_line_number` (optional override) and, for outbound `create-phone-call`, `needs, reason, consent_status` (`active` | `pending_consent`).
- Functions use Retell's default body `{"name": ..., "call": {call_id, transcript, ...}, "args": {...}}` (`args_at_root: false`), so you get `call.call_id` for idempotency and the transcript. Timeout 5 s, 1 retry, so make writes idempotent.
- `start_form` sends `{form_type, known_fields}`: pre-fill `known_fields` and return only the fields still missing in `next_fields`. `fill_form.fields` is an object of name → string. Form ids = `agents/forms/*.yaml` ids.
- Language routing: return `override_agent_id` = the `inbound_ko` / `inbound_zh` agent id (see `retell.ids.json`) for registered Korean/Chinese callers. On those lines, send `opening_line` in that language or leave it out (a Korean/Chinese default exists).
- `submit_report.cluster_match` must be `""` unless there's a real match: the agent reads any non-empty value aloud.
- `route_to_human` must return `oncall_number` (E.164, or `""`), `responder_name`, `brief`, `match_reason`. They become `{{variables}}` for the warm transfer + whisper.
- Agent webhook events: `call_started, call_ended, call_analyzed, transcript_updated, transfer_started, transfer_bridged, transfer_cancelled, transfer_ended`. On a swap, both agents' webhooks fire.
- Post-call analysis fields (inbound/crisis): `severity, category, language, needs_followup, people_at_risk, vulnerability, location_text, outcome`. Check-in: `wellbeing, needs_followup, needs_mentioned, consent_confirmed, language, outcome`. Welfare: `safe_status, can_evacuate, severity, needs_followup, people_at_risk, vulnerability, language, outcome`.
