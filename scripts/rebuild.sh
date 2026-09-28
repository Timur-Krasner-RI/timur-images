#!/bin/sh
set -e

NS=timurkri
# Prefix Hub repo names with the GitHub repo name so Aikido name-matching
# can suggest linking these containers to timur-images.
IMAGE_PREFIX=timur-images
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
IMAGES="$ROOT/images"

CASES=
for dir in "$IMAGES"/*/; do
	[ -d "$dir" ] || continue
	[ -f "${dir}Dockerfile" ] || continue
	CASES="$CASES $(basename "$dir")"
done

if [ -z "${CASES# }" ]; then
	echo "No image folders with a Dockerfile under ${IMAGES}" >&2
	exit 1
fi

hub_name() {
	name_file="$IMAGES/$1/hub-name"
	if [ -f "$name_file" ]; then
		head -n 1 "$name_file" | tr -d '\r'
		return
	fi
	printf '%s-%s' "$IMAGE_PREFIX" "$1"
}

first_from() {
	awk '
		$1 == "FROM" {
			for (i = 2; i <= NF; i++) {
				if ($i ~ /^-/) {
					if ($i !~ /=/) i++
					continue
				}
				print $i
				exit
			}
		}
	' "$1"
}

image_ref_name() {
	ref=${1%%@*}
	printf '%s' "${ref%%:*}"
}

local_from_case() {
	want=$(image_ref_name "$1")
	for c in $CASES; do
		if [ "$NS/$(hub_name "$c")" = "$want" ]; then
			printf '%s' "$c"
			return 0
		fi
	done
	return 1
}

# Parents (FROM another folder in this repo) must build and push before children.
ORDERED=
remaining=$CASES
guard=0
while [ -n "$(printf '%s' "$remaining" | tr -d '[:space:]')" ]; do
	guard=$((guard + 1))
	if [ "$guard" -gt 50 ]; then
		echo "cycle in image FROM deps:${remaining}" >&2
		exit 1
	fi
	progress=
	next=
	for img in $remaining; do
		from=$(first_from "$IMAGES/$img/Dockerfile")
		dep=
		if dep=$(local_from_case "$from"); then
			found=
			for o in $ORDERED; do
				if [ "$o" = "$dep" ]; then
					found=1
					break
				fi
			done
			if [ -z "$found" ]; then
				next="$next $img"
				continue
			fi
		fi
		ORDERED="$ORDERED $img"
		progress=1
	done
	if [ -z "$progress" ]; then
		echo "unresolved FROM deps:${next}" >&2
		exit 1
	fi
	remaining=$next
done

echo "images:${ORDERED}"

repo_json() {
	curl -sS "https://hub.docker.com/v2/repositories/${NS}/$1/"
}

is_public() {
	printf '%s' "$1" | jq -e '.is_private == false' >/dev/null 2>&1
}

hub_token() {
	creds_store=$(jq -r '.credsStore // empty' "$HOME/.docker/config.json")
	creds=$(printf 'https://index.docker.io/v1/' | "docker-credential-${creds_store}" get)
	login_body=$(printf '%s' "$creds" | jq '{username:.Username,password:.Secret}')
	curl -sS -H 'Content-Type: application/json' -d "$login_body" https://hub.docker.com/v2/users/login/ \
		| jq -r '.token // .access_token // empty'
}

make_public() {
	repo=$1
	token=$(hub_token)
	if [ -z "$token" ]; then
		echo "Docker Hub API login failed; ${NS}/${repo} is still private" >&2
		return 1
	fi

	for scheme in JWT Bearer; do
		resp=$(curl -sS -w '\n%{http_code}' -X PATCH \
			-H "Authorization: ${scheme} ${token}" \
			-H 'Content-Type: application/json' \
			-d '{"is_private":false}' \
			"https://hub.docker.com/v2/repositories/${NS}/${repo}/")
		code=$(printf '%s' "$resp" | tail -n 1)
		body=$(printf '%s' "$resp" | sed '$d')
		if [ "$code" = "200" ] && is_public "$body"; then
			echo "public: ${NS}/${repo}"
			return 0
		fi
		echo "PATCH ${scheme} ${NS}/${repo} -> HTTP ${code}" >&2
		printf '%s' "$body" | jq -r '.message // .detail // .error // empty' >&2 || true
	done
	return 1
}

failed=0
for img in $ORDERED; do
	repo=$(hub_name "$img")
	docker build --pull -t "$NS/${repo}:latest" "$IMAGES/$img"
	docker push "$NS/${repo}:latest"

	json=$(repo_json "$repo")
	if is_public "$json"; then
		echo "public: ${NS}/${repo}"
		continue
	fi
	if ! make_public "$repo"; then
		echo "not public: ${NS}/${repo}" >&2
		failed=1
	fi
done

exit "$failed"
