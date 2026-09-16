# timur-images

Three Dockerfiles built and pushed to Docker Hub for Aikido UI testing. Each case is its own repository, tagged `latest`.

| Image | `FROM` | Aikido harden image? |
| --- | --- | --- |
| [`timurkri/has-harden:latest`](https://hub.docker.com/r/timurkri/has-harden) | `python:3.13-slim` | yes |
| [`timurkri/has-harden-pending-fix:latest`](https://hub.docker.com/r/timurkri/has-harden-pending-fix) | `node:22-alpine` | yes — later switch to `docker.aikido.io/<token>/node:22-alpine` |
| [`timurkri/no-harden:latest`](https://hub.docker.com/r/timurkri/no-harden) | `httpd:2.4-alpine` | no |

```bash
npm run rebuild
```

Rebuilds, pushes, and marks public every folder under `images/` that has a Dockerfile, as `timurkri/<folder>:latest`.
