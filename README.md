# qrpack

Pack a folder into printable QR codes, print it, photograph it, get the folder
back — verified byte for byte.

> **Status: working end to end.** `estimate`, `pack` and `restore` are
> implemented and a folder round-trips through a rendered sheet byte for byte
> (see the transcripts below). `calibrate` is still in progress. 133 tests.
> See `PLAN.md` for the schedule and `CONTRIBUTING.md` before your first commit.

## Try it in thirty seconds

```bash
pip install -e ".[dev]"
qrpack pack ./some-folder -o sheet.png --chunk 300
qrpack restore sheet.png -o restored
diff -r ./some-folder restored      # prints nothing
```

## The problem

Small, high-value digital artifacts fail in ways that are hard to insure
against: disks die, accounts get locked, repositories are deleted, USB ports
are disabled. The data that hurts most when it vanishes is usually small — an
SSH key, a recovery seed, a `.env` file, a few hundred lines of source.

Paper has none of those failure modes. It needs no power, no network and no
account. Its weakness is getting the bytes back off reliably: typing a key by
hand is slow and error-prone, and OCR of base64 is worse.

QR codes solve the reading problem but introduce a size problem — a single code
holds at most a few kilobytes. So the real question is not "can I put a file in
a QR code" but: how do you split a file across many codes so an ordinary camera
can reassemble it, and so an unreadable code is detected instead of silently
corrupting the result?

## Aim

Make paper a verifiable backup medium for small digital artifacts, using only a
printer and a camera.

1. Pack any file or folder into printable sheets of QR codes.
2. Restore from an image of those sheets, with SHA-256 verification.
3. Fail specifically — name the missing part rather than produce a corrupt file.
4. Measure the real capacity of the user's own printer and scanner instead of
   quoting the QR specification.
5. Ship as a real package: tests, CI, CLI, documented findings.

## Measured Findings

The following results were obtained from experiments using Python, Segno and OpenCV.

### OpenCV Version

The experiments were performed using OpenCV `5.1.0`.

To check the installed version:

```bash
python -c "import cv2; print(cv2.__version__)"
```

### QR Sheet Decoding

A sheet containing three QR codes was generated using:

```python
make_sheet(payloads, "measurement", "measure_sheet.png", cols=3, scale=4)
```

Payload lengths: `1363`, `1363` and `775` characters.

Decoding results:

| Detector | Scale | Decoded |
|---|---|---|
| QRCodeDetector | 0.5–3.0 | 0/3 |
| QRCodeDetectorAruco | 0.5 | 0/3 |
| QRCodeDetectorAruco | 0.75–3.0 | 3/3 |

### Direct QR Decoding by ECC

The standard OpenCV `QRCodeDetector` was tested with QR codes generated using different error correction levels (ECC).

| ECC | QR Version | Scale 4 | Scale 6 | Scale 8 |
|---|---:|---|---|---|
| L | 26 | FAIL | PASS | PASS |
| M | 30 | FAIL | FAIL | FAIL |
| Q | 37 | FAIL | FAIL | FAIL |

These results show that decoding performance depends on the detector, image scale and QR code configuration.

The experiments were performed using Python, Segno and OpenCV. See the measurement script in the project instructions for the complete reproduction procedure.

### Damaged sheet

One QR code on a five-part sheet was painted black before scanning, the way a
stain or a folded corner would destroy one code on a printed sheet.

Reproduce:

```bash
python tests/measure_damaged_sheet.py
```

Measured output:

```
parts rendered    : 5
part blacked out  : 3
parts decoded     : [1, 2, 4, 5]
reassemble        : missing=[3] blob_empty=True digest=f7dbe72bcc439d2d
cli restore       : rc=1 | qrpack restore: missing parts [3]; rescan them and pass every sheet
files written     : 0
with intact copy  : rc=0 bytes_identical=True
```

The scan recovered four of the five codes. `reassemble` named part 3 and
returned an empty blob, so the restore exited non-zero and wrote no files —
it did not hand back a corrupt backup. Adding one intact copy of the same
sheet supplied the missing part and the original file came back byte for byte.
`tests/test_damaged_sheet.py` also covers the first and last parts and a code
on a later page of a multi-page sheet.

## Command line

Installing the package (see Development below) puts a `qrpack` command on your
path. `qrpack --help` lists the subcommands and `qrpack COMMAND --help` shows
the options for each.

```bash
qrpack estimate SRC              # how many codes and sheets would this take?
qrpack pack SRC -o sheet.png     # folder -> printable sheet(s)
qrpack restore IMG... -o DIR     # sheet image(s) -> original files
qrpack calibrate                 # measure this machine's real limit (planned)
```

`--chunk BYTES` sets how many compressed bytes go into each code (default
1,200) and `--cols N` how many codes sit across a page (default 3). Exit
status is `0` on success and non-zero on any failure, so a script can never
mistake a failed run for a backup that was written.

### Every transcript below is real

They come from one run of `bash tests/capture_usage.sh` on a folder of three
small files (Markdown, an SSH public key, 400 random bytes). Re-run that script
after changing the CLI: if its output stops matching this section, this section
is wrong.

#### estimate — how much paper will this take?

```
$ qrpack estimate notes
10240 B raw -> 692 B compressed -> 951 chars encoded -> 1 codes
exit 0

$ qrpack estimate notes --chunk 300
10240 B raw -> 692 B compressed -> 1005 chars encoded -> 3 codes
exit 0
```

Two things visible here that are easy to get wrong. The 10,240 B is the *tar*,
not the files: a tar pads every entry to a 512-byte record, which is why three
small files become ten kilobytes and why compressing before chunking is not an
optimisation but the thing that makes the idea work at all. And the encoded
length grows from 951 to 1,005 characters when the chunk size shrinks, because
each code carries its own `QRPK1|digest|i/n|` header — more codes means more
headers.

#### pack — folder to printable sheet

```
$ qrpack pack notes -o sheet.png --chunk 300
3 codes on 1 page(s) -> sheet.png
exit 0

$ ls
  notes
  sheet.png
```

#### restore — sheet back to folder

```
$ qrpack restore sheet.png -o restored
restored 3 file(s) -> restored
exit 0

$ diff -r notes restored
  (no output: the restored files are byte identical)
```

That silent `diff` is the entire project in one line: the bytes that came off
the image are the bytes that went onto it.

#### Failures are loud

```
$ qrpack pack does-not-exist -o x.png
qrpack pack: does-not-exist does not exist
exit 1

$ qrpack restore blank.png -o out2
qrpack restore: no qrpack codes found in the image(s)
exit 1
```

A backup tool that exits `0` without writing anything is worse than one that
crashes, so every failure path returns non-zero with a message naming the cause
instead of a traceback.

#### Environment these were captured on

```
$ python3 -m qrpack.cli --version
qrpack 0.0.1

$ python -m pytest -q
125 passed in 3.81s
```

#### calibrate

Not yet implemented, so there is no transcript to paste. It is tracked in
issues #41, #42 and #43; the planned output is a payload-size ladder with a
pixels-per-module column and one recommended `--chunk` value. The measurements
it will automate are in Measured Findings above.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
qrpack --help    # the console script is installed
```

Read `CONTRIBUTING.md` first. Work is tracked in `PLAN.md` and GitHub issues.

## Licence

MIT.
