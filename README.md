# timur-images

Three Dockerfiles built and pushed to Docker Hub for Aikido UI testing. Each case is its own Hub repository, tagged `latest`. Hub names start with `timur-images-` so container auto-link (name match) and SBOM matching can suggest connecting them to this GitHub repo.

| Image | `FROM` | Aikido harden image? |
| --- | --- | --- |
| [`timurkri/timur-images-has-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden) | `python:3.13-slim` | yes |
| [`timurkri/timur-images-has-harden-pending-fix:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden-pending-fix) | `node:22-alpine` | yes — later switch to `docker.aikido.io/<token>/node:22-alpine` |
| [`timurkri/timur-images-no-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-no-harden) | `httpd:2.4-alpine` | no |

`has-harden` and `has-harden-pending-fix` install a small app dependency set (see `requirements.txt` / `package.json` next to those Dockerfiles) so SBOM matching has something other than the base image to score against this repo.

```bash
npm run rebuild
```

Rebuilds, pushes, and marks public every folder under `images/` that has a Dockerfile, as `timurkri/timur-images-<folder>:latest`.

After rebuild, rescan the **new** Hub names in Aikido (old `timurkri/has-harden` etc. will not match). The GitHub repo `timur-images` must already be connected in the same workspace. Name-based suggestions come from the auto-link cron; SBOM suggestions from Container link suggestions (needs `sbom_repo_matching`).
