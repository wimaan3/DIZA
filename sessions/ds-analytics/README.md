# RelayLA: versioned community notice follow-up

RelayLA answers: **Who has confirmed the latest instructions, and who still needs a person to follow up?**
The initial customer is Maple Community Center, with an opt-in roster and one workflow: shuttle pickup-location changes and help reaching the pickup point.
The coordinator dashboard lives at `/ops`; private resident links open an English/Spanish form and optional Retell browser voice conversation.
All committed implementation files stay inside this session folder.

## Run RelayLA locally

```sh
python3 -m venv sessions/ds-analytics/.venv
sessions/ds-analytics/.venv/bin/python -m pip install \
  -r sessions/cs2-backend/mvp/backend/requirements.txt \
  -e 'sessions/ds-analytics[web]'
npm --prefix sessions/ds-analytics/client ci
npm --prefix sessions/ds-analytics/client run build
cp sessions/ds-analytics/client/dist/voice-sdk.js \
  sessions/ds-analytics/diza_analysis/relay_web/voice-sdk.js
sessions/ds-analytics/.venv/bin/python sessions/ds-analytics/scripts/serve_relay.py --demo
```

Open http://127.0.0.1:18772/ops and enter `relay-demo-local`, or your existing `OPS_API_TOKEN` environment value if set.
The preview binds to localhost and uses `artifacts/relay-preview.sqlite3`, without reading the repository `.env`.
`--demo` explicitly adds four synthetic residents only when the preview has no notices.
Production never seeds this scenario automatically.
Use `--ephemeral --demo` for a disposable rehearsal database.

1. Open Marisol's record and choose **Open response form**.
2. In Spanish, enter `Usaré la entrada norte`, describe help reaching the entrance, confirm the readback, and save.
3. Watch the dashboard record the instruction confirmation and a separate assistance request awaiting an owner.
4. Revise both approved language versions to the east entrance, updating the expected next steps to `east entrance` and `entrada este`.
5. The earlier confirmation stays in the history, while the latest instruction becomes unconfirmed.
6. Confirm the east entrance from the resident link, then accept and complete the assistance task as the named coordinator.

## Persistence and recovery

| Situation | Result |
|---|---|
| A notice is revised | A new immutable version and follow-up are created; earlier confirmations and open assistance remain |
| A stale form or call submits | The answer is saved against the delivered version; the latest notice still needs confirmation |
| A submission times out after the server saves it | The browser retries the same request key; no duplicate task or confirmation event is created |
| A call disconnects | Confirmed details and assistance drafts remain in the same resident/notice record |
| A resident requests assistance | The description is saved as a draft, then a task is created only after explicit readback confirmation |
| A coordinator accepts help | The task records that owner; only the accepting name can record completion |
| A resident reports uncertainty | Instruction clarification remains pending for a person |
| A previously loaded form goes offline | IndexedDB retains the draft and original notice version; the service worker can reload the form shell |
| An offline response is queued | It stays labeled Not sent until the server acknowledges it, then synchronizes when online |

Instruction confirmation requires a specific expected next step, rather than a generic yes.
The phrase check rejects common negation and uncertainty; it is not a comprehension or safety assessment.
Voice and text use the same transactional store, with one record per resident/notice and one assistance task per record.
SQLite write transactions, request receipts, expected notice versions, and assistance revision checks protect concurrent updates.
Resident access uses private per-record capability links; the signing secret persists in the attached database volume.
Operator APIs require the existing `OPS_API_TOKEN`; private responses have `Cache-Control: no-store`.
Only the resident form shell, their own notice context, and their draft are retained for offline use.

## Browser voice

Set server-side `RETELL_API_KEY` and `RELAY_RETELL_AGENT_ID` to enable the voice button.
The browser receives only a short-lived session token, through Retell's bundled Web SDK 3.0.2.
A server-owned call binding determines which record a signed Retell function may access.
Functions use the original raw request signature, persist individual answers during a call, and return current notice context after each mutation.
An old call can save its old-version response but must fetch current context before confirming a newer version.

The dedicated agent prompt and five custom tools are generated from `relay/voice_config.py`.
The setup script previews its full configuration by default and creates a new agent only with `--apply`, after verifying the deployed `/health/relay` endpoint.
It does not edit the existing DIZA phone agents, initiate calls, purchase numbers, or send messages.
See [deployment instructions](deploy/DEPLOY.md) for the activation sequence.

