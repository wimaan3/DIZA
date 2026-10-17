# Form schemas (DRAFT, owned by biomech)

CS#1 drafted these so the backend and agent can be built and tested. **Biomech owns the content** (medical/evacuation fields especially). Edit freely via PR.

How they're used (INTAKE.md, 00_CONTRACTS.md):
- `start_form {form_type, known_fields}` → backend creates a case, pre-fills `known_fields`, returns `{case_code, next_fields:[{name, ask}]}` (only fields still missing, in order).
- `fill_form {case_code, fields}` → validate → `{missing, invalid, complete, readback}`.
- `submit_form {case_code, confirmed:true}` → `{code, pool, status, next_step_text}`.

Schema keys: `id`, `label`, `route_pool` (00_CONTRACTS `pool` enum), `route_skill` (skills enum), `fields[]` (`name`, `required`, `ask`, optional `validate`: date|time|phone|int|enum, `choices`, `sensitive`), `readback` (template with `{field}` placeholders), `safety_check`, `next_step_text`.
`sensitive: true` fields are hidden from analytics and deleted after the event. Never add student ID, SSN or payment fields.
