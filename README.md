# timur-images

Dockerfiles built and pushed to Docker Hub for Aikido UI testing. Each case is its own Hub repository, tagged `latest`. Hub names start with `timur-images-` so container auto-link (name match) and SBOM matching can suggest connecting them to this GitHub repo, unless a folder has a `hub-name` file.

| Image | `FROM` | Aikido harden image? |
| --- | --- | --- |
| [`timurkri/timur-images-has-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden) | `python:3.13-slim` | yes |
| [`timurkri/timur-images-has-harden-pending-fix:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden-pending-fix) | `node:22-alpine` | yes — later switch to `docker.aikido.io/<token>/node:22-alpine` |
| [`timurkri/timur-images-no-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-no-harden) | `httpd:2.4-alpine` | no |
| [`timurkri/in-use-harden-image:latest`](https://hub.docker.com/r/timurkri/in-use-harden-image) | `docker.aikido.io/1d624ff6a3842cfbc99ca/alpine:3.18` | already using one (this is the custom base) |
| [`timurkri/timur-images-from-in-use-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-from-in-use-harden) | `timurkri/in-use-harden-image:latest` | transitive — parent is built FROM an Aikido image |

`has-harden` and `has-harden-pending-fix` install a small app dependency set (see `requirements.txt` / `package.json` next to those Dockerfiles) so SBOM matching has something other than the base image to score against this repo.

```bash
npm run rebuild
```

Rebuilds, pushes, and marks public every folder under `images/` that has a Dockerfile. Default Hub name is `timurkri/timur-images-<folder>:latest`. A `hub-name` file overrides that (`in-use-harden-image` publishes as `timurkri/in-use-harden-image`). Images that `FROM` another image in this repo are built and pushed after their parent.

After rebuild, rescan the **new** Hub names in Aikido (old `timurkri/has-harden` etc. will not match). The GitHub repo `timur-images` must already be connected in the same workspace. Name-based suggestions come from the auto-link cron; SBOM suggestions from Container link suggestions (needs `sbom_repo_matching`).
