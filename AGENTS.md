# Working in this repo

swiftster is a self-hosted Hitster: a SvelteKit app that streams a track when
you scan its printed QR card. The README explains the game and how a music
library has to be laid out — read it before touching the scripts.

Half of this project is physical. Cards get printed, cut and handed to people,
and a printed card cannot be patched. Changes that reach paper deserve more care
than the code alone suggests.

## Environment

Everything lives in the flake: `nix develop`, or `nix develop --command <cmd>`
for one-offs. `python3`, `just` and `ruff` are not on the bare PATH.

`.env` is not loaded by `nix develop`. `just` loads it, so prefer the recipes;
running a script directly means passing `--origin` and the library path
yourself.

A dev server is usually already running on `127.0.0.1:5173` — curl it instead of
starting another. If one is not running, ask before starting one.

```sh
just index -v        # rebuild songs.json from $MEDIA_DIR
just qr              # render music/qr/cards.pdf and the per-track SVGs
just check           # svelte-check; keep it at 0 errors
nix develop --command ruff check scripts/
```

`scripts/index-music.py` has a pre-existing `I001` import-order warning. Leave it
unless you are already rewriting those imports.

## Invariants

**The app never reveals the answer.** The card is the only place the title
lives. `/t/[id]` is handed the id and nothing else, the `<title>` is neutral, and
`mediaSession.metadata` is overwritten so the lock screen does not leak the FLAC
tags. Anything that puts artist, album, title or year into that page — in the
markup, in the data payload, in a fetch — breaks the game. The JSON endpoints
under `/api/tracks` return metadata by design; the game does not call them.

**Track ids are permanent.** They come out of the filename and go into codes that
are already printed on cards. Never change how an id is derived, and never
renumber a library to make something tidier.

**Duplex geometry is easy to break and invisible until it is printed.** Backs are
laid out mirrored so each one lands behind its own front: columns reverse for a
long-edge flip, and a short-edge flip additionally rotates the whole page. A
part-filled last sheet pads to the full grid before mirroring. If you touch
`build()` in `scripts/make-qr.py`, verify both flips and a part-filled page —
rendering the PDF with `pdftoppm` and looking at it is the quickest check.

**Anything that changes the back of a card changes its height.** The text block
is centred and the font shrinks to fit, so adding a line eats the slack. Check
the longest titles, which are the Speak Now vault tracks.

`music/` is gitignored: the library, `songs.json` and the generated cards never
get committed.

## Style

Match the file you are in. Across the repo: comments explain *why*, in prose,
and there are few of them — don't narrate what the next line already says.

- Svelte 5 runes throughout (`$props`, `$state`, `$derived`, `$effect`). Tabs,
  single quotes, Tailwind utilities in the markup.
- Python: 4 spaces, double quotes, type hints on signatures, small named
  functions. The scripts use the standard library plus `qrcode` and `reportlab`
  — adding a dependency means adding it to the flake, so prefer not to.
- Keep server-only code under `src/lib/server/`.

## Git

Commit messages are imperative and describe the intent, not the diff: "Drop the
reveal: the answer is on the back of the card". Body only when the why is not
obvious from the subject.

**Do not add a `Co-Authored-By` trailer.** Commit only when asked, and never
push unasked.
