#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tag="${1:-}"

[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]] || {
  printf '{"result":"invalid","reason":"tag must match vMAJOR.MINOR.PATCH-alpha","tag":"%s"}\n' "$tag" >&2
  exit 2
}

git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf '%s\n' '{"result":"invalid","reason":"release check requires a Git worktree"}' >&2
  exit 2
}

local_tag_object="$(git -C "$repo_root" show-ref --verify --hash "refs/tags/$tag")" || {
  printf '{"result":"invalid","reason":"required refs/tags/%s is missing"}\n' "$tag" >&2
  exit 2
}
tag_target="$(git -C "$repo_root" rev-parse "refs/tags/$tag^{commit}")" || {
  printf '{"result":"invalid","reason":"tag %s does not resolve to a commit"}\n' "$tag" >&2
  exit 2
}
checkout_head="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$checkout_head" == "$tag_target" ]] || {
  printf '{"result":"invalid","reason":"checkout HEAD does not equal tag target","tag":"%s"}\n' "$tag" >&2
  exit 1
}

remote_tag_object="$(git -C "$repo_root" ls-remote --exit-code --refs origin "refs/tags/$tag" | awk 'NR == 1 {print $1}')" || {
  printf '{"result":"invalid","reason":"remote controlled tag is missing","tag":"%s"}\n' "$tag" >&2
  exit 1
}
[[ "$remote_tag_object" == "$local_tag_object" ]] || {
  printf '{"result":"invalid","reason":"tag object differs from origin; tag is mutable or checkout is stale","tag":"%s"}\n' "$tag" >&2
  exit 1
}
remote_tag_object_recheck="$(git -C "$repo_root" ls-remote --exit-code --refs origin "refs/tags/$tag" | awk 'NR == 1 {print $1}')" || exit 1
[[ "$remote_tag_object_recheck" == "$remote_tag_object" ]] || {
  printf '{"result":"invalid","reason":"tag changed during preflight","tag":"%s"}\n' "$tag" >&2
  exit 1
}

QF_RELEASE_COMMIT="$tag_target" "$repo_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed
printf '{"result":"pass","tag":"%s","commit":"%s","p0":"closed","tag_object":"%s"}\n' "$tag" "$tag_target" "$local_tag_object"
