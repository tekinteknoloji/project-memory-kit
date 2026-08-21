#!/usr/bin/env python3
"""Atomically close a project-memory session with locking and verification."""

from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY, LOCK = ROOT / "memory", ROOT / "memory" / ".lock"


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def memory_lock(stale_seconds: int = 1800):
    MEMORY.mkdir(parents=True, exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime > stale_seconds:
        LOCK.unlink()
    try:
        descriptor = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("Başka bir hafıza işlemi devam ediyor: memory/.lock") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode()); os.close(descriptor); yield
    finally:
        LOCK.unlink(missing_ok=True)


def checker_report() -> dict[str, object]:
    result = subprocess.run([sys.executable, str(ROOT / "tools/memory_check.py"), "--root", str(ROOT), "--json"], capture_output=True, text=True, encoding="utf-8", timeout=30)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Doğrulama çıktısı okunamadı: {result.stderr or result.stdout}") from exc


def backup_state() -> str:
    bundle = ROOT.parent / f"{ROOT.name}-backups" / "latest.bundle"
    if not bundle.is_file():
        return "DOĞRULANMADI"
    result = subprocess.run(["git", "-C", str(ROOT), "bundle", "verify", str(bundle)], capture_output=True, text=True, timeout=30)
    return "YEREL YEDEK DOĞRULANDI" if result.returncode == 0 else "DOĞRULANMADI"


def rotate_sessions(text: str, stamp: datetime) -> str:
    entries = [line for line in text.splitlines() if line.startswith("- ")]
    if len(entries) <= 96:
        return text
    archive = MEMORY / "ARCHIVE" / f"SESSIONS-{stamp:%Y-%m}.md"
    old, keep = entries[:-80], entries[-80:]
    existing = archive.read_text(encoding="utf-8") if archive.exists() else f"# Oturum Arşivi {stamp:%Y-%m}\n\n"
    atomic_write(archive, existing.rstrip() + "\n" + "\n".join(old) + "\n")
    return "# Oturum Geçmişi\n\n" + "\n".join(keep) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--next", required=True, dest="next_action")
    parser.add_argument("--changed", nargs="*", default=[])
    parser.add_argument("--no-durable-change", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now().astimezone(); timestamp = stamp.isoformat(sep=" ", timespec="seconds")
    try:
        with memory_lock():
            sessions = MEMORY / "SESSIONS.md"
            current = sessions.read_text(encoding="utf-8") if sessions.exists() else "# Oturum Geçmişi\n\n"
            entry = f"- {timestamp} — {args.summary} — Sonraki: {args.next_action}.\n"
            atomic_write(sessions, rotate_sessions(current, stamp).rstrip() + "\n\n" + entry)
            report = checker_report()
            changed = sorted(set(args.changed + ["memory/SESSIONS.md", "memory/STATUS.md"]))
            file_result = "YENİ KALICI DEĞİŞİKLİK YOK" if args.no_durable_change else "DOĞRULANDI"
            last_write = "DEĞİŞMEDİ" if args.no_durable_change else timestamp
            status = (
                "# Hafıza Durumu\n\n- Sistem: DEVREDE\n"
                f"- Son kontrol: {timestamp}\n- Son kalıcı kayıt: {last_write}\n"
                f"- Dosya kaydı: {file_result}\n- Git durumu: {report['git_state']}\n"
                f"- Yerel yedekleme: {backup_state()}\n- Harici yedekleme: DOĞRULANMADI\n"
                f"- Hafıza kontrolü: {report['result']}\n"
                f"- Son güncellenen dosyalar: {', '.join(f'`{item}`' for item in changed)}\n"
                f"- Son işlem: {args.summary}\n- Sonraki adım: {args.next_action}\n"
            )
            atomic_write(MEMORY / "STATUS.md", status)
            if (MEMORY / "STATUS.md").read_text(encoding="utf-8") != status:
                raise RuntimeError("STATUS.md yeniden okuma doğrulaması başarısız")
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr); return 1
    print(status, end=""); return 0


if __name__ == "__main__": sys.exit(main())
