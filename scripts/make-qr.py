import argparse
import json
import os
from collections.abc import Iterator
from os.path import dirname, isfile, join
from typing import NamedTuple
from urllib.parse import quote, urlparse

import qrcode
from reportlab.lib.colors import Color, black
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

# Must match TRACK_PATH in src/lib/track-code.ts.
TRACK_PATH = "t"

# Width and height in mm of the paper a sheet can be laid out for.
PAGES = {
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}

GREY = Color(0.33, 0.33, 0.33)
FAINT = Color(0.53, 0.53, 0.53)
GUIDE = Color(0.75, 0.75, 0.75)

# Card padding, as a fraction of the card. The QR gets the rest.
PAD = 0.08


def track_url(origin: str, id: str) -> str:
    return f"{origin}/{TRACK_PATH}/{quote(id, safe='')}"


def modules(url: str, border: int) -> list[list[bool]]:
    """The QR as a square grid of dark/light modules, quiet zone included."""
    qr = qrcode.QRCode(
        # ERROR_CORRECT_M recovers ~15% of the code, which covers the scuffs a
        # card picks up without inflating it the way Q or H would.
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.get_matrix()


def runs(matrix: list[list[bool]]) -> Iterator[tuple[int, int, int]]:
    """
    Each horizontal stretch of dark modules, as (x, y, length).

    A run at a time rather than a module at a time: the same picture out of a
    fraction of the rectangles.
    """
    for y, row in enumerate(matrix):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue

            length = 1
            while x + length < len(row) and row[x + length]:
                length += 1
            yield x, y, length
            x += length


def svg(matrix: list[list[bool]], size: str) -> str:
    n = len(matrix)
    path = "".join(f"M{x} {y}h{run}v1h-{run}z" for x, y, run in runs(matrix))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
        f'<path fill="#000" d="{path}"/></svg>'
    )


