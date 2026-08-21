#!/usr/bin/env python3
"""Deterministic, read-only health check for portable project memory."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_RELATIVE = (
    "README.md", "AGENTS.md", ".gitignore", "memory/README.md", "memory/INDEX.md",
    "memory/CURRENT.md", "memory/STATUS.md", "memory/SESSIONS.md",
    "memory/REQUIREMENTS.md", "memory/DECISIONS.md", "memory/ARCHITECTURE.md",
    "memory/CONVENTIONS.md", "memory/ISSUES.md", "memory/LEARNINGS.md",
    "memory/ARCHIVE/INDEX.md", "tools/memory_check.py", "tools/memory_close.py",
    "tools/memory_backup.py", "tools/init_memory.py",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ID_RE = re.compile(r"^##\s+((?:REQ|DEC|ISSUE|LRN)-\d+)\b", re.MULTILINE)
WINDOWS_ABS_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:\\[^\s`]+|\\\\[^\s`]+)")
SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
TEXT_SUFFIXES = {".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".env"}
STATUS_FIELDS = (
    "Sistem", "Son kontrol", "Son kalıcı kayıt", "Dosya kaydı", "Git durumu",
    "Yerel yedekleme", "Harici yedekleme", "Hafıza kontrolü",
    "Son güncellenen dosyalar", "Son işlem", "Sonraki adım",
)


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Okunamayan dosya: {path} ({exc})")
        return ""


def parse_status(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def git_state(root: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), "status", "--short"], check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "KONTROL EDİLEMEDİ"
    if result.returncode != 0:
        return "GIT YOK"
    return "TEMİZ" if not result.stdout.strip() else "KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR"


def audit(root: Path) -> dict[str, object]:
    root = root.resolve()
    memory = root / "memory"
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_RELATIVE:
        if not (root / relative).is_file():
            errors.append(f"Eksik gerekli dosya: {relative}")

    markdown_files = [root / "README.md", root / "AGENTS.md"]
    if memory.is_dir():
        markdown_files.extend(sorted(memory.rglob("*.md")))
    ids: dict[str, list[str]] = {}
    for path in markdown_files:
        if not path.is_file():
            continue
        text = read_text(path, errors)
        relative = path.relative_to(root).as_posix()
        lines = text.count("\n") + 1
        limit = 100 if path.name == "SESSIONS.md" else 200
        if lines > limit:
            warnings.append(f"Boyut sınırı aşıldı: {relative} ({lines}/{limit} satır)")
        if WINDOWS_ABS_RE.search(text):
            warnings.append(f"Taşınabilirliği bozan mutlak Windows yolu: {relative}")
        if SECRET_RE.search(text):
            warnings.append(f"Olası gizli değer: {relative}")
        for record_id in ID_RE.findall(text):
            ids.setdefault(record_id, []).append(relative)
        for target in LINK_RE.findall(text):
            target = unquote(target.strip().strip("<>"))
            if not target or target.startswith("#") or "://" in target or target.startswith("mailto:"):
                continue
            target_path = target.split("#", 1)[0]
            if PureWindowsPath(target_path).is_absolute() or Path(target_path).is_absolute():
                errors.append(f"Mutlak yerel bağlantı: {relative} -> {target}")
                continue
            resolved = (path.parent / target_path).resolve()
            if not inside(root, resolved):
                errors.append(f"Proje dışına çıkan bağlantı: {relative} -> {target}")
            elif not resolved.exists():
                errors.append(f"Kırık bağlantı: {relative} -> {target}")
    for record_id, locations in sorted(ids.items()):
        if len(locations) > 1:
            errors.append(f"Yinelenen kayıt kimliği {record_id}: {', '.join(locations)}")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env":
            continue
        text = read_text(path, errors)
        if SECRET_RE.search(text):
            message = f"Olası gizli değer: {path.relative_to(root).as_posix()}"
            if message not in warnings:
                warnings.append(message)

    status_path = memory / "STATUS.md"
    status = parse_status(read_text(status_path, errors)) if status_path.is_file() else {}
    for field in STATUS_FIELDS:
        if field not in status:
            errors.append(f"STATUS.md alanı eksik: {field}")
    if status.get("Sistem") != "DEVREDE":
        errors.append("STATUS.md sistem durumu DEVREDE değil")
    for field in ("Son kontrol", "Son kalıcı kayıt"):
        value = status.get(field)
        if not value or value == "DEĞİŞMEDİ":
            continue
        try:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is None:
                errors.append(f"STATUS.md zaman dilimi eksik: {field}")
            elif stamp.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
                errors.append(f"STATUS.md gelecekte zaman damgası: {field}")
        except ValueError:
            errors.append(f"STATUS.md geçersiz zaman damgası: {field}")

    actual_git = git_state(root)
    claimed_git = status.get("Git durumu")
    if claimed_git and claimed_git != actual_git:
        warnings.append(f"STATUS.md Git durumu eski: kayıt={claimed_git}, gerçek={actual_git}")

    issues_path, current_path = memory / "ISSUES.md", memory / "CURRENT.md"
    if issues_path.is_file() and current_path.is_file():
        issues_text = read_text(issues_path, errors)
        current_text = read_text(current_path, errors)
        has_open = bool(re.search(r"^- Durum:\s*açık\s*$", issues_text, re.MULTILINE | re.IGNORECASE))
        none = bool(re.search(r"^## Engeller\s*\n+\s*Yok\.?(?:\s*)$", current_text, re.MULTILINE | re.IGNORECASE))
        if has_open and none:
            warnings.append("CURRENT.md 'Engeller: Yok' diyor fakat ISSUES.md içinde açık sorun var")

    result = "HATA" if errors else ("UYARI" if warnings else "BAŞARILI")
    missing = sum(item.startswith("Eksik gerekli dosya:") for item in errors)
    return {
        "result": result, "errors": errors, "warnings": warnings,
        "info": [f"Gerekli dosyalar: {len(REQUIRED_RELATIVE) - missing}/{len(REQUIRED_RELATIVE)}", f"Git durumu: {actual_git}"],
        "git_state": actual_git,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit(args.root)
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Hafıza kontrolü: {report['result']}")
        for item in report["info"]:
            print(item)
        for item in report["errors"]:
            print(f"HATA: {item}")
        for item in report["warnings"]:
            print(f"UYARI: {item}")
    return 1 if report["errors"] else (2 if report["warnings"] else 0)


if __name__ == "__main__":
    sys.exit(main())
