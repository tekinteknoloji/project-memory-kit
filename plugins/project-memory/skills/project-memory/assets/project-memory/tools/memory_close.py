#!/usr/bin/env python3
"""Close a session with validation, verified writes and exception rollback."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / 'memory'
LOCK = MEMORY / '.lock'

def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if path.read_bytes() != content.encode('utf-8'):
            raise RuntimeError(f'Yeniden okuma başarısız: {path.name}')
    finally:
        temporary.unlink(missing_ok=True)

@contextmanager
def memory_lock():
    # Never discard a lock based only on age; a long-running writer may own it.
    descriptor = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, f'pid={os.getpid()}\n'.encode())
        os.close(descriptor)
        yield
    finally:
        LOCK.unlink(missing_ok=True)

def checker_report() -> dict:
    result = subprocess.run([sys.executable, str(ROOT / 'tools/memory_check.py'), '--root', str(ROOT), '--json'],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    report = json.loads(result.stdout)
    if result.returncode not in (0, 2) or report.get('errors') or report.get('result') not in ('BAŞARILI', 'UYARI'):
        raise RuntimeError('Hafıza kontrolü başarısız: ' + '; '.join(report.get('errors', [])))
    return report

def backup_state() -> str:
    bundle = ROOT.parent / f'{ROOT.name}-backups' / 'latest.bundle'
    if not bundle.is_file():
        return 'DOĞRULANMADI'
    try:
        result = subprocess.run(['git', '-C', str(ROOT), 'bundle', 'verify', str(bundle)],
                                capture_output=True, text=True, timeout=30)
        return 'YEREL YEDEK DOĞRULANDI' if result.returncode == 0 else 'DOĞRULANMADI'
    except (OSError, subprocess.SubprocessError):
        return 'DOĞRULANMADI'

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', required=True)
    parser.add_argument('--next', required=True, dest='next_action')
    parser.add_argument('--changed', nargs='*', default=[])
    parser.add_argument('--no-durable-change', action='store_true')
    args = parser.parse_args()
    if any('\n' in value or '\r' in value for value in [args.summary, args.next_action, *args.changed]):
        print('HATA: Çok satırlı makbuz alanları kabul edilmez.', file=sys.stderr)
        return 1
    try:
        with memory_lock():
            report = checker_report()
            for relative in args.changed:
                path = (ROOT / relative).resolve()
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                    raise RuntimeError(f'Geçersiz dosya: {relative}')
                path.read_bytes()
            sessions, receipt = MEMORY / 'SESSIONS.md', MEMORY / 'STATUS.md'
            snapshot = {p: p.read_bytes() for p in (sessions, receipt)}
            timestamp = datetime.now().astimezone().isoformat(sep=' ', timespec='seconds')
            previous = receipt.read_text(encoding='utf-8')
            last_write = next(line.split(':', 1)[1].strip() for line in previous.splitlines()
                              if line.startswith('- Son kalıcı kayıt:')) if args.no_durable_change else timestamp
            # Existing history stays byte-for-byte intact as the prefix. Archive
            # maintenance requires a separate explicit request.
            session_text = snapshot[sessions].decode('utf-8') + f'\n- {timestamp} — {args.summary} — Sonraki: {args.next_action}.\n'
            changed = sorted(set(args.changed + ['memory/SESSIONS.md', 'memory/STATUS.md']))
            status = (
                '# Hafıza Durumu\n\n- Sistem: DEVREDE\n'
                f'- Son kontrol: {timestamp}\n- Son kalıcı kayıt: {last_write}\n'
                '- Dosya kaydı: DOĞRULANDI\n'
                f'- Git durumu: {report["git_state"]}\n'
                f'- Yerel yedekleme: {backup_state()}\n- Harici yedekleme: DOĞRULANMADI\n'
                f'- Hafıza kontrolü: {report["result"]}\n'
                f'- Son güncellenen dosyalar: {", ".join(changed)}\n'
                f'- Son işlem: {args.summary}\n- Sonraki adım: {args.next_action}\n'
            )
            try:
                atomic_write(sessions, session_text)
                atomic_write(receipt, status)
                final_report = checker_report()
                if final_report['result'] != report['result']:
                    status = status.replace(f'- Hafıza kontrolü: {report["result"]}',
                                            f'- Hafıza kontrolü: {final_report["result"]}')
                    atomic_write(receipt, status)
            except Exception:
                for path, content in snapshot.items():
                    if path.read_bytes() != content:
                        path.write_bytes(content)
                    if path.read_bytes() != content:
                        raise RuntimeError(f'Geri yükleme başarısız: {path}')
                raise
    except Exception as exc:
        print(f'HATA: {exc}', file=sys.stderr)
        return 1
    print(status, end='')
    return 0

if __name__ == '__main__':
    sys.exit(main())
