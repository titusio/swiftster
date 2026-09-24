# swiftster

A self-hosted Hitster, played with your own music library.

Every track gets a printed card: a QR code on the front, the answer on the back.
Scan a card with your phone, the track starts playing on its own, and you call
out what it is. Then you turn the card over — artist, title, album, release year
— and find out. The app itself never shows you the answer, and never sends it to
the browser, so there is nothing to peek at.

Nothing leaves your machine: the songs stream from a directory on disk, and the
phones reach the server over your own network.

```
music library ──▶ just index ──▶ songs.json ──▶ just qr ──▶ cards.pdf
                                      │
                                      └────────▶ SvelteKit ──▶ phone
```

## Setup

The Nix flake carries everything — Node, Python with `qrcode` and `reportlab`,
`just`, the language servers:

```sh
nix develop
npm install
cp .env.example .env
```

Without Nix you need Node 24, `just`, and a Python 3 with `qrcode` and
`reportlab`.

Then fill in `.env`:

| variable | what it is |
| --- | --- |
| `MEDIA_DIR` | absolute path to the music library |
| `MEDIA_INDEX` | optional, where `songs.json` lives if not inside `MEDIA_DIR` |
| `PUBLIC_ORIGIN` | the origin baked into the printed QR codes |
| `ALLOWED_HOSTS` | hostnames Vite will serve |

## Getting the files right

This is the part that takes the care. The indexer reads the *library layout*,
not the tags — the path is the source of truth for artist, album and title, and
only the release year comes out of the file itself.

### Layout

```
$MEDIA_DIR/
└── <artist>/
    └── <album>/
        └── <track>-<title>-<id>.flac
```

Exactly two levels deep: a directory that is not `<artist>/<album>/` is walked
but never indexed, so cover art and a stray `songs.json` do no harm.

The filename has to match `^(\d+)-(.+)-(\d+)\.flac$`, and anything that doesn't
is skipped silently:

- **`<track>`** — the track's position in the album. Only the ordering matters:
  the songs are sorted by it and then numbered from 1, so gaps close up and a
  compilation that starts at 0 still comes out right.
- **`<title>`** — printed on the card exactly as written here, curly
  apostrophes and all. `Love Story (Taylor’s Version)` is fine; a hyphen in the
  title is fine too, because only the first and last hyphens are structural.
- **`<id>`** — digits, unique across the whole library. This is what the QR code
  points at, so treat it as permanent: **re-using or renumbering an id
  invalidates a card that is already printed.** Whatever your ripper or tagger
  assigns works, as long as it never collides.

Both an original album and its re-recording can live in the library at once.
They are separate directories with separate ids, so `Fearless` and `Fearless
(Taylor's Version)` are two different cards for two different answers.

### Tags

One tag is read, and only one: the release year, from the first four-digit year
found in **`COPYRIGHT`**, falling back to `DATE` and then `YEAR`.

The phonogram year comes first on purpose. `DATE` is the *album's* date and lies
about re-recordings — every track of *Fearless (Taylor's Version)* is tagged
`2008-11-08`, the date of the album it re-records. `COPYRIGHT` says `℗ 2021`,
which is the year that recording actually came out. It is finer-grained than the
album, too: on *Fearless (Platinum Edition)* it dates the six bonus tracks to
2009 and the original thirteen to 2008.

If your files came from somewhere that strips the copyright, set it yourself —
any string holding the year will do:

```sh
metaflac --set-tag="COPYRIGHT=℗ 2008 Taylor Swift" *.flac
```

Everything else in the tags — titles, track numbers, lyrics, credits — is
ignored, so it does not matter if it is wrong.

### Converting

FLAC is what the indexer picks up. Converting from anything else, keep the
metadata:

```sh
ffmpeg -i "in.m4a" -c:a flac -map_metadata 0 "out.flac"
```

### Indexing

```sh
just index -v
```

That walks `MEDIA_DIR` and writes `songs.json` next to it — one entry per track
with its id, artist, album, track number, title, year and relative path. `-v`
prints each song as it goes:

```
Taylor Swift - Fearless (Platinum Edition) - [1] Jump Then Fall (2009) (3169104)
```

Read the list before printing anything. A song you expected and don't see has a
filename the pattern rejected; a `(????)` instead of a year means no usable
copyright or date tag. The server reads the index once and keeps it, so restart
it after re-indexing.

The library and the index are gitignored; only the scripts are in the repo.

## Making the cards

```sh
just qr
```

Writes `cards.pdf` into `qr/` beside the index, plus one SVG per code in case
you want to lay a card out yourself.

The PDF is A4, twelve 60mm cards a sheet, in front/back page pairs with dashed
cut guides. **Print it double-sided at 100%** — "Actual size", never "Fit to
page", or the codes shrink and the backs stop lining up with their fronts. The
backs are laid out for a printer that flips on the long edge; if yours flips on
the short edge, pass `--flip short`:

```sh
just qr --flip short --card-mm 55 --page letter
```

Print one sheet first and hold it up to the light before committing to the whole
deck.

The codes encode `$PUBLIC_ORIGIN/t/<id>`, which is why changing the origin means
reprinting — a stable name the server can move behind is worth setting up first.

## Playing

```sh
just up
```

Starts the dev server and a Tailscale HTTPS proxy, and prints the URL to open on
the phones. HTTPS is not optional: browsers only hand over the camera in a
secure context, so a plain `http://<lan-ip>` cannot scan anything. Tailscale
Serve terminates TLS with a publicly trusted certificate, which iOS accepts
without installing a profile.

Open the URL, point the camera at a card, and the round begins. A phone's own
camera app works too, since the code is a plain URL.

By default only the opening seconds play; the picker in the header sets how
many, and pressing play again after the clip runs the track to the end.

## Commands

| command | |
| --- | --- |
| `just` | list every recipe |
| `just index [-v]` | rebuild `songs.json` from the library |
| `just qr [args]` | render `cards.pdf` and the SVGs |
| `just dev` | dev server on the LAN, no HTTPS |
| `just up` | dev server plus the Tailscale HTTPS proxy |
| `just share` / `just unshare` | point the proxy at an already-running server, or tear it down |
| `just url` / `just status` | the tailnet URL, what is being proxied |
| `just check` | type-check |
| `just build` | production build |

`just qr --help` and `just index --help` list the rest of the flags: card size,
paper, margins, quiet zone, where to write.

## How it fits together

- `scripts/index-music.py` — walks the library, reads the FLAC comment block,
  writes `songs.json`.
- `scripts/make-qr.py` — the QR codes and the printable PDF, drawn with
  reportlab.
- `src/lib/server/media.ts` — loads and caches the index, resolves track paths.
- `src/routes/+page.svelte` — the scanner.
- `src/routes/t/[id]` — a round. It is handed the id and nothing else.
- `src/routes/api/tracks/[id]/stream` — ranged audio streaming, so seeking
  works.
- `src/routes/api/tracks` — the index as JSON, for when you want to look
  something up yourself. The game never calls it.
