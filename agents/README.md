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
| `retell.ids.json` | Agent + LLM IDs (not secret; commit them) |
| `remote/` | Snapshot of what's live, written by `pull.py`, for diffs |
| `CHANGELOG.md` | One line per prod publish |

## Agents
| Name | Retell name | Role | Swaps to |
|---|---|---|---|
| `inbound` | diza-inbound-en-es | Everyday line + first answer for every inbound call (EN+ES) | `crisis` |
| `crisis` | diza-crisis | Crisis intake: safe? what? where? who? vulnerability → `submit_report` → route | `inbound` (false alarm, never after a P0) |
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
```
Optional env vars: `RETELL_FROM_NUMBER` (bind the number: inbound → `inbound`, outbound → `checkin`, inbound webhook → `${BASE_URL}/retell/inbound`), `RETELL_FALLBACK_NUMBER` (CS#2's Twilio voicemail line), `PROD_CRISIS_LINE_NUMBER`.

**staging vs prod:** Retell has no API for version tags. Instead, `staging` edits only each agent's **draft**, and swaps point at `latest`. `prod` publishes, and swaps + the phone number point at `latest_published`. Test drafts in the dashboard or with a web call before running prod.

**Crisis line safety:** `transfer_to_crisis_line` dials `{{crisis_line_number}}`. During the hackathon it must be a **teammate's phone in both envs**, because drill callers role-play self-harm, and we must not send role-play calls to the real 988 Lifeline. The backend can also override it per call in the inbound webhook.

## For CS#2 (backend)
- **Inbound webhook response must be wrapped:** `{"call_inbound": {"override_agent_id": ..., "dynamic_variables": {...}, "metadata": {...}}}` (Retell docs: features/inbound-call-webhook). All dynamic-variable values must be strings.
- Dynamic variables the prompts read: `caller_name, language, zone_id, zone_level, known_incidents, is_registered, drill_mode` (inbound webhook). Also `crisis_line_number` (optional override) and, for outbound `create-phone-call`, `needs, reason, consent_status` (`active` | `pending_consent`).
- Functions are sent with `args_at_root: true`: the JSON body is just the arguments, with no `{call, args}` wrapper. Timeout 5 s, 1 retry, so make writes idempotent.
- `route_to_human` must return `oncall_number` (E.164, or `""`), `responder_name`, `brief`, `match_reason`. They become `{{variables}}` for the warm transfer + whisper.
- Agent webhook events: `call_started, call_ended, call_analyzed, transcript_updated, transfer_started, transfer_bridged, transfer_cancelled, transfer_ended`. On a swap, both agents' webhooks fire.
- Post-call analysis fields (inbound/crisis): `severity, category, language, needs_followup, people_at_risk, vulnerability, location_text, outcome`. Check-in: `wellbeing, needs_followup, needs_mentioned, consent_confirmed, language, outcome`. Welfare: `safe_status, can_evacuate, severity, needs_followup, people_at_risk, vulnerability, language, outcome`.
