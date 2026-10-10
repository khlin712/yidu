#!/usr/bin/env python3
"""Validate the structural invariants that matter for delivered EPUBs."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def validate(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing EPUB: {path}")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if not names or names[0] != "mimetype":
            raise ValueError("mimetype must be the first ZIP entry")
        if archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            raise ValueError("mimetype must be stored without compression")
        if archive.read("mimetype") != b"application/epub+zip":
            raise ValueError("invalid mimetype contents")
        if "META-INF/container.xml" not in names:
            raise ValueError("missing META-INF/container.xml")
        container = ElementTree.fromstring(archive.read("META-INF/container.xml"))
        rootfiles = [e for e in container.iter() if e.tag.rsplit("}", 1)[-1] == "rootfile"]
        if not rootfiles or not rootfiles[0].get("full-path"):
            raise ValueError("container.xml has no rootfile")
        opf_name = rootfiles[0].get("full-path")
        assert opf_name is not None
        if opf_name not in names:
            raise ValueError(f"container rootfile is missing: {opf_name}")
        opf = ElementTree.fromstring(archive.read(opf_name))
        manifest = [e for e in opf.iter() if e.tag.rsplit("}", 1)[-1] == "item"]
        spine = [e for e in opf.iter() if e.tag.rsplit("}", 1)[-1] == "itemref"]
        manifest_by_id = {e.get("id"): e for e in manifest if e.get("id")}
        missing_spine = [
            str(itemref.get("idref"))
            for itemref in spine
            if itemref.get("idref") not in manifest_by_id
        ]
        if missing_spine:
            raise ValueError(f"spine references missing manifest ids: {missing_spine}")
        artifact_markers = (
            "_translation_work/",
            "_translated/",
            "_staging/",
            "run.log",
            "glossary.json",
            "glossary.pins",
            "style_profile.md",
        )
        artifacts = [n for n in names if any(marker in n for marker in artifact_markers)]
        return {
            "path": str(path),
            "entries": len(names),
            "opf": opf_name,
            "manifest_items": len(manifest),
            "spine_items": len(spine),
            "unexpected_artifacts": artifacts,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.epub)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["unexpected_artifacts"]:
            print("validate_epub: unexpected work artifacts found", file=sys.stderr)
            return 1
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        print(f"validate_epub: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
