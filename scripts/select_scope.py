#!/usr/bin/env python3
"""Select XML files for a scope and write indexer inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("need PyYAML: pip install pyyaml") from exc

WORK_RE = re.compile(
    r"^(?P<canon>[A-Z]+)(?P<vol>\d+)n(?P<no>\d+)(?P<suf>[a-z]*)\.xml$"
)


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def work_id_from_name(name: str) -> str | None:
    m = WORK_RE.match(name)
    if not m:
        return None
    return f"{m.group('canon')}{m.group('no')}{m.group('suf')}"


def canon_of(work_id: str) -> str:
    m = re.match(r"^[A-Z]+", work_id)
    return m.group(0) if m else ""


def select_files(xml_root: Path, scope: dict) -> list[dict]:
    include_canons = set(scope.get("canons") or [])
    exclude_canons = set(scope.get("exclude_canons") or ["Y", "TX", "LC", "YP"])
    works = set(scope.get("works") or [])
    catalog = []
    for path in sorted(xml_root.rglob("*.xml")):
        work_id = work_id_from_name(path.name)
        if not work_id:
            continue
        canon = canon_of(work_id)
        if include_canons and canon not in include_canons:
            continue
        if canon in exclude_canons:
            continue
        if works and work_id not in works:
            continue
        catalog.append(
            {
                "work_id": work_id,
                "canon": canon,
                "path": path.relative_to(xml_root).as_posix(),
                "title": None,
                "author": None,
                "dynasty": None,
                "category": None,
            }
        )
    return catalog


def write_scope(out: Path, scope: dict, catalog: list[dict], tag: str, notice_src: Path | None) -> dict:
    files_blob = "\n".join(item["path"] for item in catalog)
    if files_blob:
        files_blob += "\n"
    scope_hash = hashlib.sha256(
        json.dumps({"scope": scope, "files": files_blob}, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:8]
    out.mkdir(parents=True, exist_ok=True)
    (out / "files.txt").write_text(files_blob, encoding="utf-8")
    with (out / "catalog.jsonl").open("w", encoding="utf-8") as fh:
        for row in catalog:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    exclude_canons = set(scope.get("exclude_canons") or ["Y", "TX", "LC", "YP"])
    manifest = {
        "cbeta_tag": tag,
        "scope": scope.get("name"),
        "scope_hash": scope_hash,
        "artifact_id": f"{tag}+{scope_hash}",
        "work_count": len(catalog),
        "file_count": len(catalog),
        "license": scope.get("license", "cc-by-nc-sa"),
        "exclude_canons": sorted(exclude_canons),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if notice_src and notice_src.exists():
        shutil.copyfile(notice_src, out / "NOTICE")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Select CBETA XML files for a scope")
    parser.add_argument("--scope", required=True, help="path to scopes/*.yaml")
    parser.add_argument(
        "--cache-root",
        default=os.environ.get("CBETA_CORPUS_ROOT", str(Path.home() / ".cbeta/corpus")),
    )
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    lock = load_yaml(repo / "sources.lock.yaml")
    tag = args.tag or lock.get("cbeta_release", "2026R2")
    scope = load_yaml(Path(args.scope))
    dest = Path(args.cache_root) / tag
    xml_root = dest / "src" / "xml-p5"
    if not xml_root.exists():
        raise SystemExit(f"xml-p5 not fetched: {xml_root} (run scripts/fetch.sh)")

    catalog = select_files(xml_root, scope)
    out = dest / "scopes" / scope.get("name", "unnamed")
    manifest = write_scope(out, scope, catalog, tag, repo / "NOTICE")
    print(f"wrote {out}  works={len(catalog)}  artifact={manifest['artifact_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
