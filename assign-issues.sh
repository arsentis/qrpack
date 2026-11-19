#!/usr/bin/env bash
# Assign the sprint issues to the team.
#
# RUN THIS AFTER everyone has ACCEPTED their collaborator invite.
# GitHub silently drops assignees who are not yet collaborators, which is why
# this is a separate step from create-issues.sh. Safe to re-run any time.
#
#   bash assign-issues.sh
#
set -euo pipefail
REPO="arsentis/qrpack"

A1="arsentis"        # Arsen Toktarbek  — core: archiving
A2="Rustlingrass"    # Aubakir Arman    — core: framing
A3="AliKa7"          # alikaiyr         — sheet
A4="yerassy1dev"     # Yerassyl         — scan
A5="dreamboy17"      # dreamboy17       — cli, CI
A6="Hetag-byte"      # Hetag-byte       — calibrate, docs

assign () {
  if gh issue edit "$1" --repo "$REPO" --add-assignee "$2" >/dev/null 2>&1; then
    echo "   #$1 -> $2"
  else
    echo "   #$1 -> $2   FAILED (has $2 accepted the invite?)"
  fi
}

echo "==> day 1"
assign 1  "$A1"    # core: pack_bytes / unpack_bytes
assign 2  "$A2"    # core: Header + chunk + sha256
assign 3  "$A3"    # sheet: render payloads to QR images
assign 4  "$A4"    # scan: decode a single QR image
assign 5  "$A5"    # infra: CLI skeleton, CI, README

echo "==> day 2"
assign 6  "$A1"    # core: junk dirs, deterministic tar, traversal guard
assign 7  "$A2"    # core: sha256 verification on restore
assign 8  "$A3"    # sheet: grid, cells, labels, paging, PDF
assign 9  "$A4"    # scan: whole sheet + missing parts
assign 10 "$A5"    # cli: wire up the subcommands
assign 11 "$A6"    # calibrate: ladder + px/module  (Hetag's day-2 start)

echo "==> day 3"
assign 17 "$A1"    # docs: usage with real output
assign 12 "$A2"    # test: damaged sheet
assign 13 "$A3"    # demo: print, photograph, restore
assign 14 "$A4"    # docs: measured findings
assign 15 "$A5"    # release: tag, badge, shortlog

echo
echo "==> verifying"
gh issue list --repo "$REPO" --limit 30 --json number,assignees \
  --jq '.[] | "   #\(.number) \(.assignees[0].login // "STILL UNASSIGNED")"' | sort -V

echo
echo "STILL UNASSIGNED means that person has not accepted the collaborator"
echo "invite yet. Chase them, then re-run this script."
