#!/usr/bin/env bash
# Capture the README's usage transcripts from real runs (issue #17).
#
#   bash tests/capture_usage.sh
#
# Prints exactly what the README quotes. Re-run it after any CLI change: if the
# output no longer matches the README, the README is wrong.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)

# Run from a short, tidy directory: the README quotes these transcripts
# verbatim, and absolute mktemp paths would make them unreadable.
WORK=$(mktemp -d)/demo
mkdir -p "$WORK"
cd "$WORK" || exit 1
SRC="notes"
mkdir -p "$SRC/sub"
# Deterministic content so the byte counts in the README are reproducible.
python3 - "$SRC" <<'PY'
import sys, pathlib, random
src = pathlib.Path(sys.argv[1])
(src / "todo.md").write_text("# Todo\n\n- back up the keys\n- print the sheet\n" * 12)
(src / "sub" / "keys.txt").write_text("ssh-ed25519 AAAA" + "x" * 240 + " demo@example\n")
(src / "sub" / "noise.bin").write_bytes(random.Random(7).randbytes(400))
PY

# Print the command as a reader would type it (qrpack, not python3 -m), then
# run it for real.
run () {
  # shift past "python3 -m qrpack.cli" so the transcript reads as the installed
  # console script does
  printf '$ qrpack'
  for a in "${@:4}"; do printf ' %s' "$a"; done
  printf '\n'
  "$@" 2>&1
  printf 'exit %s\n\n' "$?"
}

echo "=============== estimate ==============="
run python3 -m qrpack.cli estimate "$SRC"
run python3 -m qrpack.cli estimate "$SRC" --chunk 300

echo "=============== pack ==============="
run python3 -m qrpack.cli pack "$SRC" -o sheet.png --chunk 300
echo '$ ls'
ls | sed 's/^/  /'
echo

echo "=============== restore ==============="
run python3 -m qrpack.cli restore sheet.png -o restored
echo '$ diff -r notes restored'
diff -r "$SRC" restored && echo '  (no output: the restored files are byte identical)'
echo

echo "=============== failure modes ==============="
run python3 -m qrpack.cli pack does-not-exist -o x.png
python3 - <<'PY'
from PIL import Image
Image.new("RGB", (400, 400), "white").save("blank.png")
PY
run python3 -m qrpack.cli restore blank.png -o out2

echo "=============== environment ==============="
echo "\$ python3 -m qrpack.cli --version"
python3 -m qrpack.cli --version
echo '$ python -m pytest -q'
(cd "$REPO" && python3 -m pytest -q 2>&1 | tail -1)

cd / && rm -rf "$(dirname "$WORK")"
