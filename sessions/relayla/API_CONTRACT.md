# RelayLA implementation contract

This standalone DIZA session implements durable follow-through after intake. It accepts DIZA's upstream triage classification; it does not diagnose callers, declare incidents automatically, or send communications itself.

## HTTP routes

- `GET /api/state` — complete dashboard state.
- `GET /api/cases/{case_id}` — one case and its event history.
- `POST /api/actions/{action}` — `{ "event_id": "unique-client-id", "payload": { ... } }`. Mutation responses contain `{ "result": ..., "state": ... }`.
- `POST /api/retell/web-call` — `{ "case_id": "...", "language": "en" | "es" }`; returns a provider web-call access token only when Retell is configured. No phone call is placed.
- `POST /retell/functions/{function_name}` — Retell function envelope `{ "name": "...", "call": { ... }, "args": { ... } }`, verified against the raw request signature when enabled. The adapter normalizes these into the same store operations.
- `POST /retell/webhook` — verified provider events. Ended calls update contact state without treating connection as acknowledgment or resolution.
- `GET /health` — runtime health and integration configuration booleans, without credentials.

The operator interface uses `X-Operator-Token` when `RELAYLA_OPERATOR_TOKEN` is configured. Local demo is loopback-only by default. Live externally exposed integrations require an operator token and Retell signature verification.

## Store protocol

`Store(path)` opens SQLite and seeds synthetic demo data only when empty. `state()` returns the shape below. `get_case(case_id)` returns one case plus events. `apply(action, payload, event_id, actor='operator')` commits atomically and returns a result dict. Replaying an identical event ID returns its saved result; reusing it with different content returns HTTP 409 through `DomainError(status_code, message)`.

## State shape

```json
{
  "notices": [{"id":"notice-pickup","title":"Community pickup","version":1,"body_en":"...","body_es":"...","action_key":"north_entrance","action_label_en":"North entrance","action_label_es":"Entrada norte","zone":"Campus West","source_label":"Demo coordinator","approved_by":"Demo supervisor","updated_at":"ISO timestamp"}],
  "cases": [{"id":"case-001","resident_id":"demo-001","resident_name":"Demo resident 01","language":"es","zone":"Campus West","category":"logistics","severity":"P2","skills_needed":["mobility"],"summary":"Needs help reaching pickup","notice_id":"notice-pickup","acknowledged_version":null,"communication_status":"unreached","contact_status":"not_contacted","needs_assistance":true,"assistance_details":"...","assistance_status":"requested","owner_id":null,"recommended_responder_id":null,"callback_stage":"none","callback_due_at":null,"contact_failures":0,"created_at":"ISO timestamp","updated_at":"ISO timestamp"}],
  "responders": [{"id":"responder-01","name":"Demo coordinator","languages":["en","es"],"skills":["mobility","logistics"],"role":"professional","available":true,"capacity":2,"active_count":0}],
  "zones": [{"id":"Campus West","level":"normal","changed_by":"Demo supervisor"}],
  "events": [{"id":"...","case_id":null,"kind":"...","detail":"...","created_at":"ISO timestamp","actor":"..."}],
  "metrics": {"total_cases":0,"current_confirmations":0,"needs_human":0,"unreached":0,"pending_updates":0,"open_assistance":0},
  "demo": true,
  "server_time": "ISO timestamp",
  "integration": {"retell_configured":false,"operator_token_required":false,"telephony":"not connected","sms":"not connected"}
}
```

`integration` is supplied by the HTTP layer. Queue cases are sorted P0, P1, P2, P3, then oldest first. Communication status is one of `unreached`, `awaiting_confirmation`, `confirmed`, `needs_clarification`, `update_pending`. Assistance status is one of `none`, `requested`, `assigned`, `accepted`, `completed`. These are independent dimensions. A later contact failure cannot erase a valid confirmation, and confirmation cannot close an assistance request.

## Actions and payloads

| Action | Payload |
|---|---|
| `submit_report` | `resident_id`, `resident_name`, `language`, `zone`, `category`, `severity` (P0–P3), `skills_needed` (array), `summary`, `notice_id` (nullable), `needs_assistance` (bool), `assistance_details`; optional `case_id` to continue an existing case |
| `acknowledge` | `case_id`, `notice_version`, `action_key`, `readback_text`; optional `needs_assistance`, `assistance_details` |
| `contact` | `case_id`, `outcome` (`connected`, `dropped`, `no_answer`, `resumed`, `ended`) |
| `assign` | `case_id`, `responder_id` |
| `accept` | `case_id`, `responder_id` |
| `handoff_failed` | `case_id`, `responder_id`, `reason`; release an unaccepted assignment and keep the human request pending |
| `resolve` | `case_id`, `note` |
| `callback` | `case_id`, `minutes` (1–60), `reason` |
| `revise_notice` | `notice_id`, `expected_version`, `body_en`, `body_es`, `action_key`, `action_label_en`, `action_label_es`, `source_label`, `approved_by` |
| `zone` | `zone_id`, `level` (`normal`, `watch`, `ask`, `crisis`, `stand_down`), `reason` |

## Invariants

- A stored acknowledgment is tied to the immutable historical notice version. Current confirmation requires that version to equal the current notice version and the action key to match. Out-of-order older events cannot overwrite a newer acknowledgment.
- An incorrect read-back action requires clarification. The UI must not infer comprehension from connection or delivery.
- Report updates may escalate but never downgrade severity. P0 cannot be assigned to a volunteer or deferred into a timed callback. This is a workflow guard, not a validated clinical triage system.
- Assignment records a proposed handoff. Only the separate operator acceptance action marks it accepted. Resolution requires an accepted assignment and an operator note when assistance or P0/P1 review is needed.
- A failed human handoff is separate from a resident's unanswered call. `handoff_failed` releases the assigned responder, increments `handoff_failures`, and records `failed_responder_ids` so another responder can be recommended; it does not change resident contact counters or priority.
- Non-response remains unresolved. The callback ladder records work to do (`retry_pending`, `contact_review`, `human_review`); it sends no calls or messages. Failed contact attempts increment only once per event ID.
- Notice revisions and zone declarations are operator-only actions. Retell's allowed tool set cannot publish notices, resolve cases, accept handoffs, or change a zone.
- Retries are idempotent; all state transitions have an audit event. SQLite is a local demo store, with a documented future mapping to DIZA's proposed Supabase tables.
