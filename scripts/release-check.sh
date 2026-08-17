#!/usr/bin/env bash
set -euo pipefail

script_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="${QF_RELEASE_CHECK_ROOT:-$script_root}"
verifier_root="${QF_RELEASE_CHECK_VERIFIER_ROOT:-$repo_root}"
trusted_verifier_root="${QF_RELEASE_CHECK_TRUSTED_VERIFIER_ROOT:-}"
trusted_verifier_expected_commit="${QF_RELEASE_CHECK_TRUSTED_VERIFIER_COMMIT:-}"
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
trusted_branch="origin/main"
[[ -z "${QF_RELEASE_BRANCH+x}" || "$QF_RELEASE_BRANCH" == "$trusted_branch" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"release branch override is not allowed"}' >&2
  exit 1
}
git -C "$repo_root" fetch --no-tags origin "refs/heads/main:refs/remotes/origin/main" >/dev/null 2>&1 || {
  printf '%s\n' '{"result":"invalid","reason":"trusted release branch could not be refreshed"}' >&2
  exit 1
}
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
if [[ -n "$trusted_verifier_root" ]]; then
  [[ "$trusted_verifier_expected_commit" =~ ^[0-9a-f]{40}$ && "$trusted_verifier_expected_commit" != "0000000000000000000000000000000000000000" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier commit anchor is required"}' >&2
    exit 1
  }
  [[ "$verifier_root" == "$trusted_verifier_root" && -z "$verifier_status" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier code is not clean"}' >&2
    exit 1
  }
  trusted_verifier_remote="$(git -C "$verifier_root" remote get-url origin 2>/dev/null || true)"
  case "$trusted_verifier_remote" in
    "https://github.com/${canonical_repository}.git"|"https://github.com/${canonical_repository}"|"git@github.com:${canonical_repository}.git"|"git@github.com:${canonical_repository}") ;;
    *)
      printf '%s\n' '{"result":"invalid","reason":"trusted verifier origin is not canonical"}' >&2
      exit 1
      ;;
  esac
  git -C "$verifier_root" fetch --no-tags origin \
    "refs/heads/main:refs/remotes/origin/main" >/dev/null 2>&1 || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier main could not be refreshed"}' >&2
    exit 1
  }
  trusted_verifier_commit="$(git -C "$verifier_root" rev-parse "refs/remotes/origin/main^{commit}")" || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier main is unavailable"}' >&2
    exit 1
  }
  [[ "$trusted_verifier_commit" == "$trusted_verifier_expected_commit" && "$verifier_head" == "$trusted_verifier_expected_commit" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier is not the canonical origin/main commit"}' >&2
    exit 1
  }
else
  [[ "$verifier_head" == "$tag_target" && -z "$verifier_status" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"verifier code is not clean at the trusted tag commit"}' >&2
    exit 1
  }
fi

if [[ -n "$trusted_verifier_root" ]]; then
  trusted_verifier_head="$trusted_verifier_commit"
else
  trusted_verifier_head="$tag_target"
fi

if [[ -n "$trusted_verifier_root" && ! -x "$verifier_root/scripts/p0-check.sh" ]]; then
  printf '%s\n' '{"result":"invalid","reason":"trusted verifier is missing p0-check.sh"}' >&2
  exit 1
fi

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

pre_p0_verifier_head="$(git -C "$verifier_root" rev-parse HEAD)"
pre_p0_verifier_status="$(git -C "$verifier_root" status --porcelain=v1 --untracked-files=all)"
[[ "$pre_p0_verifier_head" == "$trusted_verifier_head" && -z "$pre_p0_verifier_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"verifier code changed immediately before P0 verification"}' >&2
  exit 1
}

QF_RELEASE_REPO_ROOT="$repo_root" QF_RELEASE_COMMIT="$tag_target" \
  "$verifier_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed
post_p0_head="$(git -C "$repo_root" rev-parse HEAD)"
post_p0_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ "$post_p0_head" == "$tag_target" && -z "$post_p0_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"worktree or HEAD changed during P0 verification"}' >&2
  exit 1
}
post_p0_verifier_head="$(git -C "$verifier_root" rev-parse HEAD)"
post_p0_verifier_status="$(git -C "$verifier_root" status --porcelain=v1 --untracked-files=all)"
[[ "$post_p0_verifier_head" == "$trusted_verifier_head" && -z "$post_p0_verifier_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"verifier code changed during P0 verification"}' >&2
  exit 1
}
post_local_tag_object="$(git -C "$repo_root" show-ref --verify --hash "refs/tags/$tag")" || exit 1
[[ "$post_local_tag_object" == "$local_tag_object" ]] || {
  printf '{"result":"invalid","reason":"local tag changed during P0 verification","tag":"%s"}\n' "$tag" >&2
  exit 1
}
post_p0_tag_object="$(git -C "$repo_root" ls-remote --exit-code --refs origin "refs/tags/$tag" | awk 'NR == 1 {print $1}')" || exit 1
[[ "$post_p0_tag_object" == "$local_tag_object" ]] || {
  printf '{"result":"invalid","reason":"tag changed during P0 verification","tag":"%s"}\n' "$tag" >&2
  exit 1
}
printf '{"result":"pass","tag":"%s","commit":"%s","p0":"closed","tag_object":"%s"}\n' "$tag" "$tag_target" "$local_tag_object"
