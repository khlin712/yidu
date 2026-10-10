#!/usr/bin/env python3
"""Prepare and validate the Yidu runtime.

The skill installer only copies this file.  The first Yidu invocation calls it
so that the heavy, platform-specific dependencies live outside the skill
directory and outside the user's system Python.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


SKILL_DIR = Path(__file__).resolve().parent
UPSTREAM_URL = "https://github.com/yihong0618/bilingual_book_maker.git"
UPSTREAM_COMMIT = "e1027a4823e98f668ef950740b6f805ec30bd3b2"
PANDOC_VERSION = "3.1.12"
PANDOC_MIN = (3, 1, 12)
PANDOC_RELEASE = (
    "https://github.com/jgm/pandoc/releases/download/"
    f"{PANDOC_VERSION}"
)
STATE_NAME = "yidu-runtime.json"
LOCK_NAME = ".yidu-runtime.lock"


class RuntimeErrorMessage(RuntimeError):
    """An actionable setup error intended for the Agent and the user."""


def command(*args: str, cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> str:
    try:
        result = subprocess.run(
            list(args),
            cwd=cwd,
            env=env,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeErrorMessage(
            f"找不到必要的系統工具 `{args[0]}`。請先安裝它，或將它加入 PATH。"
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeErrorMessage(
            f"執行 `{args[0]}` 失敗（exit {exc.returncode}）：{detail[-1200:]}"
        ) from exc
    return result.stdout.strip()


def python_version_ok(version: Tuple[int, int]) -> bool:
    return version >= (3, 10)


def configured_root() -> Path:
    configured = os.environ.get("BOOK_TRANSLATOR_RUNTIME")
    if configured:
        return Path(configured).expanduser() / UPSTREAM_COMMIT
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return codex_home / "runtimes" / "yidu" / UPSTREAM_COMMIT


def infer_profile(book: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    suffix = book.suffix.lower()
    if suffix == ".epub":
        return "epub"
    if suffix == ".pdf":
        return "pdf"
    raise RuntimeErrorMessage("Yidu 只支援 `.epub` 與 `.pdf`。")


def venv_python(root: Path) -> Path:
    name = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return root / "venv" / name


def acquire_lock(root: Path) -> Path:
    lock = root.parent / f"{UPSTREAM_COMMIT}{LOCK_NAME}"
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 900
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return lock
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeErrorMessage(
                    f"另一個 Yidu 安裝程序仍在執行：{lock}。"
                    "若確認它已停止，再刪除這個 lock 檔後重試。"
                )
            time.sleep(0.5)


def release_lock(lock: Path) -> None:
    try:
        lock.unlink()
    except FileNotFoundError:
        pass


def ensure_checkout(root: Path) -> None:
    root = root.expanduser().resolve()
    if (root / ".git").exists():
        head = command("git", "rev-parse", "HEAD", cwd=root)
        if head != UPSTREAM_COMMIT:
            raise RuntimeErrorMessage(
                f"固定 runtime 已存在但 commit 是 {head}，不是 {UPSTREAM_COMMIT}：{root}。"
                "請改用另一個 BOOK_TRANSLATOR_RUNTIME；不要覆寫現有 runtime。"
            )
        return
    if root.exists() and any(root.iterdir()):
        raise RuntimeErrorMessage(f"runtime 路徑不是空的 Git checkout：{root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    command(
        "git",
        "clone",
        "--filter=blob:none",
        "--no-tags",
        "--no-checkout",
        UPSTREAM_URL,
        str(root),
    )
    command("git", "checkout", "--detach", UPSTREAM_COMMIT, cwd=root)


def create_venv(root: Path) -> Path:
    if not python_version_ok((sys.version_info.major, sys.version_info.minor)):
        raise RuntimeErrorMessage(
            f"Yidu 需要 Python 3.10 以上，目前是 {platform.python_version()}。"
        )
    python = venv_python(root)
    if python.exists():
        result = command(str(python), "-c", "import sys; print(sys.version_info[:2])")
        if result != f"({sys.version_info.major}, {sys.version_info.minor})":
            raise RuntimeErrorMessage(
                f"既有 venv 的 Python 版本不符：{python}。請使用另一個 runtime 路徑。"
            )
        return python
    import venv

    venv.EnvBuilder(with_pip=True, clear=False).create(root / "venv")
    if not python.exists():
        raise RuntimeErrorMessage(f"虛擬環境建立後找不到 Python：{python}")
    return python


def read_state(root: Path) -> dict:
    path = root / STATE_NAME
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(root: Path, state: dict) -> None:
    path = root / STATE_NAME
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def install_requirements(python: Path, root: Path, profile: str) -> None:
    requirements = [root / "requirements.txt"]
    if profile == "pdf":
        requirements.append(root / "requirements-pdf-cpu.txt")
    for requirement in requirements:
        if not requirement.is_file():
            raise RuntimeErrorMessage(f"固定版本依賴檔不存在：{requirement}")
        print(f"yidu: 安裝 {requirement.name}（只寫入 {root / 'venv'}）", flush=True)
        command(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--requirement",
            str(requirement),
            cwd=root,
        )


def check_imports(python: Path, root: Path, profile: str) -> None:
    modules = ["book_maker", "ebooklib", "openai", "tiktoken"]
    if profile == "pdf":
        modules.extend(["docling", "pypdfium2", "torch", "onnxruntime", "rapidocr"])
    script = (
        "import importlib.util, sys; "
        f"names={modules!r}; "
        "missing=[n for n in names if importlib.util.find_spec(n) is None]; "
        "print(','.join(missing)); sys.exit(1 if missing else 0)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        missing = command(str(python), "-c", script, cwd=root, env=env)
    except RuntimeErrorMessage as exc:
        raise RuntimeErrorMessage(
            f"runtime 依賴健康檢查失敗（{profile}）：{exc}"
        ) from exc
    if missing:
        raise RuntimeErrorMessage(f"runtime 缺少 Python modules：{missing}")


def parse_version(text: str) -> Optional[Tuple[int, ...]]:
    import re

    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def system_pandoc() -> Optional[Tuple[str, str]]:
    candidate = shutil.which("pandoc")
    if not candidate:
        return None
    try:
        version_text = command(candidate, "--version")
    except RuntimeErrorMessage:
        return None
    version = parse_version(version_text)
    if version and version >= PANDOC_MIN:
        return candidate, ".".join(str(n) for n in version[:3])
    return None


def pandoc_asset() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return f"pandoc-{PANDOC_VERSION}-arm64-macOS.zip"
    if system == "Darwin" and machine in {"x86_64", "amd64"}:
        return f"pandoc-{PANDOC_VERSION}-x86_64-macOS.zip"
    if system == "Linux" and machine in {"x86_64", "amd64"}:
        return f"pandoc-{PANDOC_VERSION}-linux-amd64.tar.gz"
    if system == "Linux" and machine in {"aarch64", "arm64"}:
        return f"pandoc-{PANDOC_VERSION}-linux-arm64.tar.gz"
    if system == "Windows" and machine in {"amd64", "x86_64", "x64"}:
        return f"pandoc-{PANDOC_VERSION}-windows-x86_64.zip"
    raise RuntimeErrorMessage(
        f"Yidu 沒有提供這個平台的可攜式 Pandoc：{system}/{platform.machine()}。"
        "請自行安裝 Pandoc 3.1.12 以上後重試。"
    )


def find_executable(root: Path) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    candidates = list((root / "tools" / "pandoc" / PANDOC_VERSION).rglob(f"pandoc{suffix}"))
    if not candidates:
        raise RuntimeErrorMessage("Pandoc 下載完成但找不到可執行檔。")
    executable = candidates[0]
    if os.name != "nt":
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def download_pandoc(root: Path) -> Tuple[str, str]:
    asset = pandoc_asset()
    directory = root / "tools" / "pandoc" / PANDOC_VERSION
    existing = list(directory.rglob("pandoc.exe" if os.name == "nt" else "pandoc")) if directory.exists() else []
    if existing:
        executable = find_executable(root)
        version = parse_version(command(str(executable), "--version"))
        if version and version >= PANDOC_MIN:
            return str(executable), ".".join(str(n) for n in version[:3])

    directory.mkdir(parents=True, exist_ok=True)
    url = f"{PANDOC_RELEASE}/{asset}"
    print(f"yidu: 下載固定版本 Pandoc {PANDOC_VERSION}", flush=True)
    with tempfile.TemporaryDirectory(prefix="yidu-pandoc-") as temporary:
        archive = Path(temporary) / asset
        try:
            with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
        except Exception as exc:
            raise RuntimeErrorMessage(f"下載 Pandoc 失敗：{url}；{exc}") from exc
        extract = Path(temporary) / "extract"
        extract.mkdir()
        try:
            if asset.endswith(".zip"):
                with zipfile.ZipFile(archive) as zipped:
                    zipped.extractall(extract)
            else:
                with tarfile.open(archive, "r:gz") as tar:
                    tar.extractall(extract)
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
            raise RuntimeErrorMessage(f"解壓 Pandoc 失敗：{exc}") from exc
        for child in extract.iterdir():
            target = directory / child.name
            if target.exists():
                shutil.rmtree(target) if target.is_dir() else target.unlink()
            shutil.move(str(child), str(target))
    executable = find_executable(root)
    version = parse_version(command(str(executable), "--version"))
    if not version or version < PANDOC_MIN:
        raise RuntimeErrorMessage(f"下載的 Pandoc 版本不符合需求：{version}")
    return str(executable), ".".join(str(n) for n in version[:3])


def prepare(book: Path, profile: str, check_only: bool = False) -> dict:
    if not book.is_file():
        raise RuntimeErrorMessage(f"找不到輸入檔案：{book}")
    if not python_version_ok((sys.version_info.major, sys.version_info.minor)):
        raise RuntimeErrorMessage(
            f"Yidu 需要 Python 3.10 以上，目前是 {platform.python_version()}。"
        )
    root = configured_root().resolve()
    profile = infer_profile(book, profile)
    state = read_state(root)
    if check_only:
        if not root.exists() or not state.get(f"{profile}_ready"):
            raise RuntimeErrorMessage(
                f"Yidu runtime 尚未準備好（profile={profile}）：{root}。"
                "請移除 --check，讓第一次使用流程自動準備。"
            )
        python = venv_python(root)
        if not python.exists():
            raise RuntimeErrorMessage(f"runtime manifest 存在但找不到 venv：{python}")
        check_imports(python, root, profile)
        pandoc_path = state.get("pandoc", {}).get("path") if profile == "pdf" else None
        if profile == "pdf" and pandoc_path:
            command(pandoc_path, "--version")
        return state

    lock = acquire_lock(root)
    try:
        ensure_checkout(root)
        python = create_venv(root)
        state = read_state(root)
        if not state.get("base_ready"):
            install_requirements(python, root, "epub")
            check_imports(python, root, "epub")
            state.update({"base_ready": True, "upstream_commit": UPSTREAM_COMMIT})
            write_state(root, state)
        if profile == "pdf" and not state.get("pdf_ready"):
            install_requirements(python, root, "pdf")
            check_imports(python, root, "pdf")
            state["pdf_ready"] = True
        pandoc = None
        if profile == "pdf":
            pandoc = system_pandoc()
            if pandoc is None:
                pandoc = download_pandoc(root)
            state["pandoc"] = {"path": pandoc[0], "version": pandoc[1]}
        state.update(
            {
                "schema": 1,
                "upstream_url": UPSTREAM_URL,
                "upstream_commit": UPSTREAM_COMMIT,
                "runtime_root": str(root),
                "python": str(python),
                "profile": profile,
                "dependencies_ready": bool(
                    state.get("base_ready") and (profile != "pdf" or state.get("pdf_ready"))
                ),
                "ready": True,
            }
        )
        write_state(root, state)
        return state
    finally:
        release_lock(lock)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the Yidu pinned runtime.")
    parser.add_argument("--book", type=Path, required=True, help="EPUB or PDF input path")
    parser.add_argument("--profile", choices=("auto", "epub", "pdf"), default="auto")
    parser.add_argument("--check", action="store_true", help="Validate an existing runtime without installing")
    parser.add_argument("--json", action="store_true", help="Print the result as JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)
    book = args.book.expanduser().resolve()
    try:
        result = prepare(book, args.profile, args.check)
    except RuntimeErrorMessage as exc:
        print(f"yidu: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"runtime={result['runtime_root']}")
        print(f"python={result['python']}")
        print(f"profile={result['profile']}")
        if result.get("pandoc"):
            print(f"pandoc={result['pandoc']['path']} ({result['pandoc']['version']})")
        print("ready=yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
