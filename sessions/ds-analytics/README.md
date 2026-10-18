# DIZA data analysis

The local hotel service demo is documented in [HOTEL_DEMO.md](HOTEL_DEMO.md).
Run `sessions/ds-analytics/.venv/bin/python sessions/ds-analytics/scripts/serve_hotel.py --demo` from the repository root and open http://127.0.0.1:18772/hotel.

An installable Python package for triage, responder ranking, corroboration, evaluation, and call metrics.
Python 3.11 or newer is required; runtime dependencies are all from the standard library.
The package stays in this session's folder to honor the repository's session isolation rule.

Implemented:

- EN/ES lexicon, clause-level context guards, structured-field classification, and priority scores.
- P0 severity floors and empty P0 helper pools; verified responder eligibility before skill, language, load, and fatigue ranking.
- Space/time DBSCAN with distinct callers, per-caller rate limiting, WATCH/ASK evidence, optional normalized official evidence, and human-only crisis declaration and stand-down.
- Seeded synthetic residents, responders, drill calls, role cards, and CSV registry export.
- Forty golden cases, deterministic evaluation, agent-observation safety gates, failure mining, reach metrics, and judge agreement.
- Consent-aware pseudonymization, internal metric snapshots, and delayed public aggregates with at least five distinct contributors per cell.
- Read-only access to the deployed SQLite schema, a MyLA311 baseline loader, and a Census ACS language/age profile loader.

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
The host application is not modified or automatically wired to these functions by this PR.

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

Live backend wiring, official feed polling, reviewed production polygons, real caller collection, Supabase analytics migrations, embedding-based topic discovery/answer caching, acoustic models, and real agent/judge runs remain separate integration work.
