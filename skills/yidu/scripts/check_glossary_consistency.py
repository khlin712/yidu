#!/usr/bin/env python3
"""Find reviewed glossary variants in a translated EPUB."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return html.unescape(" ".join(self.parts))


def epub_text(path: Path) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith((".xhtml", ".html", ".htm", ".opf", ".ncx")):
                continue
            parser = TextExtractor()
            parser.feed(archive.read(name).decode("utf-8", errors="replace"))
            chunks.append(parser.text())
    return "\n".join(chunks)


def load_entries(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("glossary JSON must contain an 'entries' list")
    return [
        e
        for e in entries
        if isinstance(e, dict) and e.get("status", "accepted") in {"accepted", "confirmed"}
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    parser.add_argument("glossary", type=Path)
    parser.add_argument("--strict", action="store_true", help="return non-zero when variants are found")
    args = parser.parse_args()
    try:
        text = epub_text(args.epub)
        findings: list[dict] = []
        for entry in load_entries(args.glossary):
            canonical = str(entry.get("target", "")).strip()
            variants = [str(v).strip() for v in entry.get("variants", []) if str(v).strip()]
            for variant in variants:
                if variant == canonical:
                    continue
                count = len(re.findall(re.escape(variant), text))
                if count:
                    findings.append(
                        {
                            "source": entry.get("source", ""),
                            "canonical": canonical,
                            "variant": variant,
                            "count": count,
                            "sense": entry.get("sense", ""),
                        }
                    )
        print(json.dumps({"epub": str(args.epub), "findings": findings}, ensure_ascii=False, indent=2))
        return 1 if args.strict and findings else 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"yidu glossary check: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
