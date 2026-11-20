# qrpack

Pack a folder into printable QR codes, print it, photograph it, get the folder
back — verified byte for byte.

> **Status: in development.** This README documents the goal. Measured results
> are added as the features land; see `PLAN.md` for the schedule and
> `CONTRIBUTING.md` before your first commit.

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
1,200). The command parses its arguments today; `estimate`, `pack` and
`restore` are connected to the library during the sprint and, until then, exit
with a non-zero status and a "not implemented yet" message, so a script can
never mistake a stub for a backup that was written.

Exit status: `0` on success, non-zero on any failure.

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
