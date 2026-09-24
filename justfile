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
# Container
#
# The published image from ghcr, not a dev server: this is the one that keeps
# running. The music library is mounted read-only, so indexing and card
# rendering still happen out here on the host.
# ---------------------------------------------------------------------------

# It listens on localhost only; TLS is the reverse proxy's job — see the README.

# Pull the published image and start it.
[group('container')]
serve:
    podman compose pull
    podman compose up -d

# Stop the container.
[group('container')]
unserve:
    podman compose down

# Follow the container's log.
[group('container')]
serve-logs:
    podman compose logs -f

# Build the image locally, under the name the workflow publishes.
[group('container')]
image tag="dev":
    podman build -t "ghcr.io/titusio/swiftster:{{ tag }}" .

# Re-index, then restart: the server reads songs.json once and keeps it.
[group('container')]
serve-index *args:
    just index {{ args }}
    podman compose restart

# ---------------------------------------------------------------------------
# Tailscale — for development.
#
# Browsers only expose getUserMedia (camera, for the QR scanner) in a secure
# context. http://<lan-ip> is not one, so phones refuse to hand over the
# camera. Tailscale Serve terminates TLS with a publicly-trusted cert, which
# iOS accepts without installing a profile, and needs no DNS record.
#
# A deployment that stays up wants a real reverse proxy instead; the README
# has the Caddy and nginx configs.
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

# Defaults to the dev server; pass a port to share something else, such as the
# container's.

# Point the HTTPS proxy at an already-running server.
[group('tailscale')]
share target=port:
    @just _require-tailscale
    tailscale serve --bg --https=443 "http://127.0.0.1:{{ target }}"

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
