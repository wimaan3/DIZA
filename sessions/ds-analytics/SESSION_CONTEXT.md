# Session context: ds-analytics

- **Session:** Codex implementation of the DIZA data science work package, requested by Deepanshu.
- **Branches:** `ds/analysis-triage` for merged PR #9; `ds/live-analysis` for the follow-up production integration, started from `ff7c720`.
- **Scope:** Installable triage/analysis package plus an optional live deployment wrapper, consent capture, and protected analytics page.

## Files in this folder

| Path | Contents |
|---|---|
| `pyproject.toml` | Dependency-free package metadata and CLI entry point |
| `diza_analysis/triage.py` | Lexicon hits, context guards, classification, priority, pools, responder ranking |
| `diza_analysis/zones.py` | Distinct-caller space/time DBSCAN and human-controlled zone evidence |
| `diza_analysis/privacy.py` | Consent filtering, keyed pseudonyms, field allowlist, delayed public cells |
| `diza_analysis/metrics.py` | Metric denominators, peak concurrency, failure mining, reach, judge calibration |
| `diza_analysis/evaluation.py` | Golden classifier checks and observed-agent publish gates |
| `diza_analysis/datasets.py` | Seeded synthetic residents, responders, calls, and drill cards |
| `diza_analysis/sources.py` | Bounded MyLA311 loader and keyed Census ACS profiles |
| `diza_analysis/storage.py` | Read-only adapter for the deployed SQLite calls/reports schema |
| `diza_analysis/cli.py`, `__main__.py`, `__init__.py` | CLI and public import surface |
| `diza_analysis/config.py`, `config/*.json` | Settings, EN/ES lexicon, illustrative zones and demographic profiles |
| `diza_analysis/timeutil.py` | UTC timestamp normalization |
| `diza_analysis/evals/golden.json` | Forty labeled role-card and safety cases |
| `tests/` | Unit and end-to-end CLI tests |
| `scripts/check_backend.py` | Existing backend tests in isolated processes without Retell backfill |
| `diza_analysis/live.py`, `live_store.py` | Composed ASGI application, signed-event observer, operational consent links, and live aggregates |
| `diza_analysis/web/` | Responsive analytics page using the existing operator token |
| `deploy/` | Standalone Dockerfile, Railway config, activation instructions, and rollback procedure |
| `tests_live/` | Host integration tests for authentication, signatures, lifecycle, opt-outs, and privacy |
| `README.md` | Setup, API contracts, privacy limits, eval workflow, source links, integration notes |
| `.gitignore` | Local artifacts, build output, package metadata, and lint cache exclusions |

## Decisions made

1. Keep all committed files inside this session to comply with AGENTS.md; do not alter CS#1 or CS#2 code.
2. Preserve the handoff's function names while injecting record collections as keyword-only arguments for pure, deterministic tests.
3. Use standard-library Python and JSON config so core analysis works without model downloads, API credentials, or a live service.
4. Preserve every P0 lexical hit and existing severity floor, and return no helper pools or responder candidates for P0.
5. Require verified, available, appropriately skilled responders before applying language/load/fatigue scores.
6. Count distinct callers with location agreement; one caller cannot form a density cluster by repeatedly reporting.
7. Automatically suggest only WATCH/ASK, retain existing escalated levels, and require a human for crisis declaration and stand-down.
8. Separate synthetic fixtures, classifier performance, observed agent safety, and missing instrumentation explicitly.
9. Require actual observations for all golden cases before the evaluation CLI can authorize a publish decision.
10. Drop free text from exported analytical rows and require consent, keyed pseudonyms, verification, delay, and at least five people per public cell.
11. Treat the old SQLite last-four-digit identity as insufficient for consent joins; unknown consent remains excluded.
12. Do not apply MyLA311 service-request volumes as if they measured voice-call traffic.
13. Compose the existing host application and preserve its lifecycle/routes rather than editing another session's files.
14. Observe only successful signed Retell requests, after their response is sent; capture failures do not alter operational results.
15. Keep operational classification/routing in the host, and label analytics triage predictions separately from ground truth.
16. Use an additive operational link table to resolve future call consent; do not guess or backfill identities from legacy last-four-digit fields.

