# Demo plan

Rule from the hub: **"Show it working thing first."**
- Finalists: 5-min pitch + 5-min Q&A (problem 0:30 → working thing → twists → next).
- Demo floor: 3 min, working thing first.
- Everything risky has a recorded backup.

## Setup (table or stage)
- **Big screen:** the supervisor dashboard (map, priority queue, zone banner, trending terms, live transcript ticker).
- **Phone on speaker:** a supporter phone, so the room hears the **whisper brief** on transfer.
- **QR code** on the slide and on the table: "Call it yourself" + role cards.
- **Laptop 2:** the backup video, cued, plus the eval scoreboard tab.
- **Staging tags set:** transfers go to our phones; outbound goes only to consenting numbers (judges who say yes).

## 5-minute finalist pitch
| Time | Beat | What's on screen |
|---|---|---|
| 0:00–0:30 | **Problem.** Altadena: 14+ resident reports, west side warned at 3:25 AM, 17 of 19 deaths. Two days later, a false alert to ~10M phones. "Residents were the sensor; nobody was listening." | One photo + 3 numbers |
| 0:30–1:15 | **Tuesday, live.** A judge calls: "Check on my grandma every morning, she speaks Korean." → form filled, consent pending → **a phone rings 10 s later with the first check-in, in Korean.** | Dashboard: new registry entry |
| 1:15–2:45 | **Fire night, live.** 60-second room flood via QR. The simulator adds 150. "200 calls → 3 clusters → zone WATCH → ASK → neighbours asked → **I tap Declare**." A P0 caller ("my dad uses oxygen, there's smoke") is warm-transferred; the room hears the whisper brief. Mrs. Kim doesn't answer → text → daughter called → red flag. | Zone banner, queue reordering, ladder |
| 2:45–3:30 | **Twists + it learns.** "Each twist changed the build:" 3 one-line diffs. "Every failed call from our live drills became a test: v1 → v3, urgent recall 100%." | TWISTS.md + scoreboard chart |
| 3:30–4:30 | **Who pays, and where it goes.** Council office, home-care agency or USC on a Tuesday; the same line on fire night. Live numbers from our campus Open Line. Travel test: voice + SMS, works on flip phones. National resilience: base family lines, VA check-ins. | Customer slide + campus stats |
| 4:30–5:00 | **What it never does**, then the ask. Never sends public alerts, never claims dispatch, P0 → 911/988, only escalates. | One slide |

**Q&A prep** (biomech maintains the doc):
- false positives
- hoax floods
- privacy and consent
- cost per call (~$0.10/min)
- why not just 911
- what happens when the AI fails (failover)
- A2P SMS timeline
- HIPAA
- how a city buys this (Open311 / pilot)

## 3-minute demo-floor version
1. 0:00–0:20: one-line problem plus "call it yourself" (hand them the QR)
2. 0:20–1:30: their call shows on the dashboard; the agent does a real action (reminder, escort or form) with a confirmation code
3. 1:30–2:30: press "Run surge" (simulator) → clusters, zone escalation, transfer with whisper on speaker
4. 2:30–3:00: scoreboard + "who pays on Tuesday"

Run a **mini flood at :00 and :30** each hour on the demo floor (CALL_SCHEDULE.md).

## Backups
- A full recorded run from the Sat 3:30 Surge Drill. A screen recording, with phone audio captured.
- If Retell or the network fails: the dashboard replays the recorded drill from the database ("replay mode").
- Hotspot from a teammate's phone if venue Wi-Fi is bad.
- Pre-seeded registry + responders. Nothing depends on typing live.

## Rehearsal
- Sat 9 PM: run it after submitting.
- Sun 8 AM: run it again, with timing.
- Roles on stage:
  - Biomech presents.
  - CS#1 runs the phones.
  - CS#2 runs the dashboard and simulator.
  - DS covers the metrics in Q&A.
