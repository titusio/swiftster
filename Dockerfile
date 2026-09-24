# swiftster — the server only.
#
# Indexing the library and rendering the cards stay on the host, in the nix
# shell: those are one-off prep steps, and keeping Python out leaves this image
# to Node and the build output.

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime dependencies only. `prepare` runs svelte-kit sync, which isn't
# installed here; the script's `|| echo ''` already swallows that.
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --omit=dev

FROM node:24-alpine
WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    MEDIA_DIR=/music

COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/build ./build
COPY package.json ./

# songs.json holds paths relative to the library root, so the mount point is
# ours to choose; it does not have to match the host.
VOLUME ["/music"]

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD wget -q --spider "http://127.0.0.1:${PORT}/" || exit 1

CMD ["node", "build"]
