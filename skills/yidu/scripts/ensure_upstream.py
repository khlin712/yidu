#!/usr/bin/env python3
"""Prepare the pinned bilingual_book_maker checkout used by Yidu."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


UPSTREAM_URL = "https://github.com/yihong0618/bilingual_book_maker.git"
UPSTREAM_COMMIT = "e1027a4823e98f668ef950740b6f805ec30bd3b2"


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def default_root() -> Path:
    configured = os.environ.get("BOOK_TRANSLATOR_RUNTIME")
    if configured:
        return Path(configured).expanduser() / UPSTREAM_COMMIT
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return codex_home / "runtimes" / "bilingual_book_maker" / UPSTREAM_COMMIT


def ensure(root: Path) -> tuple[Path, bool]:
    root = root.expanduser().resolve()
    if (root / ".git").is_dir():
        head = run("git", "rev-parse", "HEAD", cwd=root)
        if head == UPSTREAM_COMMIT:
            return root, True
        raise RuntimeError(
            f"Existing runtime at {root} is {head}, not the pinned {UPSTREAM_COMMIT}. "
            "Use a different BOOK_TRANSLATOR_RUNTIME or remove only that runtime."
        )

    if root.exists():
        raise RuntimeError(f"Runtime path exists but is not a Git checkout: {root}")

    root.parent.mkdir(parents=True, exist_ok=True)
    run("git", "clone", "--no-checkout", UPSTREAM_URL, str(root))
    run("git", "checkout", "--detach", UPSTREAM_COMMIT, cwd=root)
    return root, False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, help="Override the per-user runtime path")
    parser.add_argument("--print-root", action="store_true", help="Print only the prepared checkout path")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable result")
    args = parser.parse_args()

    try:
        root, reused = ensure(args.root or default_root())
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"yidu: {exc}", file=sys.stderr)
        return 1

    if args.print_root:
        print(root)
    elif args.json:
        print(json.dumps({"root": str(root), "commit": UPSTREAM_COMMIT, "reused": reused}))
    else:
        print(f"runtime={root}")
        print(f"commit={UPSTREAM_COMMIT}")
        print(f"reused={'yes' if reused else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
