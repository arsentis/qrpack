# Contributing to qrpack

Five people, one repo, visible and even contribution history. Read this once
before your first commit.

**This is a 3-day sprint.** Timeline and task assignments are in `PLAN.md`.
Push every 1-2 hours, review within 30 minutes, never merge your own PR.

Repo: https://github.com/arsentis/qrpack
Default branch: `main` (protected — nobody pushes to it directly, including the owner)


## 0. Why the rules exist

The grade for a group project is partly "did everyone actually work". GitHub
answers that question automatically through the commit graph, and the graph is
easy to ruin by accident:

- One person pastes everyone's code and commits it → four members look idle.
- Everyone works on `main` → constant conflicts, and nobody reviews anything.
- Three commits total, all on the last night → looks like panic, because it is.

So: **your own commits, on your own branch, merged by pull request, spread
across the weeks.**


## 1. One-time setup

```bash
git clone https://github.com/arsentis/qrpack.git
cd qrpack
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q          # must print "11 passed" before you change anything
```

Set your identity so commits are attributed to *you*:

```bash
git config --global user.name  "Your Name"
git config --global user.email "your-github-email@example.com"
```

(Use `--global`. Without it, git refuses with "not in a git directory" unless
you are already inside a cloned repo.)

The email must be the one on your GitHub account, otherwise your commits show
up as an unknown author and do not count toward your contribution graph.


## 2. Who owns what

Each member owns one module. You may read anything; you only *edit* your own
area without asking. This is what makes five people work in parallel without
stepping on each other.

| # | Member | GitHub | Owns | Files |
|---|---|---|---|---|
| 1 | Arsen Toktarbek | `arsentis` | Core — archiving, and calibration | `core.py` (pack/unpack), `calibrate.py` |
| 2 | Aubakir Arman | `Rustlingrass` | Core — framing | `core.py` (`Header`, `chunk`, `estimate`, sha256) |
| 3 | alikaiyr | `AliKa7` | Sheet — layout and output | `sheet.py` |
| 4 | Yerassyl | `yerassy1dev` | Scan — decoding and recovery | `scan.py` |
| 5 | — | `dreamboy17` | CLI, CI, documentation | `cli.py`, `.github/workflows/`, `README.md` |

Members 1 and 2 share `core.py` but own different *functions*, so they never
touch the same lines — provided the signatures agreed in Hour 0 are respected.

`cli.py` is owned by member 5, but each person adds their own subcommand when
their module is ready. Keep those edits to your own subcommand.

Everyone writes tests for their own module. "The tests are member 4's job" is
how a project fails.


## 3. The loop, every single time

```bash
git switch main
git pull                                  # always start from latest main
git switch -c feat/scan-deskew            # branch named for the work

# ... edit, run tests ...
python -m pytest -q

git add -p                                # stage deliberately, not `git add .`
git commit -m "scan: correct perspective before decoding"
git push -u origin feat/scan-deskew
gh pr create --fill                       # or open the PR on github.com
```

Then another member reviews and merges it. **You do not merge your own PR.**

Branch naming: `feat/…` new behaviour, `fix/…` bug, `docs/…`, `test/…`, `chore/…`.
Prefix with your area when useful: `feat/sheet-pdf-margins`.


## 4. Commit messages

Format: `area: imperative summary under 72 chars`

```
core: zero mtime in tar so packing is deterministic
scan: try a finer scale ladder before giving up on a cell
sheet: pad codes to a uniform cell so the grid stays square
test: assert a blacked-out code names the missing part
docs: record the measured ECC capacity table
```

Not: "update", "fix bug", "changes", "asdf", "final version FINAL2".

### Commit FOUR times per feature, not once

This is the single habit that builds a long, honest history. For any piece of
work, commit at each of these moments — they are all real, none are padding:

```
1. the failing test first     test: assert tar output is byte-identical twice
2. the smallest thing passing core: sort entries and zero mtime in the tar
3. the edge case              core: skip __pycache__, .git and node_modules
4. the explanation            docs: record why mtime must be zeroed
```

One small feature = four commits. Five people × one feature a day = 20 commits
a day, every one of them genuine work.

Rules of thumb:
- One logical change per commit. Formatting and behaviour do not share a commit.
- Commit when something works, not when everything is finished.
- **Push every day you work, even if unfinished.** A branch is exactly the place
  for unfinished work. Code sitting on your laptop is invisible to the grader.
- Never commit `brag-output/`, `__pycache__/`, `.venv/`, rendered `*.png`/`*.mp4`,
  or anything in `.gitignore`.

### No bot or AI authorship — enforced by CI

