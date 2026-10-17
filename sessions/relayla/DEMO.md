# DIZA: five-minute demonstration

**Decision to demonstrate:** Which caller needs a person first, and what remains unresolved after contact or a handoff fails?

**Everyday customer:** a community service or campus team handling check-ins, pickup changes, and assistance requests. **Disruption:** the same team handles urgent reports and revised pickup instructions during a simulated service disruption.

Use synthetic data throughout. The “simulation” labels should remain visible. The local dashboard and state transitions are functional; local controls do not place calls, send SMS, transfer a telephone call, or notify an agency. A live Retell browser conversation is an optional, separately configured input to the same records. Startup instructions are in [README.md](README.md), and the operation definitions are in [API_CONTRACT.md](API_CONTRACT.md).

## Where this segment fits the team's larger demo

The newer [Ops Wall](../planning-claude/OPS_WALL.md) and [team demo plan](../planning-claude/DEMO.md) propose audience calling, map clusters, live transcripts, telephone transfers, outbound follow-up, and a quality scoreboard. Use this five-minute run as a complete demonstration of the implemented follow-through module, or use its **failed human handoff → revised instruction → accepted assistance** sequence as a shorter segment inside that larger demo once the other components work.

The response desk already supplies an urgent queue, responder matching, separate communication and assistance states, and an audit feed. The live map, automatic cluster/zone detection, concurrency measurements, transcript ticker, SMS ladder, audience-call flood, and timestamp replay player remain teammate implementation scope. Counts on this dashboard are case/workflow counts, not proof of simultaneous telephone capacity. The browser-call connection does not expose a live transcript feed or a privileged Retell key.

The [intake sandbox plan](../planning-claude/INTAKE.md) also fits this segment: a teammate can play the receiving service operator and accept a saved request. Describe that as **request recorded and accepted in our sandbox**. This module does not implement the generic form engine, clinic appointments, Google Calendar bookings, dedicated 311 inbox, or caller-notification delivery. A mobility pickup request is the supported demonstration; switching the role card to a doctor's appointment does not create the missing appointment integration.

For the [evaluation plan](../planning-claude/EVALS.md), contribute actual workflow test results and real observed failures. Keep speech/language quality, urgent-case recall, and the proposed v1-to-v3 live-drill metrics separate until those tests have been run. Do not copy target values or sample pitch statistics into a results slide.

## Before the timer starts

- Start the local service and open the dashboard. Rehearse against a fresh demo database, not a teammate's used or live database.
- Check `/health` and the dashboard's integration indicators. If Retell is unconfigured, introduce the demonstration as **local workflow simulation** and use text intake. Do not imply a voice call occurred.
- If using live Retell, test the entire browser-agent-to-signed-function-to-database path beforehand. Have the local workflow ready if that specific integration fails.
- Use a screen wide enough to show the queue, the selected case, and the separate communication and assistance states.
- Confirm that the seed cases below are present. Names and situations are fictional.

| Case | Starting purpose |
|---|---|
| `case-002` | P0 case requiring professional human review, placed ahead of less urgent cases. |
| `case-001` | Spanish-speaking person requesting mobility assistance for the community pickup; no confirmation yet. |
| `case-004` | Earlier notice confirmed; volunteer assignment awaiting separate human acceptance. |
| `case-007` | Earlier notice confirmed and a professional has accepted assistance; help remains incomplete. |
| `case-006` | Interrupted contact with a pending retry, useful as a backup scenario. |

Initial notice: `notice-pickup`, version 1, `north_entrance`. The revised instruction uses `east_entrance`. Source and approval labels refer to the fictional demo coordinator.

## Five-minute run of show

| Time | Operator action | What to say and show |
|---|---|---|
| **0:00–0:40** | Open the priority queue and select `case-002`. Show its supplied P0 classification, professional responder recommendation, and unresolved human-review state. | “DIZA gives the overnight supervisor a queue of people who still need attention. This priority came from our drill fixture; the module preserves it and prevents a volunteer assignment or a timed callback from burying it.” |
| **0:40–1:35** | Select `case-001`. Use the Spanish approved notice and record the correct v1 read-back plus the mobility assistance request. For a live configured Retell call, speak the script below; otherwise use the local controls. | Show **latest instruction confirmed** alongside **assistance requested**. “Knowing the pickup entrance and being able to reach it are separate questions. The confirmed answer does not close the request.” |
| **1:35–2:20** | Select `case-004`. Show the assignment awaiting acceptance. Record the assigned responder's simulated non-response with `handoff_failed`, then show the reopened request and next recommendation. | “Asking a responder is not the same as a responder accepting. Nobody answered this proposed handoff, so the need stays open. This is a recorded failure scenario, not a live telephone transfer.” Resident contact failures must not increase. |
| **2:20–3:00** | Return to `case-001`, simulate a dropped resident contact, then resume. Show the same case ID and previously saved information. | “The call is interrupted after we saved the answer. Reconnecting preserves the record; it does not require the resident to repeat everything.” With local controls, call this a simulated interruption. |
| **3:00–4:00** | Revise `notice-pickup` to version 2, east entrance, through the operator-only notice editor. Show `case-001` and `case-007` now requiring an updated confirmation. Record the correct v2 read-back for `case-001`. | “The plan changed. DIZA knows exactly who confirmed the earlier instruction. Existing assistance assignments survive the change, while communication follow-up reopens.” |
| **4:00–4:35** | Assign `case-001` to the available bilingual professional if needed. Have the responder role explicitly accept. Show the assistance state as accepted while communication stays confirmed. | “A person now owns this request. The AI did not accept its own handoff.” Optionally complete it with a clearly fictional operator note; do not imply real assistance occurred. |
| **4:35–5:00** | Show the audit history, remaining urgent cases, and pending callbacks. Return to the ordinary-day customer. | “The same workflow handles routine check-ins and a disruption. This prototype demonstrates durable records, human acceptance, and updated instructions. The pending callback is work to do; telephony and SMS are not connected in this local demo.” |

