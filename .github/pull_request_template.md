## Task
TASK-XX — <one line>

## What changed
<the minimal description; the diff is the detail>

## Verification
Paste the actual command and its actual output. Not a summary.

```
> pytest -q
...
```

- [ ] `pytest -q` passes
- [ ] `ruff check .` and `ruff format --check .` clean
- [ ] `LOOP_STATE.md` updated (status + commit)
- [ ] `memory/` updated if anything was learned (FACTS / DECISIONS / FAILURES / EXPERIMENTS)
- [ ] No weights, secrets, or `.env` in the diff
- [ ] Diff touches only this task
- [ ] This PR is one task. Process rules born mid-task ride their own `fix/` branch
- [ ] If `SPECS.md` changed: is it a criterion/gate/signature/target? Then there is a
      `## SPECS CHANGED` section above with old text, new text, evidence, and the ADR

## Metric delta (if applicable)
| Metric | Before | After |
| :-- | :-- | :-- |
| | | |
