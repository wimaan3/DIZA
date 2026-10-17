# Retell: APIs, MCP, knowledge base, agent handoff (how we use it)

Source: docs.retellai.com (index: /llms.txt), checked 2026-10-17. (U) = unverified.

## 1. Connect our coding agents to Retell (MCP)

Retell runs an **official hosted MCP server**. Each teammate's Claude Code can create and inspect agents, numbers, calls and knowledge bases directly:
```
claude mcp add --transport http retell https://mcp.retellai.com --header "Authorization: Bearer $RETELL_API_KEY"
```
- It exposes three tools: `list_api_endpoints`, `get_api_endpoint_schema`, `invoke_api_endpoint`. Together they cover the whole API.
- ⚠️ **Do not "always allow" `invoke_api_endpoint`.** It can delete or publish anything. Approve each call by hand.
- Local alternative: `npx -y @retell-ai/mcp-server` (needs `RETELL_API_KEY`).
- **Git is the source of truth, not the MCP.** Use MCP to explore and debug. Real config changes go through `agents/*.json` + `push.py` (below), so every change is a commit, which doubles as twist proof.

**Other tools:**
- **CLI:** `npm i -g @retell-ai/retell-cli` (Node 22+)
  - e.g. `retell get-agent <id>`, `retell create-agent --body agent.json --dry-run`
- **SDKs:** `pip install retell-sdk` (`from retell import Retell`) · `npm i retell-sdk` · browser: `retell-client-js-sdk`

## 2. Agents in git: push script

There's no export/import endpoint, so we script it:
- `pull.py`: `get-agent` + `get-retell-llm` → `agents/<name>.agent.json`, `agents/<name>.llm.json`
- `push.py`: `update-retell-llm` / `update-agent` → `create-agent-version` → `publish-agent-version` → move the **`prod`** tag
- Environment tags `prod` / `staging` each carry their own dynamic-variable values.
  - **staging:** transfers go to teammates' phones
  - **prod:** transfers go to the supporter pool
- Gotcha: the pronunciation dictionary array **replaces** the whole list on update.

## 3. Connecting Retell agents to each other (Agent Transfer / "agent swap")

**A live call can hop between our Retell agents with full context.** Same `call_id`; the new agent gets the transcript, metadata and all dynamic variables. Swaps can chain and go back, and they work on web calls too.

Our structure:
```
inbound (everyday, per-language)  ──agent_swap──►  crisis-intake (same language)
       ▲                                                │
       └──────────── swap back if it was a false alarm ──┘
outbound-checkin  ──agent_swap──► crisis-intake   ("I smell smoke" during a Tuesday check-in)
```
- **Why split:**
  - Focused prompts, each with its own tools and knowledge base. The crisis agent gets the shorter, faster, stricter prompt.
  - **Per-language agents are more accurate** than one multilingual agent; mixing language families goes through a weaker speech-recognition path.
- **Language routing:** the inbound call webhook returns `override_agent_id` (or an `agent_override` with language and boosted keywords) based on the registry or the caller's previous language. Unknown callers start on the EN+ES agent; "para español" swaps them.
- Limits:
  - Can't swap to custom-LLM or chat agents.
  - PII and storage settings stay pinned to the **first** agent.
  - Choose which agent's post-call analysis runs (set it to the crisis agent's).
- Conversation Flow also has subagent nodes and agent-transfer nodes. We stay on **Single Prompt** agents (multi-prompt agents are being retired).

## 4. Knowledge base: what goes in it vs. not

- **How it works:** retrieval runs automatically every turn and adds under 100 ms.
  - Sources: Markdown, PDF, CSV, URLs, text snippets, Google Drive, Notion.
  - Limits per KB: 25 files, 500 URLs, 50 text snippets.
  - Cost: first 10 KBs free; +$0.005/min on calls that use one.
- **Update it live from a script:** `POST /add-knowledge-base-sources/{id}`. That's our **"topic mining → approved FAQ → agent knows it"** loop. Allow a short re-index delay (U).

