# Deploy RelayLA on the existing Railway service

This release replaces the coordinator experience at `/`, `/ops`, and `/relay` with RelayLA.
Resident capability links open `/respond/<record-id>#<private-token>`.
The production image bundles the Retell Web SDK and uses the existing `/data/diza.sqlite3` persistent volume.
Changes are additive `relay_*` tables and an ASGI wrapper; no other session's source code is edited.

The current public service is https://diza-production.up.railway.app/ops.
This implementation is in [PR #13](https://github.com/wimaan3/DIZA/pull/13), awaiting teammate review and Railway activation.
It has not been declared live simply because the old app responds at that URL.

## Container validation

```sh
docker build -f sessions/ds-analytics/deploy/Dockerfile -t relayla:local .
docker run --rm -p 18774:8000 \
  -e OPS_API_TOKEN=local-container-check \
  -e DRILL_MODE=true \
  relayla:local
```

Check `/health/relay`, `/ops`, `/respond`, and `/relay/assets/voice-sdk.js`.
The Relay dashboard API must reject an unauthenticated request.
Use a disposable volume for validation; do not mount the production database in a test container.
The Dockerfile-specific ignore file excludes local environments, test artifacts, databases, and other session outputs from the build context.

## Railway activation

1. Obtain the teammate review required by `AGENTS.md`, then merge the PR through the normal `main` workflow.
2. Open [the existing DIZA Railway project](https://railway.com/project/543a6c85-18d6-423d-90a3-a08ecc347680?environmentId=1d4a33b9-4eb2-438c-a952-f4c703ea717a).
3. Keep the repository root as the build context, `main` as the source branch, and the existing volume at `/data`.
4. Set the service config file path to `/sessions/ds-analytics/deploy/railway.json`.
5. Keep `OPS_API_TOKEN` configured privately and preserve the existing provider variables.
6. Leave `RELAY_LEGACY_WORKERS` unset or `false` so the old dispatch, geocoding, and provider-wide backfill loops do not run for RelayLA.
7. Clear any custom Start Command override so the Dockerfile runs `uvicorn diza_analysis.live:create_app --factory`.
8. Deploy and verify `/health/relay` returns JSON with `product: RelayLA` and `status: ok`.
9. Open `/ops` and unlock it with the operator token.
10. Choose **Try the pickup scenario** only for an explicit synthetic demo, or publish an approved bilingual notice and enroll opted-in residents.

The service begins with an empty RelayLA workspace even if legacy DIZA call records exist.
Existing callers are not silently enrolled or treated as opted in to this new workflow.
The persistent volume also holds the generated resident-link signing secret, so links survive a restart or redeploy.
Do not detach or replace that volume when deploying this PR.

## Activate a dedicated Retell browser agent

Deploy the web service first, then choose a voice available in the connected Retell account.
Set `RETELL_API_KEY` privately in the shell running the setup script and in Railway.

```sh
sessions/ds-analytics/.venv/bin/python \
  sessions/ds-analytics/scripts/configure_relay_voice.py \
  --base-url https://diza-production.up.railway.app \
  --voice-id cartesia-Cleo
```

The command prints the full proposed agent/LLM configuration without changing Retell.
Run it again with `--apply` after inspecting the configuration to create a dedicated RelayLA LLM and agent.
The script verifies the real RelayLA health response before creating resources.
It writes IDs to ignored `artifacts/relay-retell.json`, preventing accidental repeated creation.
If agent creation fails after LLM creation, the receipt preserves the LLM ID for recovery.
Existing DIZA agent IDs and prompts are not changed.

Set Railway's `RELAY_RETELL_AGENT_ID` to the created agent ID and redeploy.
`/health/relay` then reports `voice_available: true` when both required server variables are set.
This flag reports configuration presence, not a completed real voice test.
Run a consenting browser conversation from a synthetic resident link and verify the dashboard changes before a live demo.

The server creates a Retell v3 web session and overrides the call language from the explicit English/Spanish selection.
Only a short-lived web session token and connection fields reach the browser.
No Retell API key is shipped in JavaScript.
Signed custom functions use `/retell/relay/fn/{action}`, for `context`, `save_progress`, `confirm_instruction`, `confirm_assistance`, and `needs_clarification`.
The dedicated agent webhook is `/retell/relay/webhook`.
The agent stores basic provider call attributes only; application confirmations and assistance requests persist in SQLite during the conversation.
Setup does not place calls, buy phone numbers, enable SMS, or contact residents.

## Remaining access requirements

The current agent session has no connected Railway tool or deployment credentials.
The code PR also has no teammate approval yet.
Those requirements prevent production activation; container and localhost validation do not establish that the public app has been updated.

## Rollback

Select the preceding successful Railway deployment, or restore the service config path to `/railway.json` and redeploy the preceding commit.
Keep the existing `/data` volume attached.
The additional tables can remain unused by the older app; rollback does not require deleting resident or call data.
The optional legacy analytics page remains available at `/analytics`; its private aggregates additionally require `DIZA_ANALYTICS_SALT`.
