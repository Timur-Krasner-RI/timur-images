# timur-images

Dockerfiles built and pushed to Docker Hub for Aikido UI testing. Each case is its own Hub repository, tagged `latest`. Hub names start with `timur-images-` so container auto-link (name match) and SBOM matching can suggest connecting them to this GitHub repo, unless a folder has a `hub-name` file.

| Image | `FROM` | Aikido harden image? |
| --- | --- | --- |
| [`timurkri/timur-images-has-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden) | `python:3.10-slim` | yes — older slim tag so Aikido shows CVE reduction |
| [`timurkri/timur-images-has-harden-pending-fix:latest`](https://hub.docker.com/r/timurkri/timur-images-has-harden-pending-fix) | `node:22-bookworm-slim` | yes — later switch to `docker.aikido.io/<token>/node:22-bookworm-slim` |
| [`timurkri/timur-images-no-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-no-harden) | `httpd:2.4-alpine` | no |
| [`timurkri/in-use-harden-image:latest`](https://hub.docker.com/r/timurkri/in-use-harden-image) | `docker.aikido.io/1d624ff6a3842cfbc99ca/alpine:3.18` | already using one (this is the custom base) |
| [`timurkri/timur-images-from-in-use-harden:latest`](https://hub.docker.com/r/timurkri/timur-images-from-in-use-harden) | `timurkri/in-use-harden-image:latest` | transitive — parent is built FROM an Aikido image |
| [`timurkri/node22alpine:latest`](https://hub.docker.com/r/timurkri/node22alpine) | `node:22-bookworm-slim` | catalog harden exists; official tag still has many CVEs Aikido fixes |
| [`timurkri/timur-images-alpine318:latest`](https://hub.docker.com/r/timurkri/timur-images-alpine318) | `alpine:3.17` | catalog harden exists; 3.17 (not 3.18) so Aikido actually reduces open CVEs |
| [`timurkri/timur-images-curl820:latest`](https://hub.docker.com/r/timurkri/timur-images-curl820) | `curlimages/curl:8.20.0` | official curl image |
| [`timurkri/timur-images-curl820-aikido:latest`](https://hub.docker.com/r/timurkri/timur-images-curl820-aikido) | `docker.aikido.io/1d624ff6a3842cfbc99ca/curlimages/curl:8.20.0` | already using one (Aikido curl base) |
| [`timurkri/root-php-8-4-26-apache:latest`](https://hub.docker.com/r/timurkri/root-php-8-4-26-apache) | `cr.root.io/php:8.4.26-apache` | already using one (Root PHP apache base) |
| [`timurkri/root-php-8-5-11-cli:latest`](https://hub.docker.com/r/timurkri/root-php-8-5-11-cli) | `cr.root.io/php:8.5.11-cli` | already using one (Root PHP cli base) |
| [`timurkri/root-php-8-5-11-fpm:latest`](https://hub.docker.com/r/timurkri/root-php-8-5-11-fpm) | `cr.root.io/php:8.5.11-fpm` | already using one (Root PHP fpm base) |
| [`timurkri/upstream-php-8-4-26-apache:latest`](https://hub.docker.com/r/timurkri/upstream-php-8-4-26-apache) | `php:8.4.26-apache` | official Docker Hub PHP apache image |
| [`timurkri/upstream-php-8-5-11-cli:latest`](https://hub.docker.com/r/timurkri/upstream-php-8-5-11-cli) | `php:8.5.11-cli` | official Docker Hub PHP cli image |
| [`timurkri/upstream-php-8-5-11-fpm:latest`](https://hub.docker.com/r/timurkri/upstream-php-8-5-11-fpm) | `php:8.5.11-fpm` | official Docker Hub PHP fpm image |
| [`timurkri/upstream-node-24-22-1-bookworm-slim:latest`](https://hub.docker.com/r/timurkri/upstream-node-24-22-1-bookworm-slim) | `node:24.22.1-bookworm-slim` | yes — later maintained patch `node:24.22.3-bookworm-slim` |
| [`timurkri/timur-images-node-24-22-3-bookworm-slim:latest`](https://hub.docker.com/r/timurkri/timur-images-node-24-22-3-bookworm-slim) | `node:24.22.3-bookworm-slim` | yes — already the latest maintained patch of that line |
| [`timurkri/timur-images-node-24-22-1-alpine323:latest`](https://hub.docker.com/r/timurkri/timur-images-node-24-22-1-alpine323) | `node:24.22.1-alpine3.23` | yes — later maintained patch `node:24.22.3-alpine3.23`, not bookworm-slim |
| [`timurkri/timur-images-node-24-22-slim:latest`](https://hub.docker.com/r/timurkri/timur-images-node-24-22-slim) | `node:24.22-slim` | yes — major.minor plus suffix, and that tag is maintained |
| [`timurkri/timur-images-ubuntu-22-04:latest`](https://hub.docker.com/r/timurkri/timur-images-ubuntu-22-04) | `ubuntu:22.04` | yes — major.minor tag, exact maintained entry (`22.04-fips` is a different suffix) |
| [`timurkri/timur-images-node-24-22-1-bookworm:latest`](https://hub.docker.com/r/timurkri/timur-images-node-24-22-1-bookworm) | `node:24.22.1-bookworm` | no — hardened, not maintained; bookworm-slim is a different suffix |
| [`timurkri/timur-images-node-24-22-1-slim:latest`](https://hub.docker.com/r/timurkri/timur-images-node-24-22-1-slim) | `node:24.22.1-slim` | no — maintained `node:24.22-slim` is an older patch; `slim-hardened` is a different suffix |
| [`timurkri/timur-images-node-18-20-7-bookworm-slim:latest`](https://hub.docker.com/r/timurkri/timur-images-node-18-20-7-bookworm-slim) | `node:18.20.7-bookworm-slim` | no — hardened, not maintained, and no newer maintained patch |
| [`timurkri/timur-images-node-22-bookworm:latest`](https://hub.docker.com/r/timurkri/timur-images-node-22-bookworm) | `node:22-bookworm` | no — not a patch tag; maintained `node:22-bookworm-slim` is a different tag |
| [`timurkri/timur-images-ubuntu-jammy:latest`](https://hub.docker.com/r/timurkri/timur-images-ubuntu-jammy) | `ubuntu:jammy` | no — named tag, not an exact maintained entry |

`has-harden` and `has-harden-pending-fix` install a small app dependency set (see `requirements.txt` / `package.json` next to those Dockerfiles) so SBOM matching has something other than the base image to score against this repo.

`scripts/php-oom-test.py` builds a temporary app layer on the local `root-php-*` and `upstream-php-*` images and pushes requests past the soft and hard memory limits. The app lives in `images/php-app`. These images do not include the PHP source test suite, so this does not run the upstream `oom_*.phpt` files.

```bash
npm run rebuild
python3 scripts/php-oom-test.py
```

Rebuilds, pushes, and marks public every folder under `images/` that has a Dockerfile. Default Hub name is `timurkri/timur-images-<folder>:latest`. A `hub-name` file overrides that (`in-use-harden-image` publishes as `timurkri/in-use-harden-image`). Images that `FROM` another image in this repo are built and pushed after their parent.

After rebuild, rescan the **new** Hub names in Aikido (old `timurkri/has-harden` etc. will not match). The GitHub repo `timur-images` must already be connected in the same workspace. Name-based suggestions come from the auto-link cron; SBOM suggestions from Container link suggestions (needs `sbom_repo_matching`).
