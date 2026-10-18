# DIZA Care

DIZA's full operations dashboard, with resident care integrated into the Building tab.
Imaan's existing dashboard remains the base experience; the care-home extension adds urgent and everyday care without replacing the original tools.
This implementation follows the user's explicit preference for a staff dashboard only.
All new files live in this session folder, as required by the repository's `AGENTS.md`.

## Original functionality preserved

- **911 operations:** live geographic map, report pins and manual placement, linked incidents, urgent and non-urgent lanes, incident cards, second-reader flags, priority review, callbacks, responsibility handoffs, zone drawing, offline map, load metrics, call activity, responder team, and wall view.
- **Building:** original floor-by-stack map, unit editing, urgency reasons, duplicate grouping, related tickets, repair clocks, assignments, status, tenant updates, original quotes, transcripts, merge/unmerge/split, and timeline.
- **Supporter inbox:** offers, explicit acceptance, decline with backup routing, and completion.
- **Region and language:** the existing emergency-number configuration, English/Chinese/Spanish interface, and responder coverage, hours, languages, and backup details from PRs #34 and #35.
- **Resident care:** the additional daily/urgent care, resident check-ins, and shared care-home repairs described below.

The integrated root opens `/ops`.
Open **Building** for **Repairs & floor plan** and **Resident care** in the same workspace.
The repairs overview includes care counts and direct links to urgent care, everyday care, resident check-ins, and care-home repairs.
The Building sidebar badge shows the number of unresolved urgent care requests even while staff use other sections.
`/building?section=care` opens the resident-care section directly, and older `/care` links redirect there.
The sidebar has the original three sections: Building, 911 operations, and Supporter inbox.
The apartment-building demo, crisis-map demo, and care-home demo remain distinct datasets.
Care-home room repair reports continue to share their resident requests and facilities tickets as described below.

`workspace/entry.jsx` imports the current original dashboard source directly.
The Vite integration extends the Building component with resident care without copying the operational components or editing another session's files.
Every integration anchor is checked, and a changed upstream shell fails the build instead of silently dropping functionality.
The map adapter keeps Leaflet's container classes intact when entering drawing or placement mode.
The care panel uses a same-origin frame to preserve its forms, dialogs, keyboard handling, and style isolation.
It reuses the operator token already entered in the parent dashboard.
Switching between the two Building sections preserves care dialogs, unsaved drafts, the current care section, and the selected repair ticket.

## What staff can do

- Record meals, water, personal care, medication questions, companionship, maintenance, and wellbeing requests against a resident and room.
- Review daily care and urgent response in separate queues, with an urgent banner visible from every view.
- Accept responsibility, start care, add handoff notes, escalate concerns, and resolve requests with a required outcome.
- Review resident language and interaction preferences before responding.
- Record daily wellbeing observations, with overdue checks flagged after 10 am in the facility timezone.
- Turn a check-in concern or no response into a follow-up request automatically.
- Search by resident, room, request description, or reference code and filter open requests by status.
- Review completed care and its handoff history.
- Use **Rooms & repairs** to see care needs and physical incidents on the same room map.
- Group duplicate room reports into one facilities ticket and review related issues by floor, riser, or HVAC zone.
- Assign facilities staff or a demo vendor, coordinate access, record repair outcomes, and reopen an incomplete repair.
- Merge, unmerge, or separate reports while preserving original quotes, linked resident requests, and available call transcripts.
- Review first staff action time, duplicate grouping, shared-problem hints, and maintenance review targets.

## How the two workflows connect

A room or maintenance request creates both an individual care request and a linked facilities ticket in the same SQLite transaction.
The care request tracks responsibility for the resident; the facilities ticket tracks the physical repair.
Multiple reports of the same room and issue within two hours share a repair ticket, and each resident report stays independently visible.
Issues in different rooms can be related by the same riser, floor, or HVAC zone using Imaan's existing building rules.

Nurses and care leads accept urgent resident needs.
Facilities staff and care leads coordinate contractors and repair progress.
Closing a repair does not resolve the linked resident requests.
Staff must still follow the care acceptance, progress, and outcome workflow for each resident.
Shared-area locations that are not verified rooms remain separate until staff confirm whether they are the same problem.

Every merged report's original quote and available call context remain visible on the parent incident.
Unmerging or separating a report never silently lowers its urgency.
Entry refusals and unknown permissions are preserved conservatively, and shared repairs require checking each resident's access permission.
Assignments and resident-update controls record staff actions; they do not contact anyone automatically.

The maintenance targets are demo review thresholds inherited from the building engine.
They are not clinical response guarantees.
California tenancy-law clocks from the building dashboard are not presented as care-home policy.

The original building dashboard remains available at `/building` in the integrated container.
Resident care is available at `/building?section=care`; its room map represents the resident roster rather than the separate apartment-building sample.

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
In Building, select **Resident care**, then **Load demo scenarios** to populate the care-home addition.
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
```

Backend tests cover lifecycle, clinical-role routing, concurrency, stale updates, persistence, submission retries, escalation, check-in follow-ups, facility-local due times, token protection, and signed voice functions.
Browser tests cover full care delivery, urgent escalation, check-ins, stale-data errors, network recovery, keyboard focus, mobile layout, and axe accessibility checks on daily care, urgent response, resident roster, and the request dialog.
Browser screenshots and traces are written to the ignored `test-results/` folder.
Combined-workflow tests additionally cover shared-system relationships, maintenance escalation, duplicate preservation, merge/unmerge/split, stale assignments, repair outcomes, room edits, access permission, old-demo compatibility, and unverified physical locations.
Browser tests exercise the complete facilities workflow, room filtering, J/K navigation, resident follow-up links, call context, and desktop/mobile accessibility.
The integrated workspace suite builds the current original dashboard and checks map drawing and pin placement, callback creation, original building notes and assignments, supporter navigation, language switching, wall view, shared token access, embedded care assignment, accessibility, and mobile layout.
It also checks the unified Building tabs, care shortcuts, old care-link redirects, keyboard tab navigation, and unsaved handoff drafts when switching back to the floor plan.

The existing backend suite was also verified in an isolated checkout with its original dashboard built.
Run each existing test file in a separate Python process because those modules set different environment variables before importing the shared backend.
Running all modules in one discovery process produces order-dependent baseline failures.
