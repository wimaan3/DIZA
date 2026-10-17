# Session context: relayla

- **Session:** ChatGPT / Codex implementation contribution for the user's Resilience Comms hackathon project.
- **Branch:** `codex/relayla-diza-integration`.
- **Requested scope:** Create a separate folder in `wimaan3/DIZA`, integrate the communication-resilience idea with the existing DIZA plans, and push it to GitHub.
- **Implementation:** DIZA / RelayLA, a runnable supervisor follow-through module. All changes are confined to `sessions/relayla/`. This is not the designated synthesis session and does not replace the master plan.

## Files in this folder

| File | Purpose |
|---|---|
| `README.md` | Local startup, implemented scope, optional Retell setup, integration entry point, and verification. |
| `DEMO.md` | Five-minute rehearsal with explicit failure cases and English/Spanish sample responses. |
| `INTEGRATION.md` | Mapping to DIZA's intake, triage, responders, Ops Wall, service sandbox, and proposed Supabase structure. |
| `API_CONTRACT.md` | Routes, action payloads, state schema, and shared invariants. |
| `requirements.txt`, `.env.example`, `run.py` | Pinned direct Python dependencies, environment template, and loopback-first runner. |
| `relayla/engine.py` | SQLite case store, notice history, acknowledgments, handoffs, callbacks, audit trail, and idempotency. |
| `relayla/api.py`, `relayla/settings.py` | FastAPI endpoints, operator access, configured provider boundary, and web-call token creation. |
| `relayla/retell_adapter.py` | DIZA-aligned tools, durable call bindings, normalized retry plans, and ordered call lifecycle handling. |
| `relayla/static/` | Responsive supervisor dashboard, local intake outbox, and optional browser voice client. |
| `retell/prompt.md`, `retell/tools.json` | Agent prompt and custom-function templates; require account-specific configuration. |
| `tests/test_engine.py`, `tests/test_api.py` | Synthetic domain, HTTP, and provider-envelope regression checks. |
| `VERIFICATION.md`, `preview.png` | Final observed checks and a screenshot of the running synthetic dashboard. |

## Decisions made

1. Keep **DIZA** as the product. **RelayLA** identifies this session and its follow-through module. The existing repository was planning-only when inspected, so the contribution runs independently and exposes integration seams.
2. Match the actual call-line supervisor prompt: urgency, accountable human handoffs, and what remains open after an unanswered contact. Versioned bilingual acknowledgment supports that queue.
3. Use FastAPI plus SQLite for a dependency-light local demo. Preserve transactional contracts when DIZA promotes storage to Supabase/Postgres. Use one worker for this standalone provider lifecycle implementation.
4. Accept upstream P0–P3 severity and its provenance. Preserve or escalate it; do not add medical inference, clinical claims, or automatic emergency dispatch.
5. Keep resident contact, current instruction confirmation, human assignment, explicit acceptance, and completion as independent evidence.
6. Make retries idempotent and notice revisions compare the expected current version. Calls, acknowledgments, and histories retain stable case identity across restart.
7. Expose only six bounded Retell functions. Notice publication, zone declaration, acceptance, and completion remain operator actions. Do not equate a queued callback or human request with an actual outbound operation.
8. The core demo works without credentials. The optional browser voice path uses server-created short-lived connection tokens, raw-body signature verification, an agent allowlist, and per-call case binding.
9. Contribute the follow-through panel and acceptance record to the future Ops Wall/intake sandbox. Maps, clustering, transcripts, generic forms, booking, provider concurrency, analytics scoring, and replay remain separate team work.
10. Preserve the other session's files. Follow the repository's own-branch rule; session documentation stays on this branch and any eventual app promotion requires the team's normal small reviewed PR.

## Key facts verified and sources

- The official track asks an overnight line supervisor which callers need a person now, what cannot be automated, and what happens when someone does not answer: [participant material, section 03](../../sources/participant-hub-gdoc.txt).
- Existing team choices and proposed boundaries were read from [planning context](../planning-claude/SESSION_CONTEXT.md), [workflow](../planning-claude/WORKFLOW.md), [Ops Wall](../planning-claude/OPS_WALL.md), and the other planning files linked in `INTEGRATION.md`. Their proposed vendor, legal, and performance claims are not represented as measurements of this implementation.
- Retell documents a server-created browser call followed by a browser connection: [web call deployment](https://docs.retellai.com/deploy/web-call), [create web call reference](https://docs.retellai.com/api-references/create-web-call).
- Retell documents provider lifecycle webhooks and signature verification: [webhook overview](https://docs.retellai.com/features/webhook-overview). The installed `retell-sdk==6.2.7` was inspected to confirm `retell.lib.webhook_auth.verify` and the v3 web-call response fields.
- The published browser package `retell-client-js-sdk@3.0.2` was inspected for `RetellClient`, a custom `fetch` callback, connection lifecycle, and token handling: [provider browser SDK](https://github.com/RetellAI/retell-client-js-sdk).

## Verification

- Automated checks run against temporary synthetic databases. They cover domain invariants and signed HTTP envelopes without any live provider network request.
- Installed and exercised with Python 3.12, FastAPI 0.143.3, uvicorn 0.54.0, httpx 0.28.1, and Retell Python SDK 6.2.7.
- **42 automated tests passed.** Desktop/mobile browser workflow checks also passed with zero JavaScript page errors; details are in [VERIFICATION.md](VERIFICATION.md). Use the current test command in `README.md` to reproduce.

## Open questions

- Which shared DIZA app branch and final top-level package layout should receive the reviewed code promotion?
- Which published English/Spanish agents, HTTPS deployment, and provider account will the team use for the live run?
- Which real responder roles, skill vocabulary, and language fallback policy should replace the synthetic roster?
- Which upstream service owns incident verification, approved notice publication, and triage provenance in the merged product?

## Not done

- No live Retell account, telephone/SMS transport, real transfer, emergency notification, booking, or external organizational integration was exercised.
- No live clinical triage, corroboration, location map, parallel-call capacity measurement, outage benchmark, language-accuracy evaluation, or real-world safety effectiveness is claimed.
- No root planning documents or another session's files were edited; no merge to `main` is part of this contribution.
- Provider webhook ordering is guarded in one application process and persisted across restarts. A distributed implementation needs a shared transactional lifecycle coordinator.
- This local demo has an operator token, not a production identity/role system. Local drafts live in the current browser. A fresh offline page load, offline voice, and device-to-device transport are outside scope.
