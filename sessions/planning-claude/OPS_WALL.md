# Ops Wall: real-time visualization + live audience-call demo

## 1. The Ops Wall (one big-screen page, dark theme, readable from the back row)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ZONE LADDER  West Altadena: NORMAL → WATCH → [ASK] → CRISIS   9 reports/6 min │
│ 3 corroborated · auto welfare calls in 4:59 · [DECLARE CRISIS]                │
├───────────────┬───────────────┬───────────────┬───────────────┬──────────────┤
│ LIVE CALLS    │ TOTAL CALLS   │ AI-RESOLVED   │ HUMANS ENGAGED│ CALLBACK Q   │
│ 18 / 20 ▮▮▮▮▯ │ 143           │ 71%           │ 4 / 6 on duty │ 12 (saved)   │
├───────────────────────────────────────┬──────────────────────────────────────┤
│ LIVE MAP                              │ ACTIVE CALLS (cards, auto-scroll)    │
│ pins by severity (P0 red pulsing,     │ 🇪🇸 ES · crisis agent · P1           │
│ P1 orange, P2 yellow, P3 grey),       │ "...hay mucho HUMO en la calle..."  │
│ cluster rings growing, zone polygons  │ form: evacuation_assistance ▮▮▮▯ 3/4 │
│ tinted by level                       │ → routing: evac_logistics + Spanish  │
│                                       │ 🇰🇷 KO · everyday · P3 · enroll check-in│
├───────────────────────────────────────┼──────────────────────────────────────┤
│ CALL FLOW (animated)                  │ ACTIONS FEED                         │
│ calls → AI resolved ███████           │ ✓ D-417 escort booked (Leavey 11 PM) │
│       → human (matched) ██            │ ✓ Check-in scheduled · KO · daily    │
│       → callback queue ███            │ ✓ Clinic form complete → sandbox     │
│       → 911/988 safety path ▌         │ ⚠ Mrs. K no answer → SMS → daughter  │
├───────────────────────────────────────┼──────────────────────────────────────┤
│ TRENDING TERMS (per zone)             │ RESPONDERS                           │
│ humo ×7 · smoke ×5 · oxygen ×2        │ Ana (ES, medical) ● on call 2/2      │
│                                       │ Jin (KO, general) ● available        │
└───────────────────────────────────────┴──────────────────────────────────────┘
```

**Panels and their data sources:**

| Panel | Shows | Source |
|---|---|---|
| Zone ladder banner | Current level, evidence, countdown, Declare button | `zones` table (DS crisis-detection job) |
| Stat tiles | Concurrent calls vs. limit, total, AI-resolved %, humans, callback queue, median time-to-human for P0 | `calls` + Retell `get-concurrency` (poll every 2 s) |
| Live map | Pins by severity, cluster rings, zone polygons | `reports`, `clusters`, `zones` (Leaflet + CSS pulse) |
| Active call cards | Language, which agent, severity, **live transcript with keywords highlighted by tier**, form progress, routing decision | `transcript_updated` webhook → `call_events` |
| Call flow | Where calls end up: AI-resolved / human / callback / safety path, animated as they move | `calls.outcome` |
| Actions feed | Every real action with its confirmation code | `requests`, `forms`, scheduler |
| Trending terms | Lexicon hits per zone, last 10 min | `call_events.keyword_hits` |
| Responders | Status, skills, load | `responders` |
| *(tab)* Quality | Eval scoreboard v1 → v3 | `evals` |

**Tech:**
- Retell webhooks → FastAPI writes rows → **Supabase Realtime** pushes them to the React page. No custom sockets.
- Every panel is a subscription to one table.
- **Replay mode:** the same page replays a recorded drill from timestamps. This is the backup if the network dies.
- **Privacy on the projector:**
  - Phone numbers are masked (`•••-•••-4821`).
  - Names show as initials.
  - The backend runs a regex pass to scrub addresses and numbers from the transcript ticker.
  - Callers use role cards anyway.

**Owners:** CS#2 builds the page; DS does stats, crisis detection and trending terms; CS#1 handles the concurrency poll and transcript events.

## 2. Live audience call during the pitch / demo floor

**Script (~90 s inside the 5-min pitch, beat 1:15–2:45):**
1. "Everyone, phones out. Scan this QR and you'll get a role card. Call when the countdown hits zero." 10-second countdown on the wall.
2. The wall lights up: pins drop, call cards stream, trending terms climb, the zone goes WATCH → ASK.
3. **A planted teammate makes the P0 call:** "my dad's on oxygen and there's smoke." Warm transfer; the room hears the **whisper brief** on the speaker phone.
4. The presenter taps **Declare**. Welfare calls fire. The planted no-answer resident escalates up the ladder.
5. "N of you called. Here's where every call went": point at the call-flow panel.

**Guaranteeing it works:**
- **Concurrency:** 20 free slots.
  - Either buy extra slots for the weekend (~$8/slot/month), or let the overflow show off the callback queue on purpose.
  - **Verified:** at the limit, inbound callers are queued ~40 s, then sent to the number's **fallback number**. Turn on **burst** (up to 60 concurrent, +$0.10/min) and set a fallback voicemail line.
  - Fallback: role cards stagger callers ("call at 0 s / 20 s / 40 s").
  - Set `reserved_inbound_concurrency` so outbound welfare calls can't block inbound.
- **Room noise:** dozens of people talking at once in one hall. Turn on **background-speech removal** denoising (+$0.005/min). Cards say "step to the side and hold the phone close".
- **Cell signal in Ginsburg Hall:** test Sunday 8 AM. If it's weak, more callers come from the web-call page (Retell web SDK, works over Wi-Fi) and the QR offers both.
- **Volume floor:** 8–10 planted friends + the **simulator topping up** to ~200. Say so honestly: "plus 150 simulated."
- **Agent mode:** drill greeting on, recording notice on, `feature_consent` question on.
- **Cost:** ~100 calls × 1.5 min ≈ $15. Keep the balance ≥ $30.
- **Backup:** if anything fails, switch the wall to replay mode of the Saturday Surge Drill and keep narrating.

**Stretch "magic moment":** after calling, the caller's QR page shows **their own call's status** live, by drill code ("You were routed to: AI resolved → escort booked, D-417"). Every audience member sees the system handle *them*.
