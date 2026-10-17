# DIZA — Setup & Infrastructure

Source: Retell docs (docs.retellai.com) checked 2026-10-17. Items marked (U) are unverified.

## 0. Do these first, tonight (in this order)

| # | Task | Owner | Why now |
|---|---|---|---|
| 1 | **One teammate creates the Retell account + completes KYC** (Persona gov't ID) | CS#1 | KYC is required before buying a number, making outbound calls or sending SMS. Each person can verify only **one** account. Manual review can be slow. |
| 2 | Add a card and top up ~$20. Ask organizers how the **$10 hackathon credits** are applied (Retell's docs mention no promo codes). | CS#1 | A card is required to buy a number. Every signup also gets $10 free trial credit. |
| 3 | Invite the other 3 to the Retell workspace | CS#1 | Billing is per workspace, so everyone shares one balance and set of agents. |
| 4 | Buy a number with an LA area code (**626** = Altadena/Pasadena, or 213/323); provider **twilio** | CS#1 | $2/mo. Twilio-backed numbers support transfer caller-ID and inbound SMS during calls. |
| 5 | Create a **Twilio trial** account and verify all 4 team phones (max 5 verified numbers) | CS#2 | Our SMS path for the demo (see §4) |
| 6 | Supabase project (free) | CS#2 | Database + realtime for the dashboard |
| 7 | GitHub repo access for all; Devpost accounts for all 4, joined to one project | Biomech | Required to submit |
| 8 | IBM Bob 30-day trial (ibm.biz/university-bob) | CS#2 | Best Build with IBM Bob prize |
| 9 | ngrok account, then claim the **free static domain** | CS#2 | Stable HTTPS URL for Retell webhooks while developing |

**Budget:** about $0.10/min of voice (infra $0.055 + GPT-4.1-mini $0.013 + TTS $0.015 + telephony $0.015). $10 ≈ 100 minutes. Plan on $20–30 total.

## 1. Retell configuration

- **Agent type: Single Prompt** with custom functions. This is Retell's own recommendation.
  - Multi-prompt is deprecated.
  - Conversation Flow is too rigid for crisis intake.
  - Custom LLM over WebSocket means writing our own LLM loop, which is too much for a weekend.
- **LLM:** GPT-4.1 mini or Claude 4.5 Haiku. Turn on **Structured Output** and set temperature low for reliable function calls.
- **Voice:** a platform or Cartesia voice ($0.015/min). Skip ElevenLabs; it costs 3–6× more.
- **Languages:** pass an array, e.g. `["en-US","es-ES"]`. `"multi"` is rejected.
  - Fewer languages means better speech recognition.
  - Better pattern: detect the caller's language in the inbound webhook (registry lookup) and override it per call.
  - Separate agents for Korean, Armenian and Tagalog are a stretch goal.
- **Three agents:**
  1. `inbound-line`: crisis and non-emergency intake
  2. `checkin-outbound`: the Tuesday check-in
  3. `welfare-outbound`: crisis welfare call
  - All three share the same functions.

### Inbound call webhook: this is where the mode switch lives
On every inbound call, Retell asks our backend for dynamic variables. It times out after 10 s and tries 3 times. We:
1. Look up the caller's number in the registry. Return `name`, `language`, `needs`, `zone`.
2. Return the zone's current level (`normal` / `watch` / `ask` / `crisis`) and `known_incidents`. The prompt branches on `{{zone_level}}`:
   - normal: the regular greeting
   - watch and above: the "we know about the fire near X…" greeting
3. Override the language for this call if the registry knows it.

**All dynamic-variable values must be strings.**

### Custom functions (POST to our FastAPI)
| Function | Purpose | Returns |
|---|---|---|
| `submit_report` | hazard, address/cross-streets, people count, injured/trapped, mobility/medical needs, language | `report_id`, `cluster_match` ("we already know about…") |
| `route_to_human` | called when escalation criteria are met | `oncall_number`, `responder_name`, `brief`. Mapped to dynamic variables with **"Store Fields as Variables"**. |
| `schedule_callback` | caller is below the threshold | callback ETA |
| `lookup_guidance` | evacuation zone, shelter, what to do | short text |

- Turn on **"args only"** if we just want flat args. Leave it off to also receive `call.transcript_object` with **word timings**. That gives the DS person speech-rate and pause features *at the moment of escalation*, live.
- **Verify `X-Retell-Signature`** against the **raw** request body: `retell.verify(raw, api_key, sig)`. The API key must have the webhook badge.
- Set function timeout ≈ 5 s and `max_retry` 1.

### Warm transfer (skills-based routing works natively)
- Transfer destination = `{{oncall_number}}`, filled by `route_to_human`. **Dynamic routing is supported.**
- **Whisper debrief message** (heard only by the human): "Caller {{caller_name}}, {{language}}, {{brief}}. You're getting this because {{match_reason}}."
- **Agentic warm transfer** if we want the briefing to adapt. If the human doesn't answer, the call goes back to the AI; our backend then picks the next responder.
- ⚠️ **Transfers only work on real phone calls, not web calls.** The transfer demo needs a phone.
- Webhooks `transfer_started`, `transfer_bridged` and `transfer_cancelled` update the dashboard.

### Outbound (check-ins, welfare calls, callback ladder)
- `POST create-phone-call` with `from_number`, `to_number`, `override_agent_id`, `retell_llm_dynamic_variables` (name, language, needs, reason) and `metadata` (resident_id, ladder_step).
- **Our backend owns retries.** On `call_ended`, read `disconnection_reason`:
  - `dial_no_answer` / `dial_busy` / `voicemail_reached` → next ladder step: SMS → retry at +5 min → emergency contact → red flag
- Turn on voicemail detection: leave a short message, then hang up.
- Batch calls exist (CSV → calls) but have no retries. Use them for the "Tuesday 10 AM" check-in run; use single calls for the ladder.
- Default rate is 1 call started per second. **20 concurrent calls are free.** That's plenty for real calls; the 200-call surge in the demo comes from the **simulator** (text-level, it posts reports directly), and we say so honestly.

### Webhooks to subscribe
`call_started`, `call_ended`, `call_analyzed`, `transcript_updated` (live, per turn, used for the live transcript ticker on the dashboard), and the transfer events. 10 s timeout, 3 retries, so **the backend must be warm.**

### Post-call analysis fields (filled by Retell after each call)
- `urgency` (enum)
- `hazard_type` (enum)
- `location_text`
- `people_at_risk` (number)
- `needs_human` (bool)
- `mobility_or_medical` (text)
- `caller_language`
- `sentiment`

### Recordings, for the acoustic layer
- After `call_ended`, Get Call returns:
  - `recording_multi_channel_url`: stereo, caller on its own channel, which is ideal
  - `transcript_object` with word start and end times
- **Live audio is NOT available server-side.** Only the browser Web SDK can listen. So the acoustic flags (breathlessness, slurring, alarms) run **right after the call**. They feed the callback and welfare priority and the person's baseline. Live signals come from transcript keywords and word timing.

## 2. SMS: plan around Retell's limits

- Sending SMS from our own number needs **A2P 10DLC registration, which takes about 2–3 weeks.** That isn't possible this weekend.
- **What we do:**
  - **Outbound SMS:** the backend sends via the **Twilio trial** to the 4 verified team phones (5 max). Good enough for the demo.
  - **Inbound SMS reports:** Retell Twilio numbers can receive SMS *during* a call. For text-only reports, point a Twilio trial number's SMS webhook at our backend.
  - On the Devpost page and in Q&A, say: "Production: A2P 10DLC registration (2–3 weeks) or Retell's SMS-approved pool." That shows we know the real path.

## 3. Our infrastructure

| Piece | Choice | Notes |
|---|---|---|
| Backend | **Python FastAPI** (DS-friendly) | Use the `retell-sdk` Python package for signature checks and calls. |
| Database + realtime | **Supabase** (Postgres + Realtime) | The dashboard subscribes to table changes directly, so we don't write WebSocket code. Free tier: 500 MB, 200 realtime connections. |
| Dashboard | **React (Vite) + Leaflet/OSM + supabase-js**, deployed on Vercel | Queue, map clusters, zone levels, ladder status, Declare/Approve buttons |
| Hosting the backend | Dev: **ngrok static domain**. Demo: **Railway or Fly (~$5)** or keep ngrok on a laptop that stays plugged in. | ⚠️ **Not the Render free tier.** It sleeps after 15 min and takes ~1 min to wake, longer than Retell's 10 s webhook timeout. |
| Scheduler (callback ladder, dead-man's switch) | APScheduler inside FastAPI | Simple and good enough |
| Geocoding | **Census geocoder** (free, US, no key) to pre-geocode the synthetic registry; Nominatim at 1 request/s for live addresses, cached | Mapbox free tier as backup |
| Audio analysis | librosa (speech rate, pauses, pitch, energy) + **YAMNet** (alarms, sirens, coughs) on the caller channel | Runs as a background job on `call_analyzed` |
| Clustering | scikit-learn DBSCAN on (lat, lon, time) | DS owns |
| Synthetic data | Faker + census-weighted languages; ~500 residents in Altadena / NE LA | DS owns |
| Secrets | `.env` (never commit), `.env.example` in the repo | RETELL_API_KEY, TWILIO_*, SUPABASE_URL/KEY |

## 4. Build vs. reuse

| Need | Already exists | We build |
|---|---|---|
| Voice agent, speech-to-text, text-to-speech, languages, turn-taking | **Retell** | prompts + functions |
| Warm transfer, whisper brief, dynamic destination | **Retell** | responder matching logic |
| Outbound calls, batch, voicemail detection | **Retell** | retry ladder and dead-man's switch |
| Structured extraction after a call | **Retell post-call analysis** | the schema |
| Live transcript, recordings, word timings | **Retell webhooks / Get Call** | priority score + acoustic flags |
| SMS | **Twilio** (trial) | ladder step |
| Realtime DB / pub-sub | **Supabase** | the schema |
| Map | **Leaflet + OSM** | the cluster layer |
| Audio classifiers | **YAMNet** (pretrained), librosa | thresholds + escalate-only rules |
| Retell starter code | `RetellAI/retell-custom-llm-python-demo` (signature + webhook patterns) | — |

**Our original work:**
- Corroboration and clustering engine
- Zone escalation ladder
- Skills-based routing
- Callback and welfare ladder
- Physiological voice flags
- The supervisor dashboard

## 5. Repo layout (proposed)
```
backend/      FastAPI: /retell/inbound, /retell/functions/*, /retell/webhook, /twilio/sms, scheduler
analysis/     clustering, priority score, acoustic features, synthetic data generator
dashboard/    Vite React app
agents/       Retell prompts + function JSON schemas (versioned, so twists show up as diffs)
sim/          surge simulator
TWISTS.md     twist log (what changed, why, proof)
```

## 6. Gotchas checklist
- [ ] KYC done before anything outbound
- [ ] Only call or text **team phones** while testing. New numbers with lots of unanswered calls get marked as spam.
- [ ] Backend warm (no cold starts) during the demo; webhooks time out after 10 s
- [ ] Signature verification uses the raw body
- [ ] Dynamic variables are strings only
- [ ] Transfer demo uses a real phone, not a web call
- [ ] Phones charged, plus a backup demo video
