# Rules for agents pushing to this repo

Several AI agent sessions push here. Keep their outputs separate so they don't overwrite each other, and so they can be synthesized later.

1. **Write only inside your own folder:** `sessions/<short-session-name>/`
   - Name it after the person or purpose, e.g. `sessions/ds-analytics/`, `sessions/cs1-retell/`.
   - Never edit or delete another session's folder.
2. **Every session folder has a `SESSION_CONTEXT.md`** with:
   - who / what session, and the branch
   - files in the folder
   - decisions made
   - key facts verified (with sources)
   - open questions
   - what's not done
   - Use `sessions/planning-claude/SESSION_CONTEXT.md` as the template.
3. **`sources/` is official hackathon material only.** Add new files; don't edit existing ones.
4. **Shared root files (`README.md`, `AGENTS.md`):** only append small changes. Don't restructure them.
5. **Branches + PRs (team decision, updated):**
   - **`main` is the shared trunk.** Everyone contributes to it **only through pull requests**: app code, configs, and your `sessions/<name>/` docs.
   - Work on a short-lived branch (`cs1/…`, `cs2/…`, `ds/…`, `bio/…`, or your agent's branch), then open a PR to `main`.
   - **Review:** code PRs need one teammate's review (backend/dashboard → CS#2, agents → CS#1, config/analysis → DS, docs/deliverables → biomech). Docs-only PRs to your own `sessions/` folder can be self-merged.
   - Keep PRs small. `main` must always run and demo.
   - Before pushing: `git pull --rebase origin main` on your branch. Never force-push someone else's branch, and never push directly to `main`.
6. **No secrets.** Never commit API keys, `.env` files, or personal phone numbers.
7. **Code** goes in top-level app folders (`backend/`, `dashboard/`, `agents/`, `analysis/`, `sim/`) once the team agrees on the structure. Until then, put it in your session folder.
8. **Synthesis:** one designated session reads every `sessions/*/SESSION_CONTEXT.md` and writes the merged plan to `docs/` (e.g. `docs/MASTER_PLAN.md`), citing which session each decision came from.