## Key facts verified

- The DS handoff requests triage, synthetic data, responder matching, corroboration, golden evals, privacy processing, and metric snapshots.
  Source: `sessions/planning-claude/handoff/03_DS_TRIAGE_DATA_EVALS.md` and `00_CONTRACTS.md`.
- The conservative P0 policy, three/six-caller WATCH/ASK thresholds, and human declaration come from `sessions/planning-claude/TRIAGE.md`.
- Consent and public k >= 5 rules come from `sessions/planning-claude/SYSTEM_SPEC.md` section 2.7.
- The deployed app's SQLite `calls` table has caller last four digits and no direct consent/zone/outcome/quality linkage.
  Source: `sessions/cs2-backend/mvp/backend/app/main.py` and `retell_fns.py`, read at `da67553`.
- The [MyLA311 2025 resource](https://data.lacity.org/resource/h73f-gn57.json) has `srnumber`, `createddate`, `requesttype`, `latitude`, and `longitude`.
  Verified through its live endpoint on October 17, 2026, including a successful one-day baseline fetch.
- [ACS B16001](https://api.census.gov/data/2024/acs/acs5/groups/B16001.html) identifies the language categories and [B01001](https://api.census.gov/data/2024/acs/acs5/groups/B01001.html) supplies age groups.
  The live Census data query returned a `Missing Key` HTML page without credentials; the loader now supports `CENSUS_API_KEY` and a clear missing-key error.
- The demo deterministically generates 500 residents, 10 responders, and 200 calls with the specified 60/25/10/5 drill mix and 30% non-English cards.
- The 40-case classifier evaluation passes, including nine expected P0 labels when counting the severity-floor compliance case.
  This is synthetic classifier evidence and does not establish live agent safety.
- All 54 analysis tests pass and Ruff lint/format checks pass.
- All 31 existing backend tests pass when their conflicting module-level environments are isolated with `scripts/check_backend.py`.
  The existing dashboard also builds successfully in a disposable copy.
- PR #9 was merged at `ff7c720`; Railway reported a successful deployment.
  Sources: GitHub PR #9 and deployment `7145263993` status.
- The current application responds at https://diza-production.up.railway.app/ops, and its authenticated state endpoint reports live mode.
  The deployed app has no analytics routes and its original Dockerfile omits the analysis package.
  Verified through HTTP and the live Retell agent's webhook URL on October 17, 2026.
- The follow-up wrapper passes 14 integration tests, and 36 current backend tests pass through the wrapper.
  The 54 original analysis tests still pass, Ruff/JavaScript syntax checks pass, and the new Docker image builds successfully.
- The built container serves `/ops`, `/supporter`, `/text`, `/analytics`, JavaScript assets, `/api/state`, and `/api/analytics` over HTTP.
  Its health endpoint reports the analysis key configured, and unauthenticated analytics requests return 401.
  The disposable validation container used synthetic settings and an empty temporary volume, then was stopped.

## Open questions

- Which reviewed tract-to-zone mappings and official polygons should replace the illustrative demo profiles?
- Where will the host persist explicit per-call analytics consent, verified zone, human acceptance timestamps, and quality labels?
- Which teammate will review the live integration, and who can connect the existing Railway service to apply its build configuration?

## Not done yet

- The new live integration has not been activated on Railway; the current public app continues using its existing container.
- No other session folder, shared root config, provider agent configuration, or production data was changed.
- No live callers, Retell simulations, clinical validation, or forty-label human/judge calibration were run.
- No automatic official-feed polling, Supabase migration, embeddings/topic model, semantic answer cache, acoustic inference, or photo processing is included.
- Census live demographic data requires credentials; defaults remain explicitly illustrative rather than claimed as Census-derived.
- Internal snapshots must remain private; public output uses cell suppression and does not provide differential privacy across repeated releases.
- Teammate code review and Railway connection are required before the follow-up integration can be merged and activated.
