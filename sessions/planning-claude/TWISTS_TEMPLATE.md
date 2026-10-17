# TWISTS.md template (copy to the app repo root as TWISTS.md)

Judged for "Adapting to twists" and **Best Shift Adapter**: *"what changed, why, and proof it works. The best adapters change the build, not just the slides."* Respond **within 6 hours** of each twist (11:30 PM → 5:30 AM · 4:30 AM → 10:30 AM · 7:00 AM → 1:00 PM).

---

## Twist N: <title> (dropped <time>, responded <time>)

**The twist (verbatim):**
> ...

**What it means for our seat** (overnight call-line supervisor), in one sentence:

**What we changed in the build:**
| Change | File / commit | Why |
|---|---|---|
| e.g. added "network degraded" mode: keypad-only intake, 60-second calls, SMS-first callbacks | `agents/inbound.llm.json` @ `abc123`, `backend/modes.py` @ `def456` | callers on congested networks drop long calls |

**What we deliberately did NOT change, and why:**

**Proof it works:**
- Test case(s) added: `evals/cases/twistN_*.yaml`. Pass rate before → after.
- 20-second clip / screenshot: `media/twistN.mp4`
- Metric moved: e.g. median call length 2:10 → 0:55 in degraded mode

**Which rung this touches** (watch / ask / slow / hold / hand to a person):
