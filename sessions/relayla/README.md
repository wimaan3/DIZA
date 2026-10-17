# DIZA · RelayLA response desk

**A working follow-through module for DIZA's Resilience Comms build.** It gives the overnight supervisor a priority-ordered queue, records who actually accepts a handoff, and keeps instruction confirmation separate from assistance completion.

This folder is the isolated implementation contribution on `codex/relayla-diza-integration`. It fits the existing [DIZA plan](../planning-claude/PLAN.md) and [Ops Wall proposal](../planning-claude/OPS_WALL.md). It can run on its own while the team builds the shared application. All seeded people, responders, and incidents are synthetic.

[View the response desk](preview.png) · [Verification results](VERIFICATION.md)

## Run the demo

Use Python 3.12 or newer. From the repository root:

```bash
cd sessions/relayla
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Open **http://127.0.0.1:8787/**. On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

No provider account is required for the local workflow. SQLite creates `.data/relayla.sqlite3` on the first run and preserves cases, confirmations, notice history, handoffs, and retry identifiers across restarts. To rehearse with a fresh dataset while preserving the previous one, choose another database filename:

```bash
RELAYLA_DB_PATH=.data/rehearsal-02.sqlite3 .venv/bin/python run.py --port 8788
```

Run one application worker. The local provider lifecycle guard is serialized in this process; a future distributed deployment needs an equivalent transaction or per-case lock in the shared database.

## What to show

1. **Find the person who needs a human.** P0–P3 priorities come from DIZA's upstream intake or the operator. The queue shows contact, confirmation, and assistance separately.
2. **Confirm an instruction in English or Spanish.** Select demo resident 01 and record a read-back. A wrong action needs clarification. A correct response confirms the exact notice version while their accessible-escort request remains open.
3. **Make responsibility explicit.** Assign an eligible responder, record a failed handoff if they do not accept, then record human acceptance and completion separately.
4. **Interrupt and resume.** The demo contact controls record a dropped or resumed conversation using the same case. Stored work survives the interruption.
5. **Revise the notice.** Publish a revised approved instruction. People who confirmed the older version need the new version; historical responses remain visible.
6. **Save disconnected intake.** The text form can keep an unsent draft in the current browser. Explicit sync uses the same event ID so a retry creates one report. This is a cached-page text fallback, not offline voice or a mesh network.

The full five-minute sequence, Spanish sample read-backs, and expected evidence are in [DEMO.md](DEMO.md).

## Implemented scope

| Capability | Behavior |
|---|---|
| Supervisor dashboard | Responsive HTML/CSS/JavaScript, priority queue, search, filters, notices, responder state, and per-case audit history. |
| Durable workflow | SQLite transactions, stable case identifiers, idempotent mutations, immutable notice versions, and preserved acknowledgment history. |
| Human handoffs | Recommendation, assignment, failed acceptance, explicit acceptance, and completion are separate. P0 cannot go to a volunteer or a timed callback. |
| Contact recovery | Separate resident no-answer/drop outcomes and human-handoff failures. Pending follow-up remains work for the operator. |
| Text fallback | Local browser outbox for unsent intake, explicit retry, and clear received-versus-unsent status. |
| Optional Retell browser voice | Server-created call tokens, approved-notice lookup, scoped case tools, signed provider callbacks, allowed agent IDs, and persisted call bindings. |

The agent cannot publish a notice, declare a zone state, accept its own handoff, or complete assistance. A connected call does not establish that the caller confirmed an instruction. A request, recommendation, or callback target does not mean a call was placed or help is on the way.

Actual telephone transfers, outbound calling/SMS, public alerts, bookings, clustering, medical classification, live transcripts, and the full Ops Wall map are outside this module. The Retell path is implemented and covered with local signed-envelope tests; it still needs an end-to-end run with the team's live account.

## Connect Retell browser voice

The local simulation remains usable while you configure the provider. The live path uses published English and Spanish agents, a server-side Retell API key, and a publicly reachable HTTPS backend for signed functions and webhooks. It does not require adding a privileged Retell key to browser code.

1. Copy `.env.example` to `.env`. Set a strong `RELAYLA_OPERATOR_TOKEN`, `RETELL_API_KEY`, `RETELL_AGENT_ID_EN`, and `RETELL_AGENT_ID_ES`. Keep the file out of Git. If inbound agents should access this module, list their IDs in `RETELL_ALLOWED_AGENT_IDS`.
2. Copy the text between **BEGIN AGENT PROMPT** and **END AGENT PROMPT** in [retell/prompt.md](retell/prompt.md) into the agent prompt. Configure the six custom functions from [retell/tools.json](retell/tools.json), replacing `BASE_URL` with the actual HTTPS origin and mount path. Retain the wrapped `name`/`call`/`args` envelope.
3. Configure the agents' webhook URL as `https://YOUR_BACKEND/retell/webhook`. Subscribe to `call_started` and `call_ended`. The API checks the signature against the raw body and rejects unconfigured agent IDs.
4. Publish the configured agents, set `RELAYLA_ENABLE_RETELL=true`, and restart. For remote access, run behind an HTTPS reverse proxy with an operator token configured. The supplied runner refuses a public bind without that token.
5. In **Connection settings**, enter the operator token. It is kept in this browser tab's session. Select a case and start browser voice. Microphone access and a network connection are required. The backend sets the agent and case context; the browser receives only short-lived connection fields.

