# GIT_WORKFLOW.md — Version control & GitHub

Repo: `github.com/xeseing/2048-rl` (create it in step 2 below)

---

## Part 1 — Connecting Claude Code to your GitHub

There are **two separate integrations**. You want both, and they do different things.

### 1A. Local git + GitHub CLI (this is the important one)

Claude Code runs on your machine and uses your shell. It has no GitHub account of its
own — it pushes as *you*. So you authenticate once, locally, and every `git` and `gh`
command Claude Code runs inherits that.

```bash
# install GitHub CLI
# Windows:  winget install --id GitHub.cli
# macOS:    brew install gh
# Linux:    sudo apt install gh

gh auth login
# choose: GitHub.com -> HTTPS -> "Login with a web browser" -> paste the code
# make sure you say YES to "Authenticate Git with your GitHub credentials"

gh auth status          # should show your account and the token scopes
```

Then set your identity so commits are attributed correctly:

```bash
git config --global user.name  "Himanil Datyal"
git config --global user.email "your-github-email@example.com"
```

> Use the email that GitHub has on file (or your `@users.noreply.github.com` address
> from GitHub → Settings → Emails), or your commits won't link to your profile and the
> contribution graph stays blank.

Verify Claude Code can actually reach GitHub — ask it to run `gh auth status` and
`gh repo list` in its first session. If those work, everything else (`gh repo create`,
`gh pr create`, `gh release upload`) works too.

### 1B. Create the repo

```bash
cd 2048-rl
git init -b main
gh repo create xeseing/2048-rl --public --source=. --remote=origin --push
```

Or let Claude Code do it as TASK-00.

### 1C. The Claude GitHub App (optional, but worth it)

This is the second integration: it puts Claude *inside* GitHub, so you can tag
`@claude` on an issue or PR and it responds there — reviewing your own PRs, answering
questions on issues, or implementing changes.

From inside Claude Code, run:

```
/install-github-app
```

