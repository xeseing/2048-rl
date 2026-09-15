# PROMPTS.md — Copy-paste prompts for Claude Code

---

## PROMPT 0 — Verify GitHub access (paste first, before anything else)

```
Before we start the project, verify your GitHub access and set up the repo.

1. Run `gh auth status` and `git config --get user.name && git config --get user.email`.
   Show me the output. If gh is not authenticated, stop and tell me exactly what to run
   — do not work around it and do not ask me for a token.
2. Run `git status`. If this is not a git repo yet, run:
   git init -b main
3. Create the remote: gh repo create xeseing/2048-rl --public --source=. --remote=origin
4. Confirm the scaffold files are present: CLAUDE.md, SPECS.md, LOOP_STATE.md,
   GIT_WORKFLOW.md, PROMPTS.md, CHANGELOG.md, .gitignore, .github/, memory/.
5. Commit the scaffold on a branch `task/00-repo-setup`, open a PR, and show me the
   `gh pr view --web` URL. Do not merge it yourself.

Then stop.
```

---

## PROMPT 1 — Kickoff (paste after PROMPT 0 succeeds)

```
# ROLE & OPERATING MODE: AUTONOMOUS VERIFICATION-DRIVEN AGENT

You are an autonomous senior specialist operating in a strict, evaluation-driven
feedback loop. Do NOT perform speculative, unverified, or bulk un-tested actions in a
single step.

### PROJECT GOAL
Build a 4x4 2048 game engine and an agent that learns to play it from self-play with no
human demonstrations and no hardcoded strategy inside the learner. Primary learner: an
N-tuple value network trained with TD(0) on afterstates. Secondary: a Double DQN
convnet, built for honest comparison. Full contract is in SPECS.md — read it, do not
re-invent it.

### CONSTRAINTS & ACCEPTANCE CRITERIA
1. `make test` and `make lint` pass. Every task is gated by a command that actually runs.
2. `make diff-test` reports zero divergences between the naive oracle engine and the
   bitboard engine across 100,000 random games.
3. `make bench` reports at least 200,000 moves/sec.
4. The learner receives only the environment's merge score as reward. No reward
   shaping, no heuristic features, no strategy hints. Violating this invalidates the
   project.
5. Every stochastic component is seeded and every reported result is reproducible from
   its seed.
6. N-tuple Stage 1 clears 15,000 mean score and a 50% 2048 rate over 1000 held-out
   seeds before Stage 2 begins.
7. Version control discipline per GIT_WORKFLOW.md: one branch per task, PR with green
   CI before merge, `Verified:` footer on every commit, never force-push `main`, never
   commit weights or secrets.
8. Ships as an installable app: `pip install .` then `2048rl play` works in a clean
   virtualenv.

### THE 4-PHASE ITERATION PROTOCOL

PHASE 0: DISCOVERY & STATE INITIALIZATION
1. Inspect the workspace, dependencies, and existing assets.
2. Read CLAUDE.md, then LOOP_STATE.md, memory/FACTS.md, memory/FAILURES.md.
3. Establish the verification harness before writing feature code.

PHASE 1: AUDIT & TASK BREAKDOWN
1. The roadmap already exists in LOOP_STATE.md. Audit it against the actual workspace.
2. Report any task that is missing, mis-ordered, or already satisfied. Do not silently
   rewrite it.
3. Output the audit and stop for my approval before touching TASK-01.

PHASE 2: ATOMIC EXECUTION & VERIFICATION LOOP (STRICT GATE)
For each sub-task in dependency order:
1. Plan & Test: write the failing test / define the measurable criterion first.
2. Execute: the minimal change that satisfies it.
3. Verify: run the command. Paste the real output.
   - FAILS: capture the log, diagnose the root cause, self-correct, re-test (max 4).
   - PASSES: mark [DONE] in LOOP_STATE.md with the PR number, update memory per the
     write triggers in CLAUDE.md, commit on the task branch, open the PR, wait for CI
     with `gh pr checks --watch`, show me the diff summary, and wait for my go-ahead
     before merging.

PHASE 3: POLISH & HARDENING
1. Edge-case stress tests, long-run stability, performance.
2. End-to-end integration checks.
3. Write RESULTS.md and update LOOP_STATE.md with final metrics.

### OPERATIONAL GUARDRAILS
- Never mark a task complete without running objective verification and showing output.
- Circuit breaker: 4 consecutive failures on one task -> halt, write memory/FAILURES.md,
  set the task [!] BLOCKED, ask me.
- Atomic commits: one task per branch, Conventional Commit subject, `Task:` and
  `Verified:` footers. Never commit to `main` directly; never force-push `main`.
- Follow the memory protocol in CLAUDE.md exactly. Memory records evidence, not plans.

Begin with PHASE 0, then PHASE 1, then stop for approval.
```