| Put in the KB (stable facts) | Keep OUT of the KB → custom function to our backend (live data) |
|---|---|
| Campus FAQ (dining, buildings, printing, offices, escort rules) | Open shelters and capacity, evacuation orders, road closures (change hourly; KB auto-refresh is only every 24 h) |
| Emergency and resource directory (911, 988, 211 LA, county lines, campus lines; see COMPLIANCE.md) | Request status, callbacks, responder availability |
| "What this line can and can't do" (not 911, no dispatch, how callbacks work) | Zone level and known incidents (inbound webhook variables) |
| Preparedness guides (go-bag, evacuation checklist) in each language | Registry / personal data (never in the KB) |

Separate KBs: `campus-faq`, `la-resources`, `line-policy`. The crisis agent gets only `la-resources` + `line-policy`.

## 5. High-leverage settings

- **Push news into calls already in progress:** `PATCH /v2/update-live-call/{call_id}` with `additional_context` + `trigger_response`. When a zone escalates or a new evacuation order lands, we push it into every active call in that zone. **This answers the TRIAGE.md open question:** the backend can push "caller mentioned trapped → transfer now" into a live call (test it).
- **Boosted keywords** (up to 100, dynamic variables allowed): `humo`, `fuego`, `atrapado`, Altadena, Lake Ave, shelter names, campus building names. They make speech recognition catch our trigger words.
- **Denoising:** keep remove-noise. Also consider the background-speech removal (+$0.005/min), since crisis calls are noisy.
- **Turn-taking:** `interruption_sensitivity` ≈ 0.7–0.8. Distressed callers talk over the agent.
- **Silence:**
  - `reminder_trigger_ms` ~8 s, so the agent checks in sooner.
  - Generous `end_call_after_silence_ms` on the crisis agent, **because silence can mean the caller is in trouble.** Add a function that flags silent calls for a callback.
- **Concurrency:** `reserved_inbound_concurrency` so outbound check-ins never starve inbound calls during a flood. `get-concurrency` gives a live dashboard number.
- **Keypad:** `user_dtmf_options` lets "press 0 for a person" work for callers who can't talk.
- **Post-call extraction fields:**
  - `severity` (selector P0–P3)
  - `category` (selector)
  - `needs_followup` (bool)
  - `language` (selector)
  - `people_at_risk` (number)
  - `vulnerability` (text)
  - Built-in `user_sentiment` is text-only.
- **Privacy:**
  - `pii_config` scrubbing on
  - `data_storage_retention_days` short (e.g. 7) for the event
  - HIPAA needs a signed BAA, so we don't claim HIPAA.
- **Guardrails / `handbook_config`:** presets exist (e.g. high_empathy). Evaluate the latency cost (~50 ms).

## 6. Testing floods without paying for calls

- **Simulation test cases + batch tests over the API:**
  - A simulated-user prompt plus success criteria, with mocked functions.
  - `create-batch-test` → poll `get-batch-test`.
  - Text only: no speech recognition or noise. ~$0.001–0.05 per message.
- Use them before every `push.py` publish as a regression gate. Seed from DS's role cards:
  - "smoke + wheelchair, Spanish"
  - "hoax"
  - "self-harm → must give 988 and never transfer to a volunteer"
  - "refuses help"
  - "silent caller"
- ⚠️ Mocks are ignored for MCP tools, and un-mocked custom functions hit the **real** backend. Point tests at staging.
- **Conductor** (AI inside the dashboard) can generate test cases; 30 free credits per user per day.

## 7. Agents calling external MCP servers (optional)

Retell voice agents can use **MCP tools** (Streamable HTTP, public URL, header auth, dynamic variables allowed, tool whitelist).
- Option: expose our FastAPI actions as one MCP server instead of many custom functions.
- **For the weekend, stick with custom functions:** simpler, mockable in tests, retry setting.

## 8. Caching repeated questions and answers

