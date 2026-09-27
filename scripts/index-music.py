import argparse
import json
import os
from collections import Counter
from collections.abc import Callable, Iterator
from os.path import join, isdir, relpath, splitext
import re
from dataclasses import asdict, dataclass
from typing import BinaryIO


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


def vorbis_comments(body: bytes, at: int = 0) -> dict[str, str]:
    """
    Vorbis comments, keyed by upper-cased tag name.

    A length-prefixed vendor string, a count, then that many "NAME=value"
    strings, each length-prefixed as well, all of them little-endian. FLAC and
    Ogg both carry the block verbatim, only behind different headers.
    """
    tags: dict[str, str] = {}

    at += 4 + int.from_bytes(body[at:at + 4], "little")
    count = int.from_bytes(body[at:at + 4], "little")
    at += 4

    for _ in range(count):
        if at >= len(body):
            break

        size = int.from_bytes(body[at:at + 4], "little")
        at += 4
        field = body[at:at + size]
        at += size

        if len(field) < size:
            break

        name, _, value = field.decode("utf-8", "replace").partition("=")
        # A tag may repeat; the first one wins.
        tags.setdefault(name.upper(), value)

    return tags


# FLAC metadata block type 4 is the Vorbis comment block.
COMMENT_BLOCK = 4


def flac_tags(f: BinaryIO) -> dict[str, str]:
    """
    A FLAC is the marker "fLaC" followed by metadata blocks, each a four-byte
    header — a last-block flag, a type, and a 24-bit big-endian length — then
    that many bytes of body.
    """
    if f.read(4) != b"fLaC":
        return {}

    while True:
        header = f.read(4)
        if len(header) < 4:
            return {}

        body = f.read(int.from_bytes(header[1:], "big"))

        if header[0] & 0x7F == COMMENT_BLOCK:
            return vorbis_comments(body)
        if header[0] & 0x80:
            return {}


# Pages read looking for the comment packet. It is the second one in the
# stream, so this only has to outlast a first page with cover art in it.
OGG_PAGES = 8


def ogg_tags(f: BinaryIO) -> dict[str, str]:
    """
    Ogg carries packets in pages: a 27-byte header, a table of segment sizes,
    then the segments themselves. The comment packet can spill over a page
    boundary, so the early pages are read back to back and the packet found by
    the marker it opens with — a type byte and "vorbis" in Vorbis, "OpusTags"
    in Opus. What follows either marker is a Vorbis comment block.
    """
    data = bytearray()

    for _ in range(OGG_PAGES):
        header = f.read(27)
        if len(header) < 27 or header[:4] != b"OggS":
            break

        lacing = f.read(header[26])
        data += f.read(sum(lacing))

    for marker in (b"\x03vorbis", b"OpusTags"):
        at = data.find(marker)
        if at >= 0:
            return vorbis_comments(bytes(data), at + len(marker))

    return {}


# The ID3 frames worth reading, under the Vorbis name each one stands in for.
ID3_FRAMES = {"TCOP": "COPYRIGHT", "TDRC": "DATE", "TDRL": "DATE", "TYER": "DATE"}

ID3_ENCODINGS = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}


def syncsafe(data: bytes) -> int:
    """Seven bits of each byte, so a size can never be mistaken for a frame sync."""
    size = 0
    for byte in data:
        size = size << 7 | byte & 0x7F
    return size


def id3_text(frame: bytes) -> str:
    """A text frame opens with one byte saying how the rest of it is encoded."""
    if not frame:
        return ""
    return frame[1:].decode(ID3_ENCODINGS.get(frame[0], "latin-1"), "replace").strip("\0")


def id3v1_tags(f: BinaryIO) -> dict[str, str]:
    """The 128-byte trailer an old ripper leaves behind; the year sits 93 bytes in."""
    try:
        f.seek(-128, os.SEEK_END)
    except OSError:
        return {}

    trailer = f.read(128)
    if trailer[:3] != b"TAG":
        return {}

    return {"YEAR": trailer[93:97].decode("latin-1", "replace")}