The browser helper loads `retell-client-js-sdk@3.0.2` on demand from esm.sh. All ordinary dashboard behavior uses local assets. If the demo venue blocks that CDN, vendor the pinned package into the eventual DIZA frontend bundle. The helper deliberately does not request the broader provider key scope needed for direct live-transcript streaming.

The backend caps demo web-call starts at six per minute. This is a local guard, not a measurement or promise of provider concurrency. Webhooks cannot move an ended call back to connected, and known older calls cannot overwrite a newer call's contact state. See the lifecycle ordering details in [INTEGRATION.md](INTEGRATION.md).

## Integrate with DIZA

The module keeps DIZA's product name, P0–P3 queue, language/skills-based responder ideas, and callback ladder. The practical merge is to use its state as the **follow-through panel in the Ops Wall** and the **human acceptance step in the intake sandbox**.

The [integration map](INTEGRATION.md) covers the existing plans, proposed Supabase table mapping, and remaining team work. The exact HTTP actions and state shapes are in [API_CONTRACT.md](API_CONTRACT.md).

From this folder, a parent FastAPI app can mount the application factory:

```python
from fastapi import FastAPI
from relayla.api import create_app

app = FastAPI()
app.mount("/relayla", create_app())
```

Visit `/relayla/` with the trailing slash. Assets and API requests resolve relative to that mount. When importing the module from a different project root, include this folder on the Python import path or promote the package through the team's reviewed integration PR. Environment variables must be set by the parent process; the convenience `.env` reader belongs to `run.py`.

Operator calls use `X-Operator-Token` when configured. A minimal mutation is:

```json
{
  "event_id": "demo-resident-01-contact-attempt-1",
  "payload": {"case_id": "case-001", "outcome": "dropped"}
}
```

Post it to `POST /api/actions/contact`. Keep the same event ID and payload when retrying that operation; use a new ID for a new intended action. Conflicting reuse returns HTTP 409.

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests use temporary synthetic databases and locally signed test envelopes. They make no live provider calls. They cover notice races, out-of-order and repeated callbacks, case binding, authentication, priority preservation, failed human handoffs, capacity, restart recovery, and separate confirmation/assistance state.

Before a live demo, exercise the configured browser agent through one signed tool request, notice read-back, persisted response, and call-end event. Local tests cannot establish speech accuracy, telephone delivery, or behavior during an actual communications outage.

## Files

- `relayla/engine.py`: provider-independent case state and transactional storage.
- `relayla/api.py`, `settings.py`, `retell_adapter.py`: HTTP boundary, configuration, scoped Retell tools, and lifecycle events.
- `relayla/static/`: dashboard and optional browser voice helper.
- `retell/`: prompt and provider function configuration templates.
- `tests/`: deterministic domain and HTTP integration checks.
- `DEMO.md`, `INTEGRATION.md`, `API_CONTRACT.md`, `SESSION_CONTEXT.md`: rehearsal, integration decisions, contract, and handoff context.

Sources for the track and existing DIZA ideas are linked in [INTEGRATION.md](INTEGRATION.md). This contribution stays in its own folder and branch under the repository's [collaboration rules](../../AGENTS.md).
