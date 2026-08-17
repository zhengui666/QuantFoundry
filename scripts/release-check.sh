#!/usr/bin/env bash
set -euo pipefail

script_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="${QF_RELEASE_CHECK_ROOT:-$script_root}"
verifier_root="${QF_RELEASE_CHECK_VERIFIER_ROOT:-$repo_root}"
tag="${1:-}"

[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]] || {
  printf '{"result":"invalid","reason":"tag must match vMAJOR.MINOR.PATCH-alpha","tag":"%s"}\n' "$tag" >&2
  exit 2
}

git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf '%s\n' '{"result":"invalid","reason":"release check requires a Git worktree"}' >&2
  exit 2
}

remote_url="$(git -C "$repo_root" remote get-url origin 2>/dev/null || true)"
canonical_repository="zhengui666/QuantFoundry"
[[ -z "${GITHUB_REPOSITORY:-}" || "$GITHUB_REPOSITORY" == "$canonical_repository" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"GITHUB_REPOSITORY is not the trusted repository"}' >&2
  exit 1
}
case "$remote_url" in
  "https://github.com/${canonical_repository}.git"|"https://github.com/${canonical_repository}"|"git@github.com:${canonical_repository}.git"|"git@github.com:${canonical_repository}") ;;
  *)
    printf '%s\n' '{"result":"invalid","reason":"origin is not the canonical GitHub repository"}' >&2
    exit 1
    ;;
esac

local_tag_object="$(git -C "$repo_root" show-ref --verify --hash "refs/tags/$tag")" || {
  printf '{"result":"invalid","reason":"required refs/tags/%s is missing"}\n' "$tag" >&2
  exit 2
}
tag_target="$(git -C "$repo_root" rev-parse "${local_tag_object}^{commit}")" || {
  printf '{"result":"invalid","reason":"tag %s does not resolve to a commit"}\n' "$tag" >&2
  exit 2
}
checkout_head="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$checkout_head" == "$tag_target" ]] || {
  printf '{"result":"invalid","reason":"checkout HEAD does not equal tag target","tag":"%s"}\n' "$tag" >&2
  exit 1
}
trusted_branch="${QF_RELEASE_BRANCH:-origin/main}"
git -C "$repo_root" rev-parse --verify "${trusted_branch}^{commit}" >/dev/null 2>&1 || {
  printf '{"result":"invalid","reason":"trusted release branch is unavailable","branch":"%s"}\n' "$trusted_branch" >&2
  exit 1
}
git -C "$repo_root" merge-base --is-ancestor "$tag_target" "$trusted_branch" || {
  printf '{"result":"invalid","reason":"tag target is not on the trusted release branch","tag":"%s"}\n' "$tag" >&2
  exit 1
}

git -C "$verifier_root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf '%s\n' '{"result":"invalid","reason":"verifier root is not a Git worktree"}' >&2
  exit 1
}
verifier_head="$(git -C "$verifier_root" rev-parse HEAD)"
verifier_status="$(git -C "$verifier_root" status --porcelain=v1 --untracked-files=all)"
[[ "$verifier_head" == "$tag_target" && -z "$verifier_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"verifier code is not clean at the trusted tag commit"}' >&2
  exit 1
}

worktree_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ -z "$worktree_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"release check requires a clean worktree"}' >&2
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

final_head="$(git -C "$repo_root" rev-parse HEAD)"
final_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ "$final_head" == "$tag_target" && -z "$final_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"worktree or HEAD changed during release preflight"}' >&2
  exit 1
}

QF_RELEASE_COMMIT="$tag_target" "$verifier_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed
post_p0_head="$(git -C "$repo_root" rev-parse HEAD)"
post_p0_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ "$post_p0_head" == "$tag_target" && -z "$post_p0_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"worktree or HEAD changed during P0 verification"}' >&2
  exit 1
}
post_p0_tag_object="$(git -C "$repo_root" ls-remote --exit-code --refs origin "refs/tags/$tag" | awk 'NR == 1 {print $1}')" || exit 1
[[ "$post_p0_tag_object" == "$local_tag_object" ]] || {
  printf '{"result":"invalid","reason":"tag changed during P0 verification","tag":"%s"}\n' "$tag" >&2
  exit 1
}
printf '{"result":"pass","tag":"%s","commit":"%s","p0":"closed","tag_object":"%s"}\n' "$tag" "$tag_target" "$local_tag_object"
