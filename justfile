# swiftster — dev tasks
#
# `just` with no arguments lists everything.

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

# Vite's port. Pinned rather than auto-incrementing, so `tailscale serve`
# always proxies to the port we actually started. Override with PORT in .env.
port := env("PORT", "5173")

_default:
    @just --list --unsorted

# Vite dev server, reachable from other devices on the LAN.
dev:
    npm run dev -- --host 0.0.0.0 --port {{ port }} --strictPort

# Type-check the project.
check:
    npm run check

# Production build.
build:
    npm run build

# Rebuild songs.json from the music library.
index *args:
    python3 scripts/index-music.py "$MEDIA_DIR" {{ args }}

# Render printable cards — a QR code per track pointing at PUBLIC_ORIGIN, with
# the track's name on the back — plus one SVG per code. Print cards.pdf
# double-sided, at 100%.
qr *args:
    python3 scripts/make-qr.py "${MEDIA_INDEX:-$MEDIA_DIR/songs.json}" {{ args }}

# ---------------------------------------------------------------------------
# Tailscale
#
# Browsers only expose getUserMedia (camera, for the QR scanner) in a secure
# context. http://<lan-ip> is not one, so phones refuse to hand over the
# camera. Tailscale Serve terminates TLS with a publicly-trusted cert, which
# iOS accepts without installing a profile.
# ---------------------------------------------------------------------------

# Dev server + HTTPS proxy in one go. Ctrl-C tears both down.
[group('tailscale')]
up:
    #!/usr/bin/env bash
    set -euo pipefail

    just _require-tailscale

    npm run dev -- --host 0.0.0.0 --port {{ port }} --strictPort &
    dev_pid=$!
    trap 'kill "$dev_pid" 2>/dev/null || true; tailscale serve --https=443 off >/dev/null 2>&1 || true' EXIT INT TERM

    echo "waiting for vite on :{{ port }} ..."
    for _ in $(seq 1 60); do
        if curl -sf -o /dev/null "http://127.0.0.1:{{ port }}/"; then break; fi
        if ! kill -0 "$dev_pid" 2>/dev/null; then
            echo "vite exited before it started listening" >&2
            exit 1
        fi
        sleep 0.5
    done

    tailscale serve --bg --https=443 "http://127.0.0.1:{{ port }}" >/dev/null
    echo
    echo "  tailnet → https://$(just _tsname)/"
    echo
    wait "$dev_pid"

# Point the HTTPS proxy at an already-running dev server.
[group('tailscale')]
share:
    @just _require-tailscale
    tailscale serve --bg --https=443 "http://127.0.0.1:{{ port }}"

# Tear the HTTPS proxy down.
[group('tailscale')]
unshare:
    tailscale serve --https=443 off

# Show what Tailscale is currently proxying.
[group('tailscale')]
status:
    @tailscale serve status

# Print the tailnet URL.
[group('tailscale')]
url:
    @echo "https://$(just _tsname)/"

# Fails unless tailscaled is up and the tailnet can issue HTTPS certs.
_require-tailscale:
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v tailscale >/dev/null; then
        echo "tailscale not found on PATH" >&2
        exit 1
    fi
    if ! tailscale status >/dev/null 2>&1; then
        echo "tailscaled is not running or this node is logged out — try 'tailscale up'" >&2
        exit 1
    fi
    if [ "$(tailscale status --json | jq '.CertDomains | length')" -eq 0 ]; then
        echo "no HTTPS cert domains for this tailnet — enable HTTPS in the Tailscale admin console" >&2
        exit 1
    fi

# This node's MagicDNS name, without the trailing dot.
_tsname:
    @tailscale status --json | jq -r '.Self.DNSName | rtrimstr(".")'
