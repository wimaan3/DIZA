# DIZA integration: reliable follow-through after intake

This session keeps **DIZA** as the product. **RelayLA** is the name of this implementation folder and the follow-through module it contributes: an urgent human queue, recorded handoff outcomes, confirmations tied to the latest instruction, and assistance requests that stay open until a person handles them.

The existing repository contained planning documents and the official participant material when this session began. There was no running DIZA application to patch. This folder therefore supplies a standalone implementation with explicit integration points for the planned FastAPI, Supabase, Retell, and dashboard work. It does not assert that the other session's proposed features are already implemented. This document is a session contribution, not the merged project plan reserved for the designated synthesis session in [AGENTS.md](../../AGENTS.md).

## 1. Start with the actual track problem

The source's **“03. Communication, with Retell AI: On the Line”** section puts the user in the seat of an overnight call-line supervisor. It asks who needs a person immediately, what must remain under human control, and what happens when someone does not answer. See the [official participant material](../../sources/participant-hub-gdoc.txt).

The primary screen consequently leads with the human queue. Message acknowledgment supports that work: the supervisor can distinguish an unconfirmed instruction, an accepted assistance request, and a person still awaiting a responder. A confirmation is not evidence that help arrived.

The ordinary-day customer remains consistent with DIZA's plan: a community organization or campus service team coordinating check-ins and practical assistance. The disruption scenario uses the same roster and request workflow under changing instructions and greater demand. These are proposed customer uses, not validated pilots or claimed agency partnerships.

## 2. How this fits the other session's ideas

| Existing DIZA proposal | Contribution in this folder | Boundary or next integration |
|---|---|---|
| Structured multilingual intake through Retell | `submit_report` records a case with language, zone, need, and upstream priority. English and Spanish approved instructions are available to the conversation. | The local intake form and seed data work without Retell credentials. A provider voice session requires configured agents, credentials, and a tested webhook endpoint. |
| Get urgent callers to the right human first | The queue sorts P0 through P3, then by age. Responder recommendations use availability, capacity, skills, and language. | Priority is supplied by the operator, drill fixture, or future DIZA triage service. This module does not implement or validate clinical triage or infer disease from audio. |
| Skills-based routing and supporter acceptance | Assignment, a failed handoff, human acceptance, and completion are separate recorded transitions. | These are workflow records. No telephone transfer or agency dispatch is performed. A future provider adapter must record actual transfer outcomes separately. |
| No-answer ladder | Failed contact persists; callback stages record retry, contact review, or human review work. A failed human handoff does not count as failed resident contact. | Due times are work-queue targets, not scheduled outbound calls or promised response times. P0 stays with urgent human review and cannot be put into a timed callback. |
| Tuesday check-ins and crisis follow-up | Both use one durable case record and the same approved notice lookup. | Enrollment, recurring schedules, outbound welfare calls, calendar writes, and third-party notifications remain outside this implementation. |
| Confirm actions and return a status code | `save_checkin` ties the reported action to an immutable notice version; `check_status` reports communication and assistance separately. | A connected call, a delivered message, and a caller's confirmation are different facts. No “safe” status is inferred from any of them. |
| Zone escalation and human declarations | Zone state is visible and its changes require an operator action. | Automatic anomaly detection, spatial clustering, independent-source corroboration, and public alerts are not implemented here. |
| Audit data for analytics and twist evidence | Mutations produce audit events, retain stable identifiers, and preserve notices and acknowledgments across revisions. | Drill measurements can evaluate these workflow transitions. They cannot establish real emergency-response effectiveness. |

The source ideas are documented in [planning context](../planning-claude/SESSION_CONTEXT.md), [product plan](../planning-claude/PLAN.md), [workflow](../planning-claude/WORKFLOW.md), [triage proposal](../planning-claude/TRIAGE.md), and [setup proposal](../planning-claude/SETUP.md). Product ideas and vendor claims in those files retain their original status; they are not evidence of implemented features in this session.

### Fit with the newer Ops Wall and intake sandbox plans

The later [Ops Wall plan](../planning-claude/OPS_WALL.md), [intake sandbox plan](../planning-claude/INTAKE.md), [evaluation plan](../planning-claude/EVALS.md), [team demo](../planning-claude/DEMO.md), [Retell guide](../planning-claude/RETELL_GUIDE.md), and [operating requirements draft](../planning-claude/COMPLIANCE.md) broaden DIZA's proposed application. This module contributes a working response-desk view and durable state that their larger interfaces can consume; those planning documents do not turn the additional integrations into completed work.