The contributor graph is the record of who did this project. A bot in it
devalues everyone's work, so:

- **Do not install the Claude, Copilot, or any other GitHub App on this repo.**
  An installed app commits as `claude[bot]` and is counted as a contributor.
  Only the repo owner can install one; the answer is no for this project.
- **Never leave an AI `Co-authored-by:` trailer in a commit message.** Some
  assistant tooling appends one automatically. It credits that account as a
  contributor even with no app installed. Check your message before committing.
- Using an assistant locally is fine. Commit the result under **your own name
  and your own GitHub email** — the work is yours, so the credit should be too.

`.github/workflows/authorship.yml` fails any pull request whose commits are
authored, committed, or co-authored by a bot/AI account. Audit the whole history
at any time:

```bash
bash audit-authors.sh
```

### Pair programming

If two of you wrote it together, credit both — add a blank line then:

```
Co-authored-by: Name <their-github-email@example.com>
```

GitHub then counts the commit for both people. Use this instead of one person
committing the other's work.


## 5. Pull requests

Open a PR as soon as you have something to show, even unfinished — mark it
Draft. A PR should be reviewable in ten minutes; if it touches 400 lines, split it.

PR description template:

```
What: one sentence.
Why: the problem it solves.
How to check: the exact command a reviewer should run.
Measured: any numbers you produced (before/after).
```

**Review duty.** Every PR needs one approval from someone who did not write it.
Rotate so each person reviews everyone else at least once — reviews show up in
the repo's history too, and they catch real bugs.

When you review, actually run it:

```bash
gh pr checkout 12
python -m pytest -q
```

### Merge style: REBASE AND MERGE. Never squash.

This is not a style preference, it is the rule that decides whether your work is
visible.

- **Squash and merge** collapses your 6 commits into **1** commit on `main`.
  Five commits of yours disappear from the history forever.
- **Rebase and merge** replays **all** of your commits onto `main`, each keeping
  your name and your date.

When you merge a PR on github.com, the green button has a dropdown. Open it and
choose **Rebase and merge**. If the button says "Squash and merge", you clicked
the wrong thing — change it before merging.

The repo is configured so squash is disabled, but check anyway.


## 6. Issues are the plan

Every task is a GitHub issue before it is code. Open issues for your own module
in week 1, assign yourself, and reference them from commits:

```
scan: report which parts are missing

Closes #14
```

Labels to create: `core`, `sheet`, `scan`, `calibrate`, `docs`, `bug`,
`good-first-task`.

Use the repo's Projects board (Todo / In progress / In review / Done) so the
supervisor can see the plan at a glance without reading code.


## 7. Rhythm — the part that actually matters

Commit history is judged on *spread*, not total count. Thirty commits in six
weeks beats two hundred on the last night.

**Hard minimums per person, per week:**

| | Minimum |
|---|---|
| Merged pull requests | 3 (one per day) |
| Pushed commits | 12 (~4 per day) |
| Reviews given to others | 3 |
| Days with at least one push | 3 (all of them) |

A day with zero commits from someone is visible forever in
Insights → Contributors. With only three days, one silent day is a third of
your record. It cannot be fixed later.

Stand-up twice a day (10 min): what landed, what is next, what is blocked.

Check yourselves any time:

```bash
git shortlog -sne --all          # commits per author
gh pr list --state merged --limit 50
```

If one column is far behind by week 2, rebalance the work then — not at the end,
when it is too late to fix honestly.

### Do not fake it

No backdated commits (`GIT_AUTHOR_DATE`), no committing someone else's code
under your name, no "contribution" commits that only add whitespace. Push dates
are logged separately from commit dates and the pattern is obvious to anyone who
looks. A thin but honest history explains itself; a fabricated one does not.


## 8. Definition of done

A change is done when all of these hold:

1. `python -m pytest -q` passes locally.
2. CI is green on the PR.
3. New behaviour has a test that would fail without the change.
4. Any number you claim in a docstring or the README came from a real run and
   is reproducible by the reviewer.
5. One other member approved it.

Point 4 is a house rule: this project's value is its measured findings. Never
write a number you did not produce.


## 9. Things that will break the repo

- `git push --force` to `main` — forbidden. On your own branch, use
  `--force-with-lease` only.
- Committing the 61 MB `brag-output/work/` directory or sample renders.
- Merging your own PR.
- Committing `.env`, keys, tokens, or anything personal. The repo is **public**.
- Rewriting history on a branch someone else has checked out.

If you break something, say so in the group chat immediately. Everything is
recoverable; silence is what makes it expensive.