If time is tight, omit simulated completion. A visible **accepted but unfinished** request is a useful result because it shows that the workflow does not manufacture closure.

## Spanish scenario

The following text is a fictional role card. Adjust it only to match the currently approved demo notice. It is not a medical or emergency instruction.

**Resident request:**

> Hablo español. Necesito ayuda para llegar al punto de recogida porque uso un andador.

English meaning: “I speak Spanish. I need help getting to the pickup point because I use a walker.”

**Version 1 notice:**

> El punto de recogida está en la entrada norte. ¿A qué entrada va a ir?

**Resident read-back:**

> A la entrada norte. Entiendo el cambio, pero todavía necesito ayuda para llegar.

**After the operator publishes version 2:**

> El punto de recogida ha cambiado a la entrada este. ¿A qué entrada va a ir ahora?

**Resident read-back:**

> Ahora voy a la entrada este. Todavía necesito ayuda.

An incorrect answer should produce **needs clarification**, not confirmation. Keep both the spoken response and the structured action key available in the record. Do not describe this single role-play as proof of broad multilingual accuracy.

## What each failure proves

| Scenario | Expected evidence | Claim that the evidence supports |
|---|---|---|
| Human responder does not accept | `handoff_failed` event; proposed owner released; assistance remains requested; a new recommendation can be made. | The work is not silently closed when a proposed handoff fails. |
| Resident call is interrupted | Contact changes to dropped; saved acknowledgment and help details remain; resume uses the same case. | Previously persisted progress survives that interruption. |
| An instruction changes | New notice version; old acknowledgment retained; current confirmation becomes pending until a correct v2 response. | The system distinguishes old and current instructions. |
| A write is retried | Submit the same action twice with one unchanged `event_id`; receive its stored result with no second state transition. | A delivery retry does not duplicate the recorded operation. |
| Same event ID is reused with different content | HTTP 409 and unchanged state. | Conflicting reuse is detected rather than silently accepted. |
| Local form loses connectivity | An explicitly **unsent** draft remains on that browser; after reconnection, explicit sync creates one report with the retained event ID. | The device can preserve that draft for later submission; it does not prove delivery during an outage. |

Use the resident `contact` action only for resident contact outcomes. Use `handoff_failed` for an assigned responder's failure to answer. A scheduled callback stage is not evidence that the callback happened.

## API checks for the operator rehearsal

Every operator mutation is a `POST /api/actions/{action}` with an `event_id` and `payload`. Use a fresh event ID for a new intended action; retain it only for a retry of the same action. Supply `X-Operator-Token` when configured. Full schemas are in the contract.

For the core acknowledgment, the payload should include:

```json
{
  "event_id": "rehearsal-case-001-v1-confirmation",
  "payload": {
    "case_id": "case-001",
    "notice_version": 1,
    "action_key": "north_entrance",
    "readback_text": "A la entrada norte. Todavía necesito ayuda.",
    "needs_assistance": true,
    "assistance_details": "Uses a walker and requests help reaching the pickup entrance."
  }
}
```

Post this to `/api/actions/acknowledge`. Reposting the exact request demonstrates the idempotent result. After the notice has been revised, this old request must not confirm the new version. The operator revision must carry the current `expected_version`; two competing revisions must not silently overwrite one another.

Other rehearsal actions are `contact`, `handoff_failed`, `assign`, `accept`, `callback`, `revise_notice`, and `resolve`. Do not use `resolve` as a substitute for acceptance or to hide an urgent case. Rehearse blocked paths too: P0 to a volunteer, P0 timed callback, and completion of a request that lacks an accepted owner.

## Measure only what was actually exercised

Record the local request-to-dashboard delay, whether the record survives restart and reconnection, the number of duplicate transitions after a retry, and the elapsed time until explicit operator acceptance. Save actual observations with the test conditions. Do not insert guessed response-time or triage-accuracy numbers into the deck.

If a live voice run succeeds, label that segment as live and record which configured language and agent were used. Keep synthetic surge reports, local failure controls, and live provider events visibly distinguishable. A local queue demo does not establish telephone capacity, emergency effectiveness, or all-network-outage operation.

For a twist submission, capture the requirement that changed, the code behavior that changed, the relevant commit, and a short before-and-after demonstration. Explain a revised instruction and a dropped contact as rehearsed failure scenarios unless the organizers actually issue those twists. See the track and submission details in the [official participant material](../../sources/participant-hub-gdoc.txt).
