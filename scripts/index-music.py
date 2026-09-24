import argparse
import json
import os
from os.path import join, isdir, relpath
import re
from dataclasses import asdict, dataclass

NAME = re.compile(r"^(\d+)-(.+)-(\d+)\.flac$")
YEAR = re.compile(r"(?:19|20)\d\d")

# FLAC metadata block type 4 is the Vorbis comment block.
COMMENT_BLOCK = 4


@dataclass
class Song:
    id: str
    artist: str
    album: str
    trackNumber: int
    title: str
    year: int | None
    path: str

    def __str__(self) -> str:
        return (
            f"{self.artist} - {self.album} - [{self.trackNumber}] "
            f"{self.title} ({self.year or '????'}) ({self.id})"
        )


def comments(path: str) -> dict[str, str]:
    """
    The file's Vorbis comments, keyed by upper-cased tag name.

    A FLAC is the marker "fLaC" followed by metadata blocks, each a four-byte
    header — a last-block flag, a type, and a 24-bit big-endian length — then
    that many bytes of body. The comment block holds a vendor string and a
    list of "NAME=value" strings, all of them length-prefixed little-endian.
    """
    tags: dict[str, str] = {}

    try:
        with open(path, "rb") as f:
            if f.read(4) != b"fLaC":
                return tags

            while True:
                header = f.read(4)
                if len(header) < 4:
                    return tags

                last = header[0] & 0x80
                body = f.read(int.from_bytes(header[1:], "big"))

                if header[0] & 0x7F == COMMENT_BLOCK:
                    break
                if last:
                    return tags
    except OSError:
        return tags

    at = 4 + int.from_bytes(body[:4], "little")
    count = int.from_bytes(body[at:at + 4], "little")
    at += 4

    for _ in range(count):
        size = int.from_bytes(body[at:at + 4], "little")
        at += 4
        name, _, value = body[at:at + size].decode("utf-8", "replace").partition("=")
        at += size
        # A tag may repeat; the first one wins.
        tags.setdefault(name.upper(), value)

    return tags


def released(tags: dict[str, str]) -> int | None:
    """
    The year the recording in the file came out.

    The phonogram year first: DATE is the album's, which for a re-recording
    may be the year of the album it re-records — Fearless (Taylor's Version)
    is tagged 2008. Both versions of a song can end up in the deck, so they
    have to date apart.
    """
    for tag in ("COPYRIGHT", "DATE", "YEAR"):
        found = YEAR.search(tags.get(tag, ""))
        if found:
            return int(found.group())

    return None


def collect(path: str) -> list[Song]:
    songs: list[Song] = []

    for root, dirs, files in os.walk(path):
        dirs.sort()

        # The library is laid out as <artist>/<album>/<track>-<title>-<id>.flac,
        # so only directories exactly two levels deep hold songs.
        parts = relpath(root, path).split(os.sep)
        if len(parts) != 2:
            continue
        artist, album = parts

        tracks = []
        for filename in files:
            m = NAME.match(filename)
            if m is None:
                continue

            track, title, id = m.group(1), m.group(2), m.group(3)
            tracks.append((int(track), Song(
                id=id,
                artist=artist,
                album=album,
                trackNumber=0,
                title=title,
                year=released(comments(join(root, filename))),
                # Relative to the library root, so the index stays valid
                # wherever the library is mounted. The server joins it
                # back onto MEDIA_DIR.
                path=join(*parts, filename),
            )))

        # os.walk yields files in arbitrary order; restore the album's track order.
        tracks.sort(key=lambda t: t[0])
        for i in range(len(tracks)):
            tracks[i][1].trackNumber = i + 1
        songs.extend(song for _, song in tracks)

    return songs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index a music library laid out as <artist>/<album>/"
                    "<track>-<title>-<id>.flac and write it out as JSON.",
    )
    parser.add_argument(
        "--media-dir",
        default=os.environ.get("MEDIA_DIR"),
        help="root of the music library to scan (default: $MEDIA_DIR)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.environ.get("MEDIA_INDEX"),
        help="where to write the JSON (default: $MEDIA_INDEX, or songs.json "
             "inside the library)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print the songs as they are indexed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.media_dir:
        print("no music library: pass --media-dir or set MEDIA_DIR")
        return 1

    if not isdir(args.media_dir):
        print(f"not a directory: {args.media_dir}")
        return 1

    output = args.output or join(args.media_dir, "songs.json")
    songs = collect(args.media_dir)

    if args.verbose:
        for song in songs:
            print(song)

    with open(output, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps the curly apostrophes in the titles readable.
        json.dump([asdict(song) for song in songs], f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {len(songs)} songs to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
