# Pre-deploy test round (Sat Oct 17, before Railway deploy)

Tested on `cs1/demo-deploy` (main + agents PR #2 + backend PR #4) without a public URL.

| Check | Result |
|---|---|
| Retell config audit (all 8 live agents): every `{{variable}}` has a default, 9 agent hand-offs resolve, tool URLs match functions, no hard-coded transfer numbers, KBs exist, PII scrubbing on | ✅ no problems |
| Agent safety suite (playground, 14 cases, 4 languages) | ✅ 13/14 · known flake: "can someone fix my heater" sometimes goes to a person instead of the help desk (not a safety issue) |
| Backend unit tests on the merged branch | ✅ 27/27 |
| End-to-end call simulation (signed Retell-shaped requests to the merged backend, 6 calls) | ✅ 11/11 |
| Dashboard `/ops` + `/supporter` in a real browser after the calls | ✅ renders, no page errors |

End-to-end checks: inbound webhook returns string variables · smoke + wheelchair → P1, warm transfer to the matched teammate · 2nd/3rd caller hear "we already have N reports" · teammate busy until the call ends, then free · P0 → supervisor, 911 instruction · help-desk form → case code → status by code + last 4 · real nearest place (Bethune library, Expo Park) · unknown question logged, not guessed.

## Found, to fix in the iteration round
1. **Help-desk hand-off flake** (agent prompt): "can someone fix X" → sometimes `route_to_human` instead of `swap_to_services`.
2. **Duplicate P0 rows** (backend): `flag_urgent` creates its own report; the same call's later `submit_report` creates another. Link them by `call_id`.
3. **Dashboard shows fictional demo responders** (Alex, Sam, Maya) alongside real teammates, and says "of 3 team members". Hide the seed responders when `DIZA_RESPONDERS` is set.
4. **"Simulation mode" banner** shows even when connected to Retell; should reflect drill vs live.
5. **Not on the dashboard yet:** help-desk cases, alerts (draft → approve → tally), knowledge gaps. They're in the API only.

## Still needs a real deploy to test
Real phone calls: audio, transfers (phone only), keypad, voicemail, outbound alert calls, latency.
