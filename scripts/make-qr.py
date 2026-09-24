import argparse
import json
import os
from html import escape
from os.path import dirname, isfile, join
from string import Template
from urllib.parse import quote, urlparse

import qrcode

# Must match TRACK_PATH in src/lib/track-code.ts.
TRACK_PATH = "t"

# Width and height in mm of the paper the sheet is laid out for.
PAGES = {
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}


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


def path_data(matrix: list[list[bool]]) -> str:
    """One path covering every dark module, in module units."""
    parts = []

    for y, row in enumerate(matrix):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue

            # A whole run as one rectangle rather than a square per module:
            # same picture, and it keeps the sheet a fraction of the size.
            run = 1
            while x + run < len(row) and row[x + run]:
                run += 1
            parts.append(f"M{x} {y}h{run}v1h-{run}z")
            x += run

    return "".join(parts)


def svg(matrix: list[list[bool]], size: str) -> str:
    n = len(matrix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
        f'<path fill="#000" d="{path_data(matrix)}"/></svg>'
    )


STYLE = Template("""
:root {
	--card: ${card}mm;
	--cols: ${cols};
	--rows: ${rows};
}

@page {
	size: ${page_w}mm ${page_h}mm;
	margin: 0;
}

html,
body {
	margin: 0;
	padding: 0;
	background: #fff;
	color: #000;
	font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

.hint {
	margin: 0;
	padding: 8mm;
	background: #fffbe6;
	border-bottom: 1px solid #e5d9a0;
	font-size: 10pt;
	line-height: 1.5;
}

.sheet {
	box-sizing: border-box;
	width: ${page_w}mm;
	height: ${page_h}mm;
	display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
}

.grid {
	display: grid;
	grid-template-columns: repeat(var(--cols), var(--card));
	grid-template-rows: repeat(var(--rows), var(--card));
}

.card {
	box-sizing: border-box;
	/* Cards abut, so one cut serves the two either side of it. The guide is
	   hairline and grey: visible while cutting, unobtrusive if you miss. */
	border: 0.2mm dashed #bbb;
	padding: calc(var(--card) * 0.08);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: calc(var(--card) * 0.02);
	text-align: center;
	overflow: hidden;
}

.blank {
	border-color: transparent;
}

/* A short-edge flip turns the sheet about its horizontal axis, so the whole
   back page lands upside down. Turning each card back over undoes it, and the
   text reads the right way up once the card is turned left to right. */
.upside-down .card {
	transform: rotate(180deg);
}

.qr {
	width: 100%;
	height: 100%;
}

.artist {
	font-size: calc(var(--card) * 0.048);
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: #555;
}

.title {
	font-size: calc(var(--card) * 0.085);
	font-weight: 600;
	line-height: 1.15;
	text-wrap: balance;
}

.title.small {
	font-size: calc(var(--card) * 0.068);
}

.title.tiny {
	font-size: calc(var(--card) * 0.054);
}

.album {
	font-size: calc(var(--card) * 0.048);
	color: #555;
	line-height: 1.2;
}

.track {
	margin-top: calc(var(--card) * 0.03);
	font-size: calc(var(--card) * 0.042);
	letter-spacing: 0.04em;
	color: #888;
}

@media print {
	.hint {
		display: none;
	}

	.sheet {
		break-after: page;
		page-break-after: always;
	}

	.sheet:last-of-type {
		break-after: auto;
		page-break-after: auto;
	}
}

@media screen {
	body {
		background: #e8e8e8;
	}

	.sheet {
		background: #fff;
		margin: 6mm auto;
		box-shadow: 0 1mm 3mm rgba(0, 0, 0, 0.2);
	}
}
""")

DOCUMENT = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>swiftster cards</title>
<style>${style}</style>
</head>
<body>
<p class="hint">
	${count} cards, ${per_page} to a sheet. Print <strong>double-sided</strong>,
	flipping on the <strong>${flip} edge</strong>, at <strong>100% scale</strong>
	(not &ldquo;fit to page&rdquo;) — the backs are laid out to match that flip.
	Cut along the guides.
