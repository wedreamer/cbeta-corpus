#!/usr/bin/env python3
"""Select XML files for a scope and write indexer inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("need PyYAML: pip install pyyaml") from exc

WORK_RE = re.compile(
    r"^(?P<canon>[A-Z]+)(?P<vol>\d+)n(?P<no>\d+)(?P<suf>[a-z]*)\.xml$"
)

DEFAULT_EXCLUDE_CANONS: Final = ("Y", "TX", "LC", "YP")


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


def work_type_from_title(title: str | None) -> str:
    if not title:
        return "other"
    if title.endswith("述記") or title.endswith("疏"):
        return "shu"
    if title.endswith("經"):
        return "jing"
    if title.endswith("論"):
        return "lun"
    if title.endswith("律"):
        return "lv"
    return "other"


def load_work_info(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return {}
    return data


def load_creators_csv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    authors: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            work_id = (row.get("work_id") or "").strip()
            creators = (row.get("creators") or "").strip()
            if work_id and creators:
                authors[work_id] = creators
    return authors


def load_metadata(meta_root: Path, canons: set[str]) -> tuple[dict[str, dict], dict[str, str]]:
    work_info: dict[str, dict] = {}
    creators: dict[str, str] = {}
    for canon in sorted(canons):
        work_info.update(load_work_info(meta_root / "work-info" / f"{canon}.json"))
        creators.update(load_creators_csv(meta_root / "creators" / "csv" / f"{canon}.csv"))
    return work_info, creators


def enrich_catalog(
    catalog: list[dict],
    work_info: dict[str, dict],
    creators: dict[str, str],
) -> list[dict]:
    out: list[dict] = []
    for row in catalog:
        work_id = row["work_id"]
        info = work_info.get(work_id) or {}
        title = info.get("title")
        if title is None:
            title = row.get("title")
        author = creators.get(work_id)
        if author is None:
            author = row.get("author")
        dynasty = info.get("dynasty")
        if dynasty is None:
            dynasty = row.get("dynasty")
        category = info.get("category")
        if category is None:
            category = row.get("category")
        title_str = title if isinstance(title, str) else None
        out.append(
            {
                **row,
                "title": title,
                "author": author,
                "dynasty": dynasty,
                "category": category,
                "work_type": work_type_from_title(title_str),
            }
        )
    return out


def select_files(xml_root: Path, scope: dict) -> list[dict]:
    include_canons = set(scope.get("canons") or [])
    exclude_canons = set(scope.get("exclude_canons") or list(DEFAULT_EXCLUDE_CANONS))
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
                "work_type": None,
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
    exclude_canons = set(scope.get("exclude_canons") or list(DEFAULT_EXCLUDE_CANONS))
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
    canons = {row["canon"] for row in catalog}
    work_info, creators = load_metadata(dest / "src" / "metadata", canons)
    catalog = enrich_catalog(catalog, work_info, creators)
    out = dest / "scopes" / scope.get("name", "unnamed")
    manifest = write_scope(out, scope, catalog, tag, repo / "NOTICE")
    print(f"wrote {out}  works={len(catalog)}  artifact={manifest['artifact_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
