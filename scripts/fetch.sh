#!/usr/bin/env bash
# Pin official CBETA sources listed in sources.lock.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/sources.lock.yaml"
CACHE_ROOT="${CBETA_CORPUS_ROOT:-$HOME/.cbeta/corpus}"
TAG="$(awk -F'"' '/^cbeta_release:/ {print $2; exit}' "$LOCK")"
TAG="${TAG:-2026R2}"
DEST="$CACHE_ROOT/$TAG"
FETCHED="$DEST/FETCHED.yaml"

need() { command -v "$1" >/dev/null || { echo "missing dependency: $1" >&2; exit 2; }; }
need git
need awk

clone_or_update() {
  local name="$1" url="$2" ref="$3" sparse="$4"
  local dir="$DEST/src/$name"
  mkdir -p "$DEST/src"
  if [[ ! -d "$dir/.git" ]]; then
    echo "==> clone $name ($ref)"
    if [[ "$sparse" == "true" && "$name" == "xml-p5" ]]; then
      git clone --filter=blob:none --sparse --branch "$ref" --depth 1 "$url" "$dir"
      git -C "$dir" sparse-checkout set README.md canons.json schema T X
    else
      git clone --branch "$ref" --depth 1 "$url" "$dir"
    fi
  else
    echo "==> fetch $name"
    git -C "$dir" fetch --depth 1 origin "refs/tags/$ref:refs/tags/$ref" 2>/dev/null \
      || git -C "$dir" fetch --depth 1 origin "$ref"
    git -C "$dir" checkout --detach FETCH_HEAD
  fi
  git -C "$dir" rev-parse HEAD
}

mkdir -p "$DEST"
xml_commit="$(clone_or_update xml-p5 https://github.com/cbeta-org/xml-p5.git "$TAG" true)"
meta_commit="$(clone_or_update metadata https://github.com/DILA-edu/cbeta-metadata.git master false)"
gaiji_commit="$(clone_or_update gaiji https://github.com/cbeta-org/cbeta_gaiji.git master false)"

cat > "$FETCHED" <<EOF
schema: cbeta-corpus.fetched/v1
cbeta_release: "$TAG"
fetched_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cache_root: "$DEST"
sources:
  xml-p5:
    tag: "$TAG"
    commit: "$xml_commit"
  metadata:
    ref: master
    commit: "$meta_commit"
  gaiji:
    ref: master
    commit: "$gaiji_commit"
EOF

echo "wrote $FETCHED"
