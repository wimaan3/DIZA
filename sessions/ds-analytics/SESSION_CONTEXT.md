# Session context: ds-analytics

- **Session:** Codex implementation requested by Deepanshu, followed by the explicit request to repurpose the app as RelayLA and make it live.
- **Branches:** `ds/analysis-triage` for merged PR #9; `ds/live-analysis` for [PR #13](https://github.com/wimaan3/DIZA/pull/13).
- **Scope:** RelayLA community pickup notices, versioned confirmations, separate assistance follow-up, English/Spanish text and browser voice integration, offline drafts, and deployment packaging.
- **Earlier work retained:** Installable DIZA analysis CLI and optional consent-aware legacy analytics page.

## Files in this folder

| Path | Contents |
|---|---|
| `diza_analysis/relay/schema.sql` | Additive persistent notice versions, resident records, confirmations, assistance, attempts, follow-ups, events, request receipts, and private-link secret |
| `diza_analysis/relay/store.py` | Transactional domain logic, stale-version handling, confirmation checks, explicit task ownership, concurrency, and idempotency |
| `diza_analysis/relay/models.py` | Strict API inputs with explicit confirmation booleans |
| `diza_analysis/relay/api.py` | Protected coordinator/resident APIs, signed Retell functions/webhook, RelayLA pages, assets, and readiness |
| `diza_analysis/relay/voice.py` | Server-owned Retell call bindings, per-call language selection, context refresh, and disconnect recovery |
| `diza_analysis/relay/voice_config.py` | Dedicated RelayLA prompt, five custom tools, and provider retention settings |
| `diza_analysis/relay_web/` | Responsive coordinator and resident UI, EN/ES copy, IndexedDB drafts, service worker |
| `client/` | Pinned Retell SDK build, formatting, lockfile, and Playwright browser tests |
| `scripts/serve_relay.py` | Isolated localhost preview with explicit synthetic demo option |
| `scripts/configure_relay_voice.py` | Dry-run configuration and new-agent creation after deployed health verification |
| `tests_relay/` | Domain/API, signature, concurrency, versioning, privacy, and mocked voice recovery tests |
| `deploy/` | Dockerfile, restricted build context, Railway config, activation instructions, and rollback |
| `diza_analysis/live.py`, `live_store.py`, `web/`, `tests_live/` | Composed entry point and retained legacy consent-aware analytics |
| `diza_analysis/triage.py`, `zones.py`, `privacy.py`, `metrics.py`, `evaluation.py` | Original deterministic analysis functionality |
| `diza_analysis/datasets.py`, `sources.py`, `storage.py`, `timeutil.py` | Synthetic fixtures, MyLA311/ACS sources, read-only legacy adapter, UTC normalization |
| `diza_analysis/cli.py`, `__main__.py`, `__init__.py`, `config.py`, `config/`, `evals/`, `tests/` | Core CLI, settings, lexicon, illustrative profiles, golden evaluation, and tests |
| `scripts/check_backend.py` | Original backend tests isolated in subprocesses, with external backfill/geocoding mocked |
| `README.md`, `pyproject.toml`, `.gitignore` | Setup, demo, contracts, dependency metadata, and local output exclusions |

## Decisions made

1. Implement the user's RelayLA brief as the current product direction, using one community center and pickup-location changes.
2. Keep every committed change in this session; read other sessions as dependencies without editing their source.
3. Serve RelayLA at `/`, `/ops`, and `/relay`, with private resident links at `/respond/<record-id>#<capability>`.
4. Preserve approved EN/ES notice text and title by immutable version; do not copy old acknowledgments into a new version.
5. Record a resident's specific response as caller confirmation, without claiming comprehension or safety.
6. Preserve a stable resident/notice record across voice, text, disconnects, and updates.
7. Keep assistance independent from instruction confirmation; create a task only after confirmed readback, then require explicit acceptance and completion.
8. Use SQLite transactions, unique constraints, request receipts, expected notice versions, and assistance revisions to handle retries and competing coordinators.
9. Store offline drafts and queued original-version payloads in IndexedDB; label them Not sent until acknowledged by the server.
10. Cache only the resident form shell for offline navigation; protected APIs are never cached by the service worker.
11. Bind voice functions to server-created calls, verify Retell's original raw signature, and never trust a browser-supplied record ID in provider callbacks.
12. Bundle Retell SDK 3.0.2 with a server proxy; browser code receives short-lived session credentials only.
13. Prepare a dedicated RelayLA agent without modifying existing DIZA phone agents or initiating calls.
14. Disable legacy dispatch, geocoding, and provider-wide call-backfill workers by default for this new product; preserve their explicit legacy opt-in.
15. Seed synthetic residents only on an explicit demo action; do not silently enroll existing real callers.
16. Preserve the existing SQLite volume, including its generated resident-link signing secret, during deployment and rollback.
17. Update the existing open PR #13 around the final RelayLA scope, then require the repository's teammate review before merging.

