#!/usr/bin/env python3
"""Deterministic, read-only health check for portable project memory."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote
from memory_storage import linked

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_RELATIVE = (
    "README.md", "AGENTS.md", ".gitignore", "memory/README.md", "memory/INDEX.md",
    "memory/CURRENT.md", "memory/STATUS.md", "memory/SESSIONS.md",
    "memory/REQUIREMENTS.md", "memory/DECISIONS.md", "memory/ARCHITECTURE.md",
    "memory/CONVENTIONS.md", "memory/ISSUES.md", "memory/LEARNINGS.md",
    "memory/ARCHIVE/INDEX.md", "tools/memory_check.py", "tools/memory_close.py",
    "tools/memory_backup.py", "tools/init_memory.py", "tools/memory_storage.py", "tools/memory_init.py",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ID_RE = re.compile(r"^##\s+((?:REQ|DEC|ISSUE|LRN)-\d+)\b", re.MULTILINE)
WINDOWS_ABS_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:\\[^\s`]+|\\\\[^\s`]+)")
SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
# Explicit credential assignments only; identifiers in prose are not secrets.
CREDENTIAL_RE = re.compile(
    r"(?im)^\s*[\"']?(?:[A-Za-z0-9]+_)*(?:password|passwd|secret|token|api_?key)[\"']?\s*[:=]\s*(.+?)\s*,?\s*$"
)
PLACEHOLDER_VALUES = frozenset({'example', 'sample', 'changeme', 'change_me',
                              'your_key', 'your_token', 'your_password', 'placeholder',
                              'redacted', 'none', 'null', 'test', 'dummy'})


def has_secret(text):
    if SECRET_RE.search(text):
        return True
    for match in CREDENTIAL_RE.finditer(text):
        value = match.group(1).strip().strip("\"'")
        lower = value.casefold()
        if (len(value) < 8 or lower in PLACEHOLDER_VALUES
                or value.startswith(('<', '${', '{{', '%'))
                or lower.startswith(('os.environ', 'os.getenv', 'process.env', 'getenv('))
                or set(value) <= {'*', 'x', 'X', '.'}):
            continue
        # Unquoted whitespace is usually explanatory prose, not a bound value.
        if any(char.isspace() for char in value):
            continue
        return True
    return False


TEXT_SUFFIXES = {".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".env"}
# Explicit source-scan policy: dependencies/caches only, not app data/config.
SCAN_EXCLUDED_DIRS = frozenset({'.git','__pycache__','node_modules','venv','.venv',
                               '.tox','.pytest_cache','.mypy_cache','.ruff_cache','.transaction'})


def scan_files(root, errors, warnings, counts):
    if not root.exists():
        return
    if linked(root):
        errors.append('Bağlantılı tarama kökü reddedildi: '+root.name)
        return
    def failed(error):
        errors.append('Taranamayan dizin: '+str(error.filename))
    for current,directories,files in os.walk(root,topdown=True,followlinks=False,onerror=failed):
        current=Path(current)
        kept=[]
        for name in sorted(directories):
            path=current/name
            if name in SCAN_EXCLUDED_DIRS:
                counts['pruned_directories']+=1
            elif linked(path):
                counts['pruned_directories']+=1
                warnings.append('Bağlantılı dizin taranmadı: '+path.relative_to(root).as_posix())
            else:
                kept.append(name)
        directories[:]=kept
        for name in sorted(files):
            path=current/name
            if linked(path):
                warnings.append('Bağlantılı dosya taranmadı: '+path.relative_to(root).as_posix())
            elif path.is_file():
                yield path


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
        # A broken .git entry is not evidence that the project has no Git.
        has_git_entry = any((parent / ".git").exists() or (parent / ".git").is_symlink()
                            for parent in (root, *root.parents))
        return "GIT YOK" if not has_git_entry and "not a git repository" in (result.stderr or "").casefold() else "KONTROL EDİLEMEDİ"
    return "TEMİZ" if not result.stdout.strip() else "KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR"


def open_issue_exists(issues, current):
    scope = re.search(r"(?im)^- Kapsam:[ 	]*(.+)$", current)
    for record in re.split(r"(?m)^#{1,6} ", issues):
        status = re.search(r"(?im)^- Durum:[ 	]*(.+)$", record)
        if not status or not re.match(r"(?:açık|yeniden açıldı)(?:$|[ 	(;—])",
                                      status[1].strip().casefold()):
            continue
        issue_scope = re.search(r"(?im)^- Kapsam:[ 	]*(.+)$", record)
        if not scope or not issue_scope or scope[1].strip().casefold() == issue_scope[1].strip().casefold():
            return True
    return False


def continuity(status, sessions, current):
    close_id = status.get("Kapanış kimliği")
    ids = re.findall(r"(?m)^- \d{4}-\d{2}-\d{2}[^\n]* \[close:([0-9a-f]{32})\]$", sessions)
    if not close_id and not ids:
        closure = "legacy_unverified"
    elif ids and ids[-1] == close_id and ids.count(close_id) == 1:
        closure = "matched"
    else:
        closure = "mismatch"
    missing = []
    entries = re.split(r"(?m)^### Etkin iş: ", current)[1:]
    for entry in entries:
        title, _, body = entry.partition("\n")
        body = re.split(r"(?m)^#{1,3} ", body, maxsplit=1)[0]
        for field in ("Bulgu", "Açık konu", "Sonraki adım", "Kaynak"):
            match = re.search(rf"(?m)^- {field}:[ \t]*(\S.*)$", body)
            if not match or (field == "Kaynak" and not re.search(r"\[[^\]]+\]\([^)]+\)", match[1])):
                missing.append(f"{title}: {field}")
    return {"closure": closure, "handoff": "incomplete" if missing else "checked" if entries else "legacy_unverified", "missing": missing}


def audit(root: Path, transaction_id: str | None = None) -> dict[str, object]:
    root = root.resolve()
    memory = root / "memory"
    errors: list[str] = []
    warnings: list[str] = []
    cache = {}
    scan = {'pruned_directories': 0, 'text_files_read': 0,
            'excluded_directory_names': sorted(SCAN_EXCLUDED_DIRS)}
    def read(path):
        if path not in cache:
            current=root
            for part in path.relative_to(root).parts:
                current=current/part
                if linked(current):
                    errors.append('Bağlantılı dosya yolu reddedildi: '+path.relative_to(root).as_posix())
                    cache[path]=''
                    return ''
            cache[path]=read_text(path,errors)
            scan['text_files_read']+=1
        return cache[path]


    pending = memory / '.transaction'
    if pending.exists() or pending.is_symlink():
        try:
            if linked(memory) or linked(pending) or linked(pending / 'manifest.json'):
                raise ValueError('linked journal')
            manifest = json.loads((pending / 'manifest.json').read_text(encoding='utf-8'))
            if not isinstance(manifest, dict):
                raise ValueError('invalid journal')
            owned = transaction_id and manifest.get('id') == transaction_id and manifest.get('state') == 'prepared'
            if not owned:
                errors.append('Tamamlanmamış hafıza işlemi: önce memory_close.py --recover')
        except (OSError, ValueError, TypeError):
            errors.append('İşlem günlüğü doğrulanamadı; otomatik yazma engellenmeli')
    elif transaction_id:
        errors.append('Etkin işlem günlüğü bulunamadı')

    for relative in REQUIRED_RELATIVE:
        if not (root / relative).is_file():
            errors.append(f"Eksik gerekli dosya: {relative}")

    markdown_files = [root / "README.md", root / "AGENTS.md"]
    if memory.is_dir():
        markdown_files.extend(path for path in scan_files(memory,errors,warnings,scan) if path.suffix==".md")
    ids: dict[str, list[str]] = {}
    for path in markdown_files:
        if not path.is_file():
            continue
        text = read(path)
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

    for path in scan_files(root,errors,warnings,scan):
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env":
            continue
        text = read(path)
        if has_secret(text):
            message = f"Olası gizli değer: {path.relative_to(root).as_posix()}"
            if message not in warnings:
                warnings.append(message)

    status_path = memory / "STATUS.md"
    status = parse_status(read(status_path)) if status_path.is_file() else {}
    session_path = memory / "SESSIONS.md"
    current_path = memory / "CURRENT.md"
    handoff = continuity(status, read(session_path) if session_path.is_file() else "",
                         read(current_path) if current_path.is_file() else "")
    if handoff["closure"] == "mismatch":
        warnings.append("Kapanış kimliği son oturum kaydıyla eşleşmiyor")
    warnings.extend(f"Eksik devir bilgisi: {field}" for field in handoff["missing"])
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
    git_observed_at = datetime.now().astimezone().isoformat(sep=" ", timespec="seconds")
    claimed_git = status.get("Git durumu")
    git_scope = status.get("Git ölçüm anı")
    historical_git = git_scope == "Kapanış öncesi"
    git_receipt_warning = None
    if historical_git:
        try:
            observed = datetime.fromisoformat(status.get("Git ölçüm zamanı", ""))
            if observed.tzinfo is None or observed.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError("invalid measurement time")
        except ValueError:
            errors.append("STATUS.md Git ölçüm zamanı geçersiz veya zaman dilimi eksik")
    elif git_scope:
        errors.append("STATUS.md Git ölçüm anı tanınmıyor")
    elif claimed_git and claimed_git != actual_git:
        git_receipt_warning = f"STATUS.md Git durumu eski: kayıt={claimed_git}, gerçek={actual_git}"
        warnings.append(git_receipt_warning)

    issues_path, current_path = memory / "ISSUES.md", memory / "CURRENT.md"
    if issues_path.is_file() and current_path.is_file():
        issues_text = read(issues_path)
        current_text = read(current_path)
        has_open = open_issue_exists(issues_text, current_text)
        none = bool(re.search(r"^## Engeller\s*\n+\s*Yok\.?(?:\s*)$", current_text, re.MULTILINE | re.IGNORECASE))
        if has_open and none:
            warnings.append("CURRENT.md 'Engeller: Yok' diyor fakat ISSUES.md içinde açık sorun var")

    result = "HATA" if errors else ("UYARI" if warnings else "BAŞARILI")
    missing = sum(item.startswith("Eksik gerekli dosya:") for item in errors)
    return {
        "continuity": handoff,
        "result": result, "errors": errors, "warnings": warnings,
        "info": [f"Gerekli dosyalar: {len(REQUIRED_RELATIVE) - missing}/{len(REQUIRED_RELATIVE)}", f"Git durumu: {actual_git}", f"Tarama: {scan['text_files_read']} metin dosyası okundu, {scan['pruned_directories']} dizin atlandı"],
        "git_state": actual_git,
        "git_observed_at": git_observed_at,
        "git_receipt_warning": git_receipt_warning,
        "scan": scan,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--transaction-id", help=argparse.SUPPRESS)
    args = parser.parse_args()
    report = audit(args.root, args.transaction_id)
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
