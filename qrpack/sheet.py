"""Render QR payloads as single symbols or printable A4 sheets.

The QRPK1 payload is never modified. Page labels are outside the QR quiet zone.
"""

from __future__ import annotations

from io import BytesIO
from math import ceil
from pathlib import Path
import segno
from PIL import Image, ImageDraw, ImageFont

# A4 at 300 DPI. PNGs carry DPI metadata; PDFs have actual A4 dimensions.
PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
DPI = 300
MARGIN = 80
HEADER_HEIGHT = 150
FOOTER_HEIGHT = 80
CELL_GAP = 24
LABEL_HEIGHT = 56
QUIET_ZONE = 4

# Error-correction level, as a parameter rather than a constant, because it is
# the main knob deciding whether a *printed* code still scans: "l" recovers
# ~7% of a damaged symbol, "h" ~30%, at the cost of more modules in the same
# physical square. Calibration (#11) has to sweep it to produce a
# pixels-per-module table, so it cannot be baked in.
#
# "m" stays the default: it is what every sheet rendered so far used, so
# existing output and tests are unaffected.
ECC_LEVELS = ("l", "m", "q", "h")
DEFAULT_ECC = "m"


def _check_ecc(ecc: str) -> str:
    """Normalise and validate an error-correction level.

    Accepts either case so a CLI flag like `-e H` behaves like `h`. Returns the
    lowercase level for segno.
    """
    if not isinstance(ecc, str):
        raise TypeError(f"ecc must be a string, one of {ECC_LEVELS}")
    level = ecc.strip().lower()
    if level not in ECC_LEVELS:
        raise ValueError(f"unknown error-correction level {ecc!r}; expected one of {ECC_LEVELS}")
    return level


def _validated_qr(payload: str, ecc: str = DEFAULT_ECC):
    if not isinstance(payload, str):
        raise TypeError("payload must be a string")
    if not payload:
        raise ValueError("payload must not be empty")
    level = _check_ecc(ecc)
    # boost_error stays off: segno would silently raise the level when a
    # payload leaves spare capacity, which would make a measured ECC sweep
    # report a level the caller never asked for.
    return segno.make(payload, error=level, micro=False, boost_error=False)


def _check_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise TypeError("scale must be an integer")
    if scale <= 0:
        raise ValueError("scale must be positive")


