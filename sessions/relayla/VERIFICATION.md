# Verification: DIZA / RelayLA

Observed on 2026-10-17 UTC (2026-10-16 evening in Los Angeles), using only synthetic cases.

## Automated checks

Command, from this folder:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

**Result: 42 tests passed.** Test databases are temporary. Provider callbacks are signed locally with dummy test keys, and web-call creation uses an injected fake provider client. No test makes a live Retell request.

The checks cover:

- Persistent cases and histories across store/application restart.
- Independent current-notice confirmation, contact outcomes, human acceptance, and completion.
- Wrong read-back, stale responses, immutable notice history, and competing notice revisions.
- Idempotent retries and conflicting reuse of an event ID.
- Priority preservation, P0 volunteer/callback restrictions, responder capacity, and failed handoffs.
- Operator authentication, configured agent allowlist, exact raw-body signature verification, and call-to-case scope.
- Late call starts, ended calls, older-call events, and persisted lifecycle ordering.
- Preserved assistance details and actual acceptance status in human requests.
- Operator control over a bound case's approved notice association.
- FastAPI sub-application mounting, relative assets, and no-store API responses.

Runtime exercised: Python 3.12; FastAPI 0.143.3; uvicorn 0.54.0; httpx 0.28.1; Retell Python SDK 6.2.7. The installed Starlette test helper emits an httpx deprecation warning; the suite completes successfully.

## Browser checks

Used Chromium against the running FastAPI application and SQLite store. The test database contains only synthetic data and is separate from the default demo database.

| Workflow | Observed result |
|---|---|
| Initial desktop load | Eight seeded requests, P0 first, and urgent human-handoff control prominent. |
| P0 handoff | Assign, accept, and complete produce distinct recorded transitions. |
| Spanish read-back | Wrong action requires clarification; correct action confirms the notice version. |
| Contact interruption | Dropped/resumed contact preserves an existing valid confirmation. |
| Revised notice | v1 becomes pending after v2 publication; a wrong v2 answer explicitly needs clarification; correct v2 confirmation preserves open assistance. |
| Responder does not accept | Human-handoff failure releases the proposal without incrementing resident contact failures. |
| Completion gate | Assistance requires explicit human acceptance before completion. |
| Disconnected text intake | Draft remains unsent in browser storage across reload, sync is explicit, and replay with the same event ID does not duplicate the report. |
| Mobile | At 390px, dashboard and intake dialog have no horizontal overflow. |
| JavaScript errors | Zero page errors during the exercised workflows. |

[Dashboard screenshot](preview.png)

## Retell configuration checks

All six native `general_tools` entries in `retell/tools.json` parse and validate against `GeneralToolCustomTool` from SDK 6.2.7. Their names match the adapter's exposed functions. Prompt markers are unique. The URL placeholders deliberately require replacement.

## Limits of this evidence

Live provider authentication, a published agent conversation, microphone behavior, real speech accuracy, public hosting, telephone/SMS delivery, and external dispatch or booking were not exercised. Offline verification covers a previously loaded page and its local intake drafts; it does not establish a fresh offline application load or offline voice. Workflow tests and synthetic demonstrations do not measure emergency-response effectiveness.