| Newer planned component | Available integration point here | Work still owned by the broader DIZA build |
|---|---|---|
| Ops Wall queue and responder panel | `/api/state` supplies severity-ordered cases, suggested responders, active assignments, capacity, and unresolved work. | Compose these into the proposed shared wall; preserve separate confirmation, assistance, and contact states. |
| Ops Wall actions feed and zone banner | Audit events identify recorded intake, failed handoffs, acceptance, notice revision, and operator zone decisions. | Automatic zone evidence, declaration countdowns, public-alert drafts, and real delivery events need their own implementation. |
| Live call cards, map, and concurrency tiles | Case language, supplied priority, zone, and summary can populate a basic case card. | Provider live-call counts, transcripts, keyword highlighting, coordinates, cluster rings, map polygons, and per-call timing are not supplied by this module. Do not relabel total cases as concurrent calls. |
| Typed intake and sandbox destination inboxes | `submit_report` saves a structured case and `route_to_human` creates follow-up work; an operator can act as the receiving organization and accept it. | YAML form schemas, `start_form`/`fill_form`/`submit_form`, missing-field validation, appointment slots, and dedicated clinic/311/utility inboxes are not implemented. A saved report is not a completed clinic form or a booked appointment. |
| Intake confirmation and caller status | `save_checkin` confirms a specific notice version, while `check_status` reads only the case bound to the provider call. | Map a future form's own read-back and submission evidence separately; notice acknowledgment must not be reused as consent to book or contact someone. |
| Quality tab and regression checks | Deterministic tests can verify retries, stale notice responses, priority preservation, and human acceptance requirements. | The proposed language/triage golden set, speech tests, live-drill labels, LLM judge calibration, and before/after scoreboards remain separate evaluations. Passing a workflow test is not 100% urgent-case recall. |
| Recorded-drill replay | Existing audit history supports inspection of what happened in this run. | A timestamp-driven replay player and imported drill recording are not implemented. A pre-recorded video is a presentation backup, not an application replay mode. |

The clean next step is to reuse these records as the **follow-through panel in the Ops Wall** and as the **operator acceptance step in the sandbox service world**. Keep provider delivery status, form completeness, human acceptance, and task completion as distinct fields when those projects are joined. Do not translate this module's `assistance_status = accepted` into “appointment booked” without a booking system's separate evidence.

The subsequent [requirements trace](../planning-claude/REQUIREMENTS_TRACE.md) names **ask** and **hand to a person** as the primary rungs; this module implements the confirmation and recorded-handoff portions of those rungs. The [reach strategy](../planning-claude/REACH.md) proposes outbound, keypad, registry, and additional-language work that remains outside this folder. Use the [twist template](../planning-claude/TWISTS_TEMPLATE.md) with actual code changes and observed evidence; the rehearsed notice-change and disconnected-intake scenarios are not claimed organizer-issued twists.

## 3. State rules shared by every input channel

**Communication and assistance are independent.** A resident can confirm the east entrance while still needing mobility assistance. A later dropped call must not erase an earlier valid confirmation. A later “no help needed” answer cannot silently close an active assistance task.

**Acknowledgments belong to an exact notice version.** The current confirmation requires both the current version and the correct action key. Replacing “north entrance” with “east entrance” creates a new version and renews follow-up for people who confirmed the earlier one. A late retry from an old call cannot restore an outdated confirmation or overwrite a newer one. The caller's read-back is recorded evidence of their response, not proof of comprehension.

**Retries are idempotent.** An identical request with the same `event_id` returns its stored result. Reusing that ID with different content is a conflict. This prevents network retries from creating duplicate requests or incrementing failure counts twice. It does not mean that different people describing the same event are merged; incident clustering is separate future work.

**Priority changes are conservative.** Updates can preserve or escalate an existing priority, but cannot downgrade it. P0 cannot be assigned to a volunteer or deferred into a timed callback. This is an implementation guard around supplied priorities, not a validated emergency classification system.

**A proposed handoff is not an accepted handoff.** Only the operator's separate acceptance action changes it to accepted. If the assigned responder does not answer, the failed-handoff record releases that proposal, keeps the assistance need open, and allows another recommendation. Resident contact outcomes remain separate. Cases requiring assistance or P0/P1 human review need an accepted assignment and an operator completion note before resolution.

