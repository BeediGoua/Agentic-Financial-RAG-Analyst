"""G0 diagnostics, using only Python stdlib so it works before pip install.

Examples:
  python scripts/check_env.py --profile core
  python scripts/check_env.py --profile core --strict
  python scripts/check_env.py --profile full --json

Core checks the package versions, Python version and venv, WITHOUT network.
Full additionally checks Tesseract OCR, the local Ollama API/model and the
Hugging Face model cache. Full mode does not download models.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9.+!_-]+)$")
HF_MODELS = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "cross-encoder/ms-marco-TinyBERT-L-2-v2",
]
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434").rstrip("/")


def pinned_requirements(path: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    for number, original in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = original.split("#", 1)[0].strip()
        if not line:
            continue
        match = PACKAGE_PATTERN.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{number}: requirement must be an exact == pin: {line}")
        name, version = match.groups()
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in results:
            raise ValueError(f"{path}:{number}: duplicate requirement: {name}")
        results[normalized] = version
    return results


def check_item(name: str, ok: bool, detail: str, items: list[dict]) -> None:
    items.append({"name": name, "ok": bool(ok), "detail": detail})


def check_core(items: list[dict]) -> None:
    version = sys.version_info[:2]
    check_item("python", (3, 11) <= version < (3, 14), sys.version.split()[0], items)
    check_item("virtualenv", sys.prefix != sys.base_prefix, sys.prefix, items)
    for file in ("requirements.txt", "requirements-dev.txt"):
        try:
            reqs = pinned_requirements(ROOT / file)
        except Exception as exc:
            check_item(file, False, str(exc), items)
            continue
        for package, expected in reqs.items():
            try:
                installed = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                installed = None
            check_item(f"package:{package}", installed == expected, f"expected={expected} actual={installed or 'MISSING'}", items)


def check_full(items: list[dict]) -> None:
    exe = shutil.which("tesseract")
    check_item("tesseract", bool(exe), exe or "not on PATH", items)
    if exe:
        result = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=15, check=False)
        langs = set(result.stdout.splitlines()[1:]) | set(result.stderr.splitlines()[1:])
        for language in ("fra", "eng"):
            check_item(f"ocr:{language}", language in langs, f"available={sorted(langs)}", items)

    exe = shutil.which("ollama")
    check_item("ollama-cli", bool(exe), exe or "not on PATH", items)
    try:
        with urlopen(f"{OLLAMA_API_BASE}/api/tags", timeout=3) as response:
            payload = json.load(response)
        names = [model.get("name") or model.get("model") for model in payload.get("models", [])]
        check_item("ollama-api", True, OLLAMA_API_BASE, items)
        check_item("ollama-model", OLLAMA_MODEL in names, f"expected={OLLAMA_MODEL}, available={names}", items)
    except (URLError, OSError, ValueError, TimeoutError) as exc:
        check_item("ollama-api", False, f"{OLLAMA_API_BASE}: {exc}", items)
        check_item("ollama-model", False, f"cannot check {OLLAMA_MODEL} without API", items)

    try:
        from huggingface_hub import snapshot_download
        for name in HF_MODELS:
            try:
                path = snapshot_download(repo_id=name, local_files_only=True)
                check_item(f"hf:{name}", Path(path).exists(), path, items)
            except Exception as exc:
                check_item(f"hf:{name}", False, f"missing from cache: {type(exc).__name__}", items)
    except ImportError:
        for name in HF_MODELS:
            check_item(f"hf:{name}", False, "huggingface-hub not installed", items)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the G0 environment without downloading models")
    parser.add_argument("--profile", choices=["core", "full"], default="core")
    parser.add_argument("--strict", action="store_true", help="Return exit code 1 on any unmet check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    results: list[dict] = []
    check_core(results)
    if args.profile == "full":
        check_full(results)
    missing = [r for r in results if not r["ok"]]
    report = {"profile": args.profile, "ok": not missing, "checks": results, "failed_count": len(missing)}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"G0 doctor ({args.profile}): {len(results)-len(missing)}/{len(results)} passed")
        for item in results:
            symbol = "OK" if item["ok"] else "FAIL"
            print(f"[{symbol}] {item['name']}: {item['detail']}")
    if args.strict and missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
