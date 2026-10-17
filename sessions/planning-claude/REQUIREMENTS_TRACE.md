# Requirements traceability: every requirement → where we handle it

Source: the requirements the user pasted from the Participant Hub, Problem Statement and announcements (also in `sources/`).
Status: ✅ covered · ⚠️ partly / needs a decision · ❌ gap (action listed).

## A. The Comms prompt (Retell: "On the Line")
| Requirement | Our answer | Where | Status |
|---|---|---|---|
| Seat: overnight supervisor of a call line | The supervisor dashboard / Ops Wall is *their* screen; Declare and Approve are *their* decisions | PLAN §5, OPS_WALL | ✅ |
| Surge of calls and alerts no one can verify | Corroboration: cluster reports, count distinct callers, ask neighbours, human approves | TRIAGE L3, PLAN §5 | ✅ |
| Too few people to answer | AI answers in parallel; humans only get the top slice; callbacks instead of hold; burst + fallback number | PLAN flood §, RETELL_GUIDE §9 | ✅ |
| Residents = earliest sensor *and* biggest flood | Reports become signals (crisis detection); duplicates collapsed with "we already know" | TRIAGE | ✅ |
| Blunt move = alert everyone / send all to an absent human | Per-zone ladder; AI resolves routine calls; no public alerts without a human | PLAN mode-switch § | ✅ |
| **How do you tell who needs a person right now?** | P0–P3 lexicon + LLM context + vulnerability boosters + acoustic flags (escalate only) → priority queue → skills routing | TRIAGE, PLAN routing § | ✅ |
| **What must never be automated?** | Public alerts, declaring/ending a crisis, P0 handling by volunteers, dismissing a caller, claiming dispatch, claiming to be human | PLAN §7, COMPLIANCE | ✅ |
| **What happens when someone doesn't pick up?** | Resident: call → SMS → retry → contact/neighbour → red flag. Responder: next match → any human → callback. Supervisor: 5-min dead-man's switch → high-risk welfare calls only | PLAN, WORKFLOW | ✅ |

## B. The shared problem statement
| Requirement | Our answer | Status |
|---|---|---|
| Automation that misbehaves: "where it shouldn't be / doing what nobody authorized / gone quiet when it should be talking" | (1) **Automated alerts that misfire**: Jan 2025 false alert, so we corroborate before broadcast. (2) **Gone quiet**: residents not answering → ladder; silence on a call = a risk signal. (3) **Our own AI misbehaving**: heartbeat + fallback number + safety evals as hard gates | ⚠️ **Say this framing explicitly in the pitch and on Devpost** (added to DEMO beat 1) |
| **Pre-emptive, not reactionary** ("help someone prepare for disaster") | Everyday check-ins build a live registry *before* the fire; residents save the number; needs, language and contacts known in advance; welfare list ready | ⚠️ Make "prepare" the headline: *"We build the list on Tuesday so Friday night is a phone call, not a search."* |
| Gentlest response that still works; cheap; safe around people; useful on an ordinary day | Watch/ask rungs automatic, public actions human; ~$0.10/min; voice works on any phone | ✅ |
| **Your build lives on one or two rungs** (watch, ask, slow, hold, hand to a person) | **Primary rungs: ASK + HAND TO A PERSON.** Watch is the sensing that feeds them; slow/hold we don't do | ⚠️ **Scope discipline:** the pitch names exactly these two rungs. Everything else is "supporting features", not new rungs |
| Four choices: **person** | Overnight supervisor of a community call line | ✅ |
| **Moment** ("Harbor Night in the Extended Card, or your own") | Ours: 2 AM fire night (Altadena-style). **We don't have the Extended Card.** | ❌ **Action:** get the Extended Card from the portal or help desk tonight. Keep zones and geography as **config**, so if twists build on Harbor Night we can switch to San Pedro / Wilmington (port-adjacent neighbourhoods, e.g. a shelter-in-place) in minutes |
| **Second customer on an ordinary Tuesday** (+ hint: name it and the day) | Currently three candidates: senior-services / home-care agency, council office, USC | ⚠️ **Decision needed: pick ONE headline.** Recommendation below |
| Twists encouraged (3) | Twist protocol, pre-built switches, TWISTS.md | ✅ (template now in `TWISTS_TEMPLATE.md`) |

