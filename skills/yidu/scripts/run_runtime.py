#!/usr/bin/env python3
"""Run the pinned upstream command with Yidu's prepared environment."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from ensure_runtime import prepare, venv_python


ALLOWED_COMMANDS = {"make_book.py", "pdf_to_book.py"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Yidu's runtime and run an upstream book command."
    )
    parser.add_argument("--book", type=Path, required=True, help="EPUB or PDF input path")
    parser.add_argument("--profile", choices=("auto", "epub", "pdf"), default="auto")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Use: -- make_book.py ...")
    args = parser.parse_args(argv)
    if not args.command or args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command or Path(args.command[0]).name not in ALLOWED_COMMANDS:
        parser.error("最後必須是 `-- make_book.py ...` 或 `-- pdf_to_book.py ...`")

    try:
        state = prepare(args.book.expanduser().resolve(), args.profile)
    except Exception as exc:
        print(f"yidu: runtime 準備失敗：{exc}", file=sys.stderr)
        return 1

    root = Path(state["runtime_root"])
    python = venv_python(root)
    command_name = Path(args.command[0]).name
    if command_name == "make_book.py":
        script = root / "make_book.py"
    else:
        script = root / "tools" / "pdf_to_book.py"
    forwarded = [str(script), *args.command[1:]]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root) + os.pathsep + environment.get("PYTHONPATH", "")
    environment.setdefault("HF_HOME", str(root / "model-cache"))
    if state.get("pandoc"):
        pandoc_bin = str(Path(state["pandoc"]["path"]).parent)
        environment["PATH"] = pandoc_bin + os.pathsep + environment.get("PATH", "")
    os.execvpe(str(python), [str(python), *forwarded], environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