It installs the GitHub App, adds your auth secret, and prepares the workflow PR.
Requirements: you must be repo admin (you are, it's yours), and it only works with
github.com repositories. If the command fails, install
https://github.com/apps/claude manually, add `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN` to repo secrets, and copy the workflow yourself.

Docs: https://code.claude.com/docs/en/github-actions

> Note: this is separate from the CI in `.github/workflows/ci.yml`. CI runs your tests.
> The Claude App answers `@claude` mentions. Keep both.

### 1D. What Claude Code must never do

Put this in your head, not just in CLAUDE.md:

- Never `git push --force` to `main`.
- Never commit `.env`, tokens, or API keys. The `.gitignore` here covers the obvious
  ones; CI runs a secret scan anyway.
- Never commit trained weights (268 MB). They go to GitHub Releases as assets.
- Never merge its own PR without you looking at the diff.

---

## Part 2 — Branching model

**Trunk-based, one short-lived branch per task.** This maps 1:1 onto the loop
protocol's atomic-commit rule, which is why it's the right choice here.

```
main                    always green, always deployable, protected
  └── task/08-differential-test      one branch per TASK-XX
  └── fix/spawn-probability-drift    one branch per bug
  └── exp/ntuple-6tuple-lr-sweep     experiment branches, may die unmerged
```

Rules:

1. A branch exists for exactly one task. It is born from `main` and dies at merge.
2. A branch lives for hours, not days. If it lives longer, the task was too big — split
   it and say so in `LOOP_STATE.md`.
3. `main` is never broken. If CI is red on `main`, that is the only thing anyone works
   on.
4. Experiment branches (`exp/`) are allowed to be abandoned. When one dies, the reason
   goes in `memory/FAILURES.md` **before** the branch is deleted, because the branch is
   not the record — the memory file is.

Enable branch protection on `main` once CI exists:

```bash
gh api -X PUT repos/xeseing/2048-rl/branches/main/protection \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[contexts][]=test" \
  -F "enforce_admins=false" \
  -F "required_pull_request_reviews=null" \
  -F "restrictions=null"
```

(`enforce_admins=false` so you can still push a hotfix yourself when you need to.)

---

## Part 3 — Commit convention

Conventional Commits, with the task ID, and — this is the part that matters here — the
**verification command in the footer**.

```
<type>(<scope>): <summary in imperative mood>

<why, if not obvious from the summary>

Task: TASK-08
Verified: python -m game2048.bench.differential --games 100000 --seed 7 -> 0 divergences
```

Types: `feat` `fix` `test` `perf` `refactor` `docs` `chore` `exp`

Examples:

```
feat(bitboard): add uint64 board with precomputed row tables

Task: TASK-07
Verified: pytest tests/test_engine.py -q -> 47 passed
```

```
perf(bitboard): replace per-move tuple alloc with table lookup

Throughput went 180k -> 1.4M moves/sec. The tuple allocation in the
inner loop dominated the profile.

Task: TASK-09
Verified: python -m game2048.bench.engine_bench --seconds 30 --gate 200000 -> 1,412,003 moves/sec
```

```
exp(ntuple): 4x6-tuple run, alpha=0.1 decaying

Task: TASK-13
Verified: 2048rl eval --agent ntuple --games 1000 -> mean 43,118, 2048 rate 94.2%
Run: runs/td-04/
```

**Why the footer:** in six months, `git log` becomes a searchable record of what was
actually proven, not what was claimed. `git log --grep="Verified:"` is your audit
trail. A commit without a `Verified:` line is a commit that skipped the gate.

One task, one commit (or one squashed PR). No mixed diffs.

---

## Part 4 — PR flow per task

```bash
git switch -c task/08-differential-test main
# ... work, commit ...
git push -u origin task/08-differential-test
gh pr create --fill --body-file .github/pull_request_template.md
# wait for CI
gh pr checks --watch
gh pr merge --squash --delete-branch
```

Yes, PRs for a solo project. Three reasons that are real, not cargo-cult:

1. CI runs on the PR, so `main` is protected from an agent that got confident.
2. The PR diff is your review surface. Reviewing a diff catches things reviewing a chat
   transcript never will.
3. `@claude review this PR` works on PRs, not on local branches.

---

## Part 5 — CI

`.github/workflows/ci.yml` runs on every push and PR:

- ruff lint + format check
- pytest on Python 3.11 and 3.12
- **fast** differential test (5,000 games, not 100,000)
- secret scan

`.github/workflows/nightly.yml` runs on a schedule and on manual dispatch:

- **full** differential test (100,000 games)
- throughput benchmark, with the 200k moves/sec gate as a hard failure
- 1000-seed eval of the checked-in baseline agents

The split exists because a 100k-game differential test on every push would make you
stop pushing. Cheap gate always, expensive gate nightly.

---

## Part 6 — Versioning & releases

SemVer, tagged at real milestones — not on a schedule:

| Tag | Milestone |
| :-- | :-- |
| `v0.1.0` | Engine verified: differential test + throughput gate green |
| `v0.2.0` | Eval harness + random/heuristic baselines |
| `v0.3.0` | **N-tuple Stage 1 learns** (first genuinely self-taught agent) |
| `v0.4.0` | N-tuple Stage 2 at target strength |
| `v0.5.0` | DQN track complete + comparison written |
| `v1.0.0` | Packaged app, weights published, RESULTS.md, README with real numbers |

```bash
git tag -a v0.3.0 -m "N-tuple Stage 1: mean 18,420, 2048 rate 63%"
git push origin v0.3.0
gh release create v0.3.0 --generate-notes
gh release upload v0.3.0 runs/td-02/weights.npz   # weights ship here, not in git
```

`CHANGELOG.md` gets a section per tag, written by hand, with the measured numbers in
it. Not auto-generated — the numbers are the point.

---

## Part 7 — What goes in git and what doesn't

| Thing | Where | Why |
| :-- | :-- | :-- |
| Source, tests, configs | git | obviously |
| `memory/*.md` | git | the agent's knowledge is project knowledge; it must survive a fresh clone |
| `LOOP_STATE.md` | git | commit it with the task it describes, so state and code stay in sync |
| `runs/<id>/config.json`, `metrics.csv`, `summary.md` | git | tiny, and they're the experimental record |
| `runs/<id>/weights.npz` (268 MB) | **GitHub Release asset** | too big for git; Git LFS would burn your free quota fast |
| `runs/<id>/checkpoint_*.npz` | **gitignored** | intermediate, regenerable |
| `.env`, tokens, keys | **nowhere, ever** | |

The rule for weights: git holds *how to reproduce it*, releases hold *the artifact*.
