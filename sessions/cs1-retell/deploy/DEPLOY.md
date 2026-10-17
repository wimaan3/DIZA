# Deploying the DIZA backend + dashboard

Once PRs #2, #3 (with #4 merged into it) and this one are on `main`, deploy **`main`**. Until then, `cs1/demo-deploy` is a preview branch with the same content. Files: a Dockerfile
(`sessions/cs1-retell/deploy/Dockerfile`) and `railway.json`. One container serves:
- the Retell endpoints (`/retell/inbound`, `/retell/webhook`, `/retell/fn/*`)
- the supervisor console `/ops` and supporter inbox `/supporter`
- the API (`/api/*`, protected by `OPS_API_TOKEN`)

Verified locally in the same layout: dashboard served, `agents/contract_check.py` 0 problems, place lookup reads the real resources file.

## Which host?
| Option | Cost | Stable URL | Laptop must stay on | Verdict |
|---|---|---|---|---|
| **Railway** (Docker from GitHub) | ~$5 credit | ✅ `*.up.railway.app` | No | **Use for drills + demo** |
| Fly.io | ~free–$5 | ✅ | No | Good, but CLI setup takes longer |
| ngrok static domain | Free | ✅ `*.ngrok-free.app` | Yes | Fine for dev/backup |
| Tailscale Funnel | Free | ✅ `*.ts.net` | Yes | Alternative to ngrok |
| Cloudflare quick tunnel | Free, no account | ❌ changes every restart | Yes | Only for a one-off test |
| Render free | Free | ✅ | No | ❌ sleeps; ~1 min wake > Retell's 10 s webhook timeout |
| Vercel | Free | ✅ | No | ❌ serverless: no background worker, no persistent SQLite |
| Supabase | Free | — | — | Database only; the backend uses SQLite, adapter not built |

## Railway (about 10 minutes)
1. railway.com → sign in with GitHub → **New Project → Deploy from GitHub repo** → `wimaan3/DIZA` → branch **`main`** (or `cs1/demo-deploy` before the PRs merge). It finds `railway.json` and builds the Dockerfile.
2. Service → **Variables** (Raw Editor), paste and fill in:
   ```
   RETELL_API_KEY=<the API key marked "Webhook Key" in Retell>
   OPS_API_TOKEN=<long random string; the console asks for it>
   RETELL_FROM_NUMBER=+19789153497
   RETELL_ALERT_AGENT_ID=<alert agent_id from agents/retell.ids.json>
   RETELL_ALERT_AGENT_VERSION=latest
   DRILL_MODE=true
   DIZA_RESPONDERS=[{"id":"t1","name":"<name>","phone":"+1...","skills":"evac_logistics,medical,lang:en"}]
   ALERT_CONTACTS_CSV=name,phone,language\n<name>,+1...,en
   ```
   Personal phone numbers live only here, never in git.
3. Service → **Settings → Volumes** → add a volume mounted at **`/data`** (keeps reports across restarts).
4. **Settings → Networking → Generate Domain**. Open `https://<domain>/ops`, enter `OPS_API_TOKEN` when asked.
5. Send the domain to CS#1, who runs:
   ```
   PUBLIC_BASE_URL=https://<domain> STAGING_CRISIS_LINE_NUMBER=+1... python agents/push.py --env staging
   ```
   That points every agent's functions and webhook, and the phone number's inbound webhook, at the deploy.

## ngrok instead (laptop)
```
git checkout cs1/demo-deploy && cd sessions/cs2-backend/mvp
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
(cd dashboard && npm ci && npm run build)
export RETELL_API_KEY=... OPS_API_TOKEN=... DIZA_RESPONDERS='[...]'
.venv/bin/uvicorn backend.app.main:app --port 8000
ngrok http --url=<your-static-domain>.ngrok-free.app 8000     # second terminal
```

## Security notes
- Always set `OPS_API_TOKEN` on a public deploy: without it anyone with the URL can read reports and approve alerts.
- `RETELL_API_KEY` must be the webhook-badged key or every Retell request gets 401.
- Keep `DRILL_MODE=true` all weekend (drill alerts only, no resource transfers to real lines).