**Recommendation for the second customer:**
- **Headline:** *"A council district's senior-services line, every Tuesday at 10 AM: multilingual wellness check-ins and constituent requests."* It drives the registry that the reach story depends on, and two judges are councilmembers.
- **Proof site:** *"Piloted live this weekend as the USC campus concerns line: N real calls."*
- Mention the home-care agency only as a "next customer".

## C. Judging (5 criteria, 1–5; tie → dual-use)
| Criterion | Where | Status |
|---|---|---|
| Dual-use fit (everyday LA problem, still works when things break) | One agent, two lives; Tuesday → Friday-night line; national-resilience slide | ✅ |
| Technical execution (is it real, does it work) | Real number, live floods, real actions, evals | ✅ (depends on building P0 by Sat 2 PM) |
| Feasibility & impact (could it ship, who is better off) | Off-the-shelf stack, ~$0.10/min, Open311/FHIR adapters, REACH metrics | ✅ |
| Adapting to twists (+ Best Shift Adapter: what changed, why, proof; change the build) | Protocol + TWISTS.md with commit links and clips | ✅ |
| Demo & pitch (5 min: 0:30 problem · working thing first · twist · next/feasibility) | DEMO.md beat sheet | ✅ |
| Judges who mentored us carry less weight | Book non-judge mentors (Nemani, Frazzini, McEwen, Kumar) | ✅ |
| **"Is every lens on stage? Yes, the strongest team in each lens."** | **We only need to be the best Comms project in Round 1 to make the finals.** Round 1 is judged **only from Devpost** (deck, video, repo, write-up) | ⚠️ **Make the Devpost write-up + video the #1 deliverable by 9 PM Sat**, not an afterthought |

## D. Retell track prize
| Criterion | Where | Status |
|---|---|---|
| Picked Resilience Comms **at submission** | Devpost lens field | ✅ (checklist) |
| Working voice, text or messaging flow (Retell encouraged) | 3 Retell agents + agent swap; SMS via Twilio trial | ✅ |
| **Works when networks are weak** | Voice over the phone network (no data/app); keypad-only path; short-call mode; SMS reports; overflow fallback | ⚠️ **Demo it:** one call from a flip phone or landline using keypad only ("press 1 if someone is hurt") + a "network degraded" twist switch |
| Works when people speak different languages | Per-language agents, 10+ languages, live non-English call in the demo | ✅ |
| Who it reaches that today's alerts miss | REACH.md + reach metrics | ✅ |
| Useful every day and still works in a crisis | The Tuesday line | ✅ |

## E. Submission and rules
| Requirement | Status |
|---|---|
| Devpost: name + lens + one line · deck · demo video · repo · all teammates · responsible-use note (2 lines) | ✅ checklist (PLAN §0). **Draft the one-liner now:** *"DIZA: the everyday community call line that becomes a 3 AM crisis line, triaging every caller, in their language, to the right human first."* |
| List all tools, including AI tools (rule 4): Retell, Twilio, Supabase, Claude Code, IBM Bob, models used | ⚠️ Keep a running `TOOLS.md` |
| Build after the reveal (rule 3) | ✅ (planning only so far) |
| One submission by Sat 10 PM, no extensions | ✅ target 9 PM |
| Team 2–4, locked Fri 9 PM | ✅ (confirm done) |
| One USC student for the incubator | ⚠️ confirm |
| In person; be there Sunday at noon | ✅ |
| Photos and video (Annenberg); opt out at check-in | n/a |
| Finalists: deck due Sun 9 AM; confirm demo in the app by 9 AM; Devpost links lock 11 AM | ✅ |
| "Deck Rules (Round 1 and 2)" is blank in the hub | ❌ ask the help desk |
| Where twist responses are submitted | ❌ ask the help desk / check the portal |

## F. Extra prizes
| Prize | Status |
|---|---|
| Best Build with IBM Bob: build with Bob, say how on Devpost; scored on how central Bob was + clean, running code | ⚠️ Decide: worth it only if Bob writes a real chunk (e.g. the backend + tests). Otherwise mention it but don't chase |
| Best Shift Adapter | ✅ |
| Best Live Demo / People's Choice (non-finalists) | ✅ audience calls, QR, Instagram |
| Fun Team (profile +10, Midnight Games, help other squads) | ✅ |
