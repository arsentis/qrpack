# qrpack

[![CI](https://github.com/arsentis/qrpack/actions/workflows/ci.yml/badge.svg)](https://github.com/arsentis/qrpack/actions/workflows/ci.yml)

Pack a folder into printable QR codes, print it, photograph it, get the folder
back — verified byte for byte.

> **Status: working end to end.** `estimate`, `pack` and `restore` are
> implemented and a folder round-trips through a rendered sheet byte for byte
> (see the transcripts below). `calibrate` is still in progress. 133 tests.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) to get started.

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

The same codes were also tested with `QRCodeDetectorAruco`:

| ECC | QR Version | Scale 4 | Scale 6 | Scale 8 |
|---|---:|---|---|---|
| L | 26 | PASS | PASS | PASS |
| M | 30 | PASS | PASS | PASS |
| Q | 37 | PASS | PASS | PASS |

The experiments were performed using Python, Segno and OpenCV. To reproduce every number in this section, run:

```bash
python3 tests/measure_scan_decoders.py
```

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

### ECC Cost in Printed Pixels

Raising the error-correction level needs more modules, so each module gets
smaller in the same printed square. For one realistic payload (`1227`
characters: a header plus a 1,200-byte base64 chunk) in a 40 mm cell at 300 DPI
(`472` px), computed by `qrpack.calibrate.ecc_cost`:

| ECC | Version | Modules | px/module |
|---|---|---|---|
| l | 25 | 125 | 3.78 |
| m | 29 | 141 | 3.35 |
| q | 34 | 161 | 2.93 |
| h | 40 | 185 | 2.55 |

`h` recovers the most damage but needs 1.48x the modules of `l`, which drops it
to 2.55 px/module. In the sweep below, a code at 3.01 px/module already failed
on this machine, so `h` is not usable at this printed size.

The table follows from the QR specification as implemented by Segno, so it is
the same on any machine; what depends on the printer and camera is where
decoding actually fails, which is measured separately.

Reproduce:

```bash
python -c "from qrpack.calibrate import ecc_cost; \
P = 'QRPK1|0123456789abcdef|1/9|' + 'QRPKdata' * 150; \
[print(r['ecc'], r['version'], r['modules'], round(r['px_per_module'], 2)) for r in ecc_cost(P)]"
```

### Where Decoding Fails

Each code is rendered with `render_codes`, resized to one fixed square of
`472` px (a 40 mm cell at 300 DPI), optionally blurred, and decoded with
OpenCV's `QRCodeDetector`. Every code gets the same printed size, because on
paper every cell occupies the same square: a denser symbol gets fewer pixels per
module. Scaling each code by the same fraction instead would make big codes look
better than they are.

Measured with `qrpack.calibrate.sweep` at ECC `m`:

| Chunk (B) | Payload (chars) | Version | Modules | px/module | Clean | Blur 2 |
|---:|---:|---:|---:|---:|---|---|
| 100 | 163 | 9 | 61 | 7.74 | pass | pass |
| 300 | 427 | 16 | 89 | 5.30 | pass | FAIL |
| 600 | 827 | 23 | 117 | 4.03 | pass | FAIL |
| 900 | 1227 | 29 | 141 | 3.35 | pass | FAIL |
| 1200 | 1627 | 33 | 157 | 3.01 | FAIL | FAIL |
| 1500 | 2027 | 38 | 177 | 2.67 | FAIL | FAIL |

Without blur, chunk sizes 100, 300, 600, 900 survived and 1200, 1500 failed.

The pass/fail edge comes from the decoder, not only from px/module, so these rows
are measurements on this machine and not a rule.

Reproduce:

```bash
python -c "from qrpack.calibrate import sweep; [print(r) for r in sweep()]"
```

## Command line

Installing the package (see Development below) puts a `qrpack` command on your
path. `qrpack --help` lists the subcommands and `qrpack COMMAND --help` shows
the options for each.

```bash
qrpack estimate SRC              # how many codes and sheets would this take?
qrpack pack SRC -o sheet.png     # folder -> printable sheet(s)
qrpack restore IMG... -o DIR     # sheet image(s) -> original files
qrpack calibrate                 # measure which chunk size survives, recommend one
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

```
$ qrpack calibrate
payload  ver  modules  px/module  decodes
   100 B  v9        61       7.74  PASS
   300 B  v16       89       5.30  PASS
   600 B  v23      117       4.03  PASS
   900 B  v29      141       3.35  PASS
  1200 B  v33      157       3.01  fail
  1500 B  v38      177       2.67  fail

recommended --chunk : 900 B
```

Each size is rendered at one printed square (`--printed-px`, default 472 = 40 mm
at 300 DPI), so denser codes get fewer pixels per module. `--ecc`, `--blur` and
`--jpeg-quality` model your own printer and camera. The recommendation is the
largest size that passed with every smaller size also passing. The command exits
1 when nothing decodes. Note that the default `--chunk` of 1200 B fails at ECC
`m` and 472 px, so on a 40 mm cell the measured recommendation is lower.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
qrpack --help    # the console script is installed
```
## Physical Print and Recovery Test

To verify that `qrpack` works beyond digital QR generation, we conducted a physical print-and-scan experiment using an ordinary printer and a smartphone.

### Test procedure

1. Created a sample `.txt` file containing test data.
2. Generated a printable QR sheet using `qrpack pack`.
3. Printed the generated QR sheet on paper.
4. Scanned the printed QR code using a smartphone and successfully decoded its contents.
5. Photographed the printed sheet and transferred the image to a computer.
6. Restored the original file from the photograph using `qrpack restore`.
7. Verified that the recovered file matched the original.

### Results

| Test                               | Result |
|------------------------------------|--------|
| QR sheet generation                | PASS   |
| Physical printing                  | PASS   |
| Smartphone QR scanning             | PASS   |
| Payload decoding                   | PASS   |
| File restoration from photograph   | PASS   |
| Original file content verification | PASS   |

Size of the photo to be restored successfully: 340 KB
Size of the sheet generated: 45 KB
**Chunk size:** 1,200 bytes

### Findings

The experiment confirmed that a QR code generated by our `qrpack` could be printed on paper, scanned with an ordinary smartphone, and used to recover the original text file.

The successful restoration from a photograph demonstrates that the workflow can operate across both digital and physical media without requiring specialized scanning equipment.

This test used a small text file. Further experiments with larger files, multiple QR codes, different print resolutions, and varying lighting conditions would be necessary to establish the system's practical limits.

### Conclusion

The physical experiment successfully demonstrated the core `qrpack` workflow:
Original file → QR sheet → Printed paper → Smartphone photograph → Restored file

The results support the feasibility of using our printed QR codes as a backup medium for small digital artifacts.

**Original file → QR sheet → Printed paper → Smartphone photograph → Restored file**

The results support the feasibility of using printed QR codes as a backup medium for small digital artifacts.
Photographs from the run are in [`docs/images/`](docs/images):

| Image | Shows |
|---|---|
| [`original-file.jpg`](docs/images/original-file.jpg) | the source text file before packing |
| [`printed-sheet.jpg`](docs/images/printed-sheet.jpg) | the generated QR sheet, printed |
| [`print-setup.jpg`](docs/images/print-setup.jpg) | the printer and working setup |
| [`phone-capture.jpg`](docs/images/phone-capture.jpg) | capturing the printed sheet with a phone |

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT.
