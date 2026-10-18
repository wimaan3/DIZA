# DIZA Resident Services

One staff workspace for apartments and care homes, combining Imaan's building operations with resident support.
Every resident uses the same units, intake form, floor plan, urgent/everyday queue, and request history.
Optional support belongs to a resident profile; there is no separate apartment or care-home mode.
All implementation files live in this session folder.

## Shared experience

The integrated root opens `/ops`, preserving the existing 3D/2D geographic map, report pins, urgent and non-urgent lanes, incident cards, callbacks, handoffs, zone drawing, offline map, metrics, call activity, responders, and wall view.
The original Supporter inbox, region controls, languages, responder coverage and backup details remain available.
Open **Building** at `/building` for the shared residential workflow.
Older `/care` links redirect to the same screen.

- One floor plan shows units, residents, open requests, shared risers and HVAC relationships.
- One resident directory supports apartment-style units such as 2D and care-home rooms such as 101.
- Managers, nurses and care leads can maintain resident profiles and enable or disable daily check-ins per person.
- One intake form records repairs, everyday help, personal care, medication questions and urgent needs.
- One queue shows each issue once, with urgent, everyday, completed, unit and search filters.
- A maintenance request contains the shared repair, original reports, resident follow-up, quotes, transcripts, assignment, access consent and history.
- A request stays open until the repair and every resident follow-up have recorded outcomes.
- Existing repair assignment, resident updates, merge/unmerge/split, unit editing and response insights use Imaan's building engine directly.

The former care-home/apartment selector and alternate apartment component are removed.
Existing legacy apartment demo API data is retained for compatibility; it is not another Building experience.
New residents and requests use the shared model.
The sidebar has Building, 911 operations and Supporter inbox.
Its urgent badge uses the same grouped-request counting as the Building queue.

`workspace/entry.jsx` imports the current original dashboard shell directly.
A checked Vite adapter supplies the shared Building implementation without editing another session's files.
A same-origin frame isolates workspace styles and dialogs while reusing the operator access token.
Every integration anchor is checked at build time.
The map adapter preserves MapLibre's container classes when drawing or placing reports.

## What staff can do

- Record meals, water, personal care, medication questions, companionship, maintenance, and wellbeing requests against a resident and room.
- Review care and repairs in one work queue, with urgency filters and an urgent banner.
- Accept responsibility, start care, add handoff notes, escalate concerns, and resolve requests with a required outcome.
- Review resident language and interaction preferences before responding.
- Record daily wellbeing observations, with overdue checks flagged after 10 am in the facility timezone.
- Turn a check-in concern or no response into a follow-up request automatically.
- Search by resident, room, request description, or reference code and filter open requests by status.
- Review completed care and its handoff history.
- Use the shared floor plan to filter care needs and physical incidents for a room.
- Group duplicate room reports into one facilities ticket and review related issues by floor, riser, or HVAC zone.
- Assign facilities staff or a demo vendor, coordinate access, record repair outcomes, and reopen an incomplete repair.
- Merge, unmerge, or separate reports while preserving original quotes, linked resident requests, and available call transcripts.
- Review first staff action time, duplicate grouping, shared-problem hints, and maintenance review targets.

## Request lifecycle

Resident intake and physical repairs share a transaction and appear as one request in the Building queue.
Duplicate reports for the same unit and issue within two hours share the physical repair while retaining each person's report and required outcome.
Related issues can span units through a riser, floor or HVAC zone.
Merged requests retain every affected unit for filtering.
Closing a repair leaves the request visible while any resident follow-up remains open.

Managers, care leads and facilities staff coordinate repairs and vendors.
Nurses and care leads handle urgent resident needs and medication questions.
Check-ins are opt-in for newly added residents; the existing assisted-living demo residents retain their schedules.
A check-in concern automatically creates a request in the same queue.
Profile edits check versions, retain an audit record and preserve existing physical repairs when a resident moves.

Every original quote and available call context remains visible.
Unmerging or separating reports never lowers urgency silently.
Entry refusals and unknown permissions are preserved conservatively.
Unverified shared areas remain separate until staff confirm their location.
Assignments and updates record staff actions without contacting anyone automatically.
Maintenance targets are demo review thresholds, not clinical guarantees.
No tenancy-law clock is assumed to apply to every residential setting.

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

Open <http://127.0.0.1:8000/ops> for the original map and operational tools.
Select **Load demo: falls & freeway crash** to populate the geographic map and **Load demo week** in Building to populate its floor plan.
In Building, **Load demo scenarios** populates the shared residential workflow.
The eight reports are fictional and loading them repeatedly does not duplicate care requests.
They include a fall, everyday needs, a maintenance issue, two rooms reporting heating problems, and a repeat report that shares a repair ticket.
Three clearly labeled synthetic call transcripts demonstrate the call-context panels.
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

The included `railway.json` and Dockerfile open the full operations workspace by default and include the resident-care addition.
After teammate review and merge, set the Railway service's config file path to `sessions/elder-care/railway.json` and keep its existing `/data` volume and environment settings.
Keep `CARE_INCLUDE_LEGACY=true` for the combined demo and deployment.
The `false` setting is only for the isolated care development server and excludes the operational routes.
The repository's shared root deployment configuration is unchanged because this session must write only inside its own folder.
This PR has not deployed the care app or changed live phone agents.

## Optional care-home voice intake

`agents/care-intake.md` contains an opt-in care-home prompt.
`agents/tools.json` contains function definitions with a placeholder HTTPS host.
The implemented endpoints accept Retell's signed `{call: {call_id}, args: {...}}` payload:

- `POST /retell/fn/lookup_care_resident` resolves a room to an existing resident and returns a clear not-found result for unknown rooms.
- `POST /retell/fn/create_care_request` records the confirmed resident request in the care queue and preserves the original quote.

Maintenance intake can include `facility_category` and confirmed `access_ok`.
The server records the verified Retell call ID, which lets the dashboard show matching summaries and transcripts from the existing call log when available.

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
CARE_PYTHON="$PWD/.venv/bin/python" npm run test:workspace
npm run check
node --test tests/building.model.test.js
```

Backend tests cover lifecycle, clinical-role routing, concurrency, stale updates, persistence, submission retries, escalation, check-in follow-ups, facility-local due times, token protection, and signed voice functions.
Browser tests cover full care delivery, urgent escalation, check-ins, stale-data errors, network recovery, keyboard focus, mobile layout, and axe accessibility checks on daily care, urgent response, resident roster, and the request dialog.
Browser screenshots and traces are written to the ignored `test-results/` folder.
Combined-workflow tests additionally cover shared-system relationships, maintenance escalation, duplicate preservation, merge/unmerge/split, stale assignments, repair outcomes, room edits, access permission, old-demo compatibility, and unverified physical locations.
Browser tests exercise the complete facilities workflow, room filtering, J/K navigation, resident follow-up links, call context, and desktop/mobile accessibility.
The integrated workspace suite builds the current original dashboard and checks map drawing and pin placement, callback creation, shared building tools, language switching, wall view, shared token access, embedded care assignment, accessibility, and mobile layout.
It also checks apartment resident creation, optional check-ins, shared unit filtering, grouped maintenance requests, both required outcomes, keyboard navigation, profile and unit editing, care-link redirects, preserved drafts and desktop/mobile accessibility.
Mobile checks include submitting a check-in form inside the actual visible workspace height.

The existing backend suite was also verified in an isolated checkout with its original dashboard built.
Run each existing test file in a separate Python process because those modules set different environment variables before importing the shared backend.
Running all modules in one discovery process produces order-dependent baseline failures.