Provider calls are mocked in automated tests; no live human voice conversation has been claimed as tested.
Browser microphone access needs HTTPS or localhost, and cloud voice requires connectivity.
Telephone calls, two-way SMS, bulk calling, language detection, and transport optimization remain outside this prototype.
The current workspace uses one shared operator token and typed coordinator names; account-level identity and multi-organization tenancy are future work.
Repeating an unchanged completed assistance request does not reopen it; a newly confirmed description can reopen the same task with a new revision.

## Validate RelayLA

```sh
sessions/ds-analytics/.venv/bin/python -m unittest discover \
  -s sessions/ds-analytics/tests_relay -v
sessions/ds-analytics/.venv/bin/python -m unittest discover \
  -s sessions/ds-analytics/tests_live -v
npm --prefix sessions/ds-analytics/client run check
```

Run `PLAYWRIGHT_BROWSERS_PATH=../artifacts/playwright npx playwright install chromium` and `PLAYWRIGHT_BROWSERS_PATH=../artifacts/playwright npm test` from `sessions/ds-analytics/client`.
The browser tests launch their own disposable server, use no provider key, and cover the Spanish workflow, notice revisions, assistance ownership, offline reload/synchronization, lost-response retries, and mobile layouts.
Screenshots are written to ignored `artifacts/relay-*.png`; Playwright traces and failure screenshots stay in ignored test output.
Build the production image from the repository root with `docker build -f sessions/ds-analytics/deploy/Dockerfile -t relayla:local .`.

## Existing DIZA analysis package

An installable Python package for triage, responder ranking, corroboration, evaluation, and call metrics.
Python 3.11 or newer is required; the core analysis CLI uses only the standard library.
The package stays in this session's folder to honor the repository's session isolation rule.
These analysis utilities remain available alongside the repurposed RelayLA application.

Implemented:

- EN/ES lexicon, clause-level context guards, structured-field classification, and priority scores.
- P0 severity floors and empty P0 helper pools; verified responder eligibility before skill, language, load, and fatigue ranking.
- Space/time DBSCAN with distinct callers, per-caller rate limiting, WATCH/ASK evidence, optional normalized official evidence, and human-only crisis declaration and stand-down.
- Seeded synthetic residents, responders, drill calls, role cards, and CSV registry export.
- Forty golden cases, deterministic evaluation, agent-observation safety gates, failure mining, reach metrics, and judge agreement.
- Consent-aware pseudonymization, internal metric snapshots, and delayed public aggregates with at least five distinct contributors per cell.
- Read-only access to the deployed SQLite schema, a MyLA311 baseline loader, and a Census ACS language/age profile loader.
- An optional deployment wrapper, protected live analytics API/page, and additive consent linkage for accepted Retell events.

## Run from the repository root

```sh
python3 -m venv sessions/ds-analytics/.venv
sessions/ds-analytics/.venv/bin/python -m pip install -e sessions/ds-analytics
sessions/ds-analytics/.venv/bin/diza-analysis demo \
  --out-dir sessions/ds-analytics/artifacts/demo \
  --now 2026-10-17T20:00:00Z
sessions/ds-analytics/.venv/bin/diza-analysis evaluate
sessions/ds-analytics/.venv/bin/python -m unittest discover \
  -s sessions/ds-analytics/tests -v
```

The demo creates 500 residents, 10 responders, 200 calls, role cards, a registry CSV, a classifier evaluation, simulation inputs for CS#1, zone evidence, an internal snapshot, and public aggregates.
All generated observations are labeled `synthetic`.
The drill mix is 60% everyday, 25% crisis, 10% repeated callers, and 5% alarm tests; 30% of cards use Spanish or Korean.
An alarm test is a benign negative control, not evidence that an actual caller was a hoax.
Default demographic weights and polygons are illustrative, with provenance in their config files.
Use `demo --profiles PATH` to supply a reviewed per-zone profile with the shape of `diza_analysis/config/profiles.json`.

## Import into the backend

```python
from diza_analysis import allowed_pools, classify, match_responder, score_priority

label = classify("Hay humo y uso silla de ruedas", {"language": "es"})
priority = score_priority(label)
pools = allowed_pools(label.category, label.severity)
candidates = match_responder(
    label.skills_needed, label.language, label.severity, pools,
    responders=[],  # Pass normalized operational responder records here.
)
```

