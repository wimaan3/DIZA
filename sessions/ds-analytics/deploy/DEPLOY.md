# Activate DIZA analytics on Railway

The current public application is https://diza-production.up.railway.app/ops.
PR #9 merged the analysis package, but the existing Dockerfile does not copy or install that package.
This session provides a separate Dockerfile, Railway config, and ASGI entry point so activation can stay inside the session ownership boundary.

## What this release runs

- Existing `/ops`, `/supporter`, `/text`, `/api/*`, location links, Retell functions, and webhooks.
- `/analytics` and its static assets.
- `/api/analytics`, protected by the existing operator token and `Cache-Control: no-store`.
- `/health/analysis`, exposing readiness, whether the private analytics key is configured, and the deployed revision.

The wrapper runs the existing application's startup/shutdown lifecycle and uses the same `/data/diza.sqlite3` volume.
Its additive `analysis_call_links` table stores operational consent linkage and pseudonyms, with no phone, transcript, name, address, or coordinates.
Original operational severity, routing, notifications, and dispatch behavior stay with the host application.
Analysis predictions are displayed as review signals and are not human ground truth.

## Build and validate

```sh
docker build -f sessions/ds-analytics/deploy/Dockerfile -t diza-analysis:local .
sessions/ds-analytics/.venv/bin/python -m unittest discover \
  -s sessions/ds-analytics/tests_live -v
sessions/ds-analytics/.venv/bin/python sessions/ds-analytics/scripts/check_backend.py \
  sessions/ds-analytics/artifacts/backend-compat --with-analysis
```

The compatibility runner requires a disposable copy of the current backend and built dashboard, as described in the session README.
No real provider calls are needed for these checks.

## Railway activation

1. Obtain the required teammate code review and merge the integration PR to `main`.
2. Open the existing production service in [the DIZA Railway project](https://railway.com/project/543a6c85-18d6-423d-90a3-a08ecc347680?environmentId=1d4a33b9-4eb2-438c-a952-f4c703ea717a).
3. Confirm the source branch is `main` and the build context is the repository root.
4. Set the service's config file path to `/sessions/ds-analytics/deploy/railway.json`.
5. Keep the current volume mounted at `/data` and keep existing provider/operator variables.
6. Add `DIZA_ANALYTICS_SALT` as a private, cryptographically random value of at least 16 bytes.
7. Clear a custom Start Command override so the new Dockerfile's command runs `uvicorn diza_analysis.live:create_app --factory`.
8. Deploy the latest commit and wait for `/health/analysis` to return HTTP 200 with `configured: true`.
9. Open `/analytics` and unlock it with the existing operator token.

Railway connection is required to apply the service settings.
Do not create a replacement project, detach the volume, overwrite provider keys, or use a local environment file as the production configuration.

## Data behavior

Only a successful request through the existing signed Retell handler is observed.
The original raw request bytes remain available for signature verification.
Analysis capture runs after the response is sent, and a capture failure cannot change the operational handler's result.
Agent speech is excluded from triage evidence when transcript roles are supplied.

Consent is read from the existing operational consent table, linked through the accepted caller identity rather than last four digits.
Unknown consent stays excluded.
An analytics opt-out excludes prior linked calls immediately and clears their stored prediction/pseudonym fields.
Historical calls without an identity/consent link are not guessed or silently backfilled.
Existing calls can therefore appear in the operational coverage count while the analytics count remains zero.

No synthetic observations are seeded into the production database.
Unobserved resolution, recall, safety, and handoff measures stay unmeasured.
Official crisis declarations and automated public messaging are not part of this activation.

## Rollback

Select the previous successful Railway deployment, or restore the service config file path to `/railway.json` and redeploy the previous commit.
Keep the existing `/data` volume attached.
The added table can remain unused by the old application; rollback does not require deleting call data.
