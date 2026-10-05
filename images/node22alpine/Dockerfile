# Official Node 22. bookworm-slim (not alpine) so Aikido has a large CVE reduction to show.
# Catalog node:22-alpine only fixes 1 CVE vs official; node:22-bookworm-slim fixes ~50.
# Published as timurkri/node22alpine:latest (see hub-name).
FROM node:22-bookworm-slim

LABEL org.opencontainers.image.title="node22alpine"

CMD ["node", "-e", "console.log('timur-images: node22alpine')"]