**Who controls what:** Retell's built-in LLM makes the model calls itself, so we **can't set provider prompt-caching flags** on the agent's turns. Whether Retell caches internally isn't documented (U). Here's what we can do:

1. **Answer cache (the big win, and works under flood):**
   - Repeated questions ("is the fire near me?", "where's the shelter?", "dining hours") are answered from **pre-approved answers**, not fresh reasoning.
   - Stable answers → **knowledge base** (retrieval adds under 100 ms).
   - Live answers → `lookup_info` function backed by a **semantic cache** in our backend: embed the question; if similarity to an approved Q&A is ≥ threshold, return the stored answer instantly; otherwise compute, and queue it for human approval.
   - Cache entries are tagged by zone and expire when the zone level or the incident changes. **Never serve a stale evacuation answer.**
   - The "we already know about the fire near X" greeting is itself a cached, per-zone announcement. Duplicate callers never reach the LLM for that part.
2. **Function-response caching:** shelter list, zone level and known incidents are cached in memory with short TTLs (30–60 s). Functions return in milliseconds, which keeps the agent's latency low during floods.
3. **Prompt structure that's cache-friendly and cheap:**
   - Keep each agent's system prompt **static**: rules, tone, tools. Per-call facts come only through `{{dynamic_variables}}` and function results.
   - Short prompts also avoid Retell's long-prompt token surcharge.
4. **Our own backend LLM calls** (topic naming, FAQ drafting, case summaries, digest). If we call Claude directly, use **Anthropic prompt caching** (`cache_control` on the static system prompt + KB context). Repeated calls then read the prefix from cache at a fraction of the input price and with lower latency.
5. **Measure it:** cache hit rate, median function latency and "answered without a human" rate go on the dashboard. That's a nice flood-drill metric.

## 9. Capacity and rate limits (verified: docs.retellai.com/deploy/concurrency)

- **There is no cap on total calls or callers.** Agents handle unlimited calls; the only limit is **calls at the same time**.
- **Concurrency:** **20 concurrent calls** per workspace by default (pay-as-you-go). Raise it in Settings → Limits, billed monthly (~$8 per slot per month on the pricing page).
- **Burst mode (turn on before the drills):**
  - Calls can go above the limit up to **min(3× limit, limit + 300)**. With 20, that's **60 concurrent**.
  - Calls that start in burst carry **+$0.10/min** for their whole duration. Cheap for a 20-minute drill; no monthly commitment.
  - Needs the Admin role.
- **When full (no burst):**
  - **Inbound:** Retell **queues the caller ~40 s**. If a slot opens, the call connects.
  - If no slot opens, it **transfers to the number's fallback number**. If there's no fallback, the call ends with `concurrency_limit_reached`.
  - **→ Set a fallback number:** a Twilio number playing "we're receiving many calls, leave your name, location and what's happening" (voicemail → transcribed → our queue → callback). That's our overflow design, using a built-in feature.
  - **Outbound:** rejected when full, unless burst is on. Our scheduler must retry on rejection, and `reserved_inbound_concurrency` (e.g. 8 of 20) keeps outbound from starving inbound.
- **Calls per second:** set per telephony provider (Twilio/Telnyx) under Adjust Limit. No published default; batch calls start only as slots free up.
- **API rate limits:** none published. Excess gets "Account rate limited". Poll `get-concurrency` every ~2 s at most.
- **Other limits:**
  - max call length 1 h by default (2 h max)
  - prompt max 32,768 tokens; **prompts over 4,000 tokens cost extra**, so keep prompts short
- **Throughput math:** with ~1.5 min average calls,
  - 20 concurrent ≈ **13 calls/min ≈ 800/hour**
  - burst 60 ≈ **40 calls/min ≈ 2,400/hour**
  - This covers a 100-person room flood.
- **Account-level brakes:**
  - **KYC** is required for outbound.
  - New numbers with many unanswered outbound calls get labelled **spam**. Only call consenting numbers.
- **Budget:** 100 calls × 1.5 min × ~$0.10 ≈ $15; in burst ≈ $30.
