#!/usr/bin/env bash
set -euo pipefail

script_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="${QF_RELEASE_CHECK_ROOT:-$script_root}"
verifier_root="${QF_RELEASE_CHECK_VERIFIER_ROOT:-$repo_root}"
trusted_verifier_root="${QF_RELEASE_CHECK_TRUSTED_VERIFIER_ROOT:-}"
trusted_verifier_expected_commit="${QF_RELEASE_CHECK_TRUSTED_VERIFIER_COMMIT:-}"
tag="${1:-}"
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_TERMINAL_PROMPT=0
unset GIT_SSH_COMMAND GIT_SSH GIT_PROXY_COMMAND GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT \
  GIT_SSL_NO_VERIFY GIT_ASKPASS SSH_ASKPASS GIT_CREDENTIAL_HELPER
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE GIT_EXEC_PATH GIT_REPLACE_REF_BASE
unset BASH_ENV ENV
export GIT_NO_REPLACE_OBJECTS=1
unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
while IFS='=' read -r environment_name _; do
  case "$environment_name" in
    GIT_CONFIG_KEY_*|GIT_CONFIG_VALUE_*) unset "$environment_name" ;;
  esac
done < <(env)

assert_secure_tool() {
  local tool_path="$1" cursor
  [[ "$tool_path" = /* && -x "$tool_path" && ! -L "$tool_path" ]] || return 1
  cursor="$tool_path"
  while [[ "$cursor" != / ]]; do
    [[ ! -w "$cursor" ]] || return 1
    cursor="$(dirname "$cursor")"
  done
}

reject_transport_overrides() {
  local root="$1"
  local keys lower
  keys="$(git -C "$root" config --local --name-only --get-regexp '.*')" || {
    printf '%s\n' '{"result":"invalid","reason":"local Git configuration could not be inspected"}' >&2
    exit 1
  }
  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    lower="${key,,}"
    case "$lower" in
      core.sshcommand|core.gitproxy|core.fsmonitor|core.hookspath|core.askpass|\
      credential.helper|credential.*.helper|include.*|url.*.insteadof|url.*.pushinsteadof|\
      remote.*.proxy|remote.*.proxyurl|http.proxy|http.sslverify|http.extraheader|\
      http.*.proxy|http.*.sslverify|http.*.extraheader|filter.*.process|filter.*.clean|\
      filter.*.smudge|diff.*.command|mergetool.*.cmd|submodule.*.update)
        printf '%s\n' '{"result":"invalid","reason":"transport-affecting Git configuration is not allowed"}' >&2
        exit 1
        ;;
    esac
  done <<< "$keys"
  if [[ -n "$(git -C "$root" for-each-ref --format='%(refname)' refs/replace/)" ]]; then
    printf '%s\n' '{"result":"invalid","reason":"Git replacement refs are not allowed"}' >&2
    exit 1
  fi
}

tracked_state() {
  git -C "$1" ls-files -v | awk '$1 ~ /^[a-zS]$/ { found = 1 } END { exit found ? 0 : 1 }'
}

[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]] || {
  printf '{"result":"invalid","reason":"tag must match vMAJOR.MINOR.PATCH-alpha","tag":"%s"}\n' "$tag" >&2
  exit 2
}

reject_transport_overrides "$repo_root"
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
  "https://github.com/${canonical_repository}.git"|"https://github.com/${canonical_repository}") ;;
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
if [[ -n "${QF_RELEASE_COMMIT:-}" ]]; then
  [[ "$QF_RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ && "$tag_target" == "$QF_RELEASE_COMMIT" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"tag target does not match the trusted release commit"}' >&2
    exit 1
  }
fi
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
reject_transport_overrides "$verifier_root"
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
  repo_worktree="$(git -C "$repo_root" rev-parse --show-toplevel)"
  verifier_worktree="$(git -C "$verifier_root" rev-parse --show-toplevel)"
  repo_common_dir="$(git -C "$repo_root" rev-parse --path-format=absolute --git-common-dir)"
  verifier_common_dir="$(git -C "$verifier_root" rev-parse --path-format=absolute --git-common-dir)"
  [[ "$verifier_worktree" != "$repo_worktree" && "$verifier_common_dir" != "$repo_common_dir" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier must be an independent checkout"}' >&2
    exit 1
  }
  if tracked_state "$verifier_root"; then
    printf '%s\n' '{"result":"invalid","reason":"trusted verifier has hidden tracked changes"}' >&2
    exit 1
  fi
  trusted_verifier_remote="$(git -C "$verifier_root" remote get-url origin 2>/dev/null || true)"
  case "$trusted_verifier_remote" in
    "https://github.com/${canonical_repository}.git"|"https://github.com/${canonical_repository}") ;;
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
  printf '%s\n' '{"result":"invalid","reason":"a separately pinned trusted verifier is required"}' >&2
  exit 1
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

if tracked_state "$repo_root"; then
  printf '%s\n' '{"result":"invalid","reason":"release worktree has hidden tracked changes"}' >&2
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
[[ ! -L "$verifier_root/scripts/p0-check.sh" && ! -L "$repo_root/docs/治理/p0-blockers.yaml" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"release verification inputs must not be symlinks"}' >&2
  exit 1
}
[[ "$pre_p0_verifier_head" == "$trusted_verifier_head" && -z "$pre_p0_verifier_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"verifier code changed immediately before P0 verification"}' >&2
  exit 1
}

snapshot_parent="$(mktemp -d "${TMPDIR:-/tmp}/qf-release-verifier.XXXXXX")"
snapshot_root="$snapshot_parent/verifier"
release_snapshot_root="$snapshot_parent/release"
trap 'rm -rf "$snapshot_parent"' EXIT
git clone --no-local --no-checkout -- "$verifier_root" "$snapshot_root" >/dev/null 2>&1
git -C "$snapshot_root" checkout --detach "$trusted_verifier_head" >/dev/null 2>&1
[[ "$(git -C "$snapshot_root" rev-parse HEAD)" == "$trusted_verifier_head" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"trusted verifier snapshot is not pinned"}' >&2
  exit 1
}
[[ -z "$(git -C "$snapshot_root" status --porcelain=v1 --untracked-files=all)" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"trusted verifier snapshot is not clean"}' >&2
  exit 1
}
chmod -R a-w "$snapshot_root"
git clone --no-local --no-checkout -- "$repo_root" "$release_snapshot_root" >/dev/null 2>&1
git -C "$release_snapshot_root" checkout --detach "$tag_target" >/dev/null 2>&1
[[ "$(git -C "$release_snapshot_root" rev-parse HEAD)" == "$tag_target" ]] || exit 1
uv_bin="$(command -v uv 2>/dev/null || true)"
gh_bin="$(command -v gh 2>/dev/null || true)"
assert_secure_tool "$uv_bin" || exit 1
assert_secure_tool "$gh_bin" || exit 1
uv_bin_dir="$(dirname "$uv_bin")"
gh_bin_dir="$(dirname "$gh_bin")"
export PATH="$uv_bin_dir:$gh_bin_dir:/usr/bin:/bin"
export HOME="$snapshot_parent/home"
export UV_CACHE_DIR="$snapshot_parent/uv-cache"
export UV_PROJECT_ENVIRONMENT="$snapshot_parent/venv"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$UV_CACHE_DIR"

QF_RELEASE_REPO_ROOT="$release_snapshot_root" QF_RELEASE_COMMIT="$tag_target" \
QF_RELEASE_TRUSTED_VERIFIER_ROOT="$snapshot_root" QF_RELEASE_TRUSTED_VERIFIER_COMMIT="$trusted_verifier_head" \
  "$snapshot_root/scripts/p0-check.sh" "$release_snapshot_root/docs/治理/p0-blockers.yaml" --require-closed
post_p0_head="$(git -C "$repo_root" rev-parse HEAD)"
post_p0_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ "$post_p0_head" == "$tag_target" && -z "$post_p0_status" ]] || {
  printf '%s\n' '{"result":"invalid","reason":"worktree or HEAD changed during P0 verification"}' >&2
  exit 1
}
post_p0_verifier_head="$(git -C "$snapshot_root" rev-parse HEAD)"
post_p0_verifier_status="$(git -C "$snapshot_root" status --porcelain=v1 --untracked-files=all)"
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
