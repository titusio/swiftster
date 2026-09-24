import argparse
import json
import os
from os.path import dirname, isfile, join
from urllib.parse import quote, urlparse

import qrcode
from qrcode.image.svg import SvgPathImage

# Must match TRACK_PATH in src/lib/track-code.ts.
TRACK_PATH = "t"


def track_url(origin: str, id: str) -> str:
    return f"{origin}/{TRACK_PATH}/{quote(id, safe='')}"


def render(url: str, path: str, module_mm: float, border: int) -> None:
    qr = qrcode.QRCode(
        # ERROR_CORRECT_M recovers ~15% of the code, which covers the scuffs a
        # sticker picks up without inflating it the way Q or H would.
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        # SvgPathImage sizes the document in millimetres, at box_size / 10 mm
        # per module, so scale up to take module_mm at face value.
        box_size=round(module_mm * 10),
        border=border,
        image_factory=SvgPathImage,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image().save(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render one printable QR code per track from the index "
                    "written by index-music.py.",
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
        help="directory to write the SVGs into (default: qr/ next to the index)",
    )
    parser.add_argument(
        "--module-mm",
        type=float,
        default=1.0,
        help="printed size of one QR module in mm; a track code is 41 modules "
             "wide including the border (default: 1.0, so 41mm)",
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

    with open(args.index, encoding="utf-8") as f:
        songs = json.load(f)

    output = args.output or join(dirname(args.index) or ".", "qr")
    os.makedirs(output, exist_ok=True)

    written = 0
    for song in songs:
        id = song.get("id")
        if not id:
            continue

        url = track_url(origin, id)
        path = join(output, f"{id}.svg")
        render(url, path, args.module_mm, args.border)
        written += 1

        if args.verbose:
            print(f"{path}  {url}")

    print(f"wrote {written} codes to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
