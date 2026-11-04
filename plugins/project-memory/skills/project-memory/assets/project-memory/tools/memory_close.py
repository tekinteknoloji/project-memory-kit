#!/usr/bin/env python3
"""Close a session with validation, verified writes and exception rollback."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_storage import MemoryStore, atomic_write as write_bytes

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / 'memory'

def atomic_write(path: Path, content: str) -> None:
    write_bytes(path, content.encode('utf-8'))


def checker_report(transaction_id=None) -> dict:
    command = [sys.executable, str(ROOT / 'tools/memory_check.py'), '--root', str(ROOT), '--json']
    if transaction_id:
        command += ['--transaction-id', transaction_id]
    result = subprocess.run(command,
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
    parser.add_argument('--summary')
    parser.add_argument('--next', dest='next_action')
    parser.add_argument('--recover', action='store_true', help='Bekleyen kayıt işlemini doğrula ve kurtar')
    parser.add_argument('--changed', nargs='*', default=[])
    parser.add_argument('--no-durable-change', action='store_true')
    args = parser.parse_args()
    if args.recover and (args.summary is not None or args.next_action is not None or args.changed or args.no_durable_change):
        parser.error('--recover diğer kayıt seçenekleriyle birleştirilemez')
    if not args.recover and (args.summary is None or args.next_action is None):
        parser.error('--summary ve --next gerekli')
    if any('\n' in value or '\r' in value for value in [args.summary or '', args.next_action or '', *args.changed]):
        print('HATA: Çok satırlı makbuz alanları kabul edilmez.', file=sys.stderr)
        return 1
    try:
        store = MemoryStore(ROOT, write=lambda path, content: atomic_write(path, content.decode('utf-8')))
        with store.lock(recovery=args.recover):
            if args.recover:
                print(store.recover())
                return 0
            original = store.snapshot(['memory/SESSIONS.md', 'memory/STATUS.md'])
            report = checker_report()
            for relative in args.changed:
                path = (ROOT / relative).resolve()
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                    raise RuntimeError(f'Geçersiz dosya: {relative}')
                path.read_bytes()
            sessions, receipt = MEMORY / 'SESSIONS.md', MEMORY / 'STATUS.md'
            snapshot = {sessions: original['memory/SESSIONS.md'], receipt: original['memory/STATUS.md']}
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
            def validate():
                final_report = checker_report(transaction_id=store.transaction_id)
                if final_report['result'] != report['result']:
                    raise RuntimeError('Kayıt sonrası kontrol sonucu değişti; kayıt geri alınıyor')
            store.commit({'memory/SESSIONS.md': session_text.encode('utf-8'),
                          'memory/STATUS.md': status.encode('utf-8')}, original, validate)
    except Exception as exc:
        print(f'HATA: {exc}', file=sys.stderr)
        return 1
    print(status, end='')
    return 0

if __name__ == '__main__':
    sys.exit(main())