## Key facts verified

- The detailed RelayLA brief was supplied directly by the user in this conversation.
- [Retell web-call documentation](https://docs.retellai.com/deploy/web-call) and the installed [SDK source](https://github.com/RetellAI/retell-client-js-sdk) support browser calls through `RetellClient`, a custom server fetch proxy, and per-session hooks.
  The installed SDK invokes `/v3/create-web-call`; the backend forwards the returned transport fields.
- [Retell custom functions](https://docs.retellai.com/build/single-multi-prompt/custom-function) call the backend during a conversation, enabling progress persistence before call end.
  Server-side signature and call binding checks are exercised by tests.
- [Retell language configuration](https://docs.retellai.com/agent/language) supports the explicit English/Spanish call configuration used here.
- Twenty-six RelayLA API/domain tests pass, including stale responses, preserved notice titles/text, clarification, consent, duplicate retries, task ownership, concurrent updates, signatures, and mocked voice reconnects.
- Four real Chromium browser tests pass: Spanish confirmation and assistance through a revision, offline draft reload and original-version synchronization, mobile coordinator follow-up, and retry after a lost successful server response.
- Browser screenshots were visually inspected at desktop and mobile sizes.
  The mobile coordinator now uses resident cards so names, instruction status, assistance, and actions remain visible together.
- All 54 original analysis tests, 14 legacy integration tests, and 36 native backend tests pass.
  The native test runner preserves the original dashboard assertion; the replacement RelayLA UI is tested separately.
- Ruff lint/format checks, client formatting checks, and whitespace checks pass.
- The production Docker image builds with the real bundled SDK and serves RelayLA pages, static assets, signed-function routes, protected APIs, and health over HTTP.
  A disposable container successfully saved a Spanish confirmation and assistance request, then retried without duplicating the task.
- The public `/health/relay` URL currently returns the old app's HTML fallback, not RelayLA health JSON.
  This confirms that the new product is not yet deployed.
- Railway discovery still reports the app as not installed.
  The user selected connecting Railway for deployment; installation and account sign-in remain user-side steps.
- The original DS handoff, conservative triage policy, consent restrictions, and small-cell public privacy rules remain documented in `sessions/planning-claude/handoff/`, `TRIAGE.md`, and `SYSTEM_SPEC.md`.
- PR #9 was merged at `ff7c720`; PR #13 remains the release PR for this session.

## Open questions

- Which teammate will provide the required code review for the repurposed app?
- When will Railway installation and account connection be completed so the existing service settings can be applied?
- Which available Retell voice should be used for the final live browser rehearsal?
- What exact kickoff twist or mystery problem should replace the synthetic pickup scenario, if different from the supplied brief?

## Not done yet

- Production is not running this PR; the public URL still serves the preceding DIZA app.
- No dedicated RelayLA Retell agent has been created remotely and no real human voice conversation has been run.
  The setup script and signed voice persistence path are ready, with provider calls mocked in automated tests.
- Telephone provisioning, two-way SMS, automated bulk outreach, unrestricted language detection, and transport optimization are outside this MVP.
- No real residents, personal phone numbers, provider keys, `.env` files, browser test traces, or generated SDK bundle are committed.
- The shared-token coordinator workflow does not yet provide individual accounts or multi-organization tenancy.
- Original Census live queries still require credentials; illustrative demographic profiles remain labeled as such.
- Production activation requires the teammate review and access to the existing Railway service, followed by a dedicated voice-agent configuration and a consenting browser rehearsal.