def render_qr(
    payload: str,
    out_path: str | Path,
    scale: int = 8,
    ecc: str = DEFAULT_ECC,
) -> Path:
    """Save one QR as PNG, preserving the original payload.

    `ecc` is one of "l", "m", "q", "h" (case-insensitive); see ECC_LEVELS.
    """
    qr = _validated_qr(payload, ecc)
    _check_scale(scale)
    output = Path(out_path)
    if output.suffix.lower() != ".png":
        raise ValueError("output file must have a .png extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    qr.save(str(output), kind="png", scale=scale, border=QUIET_ZONE)
    return output


def render_codes(
    payloads: list[str],
    scale: int = 8,
    ecc: str = DEFAULT_ECC,
) -> list[Image.Image]:
    """Return one in-memory image per payload, all padded to a uniform cell.

    The name issue #3 asks for, and the seam the scanner needs: `make_sheet`
    writes files, but calibration (#11) and the grid cropper (#9) want the
    images themselves without touching disk.

    Every image comes back the same size even when the payloads produce
    different QR versions. That is deliberate -- the scanner locates cells by
    grid arithmetic, so a short last chunk rendering as a smaller symbol would
    shift every following cell and break cropping silently.
    """
    if not isinstance(payloads, (list, tuple)):
        raise TypeError("payloads must be a list or tuple of strings")
    if not payloads:
        raise ValueError("payloads must contain at least one QR payload")
    _check_scale(scale)
    level = _check_ecc(ecc)

    symbols = [_qr_image(_validated_qr(p, level), scale) for p in payloads]
    side = max(max(image.size) for image in symbols)
    cells = []
    for symbol in symbols:
        cell = Image.new("RGB", (side, side), "white")
        cell.paste(symbol, ((side - symbol.width) // 2, (side - symbol.height) // 2))
        cells.append(cell)
    return cells


def _qr_image(qr, scale: int) -> Image.Image:
    """Use segno's PNG renderer so QR pixels remain crisp and unresampled."""
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=QUIET_ZONE)
    buffer.seek(0)
    with Image.open(buffer) as image:
        return image.convert("RGB")


def _page_path(out_path: Path, page: int, total: int) -> Path:
    if total == 1 or out_path.suffix.lower() == ".pdf":
        return out_path
    return out_path.with_name(f"{out_path.stem}-{page:03d}{out_path.suffix}")


def make_sheet(
    payloads: list[str],
    title: str,
    out_path: str | Path,
    cols: int = 4,
    scale: int = 4,
    ecc: str = DEFAULT_ECC,
) -> tuple[int, int]:
    """Generate printable A4 PNG page(s) or one multipage PDF.

    Returns ``(number_of_pages, number_of_QR_codes)``.
    PNG pages are named ``stem-001.png``, etc. when more than one is needed;
    a single page keeps the requested path. PDF pages stay in one PDF file.

    Raise ValueError rather than silently shrink a QR when requested columns
    and module scale do not fit A4; changing module size could break scanning.
    """
    if not isinstance(payloads, (list, tuple)):
        raise TypeError("payloads must be a list or tuple of strings")
    if not payloads:
        raise ValueError("payloads must contain at least one QR payload")
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    if isinstance(cols, bool) or not isinstance(cols, int):
        raise TypeError("cols must be an integer")
    if cols < 1:
        raise ValueError("cols must be positive")
    _check_scale(scale)
    level = _check_ecc(ecc)
    output = Path(out_path)
    if output.suffix.lower() not in (".png", ".pdf"):
        raise ValueError("output file must have a .png or .pdf extension")

    # Validate all symbols before writing any output.
    qrs = [_validated_qr(payload, level) for payload in payloads]
    sizes = [qr.symbol_size(scale=scale, border=QUIET_ZONE) for qr in qrs]
    max_width = max(width for width, _ in sizes)
    max_height = max(height for _, height in sizes)
    cell_width = max_width
    cell_height = max_height + LABEL_HEIGHT
    usable_width = PAGE_WIDTH - 2 * MARGIN
    if cols * cell_width + (cols - 1) * CELL_GAP > usable_width:
        raise ValueError(
            f"{cols} QR columns at scale={scale} do not fit A4; "
            "reduce --cols or the QR scale / chunk size"
        )
    available_height = PAGE_HEIGHT - MARGIN - HEADER_HEIGHT - FOOTER_HEIGHT - MARGIN
    rows = (available_height + CELL_GAP) // (cell_height + CELL_GAP)
    if rows < 1:
        raise ValueError("QR symbol is too tall for an A4 page at this scale")

    per_page = cols * rows
    page_count = ceil(len(qrs) / per_page)
    font = ImageFont.load_default(size=30)
    label_font = ImageFont.load_default(size=24)
    pages = []
    for page_num in range(1, page_count + 1):
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        draw = ImageDraw.Draw(page)
        heading = title.strip() or "qrpack backup"
        # Clip long headings to avoid spilling off the physical sheet.
        while heading and draw.textbbox((0, 0), heading, font=font)[2] > usable_width:
            heading = heading[:-1]
        draw.text((MARGIN, MARGIN), heading, font=font, fill="black")
        draw.text(
            (MARGIN, PAGE_HEIGHT - MARGIN - 36),
            f"Page {page_num}/{page_count}  |  {len(qrs)} QR parts total",
            font=label_font, fill="black",
        )
        start = (page_num - 1) * per_page
        for i, qr in enumerate(qrs[start : start + per_page]):
            row, col = divmod(i, cols)
            x = MARGIN + col * (cell_width + CELL_GAP)
            y = MARGIN + HEADER_HEIGHT + row * (cell_height + CELL_GAP)
            symbol = _qr_image(qr, scale)
            # Center smaller QR symbols within uniform cells; preserve quiet zone.
            qr_x = x + (cell_width - symbol.width) // 2
            page.paste(symbol, (qr_x, y))
            part_no = start + i + 1
            caption = f"Part {part_no}/{len(qrs)}"
            caption_w = draw.textbbox((0, 0), caption, font=label_font)[2]
            draw.text(
                (x + (cell_width - caption_w) // 2, y + max_height + 8),
                caption, font=label_font, fill="black",
            )
        pages.append(page)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".pdf":
        pages[0].save(
            output, format="PDF", save_all=True, append_images=pages[1:],
            resolution=DPI,
        )
    else:
        for page_num, page in enumerate(pages, start=1):
            page.save(_page_path(output, page_num, page_count), format="PNG", dpi=(DPI, DPI))
    return (page_count, len(qrs))
