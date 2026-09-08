#!/usr/bin/env python3
"""Offline self-test. Does not clone xml-p5. Run: python3 scripts/selftest.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from select_scope import (  # noqa: E402
    enrich_catalog,
    load_creators_csv,
    load_work_info,
    select_files,
    write_scope,
)
from verify_lock import verify  # noqa: E402

TESTDATA = Path(__file__).resolve().parent / "testdata"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "2026R2"
        xml = dest / "src" / "xml-p5"
        (xml / "T" / "T08").mkdir(parents=True)
        (xml / "T" / "T30").mkdir(parents=True)
        (xml / "T" / "T31").mkdir(parents=True)
        (xml / "Y" / "Y01").mkdir(parents=True)
        (xml / "T" / "T08" / "T08n0235.xml").write_text("<TEI/>", encoding="utf-8")
        (xml / "T" / "T30" / "T30n1578.xml").write_text("<TEI/>", encoding="utf-8")
        (xml / "T" / "T31" / "T31n1585.xml").write_text("<TEI/>", encoding="utf-8")
        (xml / "Y" / "Y01" / "Y01n0001.xml").write_text("<TEI/>", encoding="utf-8")

        scope = {
            "name": "taisho",
            "canons": ["T"],
            "license": "cc-by-nc-sa",
            "exclude_canons": ["Y", "TX", "LC", "YP"],
        }
        catalog = select_files(xml, scope)
        ids = {row["work_id"] for row in catalog}
        assert ids == {"T0235", "T1578", "T1585"}, ids
        assert all(row["canon"] != "Y" for row in catalog)

        work_info = load_work_info(TESTDATA / "work-info-T.snippet.json")
        creators = load_creators_csv(TESTDATA / "creators-T.snippet.csv")
        catalog = enrich_catalog(catalog, work_info, creators)

        out = dest / "scopes" / "taisho"
        manifest = write_scope(out, scope, catalog, "2026R2", ROOT / "NOTICE")
        assert manifest["work_count"] == 3
        assert (out / "files.txt").read_text(encoding="utf-8").count(".xml") == 3
        assert "Y/" not in (out / "files.txt").read_text(encoding="utf-8")
        assert (out / "NOTICE").exists()
        rows = [json.loads(line) for line in (out / "catalog.jsonl").read_text(encoding="utf-8").splitlines()]
        assert {r["work_id"] for r in rows} == {"T0235", "T1578", "T1585"}

        by_id = {r["work_id"]: r for r in rows}
        work_types = {"jing", "lun", "lv", "shu", "other"}
        t0235 = by_id["T0235"]
        assert "金剛" in t0235["title"], t0235
        assert "鳩摩羅什" in (t0235["author"] or ""), t0235
        assert t0235["work_type"] in work_types, t0235
        assert t0235["work_type"] == "jing", t0235
        if "T1578" in by_id:
            assert "掌珍" in by_id["T1578"]["title"], by_id["T1578"]
            assert by_id["T1578"]["work_type"] in work_types, by_id["T1578"]
            assert by_id["T1578"]["work_type"] == "lun", by_id["T1578"]
        if "T1585" in by_id:
            assert "成唯識" in by_id["T1585"]["title"], by_id["T1585"]
            assert "玄奘" in (by_id["T1585"]["author"] or ""), by_id["T1585"]
            assert by_id["T1585"]["work_type"] in work_types, by_id["T1585"]
            assert by_id["T1585"]["work_type"] == "lun", by_id["T1585"]
        for row in rows:
            assert row["work_type"] in work_types, row

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
