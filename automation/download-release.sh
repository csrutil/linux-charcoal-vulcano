#!/usr/bin/env bash
# Download a release of this fork into ~/Downloads/<tag>/ and check its checksums.
# Usage: automation/download-release.sh [tag]   (default: newest release, including pre-releases)
set -Eeuo pipefail

repo=${CHARCOAL_REPO:-csrutil/linux-charcoal-vulcano}
tag=${1:-$(gh release list --repo "$repo" --limit 1 --json tagName --jq '.[0].tagName')}

# The tag becomes a folder name: allow only a plain name, never a path.
if [[ ! "$tag" =~ ^[0-9][0-9A-Za-z._-]*$ || "$tag" == *..* ]]; then
  echo "error: unexpected release tag: '$tag'" >&2
  exit 1
fi

dir="$HOME/Downloads/$tag"
mkdir -p "$dir"
gh release download "$tag" --repo "$repo" --dir "$dir" --clobber

cd "$dir"
if command -v sha256sum >/dev/null 2>&1; then
  sum=(sha256sum)
else
  sum=(shasum -a 256)
fi
"${sum[@]}" -c SHA256SUMS
"${sum[@]}" -c RELEASE-ZIP-SHA256SUM
echo "Downloaded and verified: $dir"
