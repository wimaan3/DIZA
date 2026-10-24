# DIZA: emergency call overflow and hotel service

**Status:** Proposed product direction for review, based on Deepanshu's clarification on October 17, 2026.
This document describes intended behavior; it does not change or deploy the application.
The subsequent local hotel text prototype is described in [HOTEL_DEMO.md](HOTEL_DEMO.md) on the hotel demo branch.

## Product definition

DIZA is a multilingual call-handling platform with two operating modes.
During an emergency call surge, it gathers information while callers await human operators and supports prioritizing the most urgent waiting calls.
For hotels, it handles routine guest conversations directly and creates staff tasks when an issue requires physical assistance.

| | Emergency overflow mode | Hotel service mode |
|---|---|---|
| Customer | A participating emergency communications center | A hotel and its front desk, housekeeping, and maintenance teams |
| When AI answers | When human operators cannot take additional calls | For routine guest service calls |
| AI responsibility | Collect details, summarize, link related reports, and support routing | Answer approved questions, guide routine troubleshooting, and record requests |
| Human responsibility | Take over the emergency call and decide the response | Handle repairs, exceptions, safety issues, and requests needing staff |
| Completion | Confirmed human handoff | A resolved question or a tracked service task with an explicit outcome |

## Emergency overflow workflow

1. When an operator is available, route the caller directly to that operator.
2. When operators are unavailable, the agent gathers essential details while the caller waits: incident location, callback information, what is happening, and reported urgency.
3. Save progress during the conversation so the operator can see the caller's information before taking over.
4. Group reports that may concern the same incident, retaining each caller's own record, details, and queue status.
5. Present waiting calls with priority reasons, waiting time, intake details, and a transcript or summary.
6. As an operator becomes available, offer the highest-priority waiting call under the center's approved rules.
7. Transfer the caller with the saved context and record whether a human actually accepted the handoff.

The agent's emergency role is intake and routing support.
Emergency response and dispatch decisions stay with trained human operators.
An operator becoming available should interrupt AI intake rather than require the caller to finish a questionnaire.

### Prioritization and aggregation

- Use rules approved by the participating emergency center, with visible reasons and human override.
- Keep unclear or incomplete reports flagged for human review rather than assuming low urgency.
- Keep waiting time visible and define escalation and tie-breaking behavior with the center.
- Preserve every emergency caller for human follow-up, including callers reporting an already-known incident.
- Treat incident grouping as a link between records; it must not erase a caller or discard new information.
- Retain the waiting record if a transfer fails, and distinguish an attempted transfer from an accepted handoff.
- Do not claim that emergency services have been dispatched based only on AI intake or queue placement.

The authoritative operator-capacity signal, prioritization policy, and disconnected-call procedure remain integration decisions for the participating center.
The prototype should simulate those conditions and use consenting teammates as operators.
Actual emergency-line traffic requires integration with that center's call-handling infrastructure.
The National 911 Program describes NG911's role in managing call overload and transfers in its [NG911 overview](https://www.911.gov/issues/ng911/).

## Hotel service workflow

1. A guest calls with a room issue or routine request, such as Wi-Fi access, towels, an AC problem, or a maintenance concern.
2. The agent gathers the room, issue, and any missing information needed to handle the request.
3. For supported questions and routine troubleshooting, provide the hotel's approved answer or instructions directly.
4. If staff action is needed, confirm the request and create a task for the appropriate hotel team.
5. Give the guest an accurate acknowledgment or task status, then preserve the conversation and follow-up record.
6. Escalate requests needing a person, unresolved problems, and potential emergencies to the appropriate human workflow.

Handling the call does not mean that the agent has physically fixed the room issue.
A maintenance ticket being created is different from a repair being completed.
Staff ownership and completion must be recorded explicitly, and the agent must not invent repair times or staff commitments.
Potential emergencies follow the hotel's emergency procedure rather than the routine service-resolution path.

## Shared platform and separate operating policies

Both modes reuse multilingual conversation, persistent records, live dashboard updates, request deduplication, and human handoff support.
Each mode needs its own instructions, allowed actions, routing destinations, and definition of completion.
The deployment or entry point determines the mode; caller-provided text must not switch operating policies.
Emergency records and hotel guest records remain separated by customer and access permissions.

## Current implementation gaps

The existing repository contains related planning in [REFOCUS.md](../cs1-retell/REFOCUS.md) and [BUILD_PROMPT.md](../cs1-retell/BUILD_PROMPT.md).
Those documents are context for the implementation; this clarification specifies the intended distinction between emergency overflow and hotel automation.

The current [shared agent rules](../../agents/prompts/_shared_rules.md) tell an urgent caller to hang up and dial the emergency number.
The backend's [urgent-call handler](../cs2-backend/mvp/backend/app/retell_fns.py) returns similar guidance.
Those instructions require mode-specific treatment before demonstrating an agent inside an existing emergency-call overflow workflow.
A caller already awaiting a 911 operator must remain in that workflow rather than be told to restart the same call.

Further implementation must establish an operator-capacity-aware queue, visible priority reasons, preserved individual calls within incident groups, and confirmed handoff outcomes.
Hotel mode needs approved service content and staff task handling before it can claim to resolve or fulfill particular requests.
Documentation-only PR #21 introduced these requirements without changing prompts, routing, provider agents, or production settings.
The hotel demo is a subsequent implementation using synthetic data and a separate local database; real hotel-system and emergency-line integration remain open.

## Demonstration and acceptance examples

| Scenario | Expected behavior |
|---|---|
| An emergency operator is free | The caller reaches the operator without unnecessary AI intake |
| Multiple emergency callers arrive while operators are busy | The agent gathers information concurrently and the console shows the waiting calls |
| Several callers report one incident | The reports are linked, with each caller and any additional details preserved |
| An urgent report arrives during overflow | Its reported urgency and priority reasons become visible for operator review and routing |
| A caller's situation is unclear | The uncertainty remains flagged and the caller remains in the human follow-up workflow |
| An operator becomes free during intake | The selected waiting caller transfers with saved context |
| A handoff fails | The call is still tracked as awaiting human assistance |
| A hotel guest asks a supported Wi-Fi question | The agent provides the approved instructions directly |
| A guest reports broken AC | The agent records a maintenance task and accurately states its status |
| A hotel caller reports a potential emergency | The call leaves the routine service path for the hotel's emergency procedure and human escalation |

Use synthetic callers and incident data for the emergency demonstration, with no calls or transfers to real emergency numbers.
Show operator availability changing, a priority-based handoff, and a separate hotel call that the agent can handle directly.
Measure observed waiting time, intake saved before handoff, successful handoffs, and actual hotel task outcomes without claiming unmeasured improvements.

## Open decisions

- Which emergency center and call-handling integration would supply a real overflow stream and operator availability?
- Which center-approved priority rules, waiting-time escalation, and disconnected-call procedures should be implemented?
- Which hotel service questions and troubleshooting steps are approved for direct agent handling?
- Which hotel staff systems, assignment rules, and emergency procedures should the service workflow use?

The source for the two-use-case product decision is Deepanshu's clarification in this conversation on October 17, 2026.
The NG911 link supplies infrastructure context, not an endorsement or certification of this proposed application.
