# DIZA hotel service demo

The active hotel demo runs at http://127.0.0.1:18772/hotel on branch `ds/hotel-service-demo`.
It models Harbor House, a fictional hotel with 24 rooms, synthetic staff, and five sample requests.
The guest assistant provides a bounded set of scenario answers and records confirmed requests for staff.
This is a local interactive text demo; no telephone calls, provider sessions, or staff notifications are sent.

## Start the demo

From the repository root:

```sh
python3 -m venv sessions/ds-analytics/.venv
sessions/ds-analytics/.venv/bin/python -m pip install -e 'sessions/ds-analytics[hotel]'
sessions/ds-analytics/.venv/bin/python sessions/ds-analytics/scripts/serve_hotel.py --demo
```

Open `/hotel`; `/building` and `/ops` also serve this hotel workspace in the isolated demo server.
The default front-desk token is `hotel-demo-local`, which the synthetic demo UI uses automatically.
Set `HOTEL_DEMO_TOKEN` before startup to use a different token; the UI then asks for it.
This shared token and the open synthetic room selector are demo controls, not real guest identity verification or production staff accounts.
The server binds to localhost and never reads the repository `.env` or starts the original emergency application's workers.

State persists in ignored `artifacts/hotel-demo.sqlite3`.
Restarting the process preserves conversations, private guest session credentials, requests, ownership, and history.
`--demo` seeds the five sample requests only when no tickets exist; it does not reset existing requests.
Use `--ephemeral --demo` for a disposable database or `--port PORT` for another local port.

## Try the guest-to-staff workflow

1. Keep demo room 402 selected and choose **Wi-Fi help**.
   The assistant provides the fictional hotel's scenario instructions, and the answered-question count increases without creating a staff task.
2. Choose **Extra towels** or **AC not cooling**.
   The assistant saves the conversation and reads back a proposed request.
3. Review the description and optionally authorize entry while away, then choose **Confirm request**.
   A new task appears as awaiting an owner; the agent does not invent an arrival or completion time.
4. Open the request in the front-desk queue and choose the responsible staff member.
   Select **Accept request**, **Start work**, and **Record completed** in that order.
5. Watch the saved guest request show the staff owner's name and updated status.
   Add a handover note to preserve what happened without changing the original completion timestamp.

Choose **Español** and another room to try the same request flow in Spanish.
Room tiles filter open requests, and same-category reports on the same floor are linked for staff review.
Each request remains a distinct record; the demo does not claim that a shared floor proves a shared cause.

## Behavior and limits

- Approved scenario answers cover Wi-Fi access, checkout, and breakfast.
- A failed answer or request for a person becomes a front-desk request for the guest to confirm.
- Housekeeping, AC, lighting, water leaks, noise, and room-access concerns route to the appropriate demo team.
- Room-entry permission starts false and is independent of request confirmation.
- Requests are persisted before a success response, with idempotency receipts for retries and revision checks for competing updates.
- A changed readback cannot be confirmed against an older revision.
- Guests see only their own conversation and request statuses; staff APIs require the demo token.
- Staff acceptance, work started, completion, and notes are separate recorded actions.
- A small conservative safety-word check flags possible emergencies for front-desk review and states that this demo cannot place calls or send help.
- The safety-word check is not a validated emergency classifier and does not provide a 911 integration.
- Guest text that has not reached the server remains in the composer for retry; this demo does not claim offline automatic submission.
- The scenario answers and room selector are synthetic; they are not connected to a real hotel's network, property system, or service team.

Retell telephone or browser voice, individual staff accounts, actual guest identity, and hotel-system integration remain separate work.
The emergency-overflow product requirements remain in [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md).

## Verification

```sh
sessions/ds-analytics/.venv/bin/python -m unittest discover \
  -s sessions/ds-analytics/tests_hotel -v
npm --prefix sessions/ds-analytics/hotel_client ci
npm --prefix sessions/ds-analytics/hotel_client run check
```

From `sessions/ds-analytics/hotel_client`, install the test browser with `PLAYWRIGHT_BROWSERS_PATH=../artifacts/playwright npx playwright install chromium`.
Run `PLAYWRIGHT_BROWSERS_PATH=../artifacts/playwright npm test` from that same folder.
The browser suite launches a separate disposable server and covers the guest-to-staff path, completion history, Spanish mobile layout, saved conversation reload, and a lost successful confirmation response.
Screenshots are written to ignored `artifacts/hotel-desktop.png` and `artifacts/hotel-mobile.png`.
