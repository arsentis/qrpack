#!/usr/bin/env bash
# qrpack repo setup — run ONCE, from the repo root, as the owner (Arsen).
#
#   bash setup-repo.sh
#
# Teammates are already listed below. Requires: gh (authenticated), git.
# Safe to re-run: everything except the first commit is idempotent.

set -euo pipefail

REPO="arsentis/qrpack"
TEAM=(Rustlingrass dreamboy17 AliKa7 yerassy1dev)

echo "==> 0. identity check"
# Note: use --global. A bare `git config` fails with "not in a git directory"
# until `git init` has run, and init happens in step 1 below.
if ! git config --global user.email >/dev/null 2>&1; then
  echo "!! set your identity first, then re-run this script:"
  echo "   git config --global user.name  'Arsen Toktarbek'"
  echo "   git config --global user.email '216891376+arsentis@users.noreply.github.com'"
  exit 1
fi
echo "   committing as: $(git config --global user.name) <$(git config --global user.email)>"

echo
echo "==> 1. git init + first commit (docs only — code is written by the team)"
[ -d .git ] || git init -b main
git add CONTRIBUTING.md PLAN.md .gitignore
git commit -m "docs: contribution rules and 3-day sprint plan" || echo "   (nothing new to commit)"
git remote add origin "https://github.com/${REPO}.git" 2>/dev/null || true
git push -u origin main

echo
echo "==> 2. invite collaborators"
for u in "${TEAM[@]}"; do
  gh api -X PUT "repos/${REPO}/collaborators/${u}" -f permission=push >/dev/null \
    && echo "   invited ${u}"
done

echo
echo "==> 3. merge settings: REBASE ONLY"
echo "    (squash would collapse each person's commits into one and erase the history)"
gh api -X PATCH "repos/${REPO}" \
  -F allow_squash_merge=false \
  -F allow_rebase_merge=true \
  -F allow_merge_commit=false \
  -F delete_branch_on_merge=true >/dev/null
echo "   squash disabled, rebase enabled"

echo
echo "==> 4. protect main: pull request + 1 approval required"
# Must be sent as JSON: the -f flag stringifies the review count and the API
# rejects "1" because it requires an integer.
cat > /tmp/qrpack-protection.json <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
gh api -X PUT "repos/${REPO}/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input /tmp/qrpack-protection.json >/dev/null
echo "   main protected — nobody pushes directly, including you"

echo
echo "==> 5. labels"
for l in core sheet scan calibrate cli docs infra; do
  gh label create "$l" --repo "$REPO" >/dev/null 2>&1 && echo "   + $l" || true
done
gh label create day1 --repo "$REPO" --color 0e8a16 >/dev/null 2>&1 || true
gh label create day2 --repo "$REPO" --color fbca04 >/dev/null 2>&1 || true
gh label create day3 --repo "$REPO" --color d93f0b >/dev/null 2>&1 || true

echo
echo "==> 6. issues (15, already assigned)"
bash ./create-issues.sh

echo
echo "============================================================"
echo "DONE. Now, by hand:"
echo
echo "  1. Tell the four to ACCEPT the collaborator invite (GitHub notification"
echo "     or email). Nothing works until they do."
echo
echo "  2. Post this in the group chat:"
echo
echo "     Repo: https://github.com/${REPO}"
echo "     Read CONTRIBUTING.md before your first commit."
echo "     Your tasks are assigned to you in Issues."
echo "     Before you start, run these and reply 'ready':"
echo "       git clone https://github.com/${REPO}.git && cd qrpack"
echo "       python3 -m venv .venv && source .venv/bin/activate"
echo "       pip install -e '.[dev]' && python -m pytest -q"
echo "       git config --global user.email 'YOUR GitHub email'"
echo
echo "  3. Check the spread tonight and tomorrow:"
echo "       git fetch && git shortlog -sne --all"
echo "============================================================"