**Operator decisions stay outside the agent's tool permissions.** Publishing a revised instruction, declaring a zone state, accepting a handoff, and completing a case are operator actions. The agent can ask for a human, save a caller-confirmed response, look up an approved notice, or record a callback request. It cannot declare an area safe, issue broadcasts, diagnose a caller, accept its own handoff, or claim that help has been dispatched.

The authoritative action schemas and state values are in [API_CONTRACT.md](API_CONTRACT.md).

## 4. Retell adapter and operator API

The implementation exposes the following integration surface. All mutations use the same domain operations, regardless of whether they originate in the local dashboard or the allowed Retell function adapter.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health and integration-configuration flags without credentials. |
| `GET /api/state` | Queue, notices, responders, zones, metrics, and integration status. |
| `GET /api/cases/{case_id}` | One case and its recorded history. |
| `POST /api/actions/{action}` | Operator mutation, using `{ "event_id": "stable-id", "payload": { ... } }`. |
| `POST /api/retell/web-call` | Request a Retell browser-call token for a specific case and language when configured. It does not place a telephone call. |
| `POST /retell/functions/{function_name}` | Receive the Retell function envelope and normalize an allowed function into domain operations. |
| `POST /retell/webhook` | Receive authenticated provider events and update actual contact outcomes. |

Operator actions include `submit_report`, `acknowledge`, `contact`, `assign`, `handoff_failed`, `accept`, `resolve`, `callback`, `revise_notice`, and `zone`. The request shape is defined in the contract rather than duplicated here.

| Retell function | What it may do | What its result does not mean |
|---|---|---|
| `submit_report` | Save or update structured intake, preserving an existing higher priority. | A verified incident, diagnosis, or emergency-service notification. |
| `lookup_guidance` | Retrieve the case's approved notice and version. | Independently generated evacuation, shelter, or medical guidance. |
| `save_checkin` | Record a caller-confirmed action against the stated notice version and capture requested help. | The person is safe or their help request is complete. |
| `check_status` | Return recorded communication, assistance, and follow-up status for the bound case. | Permission to browse another resident's information. |
| `route_to_human` | Request human follow-up and return a responder recommendation. | A bridged phone transfer, accepted assignment, or dispatch. |
| `schedule_callback` | Record pending callback work when allowed for the case priority. | A live outbound job or a guaranteed callback. |

The adapter and prompt live in `relayla/retell_adapter.py`, `retell/prompt.md`, and `retell/tools.json`; the HTTP application factory is `create_app` in `relayla/api.py`. See [README.md](README.md) for the supported startup and configuration steps.

For local rehearsal, the service binds to loopback and uses synthetic data. When an integration is exposed beyond the local machine, enable the operator token and Retell signature verification. The adapter uses `retell.lib.webhook_auth.verify` from the pinned Python SDK against the raw request body before processing a provider event; it also checks the configured agent allowlist. API keys remain server-side. The browser receives a short-lived call-access token, not a privileged provider key. These are concrete deployment requirements, not a claim that live provider integration has been tested.

The browser integration does not provide a live transcript ticker. The current provider webhook adapter handles call lifecycle outcomes; `transcript_updated` is not an implemented transcript-ingestion path. To add the planned Ops Wall ticker, receive authorized transcript events on the server, scope and redact the displayed fields, and expose that bounded view through the application. Do not give the browser a broader provider key to unlock transcript access.

Provider lifecycle events are ordered conservatively: a terminal or superseded call cannot reverse a newer contact state. The adapter uses durable call bindings and provider timestamps when available. When another call owns the latest contact state, an unobserved terminal event without usable ordering information is recorded as superseded and ignored. Run one application worker for this local integration. A production merge needs shared ordering and execution coordination across workers.


## 5. Proposed merge into DIZA's FastAPI and Supabase structure

Keep this folder and its documentation on the session's branch until the team agrees to promote selected code into the top-level application directories, as required by [AGENTS.md](../../AGENTS.md). The updated branch rule reserves `main` for the runnable app through small, teammate-reviewed PRs; session documentation stays on its own branch. The useful merge is at the domain/API boundary:

1. DIZA's intake and triage service produces a structured report and stable case identifier. Preserve the original classification and its source; submit it to the follow-through module.
2. The responder service supplies profiles and availability. Map its identifiers to this module's responder identifiers before assigning work.
3. DIZA's approved-information service provides versioned notices and source metadata. Publish material changes through `revise_notice` with an expected version to prevent accidental concurrent overwrites.
4. Mount or adapt the application factory in `relayla/api.py` inside the planned FastAPI service. If the route prefixes are already in use, move the routes together and update the dashboard and Retell configuration together.
5. Replace the local SQLite persistence behind `Store` with Postgres transactions. Preserve the store protocol and its invariants while the broader application adopts Supabase.
6. Drive actual transfer, call, or SMS operations through a separate provider worker only when the team has implemented and authorized that channel. Write delivery, acceptance, and failure evidence back to the case; never infer them from the request to send.

