# DIZA demo happy path: say / show / do (feature freeze)

- **Session:** ops-agent, Sat 2026-10-17, 8:35 PM PDT.
- **Rule from here on:** no new features. Only fix what breaks the steps below.
- **Live:** https://diza-production.up.railway.app (drill mode, nothing reaches real 911).
- **Line:** +1 978-915-3497.

## 0. Before 10:00 PM: Devpost, or nothing else counts

The hub says "No extensions." Required: **name + lens + one line · pitch deck · demo video · code repo · all teammates · responsible-use note.**

| Item | Text / where |
|---|---|
| Name | DIZA |
| Lens | Resilience Comms (Retell AI) |
| One line | DIZA answers every call in the caller's language, pins each place they mention on a live map, ranks who needs a person first, and phones the right teammate, for a building on a normal day and a 911 floor in a mass-casualty surge. |
| Code repo | https://github.com/wimaan3/diza (make sure it's public, or judges get a 404) |
| Demo video | 2–3 min screen recording of sections 2–4 below, with phone audio. Record it **now**; it doubles as the backup. |
| Deck | 5–6 slides, matching section 1 |
| Responsible use (2 lines) | **Misuse:** a fake call flood could bury real ones, and an AI that "decides" could deny someone help. **Limits:** DIZA never dispatches, never sends public alerts and never closes an emergency on its own. A human takes every P0, answers are rule-ranked with reasons shown, independent callers are counted (not trusted), and in drill mode transfers only reach teammates. |
| Tools | Retell AI (voice agents, custom functions, outbound calls), FastAPI + SQLite, React + Vite, MapLibre, OpenStreetMap Nominatim, Railway, Claude Code |

## 1. The story (30 s problem, then working thing first)

> "When a building or a city has a bad night, the phones are the first thing to break. Ten people call about the same crash, three grandparents fall in three different towns, the one Spanish speaker waits for an interpreter, and the person on duty is typing addresses instead of helping. DIZA answers every call, writes it down, puts it on the map, ranks it and calls the right person. The AI listens and asks. Rules rank. People decide."

**Dual-use (say the second customer by name):** on Tuesday it's the **building management line** (leaks, noise, lockouts → tickets → the maintenance person's phone rings). On a crisis night it's the **911 / overflow line**, with the same agent, map and team.

## 2. Tuesday: building management (≈60 s)

**Do:** on `/building`, click **Load demo week** first so the board isn't empty. Then call the line from a phone on speaker:

> "Hi, I'm in Larchmont Court Apartments, unit 4A. Water is leaking from my bathroom ceiling. Also there's a loud disturbance in 2F."

**Show:**
1. Two tickets appear, **4A water leak (emergency)** and **2F noise**, each with its unit and building, not one blob.
2. Category chips filter them (Water / Noise …).
3. **Assign** 4A to a teammate. **That teammate's phone rings**; DIZA briefs them, they say "yes", and the ticket moves to **In progress** by itself.
4. They open **Supporter inbox** (pick their name), then **Close · fixed**, and the ticket is handled.

**Say:** "Nobody typed anything. The tenant spoke; a ticket exists, the right person was called and accepted by voice, and it's closed with a timeline."

## 3. Crisis night: elderly falls + freeway crash (≈90 s)

**Do:** go to `/ops` and click **Load demo: falls & freeway crash** (pre-seeded surge). Then make the live call, ideally in Spanish:

> "Mi abuela se cayó y no puede levantarse, en Western y la Sexta en Los Ángeles. Y mi vecino también se cayó en Santa Mónica, en la calle 11 y Broadway."

**Show:**
1. **Two separate pins** from one caller, at the actual corners (Western & 6th LA; 11th & Broadway Santa Monica).
2. The cards rank to the top with **reasons shown** ("fall, can't get up, elderly").
3. The 110 Fwy crash shows **many callers merged into one incident**; each call is still its own record. Say: "That's the grouping LAPD did by hand in the Palisades."
4. The **load strip**: calls answered with no wait, intake done before a human picked up.
5. **Offer to eligible responder** on a P1 card. The on-duty teammate with the right skill/area **gets a phone call**; "no" goes to their backup automatically.
6. **Take call** / **Callback** on an ended call. DIZA phones the operator with the caller's number read out.
7. **Mark done**: the card moves to the **Done** tab, and the responder is free again.

**Say:** "The AI never sent an ambulance. It gave the human a ranked, located, translated queue and called the right teammate. That's the load off the operator."

## 4. Global, in 15 s (Twist 2)

**Show:** switch the language picker to 中文 / Español; the whole UI changes. Point to the region badge (`US · Emergency 911`).

**Say:** "One setting, `DIZA_COUNTRY`, sets the emergency number, map area and agent language. For China it's 120 for ambulance and Mandarin; the limits (number purchase, PIPL) are in our twist doc."

## 5. Close (20 s)

- **Never automated:** dispatch, public alerts, deciding who gets help.
- **Why it ships:** a phone number + a browser, about $0.10/min.
- **Funding (Twist 1):** a building owner pays monthly, and a city funds the 911 version through FEMA UASI/EMPG, with NSF SBIR for the R&D.

## Fallbacks, if a live call fails

| Problem | What to do |
|---|---|
| Call doesn't connect | Use the seeded `/ops` surge and the **New demo report** bar; play the recorded video for the call. |
| Pin lands wrong | Say the city every time ("…in Los Angeles"). Corners without a city get no pin, by design. |
| Teammate's phone doesn't ring | The same offer is in **Supporter inbox**; accept it there. |
| Wi-Fi bad | Hotspot. The video is the backup. |

## Roles on stage

- **Presenter:** talks, sections 1, 4, 5.
- **Caller:** makes the two live calls.
- **Driver:** clicks the dashboard.
- **"Responder":** holds the phone that rings and says "yes" out loud.

## Don't demo (half-done or off-story)

Fire, public alert approval, check-in calls, the volunteer chat. Don't claim a GPS link or Korean; the live path we've verified is EN/ES with spoken locations.
