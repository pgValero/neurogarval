#!/usr/bin/env bash
# compare_site_test.sh — regression test for infrastructure changes.
#
# Builds the site from HEAD (in a clean worktree) and from the current working
# tree, then asserts both generated sites are byte-identical. Use it before and
# after touching the infrastructure (templates, styles, script, build.py,
# .pages.yml, workflows) to prove the change does not alter the output.
# Content changes (content/*.yml, media/*) are expected to alter the output,
# so only run this when the content is the same on both sides.
#
# Usage:
#   bash scripts/compare_site.sh [--keep] [--build-cmd "..."]
#
# Options:
#   --keep            Keep the temporary directory with both snapshots for
#                     inspection (its path is printed). Removed by default.
#   --build-cmd CMD   Command run to build the site, from the tree root.
#                     Default: uv-based build when uv is available, else
#                     "python3 scripts/build.py" (dependencies must be installed,
#                     see CONTRIBUTING.md). The same command builds both sides.
#   -h, --help        Show this help.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

keep=0
build_cmd=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep)
      keep=1
      shift
      ;;
    --build-cmd)
      build_cmd="${2:?--build-cmd needs a command argument}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,20p' "$script_dir/compare_site_test.sh"
      exit 0
      ;;
    *)
      echo "::error::Unknown argument: $1 (try --help)" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$build_cmd" ]]; then
  if command -v uv >/dev/null 2>&1; then
    build_cmd="uv run --with pyyaml --with markdown --with pillow python scripts/build.py"
  else
    build_cmd="python3 scripts/build.py"
  fi
fi

if ! git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
  echo "::error::Not a git repository: $repo_root" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
head_tree="$tmp_dir/head"
before_dir="$tmp_dir/before"
after_dir="$tmp_dir/after"
worktree_added=0

cleanup() {
  if [[ "$worktree_added" -eq 1 ]]; then
    git -C "$repo_root" worktree remove --force "$head_tree" >/dev/null 2>&1 || true
  fi
  if [[ "$keep" -eq 1 ]]; then
    echo "::notice::Kept snapshots in $tmp_dir"
  else
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

run_build() {
  local tree_dir="$1"
  local log_file="$2"
  if ! (cd -- "$tree_dir" && bash -c "$build_cmd" >"$log_file" 2>&1); then
    echo "::error::Build failed in $tree_dir (command: $build_cmd)" >&2
    tail -n 30 "$log_file" >&2 || true
    exit 1
  fi
  if [[ ! -d "$tree_dir/_site" ]]; then
    echo "::error::Build in $tree_dir produced no _site/ directory" >&2
    exit 1
  fi
}

echo "Building HEAD in a clean worktree..."
if ! git -C "$repo_root" worktree add --detach "$head_tree" HEAD >/dev/null 2>&1; then
  echo "::error::Could not create a worktree for HEAD" >&2
  exit 1
fi
worktree_added=1
run_build "$head_tree" "$tmp_dir/head-build.log"
cp -a "$head_tree/_site" "$before_dir"

echo "Building the working tree..."
run_build "$repo_root" "$tmp_dir/worktree-build.log"
cp -a "$repo_root/_site" "$after_dir"

echo "Comparing file lists..."
if ! list_diff="$(diff -u \
    --label "HEAD _site" --label "worktree _site" \
    <(cd -- "$before_dir" && find . -type f | LC_ALL=C sort) \
    <(cd -- "$after_dir" && find . -type f | LC_ALL=C sort))"; then
  echo "::error::The generated sites contain different files:" >&2
  echo "$list_diff" >&2
  exit 1
fi

echo "Comparing file contents..."
fail=0
while IFS= read -r rel; do
  if ! cmp -s "$before_dir/$rel" "$after_dir/$rel"; then
    fail=1
    if grep -Iq . "$before_dir/$rel" && grep -Iq . "$after_dir/$rel"; then
      echo "--- text differs: $rel"
      diff -u --label "HEAD _site/$rel" --label "worktree _site/$rel" \
        "$before_dir/$rel" "$after_dir/$rel" | head -n 200 || true
    else
      echo "--- binary files differ: $rel"
    fi
  fi
done < <(cd -- "$before_dir" && find . -type f | LC_ALL=C sort)

if [[ "$fail" -ne 0 ]]; then
  echo "::error::The generated sites differ (HEAD vs working tree)" >&2
  exit 1
fi

echo "::notice::Sites are identical (HEAD vs working tree)"
