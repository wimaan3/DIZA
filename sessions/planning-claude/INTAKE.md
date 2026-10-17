# Intake, forms and the "simulated world"

**Question:** if someone says "I want an appointment with my doctor", do we really fill out the doctor's forms?

**Answer:**
- **Yes, we do real structured intake.** The agent asks clarifying questions until a form is complete, then attaches it to the caller's case and to whoever it's routed to.
- **No, we don't submit into real third-party systems this weekend.** That would mean impersonating callers, health privacy (HIPAA) exposure, and no permission.
- **Third parties live in a sandbox "service world" that we control.** Our own supporters are real (real Google Calendar, real phones).

## 1. Forms engine (generic slot-filling)

Each request type is a schema in `forms/*.yaml`:
```yaml
id: medical_appointment
label: Doctor appointment request
route_skill: medical_admin
fields:
  - {name: patient_name, required: true}
  - {name: date_of_birth, required: true, validate: date}
  - {name: provider, required: true, ask: "Which clinic or doctor?"}
  - {name: reason, required: true, ask: "In a few words, what's the visit for?", sensitive: true}
  - {name: preferred_times, required: true}
  - {name: insurance, required: false}
  - {name: needs_interpreter, required: false, default: "{{language}} != en"}
  - {name: transport_needed, required: false}
safety_check: "If symptoms sound urgent (chest pain, trouble breathing, stroke signs) → stop and give 911."
```

**Two functions run the loop. This keeps the agent prompt small and the same for every form:**
1. `start_form(type)` → returns the first missing fields and how to ask for them
2. `fill_form(case_id, fields)` → validates, returns `missing[]`, `invalid[]` or `complete`
3. The agent keeps asking clarifying questions until `complete`, **reads it back**, gets a "yes", then calls `submit_form` → confirmation code.

**Other forms:**
- `maintenance_request`
- `escort_request`
- `evacuation_assistance` (mobility, oxygen, pets, people count)
- `checkin_enrollment` (pending consent)
- `lost_item`
- `shelter_need`
- `benefits_help` (e.g. disaster-aid paperwork prep)

DS and biomech write the schemas. Biomech owns the medical and evacuation ones.

## 2. Case file → the routed profile

Every call creates or updates a **case**: caller profile, history, filled forms, triage label, transcript summary, status.
- On transfer, the human gets the **whisper brief** *and* the case on screen in the supporter app, so they never re-ask.
- The caller can `check_status` by confirmation code. Status changes trigger a callback or email.
- Data minimization:
  - Only the fields the form needs.
  - Fields marked `sensitive` are hidden in analytics and deleted after the event.

## 3. Where a completed form goes

| Destination | This weekend | Production path (say this in the pitch) |
|---|---|---|
| Our supporters (escort, housing, peer listener, tutoring) | **Real:** request queue + **Google Calendar** booking | Same |
| Doctor's office / clinic | **Sandbox clinic** ("Altadena Family Clinic") with its own inbox in our app. A teammate plays the receptionist and accepts or proposes a time; status flows back to the caller. | FHIR scheduling APIs (Epic/Cerner) or the clinic's online booking, under a BAA |
| City services (pothole, streetlight, debris) | **Sandbox 311** inbox | **Open311 GeoReport v2**, a real open standard many cities use for 311 requests, or the city's CRM |
| Utility / power outage | Sandbox utility inbox | Utility outage APIs / partner integration |
| Shelters | Read-only lookup (live function) | County / Red Cross feeds |

**Stretch "wow":** the agent **phones the sandbox clinic**. That's a second Retell agent playing receptionist, or a teammate. It books the slot on the caller's behalf, then calls the caller back with the time. A good demo of "it actually does things".

## 4. Why a sandbox is the right call
- Judges can watch the whole loop end to end (request → form → provider accepts → caller notified) without us touching a real clinic.
- No impersonation, no PHI sent to systems we don't control (rule 7, responsible use).
- The adapter interface (`submit(form) → status updates`) is the same for sandbox and real integrations. That's the feasibility story: swapping in Open311 or FHIR is one adapter.