def id3_tags(f: BinaryIO) -> dict[str, str]:
    """
    An ID3v2 tag is "ID3", a two-byte version, a flag byte and a sync-safe
    size, then frames of a four-byte name, a size, two flag bytes and a body.
    Version 2.4 writes the frame sizes sync-safe too; 2.3 writes them plain.

    Anything older, or a tag with nothing usable in it, falls back to the
    ID3v1 trailer — which is all a lot of old rips ever had.
    """
    head = f.read(10)
    if head[:3] != b"ID3" or head[3] < 3:
        return id3v1_tags(f)

    major = head[3]
    body = f.read(syncsafe(head[6:10]))
    at = 0

    # An extended header sits before the frames. 2.4 counts its own size field
    # in the length it gives; 2.3 does not.
    if head[5] & 0x40:
        at = syncsafe(body[:4]) if major >= 4 else int.from_bytes(body[:4], "big") + 4

    tags: dict[str, str] = {}

    while at + 10 <= len(body):
        name = body[at:at + 4].decode("latin-1")
        # The tag is padded out with zeroes once the frames run out.
        if not name.strip("\0"):
            break

        if major >= 4:
            size = syncsafe(body[at + 4:at + 8])
        else:
            size = int.from_bytes(body[at + 4:at + 8], "big")

        at += 10
        frame = body[at:at + size]
        at += size

        key = ID3_FRAMES.get(name)
        if key:
            tags.setdefault(key, id3_text(frame))

    return tags or id3v1_tags(f)


# The path to an m4a's tags is moov.udta.meta.ilst. `meta` is the one container
# along the way that puts a version and flags before its children.
MP4_CONTAINERS = (b"moov", b"udta", b"meta", b"ilst")

# The tag atoms worth reading, under the Vorbis name each one stands in for.
MP4_ATOMS = {b"\xa9day": "DATE", b"cprt": "COPYRIGHT"}


def mp4_atoms(f: BinaryIO, end: int) -> Iterator[tuple[bytes, int, int]]:
    """
    Each atom between the current position and `end`, as (name, body, stop).

    An atom is a four-byte big-endian size and a four-byte name, then a body of
    whatever is left of that size. A size of 1 means the real one follows as
    eight bytes; a size of 0 means the atom runs to the end.
    """
    while True:
        at = f.tell()
        if at + 8 > end:
            return

        header = f.read(8)
        if len(header) < 8:
            return

        size = int.from_bytes(header[:4], "big")
        body = at + 8

        if size == 1:
            size = int.from_bytes(f.read(8), "big")
            body = at + 16
        elif size == 0:
            size = end - at

        stop = min(at + size, end)
        if stop <= body:
            return

        yield header[4:8], body, stop
        f.seek(at + size)


def mp4_value(f: BinaryIO, body: int, stop: int) -> str:
    """
    The text inside a tag atom, which keeps it in a "data" atom behind four
    bytes of type and four of locale.
    """
    f.seek(body)

    for name, start, end in mp4_atoms(f, stop):
        if name == b"data" and end - start > 8:
            f.seek(start + 8)
            return f.read(end - start - 8).decode("utf-8", "replace")

    return ""


def mp4_walk(f: BinaryIO, end: int, tags: dict[str, str], depth: int = 0) -> None:
    for name, body, stop in mp4_atoms(f, end):
        if name in MP4_CONTAINERS and depth < len(MP4_CONTAINERS):
            f.seek(body + 4 if name == b"meta" else body)
            mp4_walk(f, stop, tags, depth + 1)
        elif name in MP4_ATOMS:
            value = mp4_value(f, body, stop)
            if value:
                tags.setdefault(MP4_ATOMS[name], value)


def mp4_tags(f: BinaryIO) -> dict[str, str]:
    """An MP4 is a tree of atoms; only the ones on the way to the tags are opened."""
    tags: dict[str, str] = {}

    end = f.seek(0, os.SEEK_END)
    f.seek(0)
    mp4_walk(f, end, tags)

    return tags