### Proposed database mapping

This table is a migration design, not a deployed Supabase schema. DIZA's existing proposed tables are listed in [WORKFLOW.md](../planning-claude/WORKFLOW.md).

| Local concept | Proposed DIZA/Supabase mapping | Requirement to preserve |
|---|---|---|
| Resident and language | Existing `residents` | Stable resident ID; minimal scoped access. |
| Intake case | Existing `reports` with a linked operational `requests` record | Stable case ID and upstream classification; no silent priority downgrade. |
| Assistance assignment | Existing `requests` plus responder foreign key | Assignment, failure, acceptance, and completion are distinct events. |
| Responder profile | Existing `responders` | Availability, permitted role, capacity, skills, and language. |
| Contact attempt/provider call | Existing `calls` and `call_events` | Provider call ID is distinct from case ID; retries do not create duplicate attempts. |
| Current and historical instructions | New `notices` and `notice_versions` | Unique `(notice_id, version)`; published historical text and action keys remain immutable. |
| Caller confirmation | New `notice_acknowledgments` linked to case and version | Unique event ID; preserve history and the version actually confirmed. |
| Idempotency result | New `processed_events` or equivalent transactional event table | Unique event ID plus content fingerprint and stored result, committed atomically with state changes. |
| Provider call binding | New `call_case_bindings` or a unique case reference on `calls` | One provider call can access only its bound case; a restarted session retains that association. |
| Future structured form | Future `forms` linked to `reports`/`requests` | Completeness, caller read-back, submission, destination acceptance, and actual booking are separate from notice acknowledgment. |
| Callback work | Existing `requests`, with stage and due time | Pending work remains distinct from an actual outbound execution. |
| Zone state | Existing `zones`, with audit history | Operator-attributed declaration and stand-down. |

Use database constraints and transactions for version checks, responder capacity, and idempotency. A client-side check followed by an unrelated write is insufficient when two operators or retried provider calls arrive together. Keep credentials and provider writes on the server; use scoped access for any future Supabase dashboard subscriptions.

## 6. What to validate next

First run a supervised local drill with synthetic cases and willing team participants. Assign one operator and one simulated responder. Exercise an urgent case, a Spanish assistance request, a responder who does not accept, an interrupted conversation, a revised notice, and duplicate retries. Record the observed preservation of state, time until the dashboard update, and time until a human explicitly accepts.

The live Retell path needs a separately recorded end-to-end check: configured browser agent, signed function calls, a persisted response, a provider termination event, and a return conversation using the same case. Passing local tests or displaying a browser-call button is not that check. Any later pilot with a real organization should have that organization's authorization, a small opt-in roster, current approved information, and a staffed follow-up process.

Open work includes live telephone handoff and outbound delivery, provider outage handling, real low-bandwidth performance, language accuracy with target users, authenticated multi-organization access, and triage evaluation. Nothing in this module validates physiological risk inference, independently corroborates an incident, or guarantees connectivity during an outage. The dashboard's offline draft capability retains unsent text on that device; it cannot deliver that text until connectivity returns.

## 7. Primary technical references

These references describe provider capabilities and integration requirements. They do not establish that the configured project exercised those capabilities.

- Retell, [Web call](https://docs.retellai.com/deploy/web-call) and [Create web call API](https://docs.retellai.com/api-references/create-web-call): browser voice-session integration.
- Retell, [Language](https://docs.retellai.com/agent/language) and [Multilingual](https://docs.retellai.com/agent/multilingual): agent language configuration; test the actual selected speech model and languages.
- Retell, [Custom function](https://docs.retellai.com/build/single-multi-prompt/custom-function): function requests and backend actions during a conversation.
- Retell, [Webhook overview](https://docs.retellai.com/features/webhook-overview): provider events and signature verification.
- Retell, [Enable SMS](https://docs.retellai.com/deploy/enable-sms): SMS setup and registration dependencies. SMS is not implemented in this module.

Claims elsewhere in the repository about trial limits, prices, universal language support, weak-signal reliability, alert-system coverage, or incident casualty statistics need their own current verification before inclusion in the pitch. This session's demo does not depend on them.
