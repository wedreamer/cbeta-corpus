#!/usr/bin/env python3
"""Verify fetched sources and a selected scope against license policy."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("need PyYAML: pip install pyyaml") from exc

BANNED = {"Y", "TX", "LC", "YP"}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def canon_from_rel(rel: str) -> str:
    top = rel.split("/", 1)[0]
    m = re.match(r"^[A-Z]+", top)
    return m.group(0) if m else top


def verify(dest: Path, tag: str, scope_name: str) -> list[str]:
    errors: list[str] = []
    fetched = dest / "FETCHED.yaml"
    if not fetched.exists():
        errors.append(f"missing {fetched}; run scripts/fetch.sh")
    else:
        data = load_yaml(fetched)
        sources = data.get("sources") or {}
        for name in ("xml-p5", "metadata", "gaiji"):
            commit = (sources.get(name) or {}).get("commit")
            if not commit:
                errors.append(f"FETCHED.yaml missing commit for {name}")
        if data.get("cbeta_release") != tag:
            errors.append(f"release mismatch: {data.get('cbeta_release')} != {tag}")

    files_txt = dest / "scopes" / scope_name / "files.txt"
    if not files_txt.exists():
        errors.append(f"missing {files_txt}; run scripts/select_scope.py")
    else:
        for line in files_txt.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            canon = canon_from_rel(line)
            if canon in BANNED:
                errors.append(f"Category B file in scope: {line}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CBETA lock and scope")
    parser.add_argument("--scope-name", default="taisho")
    parser.add_argument(
        "--cache-root",
        default=os.environ.get("CBETA_CORPUS_ROOT", str(Path.home() / ".cbeta/corpus")),
    )
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    lock = load_yaml(repo / "sources.lock.yaml")
    tag = args.tag or lock.get("cbeta_release", "2026R2")
    dest = Path(args.cache_root) / tag
    errors = verify(dest, tag, args.scope_name)
    if errors:
        print("verify_lock FAILED", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2
    print(f"verify_lock OK  tag={tag} scope={args.scope_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
