#!/usr/bin/env bash
# Creates the 15 sprint issues (5 per day), one per person per day,
# already assigned to the right GitHub user. Run from the repo root.
#   bash create-issues.sh
set -euo pipefail
REPO="arsentis/qrpack"

# ---- the team -------------------------------------------------------------
A1="arsentis"        # Arsen Toktarbek  — core: archiving + calibrate
A2="Rustlingrass"    # Aubakir Arman    — core: framing
A3="AliKa7"          # alikaiyr         — sheet
A4="yerassy1dev"     # Yerassyl         — scan
A5="dreamboy17"      # dreamboy17       — cli, CI, docs
# A sixth member can be added later; see the note at the bottom of this file.

mk () {  # mk "title" "body" "labels" "assignee"
  gh issue create --repo "$REPO" --title "$1" --body "$2" \
     --label "$3" --assignee "$4" >/dev/null \
    && echo "   + [$4] $1"
}

echo "   creating day 1 issues..."

mk "core: pack_bytes / unpack_bytes (tar + lzma)" \
"**Owner: Arsen (@${A1})**

Turn a directory into one compressed blob and back again.

Done when:
- \`pack_bytes(Path) -> bytes\` tars the files, sorted by name
- \`unpack_bytes(blob, dest) -> list[str]\` restores them
- a test packs a fixture tree, unpacks it, asserts the files match
- the round trip is byte-identical

Commit in four steps: failing test, minimal pass, edge case, docs." "core,day1" "$A1"

mk "core: Header + chunk() + sha256" \
"**Owner: Aubakir (@${A2})**

The framing layer: split encoded data into labelled payloads.

Payload format (agreed in Hour 0, never change it):
\`\`\`
QRPK1|<sha256-first-16>|<index>/<total>|<base64 chunk>
\`\`\`

Done when:
- \`Header\` renders and parses that line
- \`chunk(blob, size)\` returns complete payloads
- a test round-trips a header and asserts the fields survive" "core,day1" "$A2"

mk "sheet: render payloads to QR images" \
"**Owner: alikaiyr (@${A3})**

Done when:
- \`render_codes(payloads)\` returns one image per payload using segno
- a test writes a PNG and asserts it is non-empty and square
- the error-correction level is a parameter, not hard-coded" "sheet,day1" "$A3"

mk "scan: decode a single QR image" \
"**Owner: Yerassyl (@${A4})**

Done when:
- \`decode_one(path) -> str | None\` reads back a code produced by @${A3}
- a test generates a code, decodes it, asserts the text matches
- note in the docstring any size or scale that fails — that becomes a finding" "scan,day1" "$A4"

mk "infra: CLI skeleton, CI, README problem and aim" \
"**Owner: @${A5}**

Done when:
- \`qrpack --help\` lists estimate / pack / restore (stubs are fine)
- the console script is registered in pyproject.toml
- .github/workflows/ci.yml runs pytest on 3.10, 3.11 and 3.12 and is green
- README states the problem and the aim (no results yet)" "cli,infra,day1" "$A5"

echo "   creating day 2 issues..."

mk "core: skip junk dirs, deterministic tar, path-traversal guard" \
"**Owner: Arsen (@${A1})**

Done when:
- \`__pycache__\`, \`.git\`, \`node_modules\`, \`.venv\` are excluded
- mtime/uid/gid are zeroed so packing the same folder twice is byte-identical
- an entry containing \`../\` raises instead of escaping the destination
- one test per behaviour" "core,day2" "$A1"

mk "core: sha256 verification on restore" \
"**Owner: Aubakir (@${A2})**

Done when:
- the digest in the header is checked against the restored bytes
- a mismatch raises with a clear message and never returns bad data
- a test flips one byte and asserts the restore is refused" "core,day2" "$A2"

mk "sheet: grid layout, uniform cells, labels, multi-sheet, PDF" \
"**Owner: alikaiyr (@${A3})**

Done when:
- codes are laid out in a grid with a header line and 'part i of n' labels
- codes of different QR versions are padded to identical cells (otherwise the
  grid breaks and cropping during the scan becomes impossible)
- more codes than fit on a page produce sheet-01, sheet-02, ...
- a .pdf output path writes a PDF
- a test asserts every cell has the same pixel size" "sheet,day2" "$A3"

mk "scan: read a whole sheet and report missing parts" \
"**Owner: Yerassyl (@${A4})**

Done when:
- \`scan_image\` finds every code on a rendered sheet
- \`reassemble\` raises naming the missing index ('missing parts [2] of 5')
  and never returns a corrupt blob
- a test removes one payload and asserts the index is named" "scan,day2" "$A4"

mk "cli: wire up estimate / pack / restore for real" \
"**Owner: @${A5}**

Done when:
- \`qrpack estimate SRC\` prints raw -> compressed -> encoded -> codes
- \`qrpack pack SRC -o sheet.png\` writes a sheet
- \`qrpack restore sheet.png -o out\` restores files and verifies the checksum
- exit codes: 0 success, non-zero on any failure" "cli,day2" "$A5"

echo "   creating day 3 issues..."

mk "calibrate: payload ladder and px/module table" \
"**Owner: Arsen (@${A1})**

The feature nobody else has: measure the real limit instead of quoting the spec.

Done when:
- a ladder of payload sizes is encoded and decoded under degraded conditions
- the report prints pixels-per-module per size and recommends a chunk size
- the sweep is monotonic (a bigger payload is never more robust than a smaller
  one) — if it is not, the degradation model is wrong; fix it, do not hide it" "calibrate,day3" "$A1"

mk "test: damaged sheet names the lost part" \
"**Owner: Aubakir (@${A2})**

Done when:
- a test blacks out one code on a rendered sheet
- scanning recovers n-1 codes and the restore is refused, naming that part
- the result is recorded in the README findings" "core,day3" "$A2"

mk "demo: print a sheet, photograph it, restore it" \
"**Owner: alikaiyr (@${A3})**

The claim is physical, so test it physically.

Done when:
- a sheet is printed on paper and photographed with a phone
- the outcome is recorded honestly in the README, including the chunk size that
  worked and anything that failed" "docs,day3" "$A3"

mk "docs: measured findings section" \
"**Owner: Yerassyl (@${A4})**

Done when:
- every number in the README has the command that produced it
- nothing is quoted from a spec without being measured
- a reviewer can reproduce each number" "docs,day3" "$A4"

mk "release: tag v0.1.0, CI badge, contributor check" \
"**Owner: @${A5}**

Done when:
- version bumped and tagged v0.1.0
- CI badge in the README
- \`git shortlog -sne\` output pasted into the PR so the spread is on record" "infra,day3" "$A5"

echo "   done — 15 issues, 3 per person."
echo
echo "   If a sixth member joins:"
echo "     gh api -X PUT repos/${REPO}/collaborators/THEIR_USER -f permission=push"
echo "   then reassign the three 'calibrate' / spare issues to them:"
echo "     gh issue edit N --add-assignee THEIR_USER --remove-assignee ${A1}"