def draw_qr(c: Canvas, matrix: list[list[bool]], left: float, bottom: float, size: float) -> None:
    n = len(matrix)
    module = size / n

    path = c.beginPath()
    for x, y, run in runs(matrix):
        # A PDF counts up from the bottom of the page, the matrix down from its
        # own top row.
        path.rect(left + x * module, bottom + size - (y + 1) * module, run * module, module)

    c.setFillColor(black)
    c.drawPath(path, stroke=0, fill=1)


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    line = ""

    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if line and stringWidth(candidate, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate

    if line:
        lines.append(line)
    return lines or [""]


def fit(text: str, font: str, size: float, width: float, lines: int) -> tuple[float, list[str]]:
    """
    The largest size at or below `size` that fits the text in `lines` lines.

    Measured rather than guessed from the length, because the titles run from
    "Mine" to "When Emma Falls in Love (Taylor's Version) (From The Vault)".
    """
    while size > 4:
        wrapped = wrap(text, font, size, width)
        if len(wrapped) <= lines and all(stringWidth(w, font, size) <= width for w in wrapped):
            return size, wrapped
        size -= 0.25

    return size, wrap(text, font, size, width)


class Line(NamedTuple):
    text: str
    font: str
    size: float
    colour: Color
    leading: float
    space: float = 0.0
    tracking: float = 0.0


def back_lines(song: dict, width: float, card: float) -> list[Line]:
    artist = str(song.get("artist") or "").strip()
    title = str(song.get("title") or song["id"]).strip()
    album = str(song.get("album") or "").strip()
    year = song.get("year")
    track = song.get("trackNumber")

    lines: list[Line] = []

    if artist:
        size, wrapped = fit(artist.upper(), "Helvetica", card * 0.042, width, 1)
        lines += [
            Line(w, "Helvetica", size, GREY, size * 1.3, tracking=size * 0.08) for w in wrapped
        ]

    size, wrapped = fit(title, "Helvetica-Bold", card * 0.085, width, 3)
    lines += [
        Line(w, "Helvetica-Bold", size, black, size * 1.2, space=card * 0.035 if i == 0 else 0)
        for i, w in enumerate(wrapped)
    ]

    if album:
        size, wrapped = fit(album, "Helvetica", card * 0.046, width, 2)
        lines += [
            Line(w, "Helvetica", size, GREY, size * 1.25, space=card * 0.03 if i == 0 else 0)
            for i, w in enumerate(wrapped)
        ]

    if year:
        size = card * 0.07
        lines.append(Line(str(year), "Helvetica-Bold", size, black, size * 1.2, card * 0.035))

    if track:
        size = card * 0.042
        lines.append(Line(f"Track {int(track)}", "Helvetica", size, FAINT, size * 1.25, card * 0.03))

    return lines


def draw_back(c: Canvas, song: dict, left: float, bottom: float, card: float) -> None:
    pad = card * PAD
    width = card - 2 * pad
    lines = back_lines(song, width, card)

    # Centred as a block, so a one-line title and a three-line one both sit
    # square in the middle of the card.
    total = sum(line.space + line.leading for line in lines)
    y = bottom + (card + total) / 2
    middle = left + card / 2

    for line in lines:
        y -= line.space + line.leading
        c.setFont(line.font, line.size)
        c.setFillColor(line.colour)

        # A quarter of the leading below the text box leaves room for descenders.
        baseline = y + line.leading * 0.25

        if line.tracking:
            # Letter-spacing lives on a text object, and it widens the string,
            # which drawCentredString cannot see. So measure and place it.
            span = stringWidth(line.text, line.font, line.size)
            span += line.tracking * (len(line.text) - 1)
            text = c.beginText(middle - span / 2, baseline)
            text.setFont(line.font, line.size)
            text.setFillColor(line.colour)
            text.setCharSpace(line.tracking)
            text.textOut(line.text)
            c.drawText(text)
        else:
            c.drawCentredString(middle, baseline, line.text)


def draw_guides(c: Canvas, x: float, y: float, cols: int, rows: int, card: float) -> None:
    """Cut lines across the whole grid: one cut serves the cards either side."""
    c.setStrokeColor(GUIDE)
    c.setLineWidth(0.2 * mm)
    c.setDash(2, 2)

    for i in range(cols + 1):
        c.line(x + i * card, y, x + i * card, y + rows * card)
    for j in range(rows + 1):
        c.line(x, y + j * card, x + cols * card, y + j * card)

    c.setDash()


def build(
    path: str,
    songs: list[dict],
    matrices: dict[str, list[list[bool]]],
    page: tuple[float, float],
    card: float,
    cols: int,
    rows: int,
    flip: str,
) -> None:
    page_w, page_h = page
    per_page = cols * rows

    # The grid is centred, which leaves at least the requested margin and keeps
    # the sheet unchanged under the half turn a short-edge flip needs.
    left = (page_w - cols * card) / 2
    foot = (page_h - rows * card) / 2

    def cell(i: int) -> tuple[float, float]:
        row, col = divmod(i, cols)
        return left + col * card, foot + (rows - 1 - row) * card

    c = Canvas(path, pagesize=page, pageCompression=1)
    c.setTitle("swiftster cards")

    for start in range(0, len(songs), per_page):
        sheet = songs[start : start + per_page]

        draw_guides(c, left, foot, cols, rows, card)
        for i, song in enumerate(sheet):
            x, y = cell(i)
            draw_qr(c, matrices[song["id"]], x + card * PAD, y + card * PAD, card * (1 - 2 * PAD))
        c.showPage()

        if flip == "short":
            # Flipping on the short edge turns the sheet about its horizontal
            # axis, so the back comes out of the printer upside down. Turning
            # the page over is the same layout given the same half turn.
            c.translate(page_w, page_h)
            c.rotate(180)

        draw_guides(c, left, foot, cols, rows, card)
        for i, song in enumerate(sheet):
            # Behind its own front: a flip reverses the columns, so a card in
            # the first column of the front is in the last column of the back.
            row, col = divmod(i, cols)
            x, y = cell(row * cols + (cols - 1 - col))
            draw_back(c, song, x, y, card)
        c.showPage()

    c.save()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render printable track cards from the index written by "
                    "index-music.py: a QR code on the front, the answer on "
                    "the back.",
    )
    parser.add_argument(
        "--index",
        default=os.environ.get("MEDIA_INDEX"),
        help="path to songs.json (default: $MEDIA_INDEX, or songs.json inside "
             "the library)",
    )
    parser.add_argument(
        "--media-dir",
        default=os.environ.get("MEDIA_DIR"),
        help="root of the music library, which is where the index is looked "
             "for (default: $MEDIA_DIR)",
    )
    parser.add_argument(
        "--origin",
        default=os.environ.get("PUBLIC_ORIGIN"),
        help="origin the codes point at, e.g. https://host.ts.net "
             "(default: $PUBLIC_ORIGIN)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="directory to write cards.pdf and the SVGs into "
             "(default: qr/ next to the index)",
    )
    parser.add_argument(
        "--card-mm",
        type=float,
        default=60.0,
        help="printed size of one square card in mm (default: 60)",
    )
    parser.add_argument(
        "--page",
        choices=sorted(PAGES),
        default="a4",
        help="paper to lay the sheet out for (default: a4)",
    )
    parser.add_argument(
        "--margin-mm",
        type=float,
        default=8.0,
        help="smallest margin to leave around the grid in mm; whatever is left "
             "over is shared out evenly (default: 8)",
    )
    parser.add_argument(
        "--flip",
        choices=("long", "short"),
        default="long",
        help="which edge the printer flips on for double-sided printing; the "
             "backs are laid out to match (default: long)",
    )
    parser.add_argument(
        "--module-mm",
        type=float,
        default=1.0,
        help="printed size of one QR module in mm in the per-track SVGs; a "
             "track code is 41 modules wide including the border "
             "(default: 1.0, so 41mm). The PDF scales its codes to the card.",
    )
    parser.add_argument(
        "--border",
        type=int,
        default=4,
        help="quiet zone in modules; below 4 scanners get unreliable (default: 4)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print each code as it is written",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.origin:
        print("no origin: pass --origin or set PUBLIC_ORIGIN")
        return 1

    # Printed codes are immutable, so a typo here is expensive to discover later.
    origin = args.origin.rstrip("/")
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"origin must be a URL like https://host.example: {args.origin}")
        return 1

    index = args.index or (join(args.media_dir, "songs.json") if args.media_dir else "")
    if not index:
        print("no index: pass --index or --media-dir, or set MEDIA_INDEX "
              "or MEDIA_DIR")
        return 1

    if not isfile(index):
        print(f"not a file: {index}")
        return 1

    page_w, page_h = (side * mm for side in PAGES[args.page])
    card = args.card_mm * mm
    margin = args.margin_mm * mm

    # A hair of slack, so a card that divides the page exactly is not rounded
    # out of the grid by floating point.
    cols = int((page_w - 2 * margin + 1e-6) / card)
    rows = int((page_h - 2 * margin + 1e-6) / card)
    if cols < 1 or rows < 1:
        print(f"a {args.card_mm:g}mm card does not fit on {args.page} "
              f"with a {args.margin_mm:g}mm margin")
        return 1

    with open(index, encoding="utf-8") as f:
        songs = [song for song in json.load(f) if song.get("id")]

    if not songs:
        print(f"no songs with an id in {index}")
        return 1

    output = args.output or join(dirname(index) or ".", "qr")
    os.makedirs(output, exist_ok=True)

    matrices = {}
    for song in songs:
        id = song["id"]
        url = track_url(origin, id)
        matrices[id] = modules(url, args.border)

        path = join(output, f"{id}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg(matrices[id], f"{len(matrices[id]) * args.module_mm:g}mm") + "\n")

        if args.verbose:
            print(f"{path}  {url}")

    cards = join(output, "cards.pdf")
    build(cards, songs, matrices, (page_w, page_h), card, cols, rows, args.flip)

    sheets = -(-len(songs) // (cols * rows))
    print(f"wrote {len(songs)} codes to {output}")
    print(f"wrote {cards} — {cols}x{rows} {args.card_mm:g}mm cards on {args.page}, "
          f"{sheets} sheet{'s' if sheets != 1 else ''} double-sided, "
          f"flipping on the {args.flip} edge, printed at 100%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())