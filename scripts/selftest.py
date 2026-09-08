#!/usr/bin/env python3
"""Offline self-test. Does not clone xml-p5. Run: python3 scripts/selftest.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from select_scope import select_files, write_scope  # noqa: E402
from verify_lock import verify  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "2026R2"
        xml = dest / "src" / "xml-p5"
        (xml / "T" / "T08").mkdir(parents=True)
        (xml / "T" / "T30").mkdir(parents=True)
        (xml / "Y" / "Y01").mkdir(parents=True)
        (xml / "T" / "T08" / "T08n0235.xml").write_text("<TEI/>", encoding="utf-8")
        (xml / "T" / "T30" / "T30n1578.xml").write_text("<TEI/>", encoding="utf-8")
        (xml / "Y" / "Y01" / "Y01n0001.xml").write_text("<TEI/>", encoding="utf-8")

        scope = {
            "name": "taisho",
            "canons": ["T"],
            "license": "cc-by-nc-sa",
            "exclude_canons": ["Y", "TX", "LC", "YP"],
        }
        catalog = select_files(xml, scope)
        ids = {row["work_id"] for row in catalog}
        assert ids == {"T0235", "T1578"}, ids
        assert all(row["canon"] != "Y" for row in catalog)

        out = dest / "scopes" / "taisho"
        manifest = write_scope(out, scope, catalog, "2026R2", ROOT / "NOTICE")
        assert manifest["work_count"] == 2
        assert (out / "files.txt").read_text(encoding="utf-8").count(".xml") == 2
        assert "Y/" not in (out / "files.txt").read_text(encoding="utf-8")
        assert (out / "NOTICE").exists()
        rows = [json.loads(line) for line in (out / "catalog.jsonl").read_text(encoding="utf-8").splitlines()]
        assert {r["work_id"] for r in rows} == {"T0235", "T1578"}

        (dest / "FETCHED.yaml").write_text(
            "\n".join(
                [
                    'cbeta_release: "2026R2"',
                    "sources:",
                    "  xml-p5:",
                    '    commit: "abc"',
                    "  metadata:",
                    '    commit: "def"',
                    "  gaiji:",
                    '    commit: "ghi"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        errors = verify(dest, "2026R2", "taisho")
        assert errors == [], errors

        (out / "files.txt").write_text("Y/Y01/Y01n0001.xml\n", encoding="utf-8")
        errors = verify(dest, "2026R2", "taisho")
        assert any("Category B" in e for e in errors), errors

    print("selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