`classify` returns a frozen `Label`, including category, severity, vulnerabilities, skills, keyword evidence, and context guards.
Existing severity and P0 lexical hits are never lowered, including negated P0 wording, as required by the team's conservative policy.
These deterministic rules are not a clinically validated model.
Only EN/ES have a lexical implementation; other-language golden cases depend on structured fields produced by the voice agent.

Each responder record has `id`, `skills`, `languages`, `pools`, `status`, `verified`, `active_calls`, and `calls_this_shift`.
The matcher returns ranked candidates without reserving anyone; the backend must perform its existing atomic availability check and reservation.
No eligible responder produces an empty list for the backend's escalation/callback path.

`cluster_reports(zone_id, reports=..., now=...)` and `detect_zone_level(zone_id, now, reports=...)` require explicitly injected records.
Reports need `id`, `caller_hash`, `zone_id`, `category`, `severity`, `hazard_here_now`, `lat`, `lon`, and `ts`.
Missing identity, missing coordinates, stale/future observations, and non-hazard reports cannot establish corroboration.
Repeated callers contribute one vote per category per window.
Optional official events require `verified: true`, matching `zone_id` and `category`, `starts_at`, `expires_at`, and `source`.
The caller supplies official feed ingestion and geographic verification.
Calling these functions does not change a database or declare a crisis.

The functions add keyword-only record inputs to the handoff signatures so they remain pure and independently testable.
Config is versioned JSON rather than YAML to keep installation dependency-free.
The `diza_analysis.live:create_app` entry point serves RelayLA and retains the original backend API and optional analytics routes.
Legacy dispatch, geocoding, and provider-wide call-backfill workers are disabled by default for RelayLA.
An explicit `RELAY_LEGACY_WORKERS=true` restores the original background lifecycle when operating the legacy product.
See [deploy/DEPLOY.md](deploy/DEPLOY.md) for the concrete container, Railway settings, validation, and rollback procedure.

## Analyze operational records

Set `DIZA_ANALYTICS_SALT` in the process environment to a private random value of at least 16 bytes.
Keep this value outside git and reuse it only within the intended analytics retention window.
Do not put it in a command-line argument.

```sh
sessions/ds-analytics/.venv/bin/diza-analysis snapshot \
  --input sessions/ds-analytics/artifacts/demo/synthetic.json \
  --output sessions/ds-analytics/artifacts/internal/snapshot.json \
  --prompt-version v1
sessions/ds-analytics/.venv/bin/diza-analysis snapshot \
  --db sessions/cs2-backend/mvp/diza.sqlite3 \
  --output sessions/ds-analytics/artifacts/internal/live.json
```

JSON input is a list of call records or an object containing `calls`.
Records use `call_id`, `consent_analytics`, `started_at`, `ended_at`, `human_at`, `severity`, `expected_severity`, `category`, `language`, `outcome`, `zone_id`, `source`, and optional boolean quality labels.
Timestamps are Unix seconds or timezone-aware ISO timestamps; convert Retell milliseconds before supplying them.
For caller pseudonyms, supply `caller_hash`, `from_hash`, `phone`, or inbound/outbound `from_number` and `to_number`.
Anonymization applies keyed HMAC, removes free text, names, phones, exact coordinates, and every non-allowlisted field, and excludes unknown consent or opt-outs.
Failure mining inspects raw questions/transcripts only in memory and exports reason codes without copying text.

Snapshots report rates as `value`, `numerator`, and `denominator`.
Unobserved metrics stay `null`, including time to human when only transfer initiation is known.
P0 recall requires role-card or human ground truth; a severity prediction alone cannot establish recall.
Call intervals use `[start, end)`, and duplicate call events count once.
Internal artifacts are written atomically with owner-only permissions and must remain private.

The deployed SQLite schema stores only `caller_last4` on calls and cannot reliably join its phone-hash consent table.
The adapter therefore excludes unknown consent rather than joining unrelated people by last four digits.
If a trusted operational export provides consent per call, pass `--consent-file PATH`, whose JSON shape is `{"call_id": true}`.
A persisted opt-out takes precedence over supplementary consent.
Missing zone, outcomes, labels, and routing acceptance are reported as missing coverage rather than inferred from summaries.
The connection uses SQLite read-only mode and a consistent read transaction.

For public output, run `public` with the same input options and an `--output` path.
It emits only verified observations at least ten minutes old, grouped by zone, category, severity, and observed/synthetic source.
Every emitted cell has at least five distinct caller pseudonyms; call count alone is insufficient.
Suppressed-cell counts, overall totals, transcripts, identities, and precise locations are omitted.
This is small-cell suppression, not differential privacy; a host serving repeated public snapshots must also control differencing across releases.

