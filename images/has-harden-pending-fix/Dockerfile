# Aikido has a harden image for this base.
# Later change FROM to: docker.aikido.io/<token>/node:22-alpine
FROM node:22-alpine

LABEL org.opencontainers.image.title="timur-images-has-harden-pending-fix"

WORKDIR /app
COPY package.json .
RUN npm install --omit=dev

CMD ["node", "-e", "console.log('timur-images: has-harden-pending-fix')"]