---

## PROMPT 1B — Release checkpoint (paste when a milestone task goes green)

```
We just cleared a milestone. Cut the release.

1. Confirm `main` is green: `gh run list --branch main --limit 1`.
2. Update CHANGELOG.md with a section for this version. Every bullet must contain a
   measured number, not an adjective.
3. Tag with the numbers in the message, e.g.
   git tag -a v0.3.0 -m "N-tuple Stage 1: mean 18,420, 2048 rate 63%"
4. Push the tag and run `gh release create <tag> --generate-notes`.
5. If this milestone produced weights, upload them as release assets and record their
   SHA-256 in the matching runs/<id>/config.json.
6. Append the EXPERIMENTS.md row if you have not already.

Show me the release URL.
```

---

## PROMPT 2 — Resume (paste at the start of every later session)

```
Resume the loop.

1. Read CLAUDE.md, LOOP_STATE.md, memory/FACTS.md, memory/FAILURES.md.
2. State in one line: which task is active and its attempt count.
3. Re-run the verification command for the last task marked [DONE] to confirm the repo
   is actually green before building on it.
4. Continue PHASE 2 from the active task. Same gates, same circuit breaker.

Do not start new work until step 3 passes.
```

---

## PROMPT 3 — Circuit breaker tripped

```
You have hit 4 attempts on this task. Stop coding.

Give me:
1. The exact failing command and its full output.
2. Your three best hypotheses for the root cause, ranked, with what evidence would
   distinguish them.
3. The smallest experiment that would separate hypothesis 1 from hypothesis 2.
4. A proposal to either shrink the task's scope or change the approach.

Then append the entry to memory/FAILURES.md and wait for me.
```

---

## PROMPT 4 — Before any long training run

```
Before starting the full run:
1. Confirm `make diff-test` and `make bench` are green — paste the output.
2. Run the identical pipeline for 1,000 games. Show me: mean score, max tile, wall
   time, RAM used, and a checkpoint written and reloaded successfully.
3. Extrapolate the full run's wall time and RAM from that smoke run.
4. Confirm checkpoint/resume works by killing and restarting from a checkpoint.

Only then start the full run, and append the EXPERIMENTS.md row when it ends —
including if it crashes or I kill it.
```

---

## PROMPT 5 — Track A vs Track B write-up (TASK-18)

```
Write RESULTS.md. All six agents, evaluated on the same 1000 held-out seeds.

Include: mean, median, and max score; max-tile histogram; 2048/4096/8192 rates; decision
time per move; training wall time.

Then answer, in prose and with evidence from your own numbers: why does a sparse linear
n-tuple network beat a convolutional DQN on this task? Address sample efficiency,
afterstate valuation, and how well each representation captures the tile-adjacency
structure that matters in 2048.

Do not flatter either track. If Track B lost badly, say so and explain it.
```

---

## Notes on running this well

- **Approve the Phase 1 audit yourself.** It takes two minutes and catches a
  misunderstanding that would otherwise cost you ten tasks.
- **Commit after every green task.** The loop protocol assumes you can roll back to the
  last verified state; without commits that is not true.
- **When Claude says "this should work", ask for the command output.** That sentence is
  the failure mode this whole protocol exists to prevent.
- **Run `/install-github-app` once, early.** It puts Claude inside GitHub so you can
  tag `@claude` on a PR to review the diff. Reviewing a PR is a different and better
  check than reviewing the chat transcript that produced it.
- **TASK-12 is the moment the project becomes real.** Everything before it is
  infrastructure. Do not let the infrastructure sprawl — if the agent proposes extra
  polish before TASK-12, defer it.
