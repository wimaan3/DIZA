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
5. **Before pushing:** `git pull --rebase` (or fetch and merge). Never force-push a branch you didn't create. Each agent pushes to its own branch unless the team says otherwise.
6. **No secrets.** Never commit API keys, `.env` files, or personal phone numbers.
7. **Code** goes in top-level app folders (`backend/`, `dashboard/`, `agents/`, `analysis/`, `sim/`) once the team agrees on the structure. Until then, put it in your session folder.
8. **Synthesis:** one designated session reads every `sessions/*/SESSION_CONTEXT.md` and writes the merged plan to `docs/` (e.g. `docs/MASTER_PLAN.md`), citing which session each decision came from.
