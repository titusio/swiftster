import argparse
import json
import os
from os.path import join, isdir, relpath
import re
from dataclasses import asdict, dataclass

NAME = re.compile(r"^(\d+)-(.+)-(\d+)\.flac$")


@dataclass
class Song:
    id: str
    artist: str
    album: str
    trackNumber: int
    title: str
    path: str

    def __str__(self) -> str:
        return f"{self.artist} - {self.album} - [{self.trackNumber}] {self.title} ({self.id})"


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
        "music_dir",
        help="root of the music library to scan",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="where to write the JSON (default: songs.json inside MUSIC_DIR)",
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

    if not isdir(args.music_dir):
        print(f"not a directory: {args.music_dir}")
        return 1

    output = args.output or join(args.music_dir, "songs.json")
    songs = collect(args.music_dir)

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