</p>
${sheets}
</body>
</html>
""")


def title_class(title: str) -> str:
    """Long titles step down a size rather than overflowing the card."""
    if len(title) > 38:
        return "title tiny"
    if len(title) > 22:
        return "title small"
    return "title"


def front(matrix: list[list[bool]]) -> str:
    return f'<div class="card">{svg(matrix, "100%")}</div>'


def back(song: dict) -> str:
    title = escape(str(song.get("title") or song["id"]))
    artist = escape(str(song.get("artist") or ""))
    album = escape(str(song.get("album") or ""))
    track = song.get("trackNumber")

    lines = ['<div class="card">']
    if artist:
        lines.append(f'<div class="artist">{artist}</div>')
    lines.append(f'<div class="{title_class(title)}">{title}</div>')
    if album:
        lines.append(f'<div class="album">{album}</div>')
    if track:
        lines.append(f'<div class="track">Track {int(track)}</div>')
    lines.append("</div>")
    return "".join(lines)


BLANK = '<div class="card blank"></div>'


def mirror(cells: list[str], cols: int, flip: str) -> list[str]:
    """
    Reorder a page's cells so each back lands behind its own front.

    Flipping on the long edge of a portrait sheet turns it about the vertical
    axis, so the columns run the other way; the short edge turns it about the
    horizontal axis, so the rows do.
    """
    rows = [cells[i : i + cols] for i in range(0, len(cells), cols)]
    if flip == "long":
        rows = [row[::-1] for row in rows]
    else:
        rows = rows[::-1]
    return [cell for row in rows for cell in row]


def sheet(cells: list[str], grid_class: str = "grid") -> str:
    return f'<div class="sheet"><div class="{grid_class}">{"".join(cells)}</div></div>'


def build_sheets(
    songs: list[dict],
    matrices: dict[str, list[list[bool]]],
    cols: int,
    rows: int,
    flip: str,
) -> str:
    per_page = cols * rows
    out = []

    for start in range(0, len(songs), per_page):
        page = songs[start : start + per_page]
        # Padded to a full grid so a part-filled last page keeps its geometry
        # and the mirrored backs still line up with the fronts.
        fronts = [front(matrices[song["id"]]) for song in page]
        backs = [back(song) for song in page]
        fronts += [BLANK] * (per_page - len(fronts))
        backs += [BLANK] * (per_page - len(backs))

        out.append(sheet(fronts))
        out.append(
            sheet(
                mirror(backs, cols, flip),
                "grid" if flip == "long" else "grid upside-down",
            )
        )

    return "\n".join(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render printable track cards from the index written by "
                    "index-music.py: a QR code on the front, the answer on "
                    "the back.",
    )
    parser.add_argument(
        "index",
        help="path to songs.json",
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
        help="directory to write cards.html and the SVGs into "
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
        help="paper the sheet is laid out for (default: a4)",
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
        help="which edge your printer flips on for double-sided printing; the "
             "backs are mirrored to match (default: long)",
    )
    parser.add_argument(
        "--module-mm",
        type=float,
        default=1.0,
        help="printed size of one QR module in mm in the per-track SVGs; a "
             "track code is 41 modules wide including the border "
             "(default: 1.0, so 41mm). The sheet scales its codes to the card.",
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

    if not isfile(args.index):
        print(f"not a file: {args.index}")
        return 1

    page_w, page_h = PAGES[args.page]
    # A hair of slack, so a card that divides the page exactly is not rounded
    # out of the grid by floating point.
    cols = int((page_w - 2 * args.margin_mm + 1e-9) / args.card_mm)
    rows = int((page_h - 2 * args.margin_mm + 1e-9) / args.card_mm)
    if cols < 1 or rows < 1:
        print(f"a {args.card_mm:g}mm card does not fit on {args.page} "
              f"with a {args.margin_mm:g}mm margin")
        return 1

    with open(args.index, encoding="utf-8") as f:
        songs = json.load(f)

    songs = [song for song in songs if song.get("id")]
    if not songs:
        print(f"no songs with an id in {args.index}")
        return 1

    output = args.output or join(dirname(args.index) or ".", "qr")
    os.makedirs(output, exist_ok=True)

    matrices = {}
    for song in songs:
        id = song["id"]
        url = track_url(origin, id)
        matrices[id] = modules(url, args.border)

        path = join(output, f"{id}.svg")
        with open(path, "w", encoding="utf-8") as f:
            size = f"{len(matrices[id]) * args.module_mm:g}mm"
            f.write(svg(matrices[id], size) + "\n")

        if args.verbose:
            print(f"{path}  {url}")

    style = STYLE.substitute(
        card=f"{args.card_mm:g}",
        cols=cols,
        rows=rows,
        page_w=f"{page_w:g}",
        page_h=f"{page_h:g}",
    )
    document = DOCUMENT.substitute(
        style=style,
        count=len(songs),
        per_page=cols * rows,
        flip=args.flip,
        sheets=build_sheets(songs, matrices, cols, rows, args.flip),
    )

    cards = join(output, "cards.html")
    with open(cards, "w", encoding="utf-8") as f:
        f.write(document)

    print(f"wrote {len(songs)} codes to {output}")
    print(f"wrote {cards} — {cols}x{rows} cards a sheet, "
          f"double-sided, flipping on the {args.flip} edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
