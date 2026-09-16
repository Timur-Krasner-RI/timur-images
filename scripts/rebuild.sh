#!/bin/sh
set -e

NS=timurkri
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

echo "images:${CASES}"

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

for case in $CASES; do
	docker build --pull -t "$NS/$case:latest" "$IMAGES/$case"
done

for case in $CASES; do
	docker push "$NS/$case:latest"
done

failed=0
for case in $CASES; do
	json=$(repo_json "$case")
	if is_public "$json"; then
		echo "public: ${NS}/${case}"
		continue
	fi
	if ! make_public "$case"; then
		echo "not public: ${NS}/${case}" >&2
		failed=1
	fi
done

exit "$failed"
