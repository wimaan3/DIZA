# Session context: ops-token-login

- **Session:** Codex local portal login repair.
- **Branch:** `codex/ops-token-login`.
- **Scope:** Fix operator token entry and connection feedback in the running local dashboard.

## Files in this folder

| File | Contents |
|---|---|
| `dashboard-auth.patch` | Dashboard change applied to a temporary build copy of the CS#2 MVP. |
| `preview_dashboard.py` | Build the patch and replace the static assets in an existing temporary preview. |
| `check_login_e2e.py` | Browser checks against the real token-protected backend. |

## Decisions made

- Keep all repository writes in this session folder, following the root `AGENTS.md` isolation rule.
- Apply the patch to a temporary build copy; preserve the CS#2 source folder and the running backend, database, and tunnel.
- Submit credentials through an explicit Connect form rather than sending a request for each edit.
- Accept the token value or a copied `OPS_API_TOKEN=...` line, including surrounding quotes and whitespace.
- Keep connection failures separate from action errors and cancel obsolete polling requests when credentials change.
- Describe phone and simulated reports accurately in the drill banner and calculate the responder count from current data.

## Key facts verified

- The running backend returns HTTP 200 for the token in the root `.env`, and HTTP 401 for missing or incorrect credentials.
- Before the fix, an E2E browser test showed 13 reports after successful authentication while the login error remained visible.
- Before the fix, pasting the complete environment assignment returned HTTP 401 and showed no reports.
- Sources: `sessions/cs2-backend/mvp/dashboard/src/main.jsx`, `sessions/cs2-backend/mvp/backend/app/main.py`, and local HTTP/browser reproduction.
- Credentials, phone numbers, and environment files are excluded from this session's artifacts.
- The production dashboard build passed and the corrected assets are running in the existing local preview.
- All five E2E scenarios passed: token value, copied environment assignment, quoted assignment with spaces, incorrect-token recovery with Enter on mobile, and an initial unauthorized response delayed until after a successful login.
- Valid credentials remain usable after reload, invalid credentials still receive HTTP 401, and the authenticated dashboard has no browser errors.
- Desktop and mobile screenshots were inspected; the mobile layout has no horizontal overflow.

## Reproduce and validate

Run with the backend Python dependencies, Playwright, and an installed Chromium browser.
The environment loader reads credentials from the ignored root `.env`.
These checks read the existing report queue and do not reset demo data or place phone calls.

```sh
python sessions/ops-token-login/preview_dashboard.py --preview-root /path/to/existing-preview
python sessions/ops-token-login/check_login_e2e.py --base-url http://127.0.0.1:8000
```

The build helper copies the original dashboard into a temporary directory before applying the patch.
Existing assets stay available for open tabs, and the new HTML is replaced atomically after its assets are copied.
It does not restart the backend or tunnel.

After review, CS#2 can apply the same source change from the repository root:

```sh
git apply --directory=sessions/cs2-backend/mvp/dashboard sessions/ops-token-login/dashboard-auth.patch
```

## Open questions

- CS#2 should review the patch before integrating it into the shared MVP source or moving the dashboard into a top-level app folder.

## Not done yet

- This repair does not address the previously reported phone routing, case visibility, or callback scheduling issues.
- Integration into the shared dashboard source remains for the CS#2 review; the running temporary preview already contains the fix.
