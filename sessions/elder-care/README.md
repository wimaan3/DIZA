# DIZA Care

A staff dashboard for an elderly residential care home, with urgent response and everyday care in one workspace.
This implementation follows the user's explicit preference for a staff dashboard only.
All new files live in this session folder, as required by the repository's `AGENTS.md`.

## What staff can do

- Record meals, water, personal care, medication questions, companionship, maintenance, and wellbeing requests against a resident and room.
- Review daily care and urgent response in separate queues, with an urgent banner visible from every view.
- Accept responsibility, start care, add handoff notes, escalate concerns, and resolve requests with a required outcome.
- Review resident language and interaction preferences before responding.
- Record daily wellbeing observations, with overdue checks flagged after 10 am in the facility timezone.
- Turn a check-in concern or no response into a follow-up request automatically.
- Search by resident, room, request description, or reference code and filter open requests by status.
- Review completed care and its handoff history.

Urgent requests and medication questions require a nurse or care lead to accept them.
Facilities staff can accept routine maintenance requests.
A routine request escalated while held by a caregiver or facilities staff returns to the urgent queue awaiting a nurse or care lead.
There is no priority-lowering action.

Original report words are preserved separately from summaries.
A small, conservative English cue matcher can raise urgency from either field.
This is a routing safeguard for human review, not a clinically validated triage system or multilingual medical classifier.
Staff can explicitly mark any request urgent.

## Run the integrated app with Docker

From the repository root:

```sh
docker build -f sessions/elder-care/Dockerfile -t diza-care .
docker run --rm -p 127.0.0.1:8000:8000 diza-care
```

Open <http://127.0.0.1:8000/care> and select **Load demo scenarios**.
The five scenarios are fictional and loading them repeatedly does not duplicate requests.
The original `/ops`, `/supporter`, `/text`, `/api/*`, and signed Retell endpoints remain reachable through the same server.
Care requests use their own SQLite database and do not pollute the legacy incident queue.

To preserve demo data across container restarts, mount a local Docker volume at `/data`.
The container defaults to `/data/care.sqlite3` for care records and `/data/diza.sqlite3` for the original engine.

## Run only the care workspace locally

From this folder:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
CARE_INCLUDE_LEGACY=false .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The care frontend is plain JavaScript and CSS and needs no build step.
Its default local database is `care.sqlite3`, ignored by Git.
The `CARE_INCLUDE_LEGACY=false` option excludes the original engine and its screens for this lighter local run.
The Docker build includes both apps and compiles the original React frontend.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `CARE_DB` | `care.sqlite3` beside `app.py` | Persistent care database |
| `CARE_FACILITY_NAME` | `Willow House` | Facility display name |
| `CARE_TIMEZONE` | `America/Los_Angeles` | Daily check-in boundary and 10 am due time |
| `CARE_INCLUDE_LEGACY` | `true` | Mount the existing DIZA backend and built screens |
| `DIZA_DB` | `legacy.sqlite3` beside `app.py`, unless already set | Original engine database |
| `OPS_API_TOKEN` | Unset | Optional shared staff token on care APIs and existing operations APIs |
| `DRILL_MODE` | `true` | Enables fictional demo loading; `false` disables that endpoint |
| `RETELL_API_KEY` | Unset | Required for signed voice room lookup and request intake |

This is a demo with synthetic resident and staff identities.
The staff selector simulates roles and is not authenticated individual identity.
The shared token does not provide individual role authorization, and the app is not ready to hold real resident health information.
Keep the demo bound to localhost or behind existing access controls.
It does not send staff pages, texts, calls, medication instructions, or emergency dispatch.

## Deployment handoff

The included `railway.json` and Dockerfile are ready to make the care workspace the root experience while preserving the original routes.
After teammate review and merge, set the Railway service's config file path to `sessions/elder-care/railway.json` and keep its existing `/data` volume and environment settings.
The repository's shared root deployment configuration is unchanged because this session must write only inside its own folder.
This PR has not deployed the care app or changed live phone agents.

## Optional care-home voice intake

`agents/care-intake.md` contains an opt-in care-home prompt.
`agents/tools.json` contains function definitions with a placeholder HTTPS host.
The implemented endpoints accept Retell's signed `{call: {call_id}, args: {...}}` payload:

- `POST /retell/fn/lookup_care_resident` resolves a room to an existing resident and returns a clear not-found result for unknown rooms.
- `POST /retell/fn/create_care_request` records the confirmed resident request in the care queue and preserves the original quote.

Unsigned requests are rejected and an unset API key returns 503.
Retries with the same call and arguments reuse the existing request.
These endpoints do not connect the currently deployed voice agents automatically.
A verified staff-transfer destination and a live integration test are still required before operating a care-home phone line.

## Validation

From this folder:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
npm ci
npx playwright install chromium
CARE_PYTHON="$PWD/.venv/bin/python" npm run test:e2e
npm run check
```

Backend tests cover lifecycle, clinical-role routing, concurrency, stale updates, persistence, submission retries, escalation, check-in follow-ups, facility-local due times, token protection, and signed voice functions.
Browser tests cover full care delivery, urgent escalation, check-ins, stale-data errors, network recovery, keyboard focus, mobile layout, and axe accessibility checks on daily care, urgent response, resident roster, and the request dialog.
Browser screenshots and traces are written to the ignored `test-results/` folder.

The existing backend suite was also verified in an isolated checkout with its original dashboard built.
Run each existing test file in a separate Python process because those modules set different environment variables before importing the shared backend.
Running all modules in one discovery process produces order-dependent baseline failures.