# The INFO fields worth reading, under the Vorbis name each one stands in for.
RIFF_INFO = {b"ICOP": "COPYRIGHT", b"ICRD": "DATE"}


def riff_chunks(data: bytes) -> Iterator[tuple[bytes, bytes]]:
    """Each chunk of a RIFF body, as (name, body)."""
    at = 0

    while at + 8 <= len(data):
        size = int.from_bytes(data[at + 4:at + 8], "little")
        yield data[at:at + 4], data[at + 8:at + 8 + size]
        at += 8 + size + (size & 1)


def riff_tags(f: BinaryIO) -> dict[str, str]:
    """
    A WAV is "RIFF", a size and "WAVE", then chunks of a four-byte name, a
    little-endian size and a body padded out to an even length. The tags, if
    there are any, are an INFO list among them.
    """
    if f.read(4) != b"RIFF":
        return {}

    f.seek(8)
    if f.read(4) != b"WAVE":
        return {}

    while True:
        header = f.read(8)
        if len(header) < 8:
            return {}

        size = int.from_bytes(header[4:8], "little")
        if header[:4] != b"LIST":
            f.seek(size + (size & 1), os.SEEK_CUR)
            continue

        body = f.read(size + (size & 1))
        if body[:4] != b"INFO":
            continue

        tags: dict[str, str] = {}
        for name, value in riff_chunks(body[4:size]):
            if name in RIFF_INFO:
                tags.setdefault(RIFF_INFO[name], value.decode("utf-8", "replace").strip("\0"))

        return tags


# A reader per container, and between them the formats a library may hold. The
# server picks what it serves by extension as well, so this has to stay a
# subset of MIME_TYPES in src/lib/server/media.ts: indexing a format it cannot
# serve prints a card whose code leads to a 404.
READERS: dict[str, Callable[[BinaryIO], dict[str, str]]] = {
    "flac": flac_tags,
    "mp3": id3_tags,
    "m4a": mp4_tags,
    "ogg": ogg_tags,
    "opus": ogg_tags,
    "wav": riff_tags,
}

NAME = re.compile(rf"^(\d+)-(.+)-(\d+)\.(?:{'|'.join(READERS)})$", re.IGNORECASE)
YEAR = re.compile(r"(?:19|20)\d\d")


def tags(path: str) -> dict[str, str]:
    """
    The file's tags, under the Vorbis names `released` looks for.

    Every container keeps them somewhere else, so each one gets a reader and
    they all answer in Vorbis comments. A file that gives nothing up — no tag
    block, or a truncated one — comes back empty rather than raising.
    """
    reader = READERS.get(splitext(path)[1].lower().lstrip("."))
    if reader is None:
        return {}

    try:
        with open(path, "rb") as f:
            return reader(f)
    except OSError:
        return {}


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

        # The library is laid out as <artist>/<album>/<track>-<title>-<id>.<ext>,
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
                year=released(tags(join(root, filename))),
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


def duplicates(songs: list[Song]) -> list[str]:
    counts = Counter(song.id for song in songs)
    return sorted(id for id, seen in counts.items() if seen > 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index a music library laid out as <artist>/<album>/"
                    "<track>-<title>-<id>.<ext>, where <ext> is one of "
                    f"{', '.join(READERS)}, and write it out as JSON.",
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

    # Both of these end up on paper if they go unnoticed, so say them out loud.
    for id in duplicates(songs):
        print(f"id {id} is claimed by more than one file, and so would be by "
              "more than one card — two copies of a song in different formats "
              "will do this")

    undated = sum(1 for song in songs if song.year is None)
    if undated:
        print(f"{undated} song{'s' if undated != 1 else ''} without a usable "
              "copyright or date tag: their cards print without a year")

    with open(output, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps the curly apostrophes in the titles readable.
        json.dump([asdict(song) for song in songs], f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {len(songs)} songs to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
