"""Small, journaled Markdown transaction store. No model, network or global state.

Cooperating readers/writers must respect the lock and pending journal. Individual
replaces are atomic; multi-file visibility and hardware durability are not promised.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import uuid


def digest(content):
    return hashlib.sha256(content).hexdigest()


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def atomic_write(path, content):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if path.read_bytes() != content:
            raise RuntimeError('Yeniden okuma başarısız: ' + path.name)
    finally:
        temporary.unlink(missing_ok=True)


def process_alive(pid):
    """Conservative liveness check; never send a Windows termination signal."""
    if type(pid) is not int or pid <= 0:
        raise ValueError('Geçersiz kilit süreç kimliği')
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Invalid PID; denied/unknown is live.
        try:
            return kernel.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class MemoryStore:
    def __init__(self, root, write=atomic_write):
        self.root = Path(root).resolve()
        self.memory = self.root / 'memory'
        self.pending = self.memory / '.transaction'
        self.lock_path = self.memory / '.lock'
        self.write = write
        self.owner = None
        self.transaction_id = None

    def _memory_directory(self):
        if linked(self.memory) or not self.memory.is_dir():
            raise RuntimeError('memory gerçek bir proje klasörü olmalı')

    def path(self, relative):
        relative = str(relative)
        parts = Path(relative).parts
        if (Path(relative).is_absolute() or PureWindowsPath(relative).drive
                or not parts or parts[0] != 'memory' or '..' in parts
                or Path(relative).suffix != '.md' or ':' in relative or '\\' in relative):
            raise RuntimeError('Geçersiz hafıza yolu: ' + relative)
        path = self.root
        for part in parts:
            path = path / part
            if linked(path):
                raise RuntimeError('Bağlantılı hafıza yolu reddedildi: ' + relative)
        if not path.is_file() or not path.resolve().is_relative_to(self.memory):
            raise RuntimeError('Geçersiz hafıza dosyası: ' + relative)
        return path

    def _owned(self):
        self._memory_directory()
        if (not self.owner or linked(self.lock_path)
                or self.lock_path.read_bytes() != self.owner):
            raise RuntimeError('Hafıza kilidinin sahipliği değişti')

    def _acquire(self, recovery):
        try:
            return os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if not recovery:
                raise RuntimeError('Başka bir hafıza işlemi var; kilit korunuyor')
        # Serialize explicit recovery attempts before reclaiming a dead owner's lock.
        guard = self.memory / '.recovery-lock'
        descriptor = os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        marker = uuid.uuid4().hex.encode()
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(marker)
        try:
            if linked(self.lock_path):
                raise RuntimeError('Bağlantılı kilit reddedildi')
            previous = self.lock_path.read_bytes()
            owner = json.loads(previous)
            if process_alive(owner.get('pid')):
                raise RuntimeError('Kilit sahibi hâlâ çalışıyor veya doğrulanamıyor')
            if self.lock_path.read_bytes() != previous:
                raise RuntimeError('Kurtarma sırasında kilit değişti')
            self.lock_path.unlink()
            return os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        finally:
            if not linked(guard) and guard.read_bytes() == marker:
                guard.unlink()

    @contextmanager
    def lock(self, *, recovery=False):
        self._memory_directory()
        owner = json.dumps({'pid': os.getpid(), 'token': uuid.uuid4().hex}).encode()
        descriptor = self._acquire(recovery)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(owner)
                stream.flush()
                os.fsync(stream.fileno())
            self.owner = owner
            if self.pending.exists() or self.pending.is_symlink():
                if not recovery:
                    raise RuntimeError('Tamamlanmamış hafıza işlemi var; önce --recover kullanın')
            yield
        finally:
            try:
                if not linked(self.lock_path) and self.lock_path.read_bytes() == owner:
                    self.lock_path.unlink()
            finally:
                self.owner = None

    def snapshot(self, relatives):
        self._owned()
        return {name: self.path(name).read_bytes() for name in relatives}

    def _journal_directory(self):
        self._owned()
        if linked(self.pending) or not self.pending.is_dir():
            raise RuntimeError('Geçersiz işlem günlüğü klasörü')

    def _manifest(self):
        self._journal_directory()
        path = self.pending / 'manifest.json'
        if linked(path):
            raise RuntimeError('Geçersiz işlem günlüğü')
        data = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or data.get('schema') != 1 or data.get('state') not in ('preparing', 'prepared', 'committed', 'rolled_back')
                or not re.fullmatch('[a-f0-9]{32}', data.get('id', ''))
                or not isinstance(data.get('entries'), list) or not data['entries']):
            raise RuntimeError('İşlem günlüğü doğrulanamadı')
        seen = set()
        for entry in data['entries']:
            if not isinstance(entry, dict):
                raise RuntimeError('Geçersiz işlem kaydı')
            self.path(entry['path'])
            key = entry['path'].casefold()
            if key in seen or not all(re.fullmatch('[a-f0-9]{64}', entry.get(k, '')) for k in ('before', 'after')):
                raise RuntimeError('İşlem günlüğü kayıtları doğrulanamadı')
            seen.add(key)
        return data

    def _save_manifest(self, data):
        self._journal_directory()
        atomic_write(self.pending / 'manifest.json', json.dumps(data, sort_keys=True).encode())

    def _check_files(self, data, allowed):
        for entry in data['entries']:
            if digest(self.path(entry['path']).read_bytes()) not in {entry[k] for k in allowed}:
                raise RuntimeError('Dış değişiklik var; üzerine yazılmadı: ' + entry['path'])

    def _cleanup(self):
        self._journal_directory()
        # Flat, owned journal only. Never recursively delete a computed path.
        children = list(self.pending.iterdir())
        for path in children:
            if linked(path) or not path.is_file() or not re.fullmatch(r'(manifest\.json|(?:old|new)-[0-9]+|\.manifest\.json\.[a-f0-9]+\.tmp)', path.name):
                raise RuntimeError('İşlem günlüğünde beklenmeyen dosya; silinmedi')
        for path in children:
            if path.name != 'manifest.json':
                path.unlink()
        (self.pending / 'manifest.json').unlink(missing_ok=True)
        self.pending.rmdir()

    def commit(self, changes, expected, validate=lambda: None):
        self._owned()
        if self.pending.exists() or self.pending.is_symlink():
            raise RuntimeError('Önce bekleyen işlem kurtarılmalı')
        if not changes or set(changes) != set(expected) or len({k.casefold() for k in changes}) != len(changes):
            raise ValueError('İşlem dosyaları ve başlangıç görüntüsü eşleşmiyor')
        for name, content in changes.items():
            if not isinstance(content, bytes) or not isinstance(expected[name], bytes):
                raise TypeError('İşlem içeriği bytes olmalı')
            if self.path(name).read_bytes() != expected[name]:
                raise RuntimeError('Başlangıçtan sonra dosya değişti: ' + name)
        self.transaction_id = uuid.uuid4().hex
        data = {'schema': 1, 'id': self.transaction_id, 'state': 'preparing',
                'entries': [{'path': name, 'before': digest(expected[name]), 'after': digest(content)}
                            for name, content in changes.items()]}
        self.pending.mkdir(mode=0o700)
        self._save_manifest(data)
        # No live write occurs until every snapshot and manifest has been staged.
        for index, (name, content) in enumerate(changes.items()):
            atomic_write(self.pending / ('old-' + str(index)), expected[name])
            atomic_write(self.pending / ('new-' + str(index)), content)
        data['state'] = 'prepared'
        self._save_manifest(data)
        try:
            self._check_files(data, ('before',))
            for name, content in changes.items():
                self._owned()
                if self.path(name).read_bytes() != expected[name]:
                    raise RuntimeError('Yazma sırasında dosya değişti: ' + name)
                self.write(self.path(name), content)
            self._check_files(data, ('after',))
            validate()
            self._check_files(data, ('after',))
            data['state'] = 'committed'
            self._save_manifest(data)
        except Exception:
            # Reload disk state: an interruption may have persisted the commit.
            disk = self._manifest()
            if disk['state'] == 'prepared':
                self._rollback(disk)
            raise
        self._cleanup()
        self.transaction_id = None

    def _rollback(self, data):
        self._journal_directory()
        originals = []
        for index, entry in enumerate(data['entries']):
            for kind, key in (('old', 'before'), ('new', 'after')):
                path = self.pending / (kind + '-' + str(index))
                if linked(path) or digest(path.read_bytes()) != entry[key]:
                    raise RuntimeError('Kurtarma kopyası doğrulanamadı; dosyalara dokunulmadı')
            originals.append((entry, (self.pending / ('old-' + str(index))).read_bytes()))
        # Validate ALL destinations before restoring any of them.
        self._check_files(data, ('before', 'after'))
        for entry, content in originals:
            self._owned()
            self._check_files({'entries': [entry]}, ('before', 'after'))
            path = self.path(entry['path'])
            if path.read_bytes() != content:
                self.write(path, content)
        self._check_files(data, ('before',))
        data['state'] = 'rolled_back'
        self._save_manifest(data)
        self._cleanup()
        self.transaction_id = None

    def recover(self):
        self._owned()
        if not self.pending.exists():
            return 'Bekleyen işlem yok'
        data = self._manifest()
        if data['state'] == 'preparing':
            self._check_files(data, ('before',))
            data['state'] = 'rolled_back'
            self._save_manifest(data)
            self._cleanup()
            return 'Yazma başlamamış hazırlık güvenle kaldırıldı'
        if data['state'] == 'prepared':
            self._rollback(data)
            return 'Yarım işlem önceki kayda geri alındı'
        self._check_files(data, ('after',) if data['state'] == 'committed' else ('before',))
        self._cleanup()
        return 'Doğrulanmış işlem günlüğü temizlendi: ' + data['state']
