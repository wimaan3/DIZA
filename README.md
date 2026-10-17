# DIZA

InnovateLA × Dual-Use Hackathon (USC, Oct 16–18 2026). **Resilience Comms track (Retell AI).**

A multilingual Retell voice line with two lives:
- **Ordinary day:** a campus and community concerns line, plus wellness check-ins.
- **Crisis night:** surge triage, corroboration, skills-based handoff to humans, and callback ladders.


> ## 👉 START HERE
> Everything is on **`main`**. Work on your own branch and open a PR to `main` (see AGENTS.md rule 5).

### Your work package (give it to your AI agent)
| Who | Open this |
|---|---|
| **Everyone, read first** | [00_CONTRACTS.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/handoff/00_CONTRACTS.md): tables, endpoints, branches, milestones |
| **CS#1, Retell agents** | [01_CS1_RETELL_AGENT.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/handoff/01_CS1_RETELL_AGENT.md) |
| **CS#2, backend + dashboards** | [02_CS2_BACKEND_DASHBOARDS.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/handoff/02_CS2_BACKEND_DASHBOARDS.md) |
| **Data science, triage + data + evals** | [03_DS_TRIAGE_DATA_EVALS.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/handoff/03_DS_TRIAGE_DATA_EVALS.md) |
| **Biomech, domain + ops + pitch** | [04_BIO_DOMAIN_OPS_STORY.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/handoff/04_BIO_DOMAIN_OPS_STORY.md) |

### Reference docs (all in `sessions/planning-claude/`)
| Topic | Doc |
|---|---|
| Overview of every decision | [SESSION_CONTEXT.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/SESSION_CONTEXT.md) |
| Hackathon requirements → where handled | [REQUIREMENTS_TRACE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/REQUIREMENTS_TRACE.md) |
| Master plan | [PLAN.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/PLAN.md) |
| System spec (agent scope, pools, KB, dashboards, privacy) | [SYSTEM_SPEC.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/SYSTEM_SPEC.md) |
| Retell: MCP, APIs, KB, capacity | [RETELL_GUIDE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/RETELL_GUIDE.md) · [SETUP.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/SETUP.md) |
| Triage + routing | [TRIAGE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/TRIAGE.md) |
| Forms + sandbox world | [INTAKE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/INTAKE.md) |
| Laws + rules | [COMPLIANCE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/COMPLIANCE.md) |
| Reach (who alerts miss) | [REACH.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/REACH.md) |
| Flows + team process | [WORKFLOW.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/WORKFLOW.md) · [BUILD_PLAN.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/BUILD_PLAN.md) |
| Evals | [EVALS.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/EVALS.md) |
| Live dashboard + audience demo | [OPS_WALL.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/OPS_WALL.md) · [DEMO.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/DEMO.md) |
| Deck, numbers, lines to say | [DECK.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/DECK.md) |
| Call schedule + floods | [CALL_SCHEDULE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/CALL_SCHEDULE.md) |
| Twist response template | [TWISTS_TEMPLATE.md](https://github.com/wimaan3/DIZA/blob/main/sessions/planning-claude/TWISTS_TEMPLATE.md) |
| Official hackathon material | [sources/](https://github.com/wimaan3/DIZA/tree/main/sources) |

## Branches
- `main`: the shared trunk: app code + docs, **PRs only**
- one short-lived branch per person/agent/feature → PR to `main`
- other branches: `claude/relaxed-goodall-tmz8gz` (planning session), `codex/relayla-diza-integration` (another agent's RelayLA notes; should rebase on `main` and open a PR)

## Repo map
- `AGENTS.md`: rules for the AI agent sessions pushing here (read first)
- `sources/`: official hackathon material and summaries
- `sessions/<name>/`: each session's docs + `SESSION_CONTEXT.md`
  - `sessions/planning-claude/`: full plan, specs, and `handoff/` work packages
- `docs/`: synthesized plan (to come)

## Deadlines
- Teams lock: Fri 9 PM
- **Devpost: Sat 10 PM** (no extensions)
- Finalist deck: Sun 9 AM
- Devpost links lock: Sun 11 AM
