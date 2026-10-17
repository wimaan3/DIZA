# DIZA — Public Call Schedule & Flood Drills

The schedule fits around: P0 working by Sat 2 PM, the talks (Retell 10:30 AM, keynote 11 AM, IBM 1 PM), the Twist 3 response due 1 PM, Devpost due 10 PM, and Sunday's demo floor (12–2:30 PM) and finalist pitches (1:15 PM).

## The windows

| Window | When (PT) | Who we invite | What callers do | What we get |
|---|---|---|---|---|
| **Internal test** | Fri night → Sat 10 AM | Team only | Break it | Bugs fixed before the public calls |
| **Open Line** | **Sat 11 AM → 9 PM** and **Sun 9 AM → 3:30 PM** | Everyone: hackathon, USC friends, classes | Call with **any campus question, need or request** | Ordinary-day data: topics, baselines, routing to supporters |
| **Flood #1: Dry Run** | **Sat 12:30–12:45 PM** | ~20–30 people (friends + other squads) | Call at the same time with a role card | Find load bugs early |
| **Flood #2: Surge Drill** ⭐ | **Sat 3:30–3:50 PM** | As many as possible (target 60–100) | Everyone calls in the first 5 min with a role card | Main load test; **record the demo video during this** |
| **Flood #3: After the Fix** | **Sat 8:00–8:15 PM** | Same crowd | Same | Before/after metrics: proof of the learning loop, ready for Devpost at 10 PM |
| **Live Flood (Sunday)** | Demo floor: **12:30, 1:00, 1:30, 2:00 PM**, 3 min each. If finalist: a 60-second flood **during our pitch** | Judges, guests, other teams | Scan the QR code on our table or slide and call | The "wow" moment + People's Choice votes |

Why short floods: Retell runs **20 concurrent calls** for free. A 10–20 minute window with 60–100 people deliberately overflows that, so the callback queue ("your place is saved") gets shown working.

## How a flood works

1. People open the QR code / link → **drill page** showing:
   - the number
   - a random **role card** with a **drill code**
   - the safety note
2. Caller dials and says **"drill code 47"** first. The agent passes `drill_code` into `submit_report`. This is DS's ground truth.
3. The dashboard goes into **Drill Mode**:
   - countdown timer
   - live counters: calls, concurrent calls, overflow → callbacks, routed to supporters
   - map pins appearing
   - Put it on a projector/laptop facing the room. It's fun to watch, and fun points.
4. Supporters are on duty (texted `IN`) **before** the window opens.
5. At the end: freeze a **metrics snapshot**, save it in `analysis/snapshots/`, list fixes, ship them before the next flood.

**Role-card mix** (DS generates it):
- 60% everyday concerns (housing, lost item, escort, building issue, class/where-do-I-go)
- 25% crisis (smoke, power out, injury, someone not answering)
- 10% duplicates of one incident
- 5% hoax
- **Languages:** ~30% non-English (Spanish, Korean, Mandarin, Armenian, Tagalog). Ask bilingual friends to take those cards.

## Pre-flight checklist (T-15 min before every flood)
- [ ] Retell balance ≥ $20; concurrency limit known
- [ ] Backend warm, webhooks green, Supabase up
- [ ] ≥ 4 supporters `IN`, covering ≥ 2 languages
- [ ] Drill page live, cards generated, codes unique
- [ ] Dashboard in Drill Mode on the big screen
- [ ] Screen recording running (Flood #2)
- [ ] Safety path tested: say "I want to hurt myself" → agent gives 988/911 and offers transfer, never to a volunteer

## Announcement copy (get organizer OK before using their WhatsApp channel)

**Open Line (post Sat ~10:45 AM; also on posters + QR in RTH 526):**
> 📞 **Got a campus question? Call DIZA: (626) XXX-XXXX**
> Today 11 AM–9 PM and Sunday 9 AM–3:30 PM. Ask anything: where to go, housing, lost items, safety escort, food, a building issue, in English, Español, 한국어, 中文, Հայերեն or Tagalog. A real person picks up when it matters.
> Built this weekend by Team DIZA at the InnovateLA Dual-Use Hackathon. Calls are recorded for this student project. **Not for emergencies: call 911.**

**Flood drill (post 30 min before, then again at T-5):**
> 🌊 **SURGE DRILL at 3:30 PM: help us break our phone line!**
> At 3:30 sharp, scan this QR, grab a role card, and call (626) XXX-XXXX. Say your drill code first, then play your role. We want 100 calls in 5 minutes to show how the line holds up when everyone calls at once.
> Takes 2 minutes. Recorded for a student project. Real emergency? Call 911.

**Sunday demo table / pitch slide:**
> 📱 **Call it yourself: (626) XXX-XXXX.** Scan for a role card. Flood at :00 and :30.

## Owners
- **Biomech:** drill page + copy + posters, recruiting callers and supporters, organizer approval
- **DS:** role cards + drill codes, snapshots and before/after metrics
- **CS#1:** agent handles `drill_code`, flood-mode greeting, safety path
- **CS#2:** Drill Mode on the dashboard, counters, overflow → callback queue