## Evaluate recorded agent behavior

```sh
sessions/ds-analytics/.venv/bin/diza-analysis evaluate \
  --observations observed-agent-run.json \
  --require-publish \
  --output sessions/ds-analytics/artifacts/internal/agent-eval.json
```

Each observation has `case_id`, `severity`, `category`, `response`, `functions` as a list of function names, and `routed_pool`.
If required by a case, also supply `form_complete`.
Exactly one observation per golden case is required for a publish decision.
Emergency guidance, no false dispatch or human-identity claims, required function calls, P0 recall, and severity/category checks must all pass.
Self-harm cases require 988 guidance; other P0 cases require 911 guidance.
Classifier-only runs deliberately report safety compliance as `null` and cannot authorize publishing.
`--require-publish` exits nonzero when any gate or observation is missing.
The generated `retell-cases.json` contains portable caller prompts and criteria; CS#1's provider adapter owns Retell's upload schema.

`metrics.reach_metrics` computes unique high-risk opted-in residents reached within fifteen minutes, including contact/neighbor reach.
`metrics.judge_agreement` reports exact agreement by criterion and requires at least forty paired labels and 80% agreement before marking a criterion trusted.

## Public-data loaders

```sh
sessions/ds-analytics/.venv/bin/diza-analysis baseline \
  --start 2025-01-01 --end 2025-01-02 \
  --output sessions/ds-analytics/artifacts/myla311.json
sessions/ds-analytics/.venv/bin/diza-analysis acs \
  --year 2024 --state 06 --county 037 --tract 460100 \
  --output sessions/ds-analytics/artifacts/acs-tract.json
```

The MyLA311 loader uses the verified [2025 City of Los Angeles dataset](https://data.lacity.org/City-Infrastructure-Service-Requests/MyLA311-Service-Request-Data-2025/h73f-gn57), bounded pagination, an exclusive end date, Los Angeles local time, deduplication, and zero-volume days in area/hour means and standard deviations.
It selects only request number, creation time, request type, and coordinates, then exports area aggregates.
MyLA311 does not cover Altadena and service requests are not voice calls; these baselines cannot directly trigger voice-call z-score thresholds.
`detect_zone_level` accepts only a baseline explicitly marked `distinct_hazard_callers_per_window`.

The ACS loader uses [2024 B16001 language estimates](https://api.census.gov/data/2024/acs/acs5/groups/B16001.html) and [B01001 age estimates](https://api.census.gov/data/2024/acs/acs5/groups/B01001.html) for an explicitly supplied tract.
Set `CENSUS_API_KEY` in the environment when the service requires a key; keys are omitted from output provenance.
Language spoken at home is not a measure of English comprehension or proof that an alert missed someone.
Review tract-to-zone mappings before replacing the illustrative demographic profiles.

## Validation and remaining integration

The package has unit and CLI integration coverage for triage guards, priority ordering, responder eligibility, duplicate/hoax resistance, spatial/time windows, privacy suppression, consent revocation, metric denominators, source pagination, and publish gates.
The forty-case set includes eight P0 cases, eight hazard/context cases, twelve everyday actions, six language cases, and six compliance cases.
One compliance case also preserves a previous P0 label.

For backend compatibility, copy `sessions/cs2-backend/mvp` into this session's ignored `artifacts/backend-compat/`, install its requirements in this session's virtual environment, and run `npm ci` and `npm run build` inside the copy's dashboard folder.
Then run `python sessions/ds-analytics/scripts/check_backend.py sessions/ds-analytics/artifacts/backend-compat` using that virtual environment.
The runner isolates test modules because their import-time environment changes otherwise mix live and simulation settings, and mocks Retell backfill and external geocoding by default to avoid provider calls.
Individual tests can supply their own geocoding mock.
The runner validates the original backend, including its original dashboard assertion.
RelayLA's intentional replacement of `/ops` is covered by `tests_relay/` and the real browser tests.
The additional `tests_live/` suite verifies additive startup, original signature checks, API authentication, consent revocation, privacy, and caller-only transcript evidence.

Production activation requires a reviewed integration PR and access to the existing Railway service.
Official feed polling, reviewed production polygons, Supabase analytics migrations, embedding-based topic discovery/answer caching, acoustic models, automatic routing using the DS ranker, and real agent/judge runs remain separate integration work.
