# Contributing to qrpack

Thanks for your interest in qrpack. This document covers how to get set up, the
conventions the project follows, and what a change needs before it can be merged.

## Getting set up

```bash
git clone https://github.com/arsentis/qrpack.git
cd qrpack
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

The suite should pass before you change anything. If it does not, that is a bug
worth reporting on its own.

## Making a change

Work on a branch, never directly on `main`:

```bash
git switch -c scan/report-missing-parts
```

Branch names are prefixed with the area they touch — `core/`, `sheet/`, `scan/`,
`calibrate/`, `cli/`, `docs/`, `ci/` — followed by a short description.

Before opening a pull request:

```bash
python -m pytest -q
git rebase origin/main
```

Rebasing matters: CI tests your branch *merged with* `main`, so a green check on
a stale branch does not prove the branch works. Rebase first and run the tests
locally.

## Code conventions

- **`core.py` imports nothing outside the standard library.** It is the path
  that decides whether a user's bytes come back intact; third-party code does
  not belong there.
- **Validate before writing.** Build and check everything first, then create
  files. A failure should never leave a half-written sheet or a partial restore.
- **Fail loudly and exit non-zero.** A backup tool that exits `0` without
  writing anything is worse than one that crashes. Error messages name the
  cause; tracebacks are not an interface.
- **Keep archives deterministic.** Entries are sorted and metadata zeroed so the
  same input always produces the same bytes. Without that, the printed digest
  verifies nothing.
- Type hints on public functions, and a docstring explaining *why* rather than
  restating the signature.

## Tests

Every behavioural change needs a test. New tests go in `tests/test_<area>.py`
and should fail before your fix and pass after it.

Two conventions specific to this repository:

- **`tests/measure_*.py` are not tests.** They are measurement scripts whose
  output is quoted in the README. If you change behaviour they describe, re-run
  them and update the README with the new numbers.
- **`tests/test_readme_usage.py` guards the documentation.** It re-runs the
  commands shown in the README and fails if their output no longer matches, so
  stale documentation breaks the build instead of misleading a reader. If you
  change the CLI, regenerate the transcripts with `bash tests/capture_usage.sh`.

Any number added to the README should name the command that reproduces it.

## Commits

One logical change per commit, with a message in the imperative mood and the
area as a prefix:

```
scan: report which parts are missing
core: reject archive members with absolute paths
docs: record the measured ECC cost in printed pixels
```

Explain *why* in the body if the reason is not obvious from the diff.

## Pull requests

Open the pull request against `main` with:

- a description of what changed and why;
- the test output, or the commands you ran to verify it;
- `Closes #N` in the description if it resolves an issue. Only the description
  works — a closing keyword in the title or a comment is ignored by GitHub.

Keep pull requests focused and reasonably small; they get reviewed faster and
regressions are easier to trace later.

One approving review is required before merge, and `main` is protected. Merge
with **rebase and merge** so individual commits are preserved in the history.

## Definition of done

A change is done when:

- [ ] the full suite passes locally and in CI;
- [ ] new behaviour has a test that fails without the change;
- [ ] errors exit non-zero with a message that names the cause;
- [ ] the README is updated if behaviour, output or measured numbers changed;
- [ ] the branch is rebased on `main` and has one approving review.

## Reporting bugs

Open an issue with the command you ran, the output you got, the output you
expected, and your Python and OpenCV versions:

```bash
python -c "import sys, cv2; print(sys.version); print(cv2.__version__)"
```

Decoding behaviour in particular varies between OpenCV builds, so that version
is often the most useful line in the report.
