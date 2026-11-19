#!/usr/bin/env bash
# audit-authors.sh — who is in this repository's history?
#
# Run before submitting. Lists every author, committer and co-author trailer,
# and fails if any of them is a bot or AI assistant account.
#
#   bash audit-authors.sh
#
set -uo pipefail

PATTERN='claude|anthropic|copilot|chatgpt|openai|\[bot\]|bot@|codex|cursor|devin|gemini'
fail=0

echo "=============================================="
echo " commits per author"
echo "=============================================="
git shortlog -sne --all

echo
echo "=============================================="
echo " every author / committer identity"
echo "=============================================="
git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u | sed 's/^/  /'

echo
echo "=============================================="
echo " co-author trailers"
echo "=============================================="
trailers=$(git log --all --format='%(trailers:key=Co-authored-by)' | grep -v '^$' || true)
if [ -n "$trailers" ]; then
  echo "$trailers" | sort -u | sed 's/^/  /'
else
  echo "  (none)"
fi

echo
echo "=============================================="
echo " verdict"
echo "=============================================="
if git log --all --format='%an <%ae>|%cn <%ce>' | grep -iqE "$PATTERN"; then
  echo "  FAIL: a bot/AI account appears as author or committer:"
  git log --all --format='%an <%ae>|%cn <%ce>' | grep -iE "$PATTERN" | sort -u | sed 's/^/    /'
  fail=1
fi

if [ -n "$trailers" ] && echo "$trailers" | grep -iqE "$PATTERN"; then
  echo "  FAIL: a commit credits a bot/AI as co-author:"
  echo "$trailers" | grep -iE "$PATTERN" | sort -u | sed 's/^/    /'
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "  OK — human authorship only."
else
  echo
  echo "  To fix, rewrite the offending commits:"
  echo "    git rebase -i <commit-before-the-problem>"
  echo "    # mark them 'edit' (wrong author) or 'reword' (bad trailer)"
  echo "    git commit --amend --author='Your Name <your-github-email>'"
  echo "    git rebase --continue"
  exit 1
fi

echo
echo "=============================================="
echo " GitHub Apps installed on this repo"
echo "=============================================="
echo " (requires gh; an app named claude/copilot here can commit as a bot)"
gh api repos/arsentis/qrpack/installation --jq '"  INSTALLED: " + .app_slug' 2>/dev/null \
  || echo "  none detected"
