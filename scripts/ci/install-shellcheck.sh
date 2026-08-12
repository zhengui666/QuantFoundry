#!/usr/bin/env bash
set -euo pipefail

readonly shellcheck_version='0.10.0'
readonly shellcheck_sha256='6c881ab0698e4e6ea235245f22832860544f17ba386442fe7e9d629f8cbedf87'
readonly archive="shellcheck-v${shellcheck_version}.linux.x86_64.tar.xz"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/qf-shellcheck.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

curl --fail --location --silent --show-error --output "$work_dir/$archive" \
  "https://github.com/koalaman/shellcheck/releases/download/v${shellcheck_version}/${archive}"
printf '%s  %s\n' "$shellcheck_sha256" "$work_dir/$archive" | sha256sum --check --strict
tar --extract --xz --file "$work_dir/$archive" --directory "$work_dir"
sudo install --mode 0755 "$work_dir/shellcheck-v${shellcheck_version}/shellcheck" /usr/local/bin/shellcheck
test "$(shellcheck --version | awk '/version:/ {print $2}')" = "$shellcheck_version"
