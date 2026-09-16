# FAILURES.md — Dead ends and why they died

**APPEND ONLY.** Anything on this list is not retried without a stated new reason.

Format:
### F-NNN — <what was tried> (TASK-NN, YYYY-MM-DD)
- **Symptom:** what went wrong
- **Root cause:** why, if known
- **Verdict:** abandoned / superseded by <what>

---

(empty)

### F-001 — TD training with 256 games per batched update (TASK-12, 2026-09-17)
- **Symptom:** 1000-game smoke, seed 1: training mean stuck at 1,500–2,200 (batch 64 reached 12,900 on the same games budget; batch 16 reached 11,785 and was no faster).
- **Root cause:** every game in a batch reads the same weights and all updates land at once; with 256 near-identical early-game boards the summed update on shared entries is ~256x one step and overshoots.
- **Verdict:** abandoned; batch 64 is the default. Re-test only alongside a smaller alpha.
