"""Adversarial storage tests: observed data preservation, not implementation mirrors."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/project-memory/skills/project-memory'
TOOLS = SKILL / 'assets/project-memory/tools'
sys.path.insert(0, str(TOOLS))
from memory_storage import MemoryStore, atomic_write


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='memory-storage-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'memory').mkdir()
        self.original = {'memory/SESSIONS.md': '# Geçmiş\r\n- Türkçe ğüşöçıİ\r\n'.encode(),
                         'memory/STATUS.md': b'# Before\n'}
        self.changes = {'memory/SESSIONS.md': self.original['memory/SESSIONS.md'] + b'- new\n',
                        'memory/STATUS.md': b'# After\n'}
        for name, content in self.original.items():
            (self.root / name).write_bytes(content)
        (self.root / 'memory/DECISIONS.md').write_bytes(b'untouched decision')
        self.store = MemoryStore(self.root)

    def files(self):
        return {name: (self.root / name).read_bytes() for name in self.original}

    def interrupted(self):
        def crash(path, content):
            atomic_write(path, content)
            raise KeyboardInterrupt('simulated process interruption')
        self.store.write = crash
        with self.assertRaises(KeyboardInterrupt), self.store.lock():
            self.store.commit(self.changes, self.original)
        self.store = MemoryStore(self.root)

    def test_commit_preserves_other_records_and_removes_journal(self):
        observed = []
        with self.store.lock():
            self.store.commit(self.changes, self.original, lambda: observed.append(self.files()))
        self.assertEqual(self.files(), self.changes)
        self.assertEqual(observed, [self.changes])
        self.assertEqual((self.root/'memory/DECISIONS.md').read_bytes(), b'untouched decision')
        self.assertFalse(self.store.pending.exists())
        self.assertFalse(self.store.lock_path.exists())

    def test_changed_baseline_is_rejected_without_writes(self):
        external = b'new external work'
        (self.root/'memory/STATUS.md').write_bytes(external)
        with self.assertRaisesRegex(RuntimeError, 'Başlangıçtan'), self.store.lock():
            self.store.commit(self.changes, self.original)
        self.assertEqual((self.root/'memory/STATUS.md').read_bytes(), external)
        self.assertEqual((self.root/'memory/SESSIONS.md').read_bytes(), self.original['memory/SESSIONS.md'])
        self.assertFalse(self.store.pending.exists())

    def test_second_write_failure_restores_exact_original_bytes(self):
        def fail_second(path, content):
            if path.name == 'STATUS.md':
                raise OSError('disk full')
            atomic_write(path, content)
        self.store.write = fail_second
        with self.assertRaises(OSError), self.store.lock():
            self.store.commit(self.changes, self.original)
        self.assertEqual(self.files(), self.original)
        self.assertFalse(self.store.pending.exists())

    def test_failure_after_replace_also_rolls_back(self):
        failed = False
        def fail_once(path, content):
            nonlocal failed
            atomic_write(path, content)
            if path.name == 'STATUS.md' and not failed:
                failed = True
                raise OSError('verification failed after replace')
        self.store.write = fail_once
        with self.assertRaises(OSError), self.store.lock():
            self.store.commit(self.changes, self.original)
        self.assertEqual(self.files(), self.original)

    def test_validator_failure_restores_both_files(self):
        def invalid():
            raise ValueError('post-write audit rejected')
        with self.assertRaises(ValueError), self.store.lock():
            self.store.commit(self.changes, self.original, invalid)
        self.assertEqual(self.files(), self.original)

    def test_interrupted_write_blocks_new_work_then_recovers(self):
        self.interrupted()
        mixed = self.files()
        self.assertNotEqual(mixed, self.original)
        with self.assertRaisesRegex(RuntimeError, 'Tamamlanmamış'), self.store.lock():
            self.fail('new writes must not start')
        self.assertEqual(self.files(), mixed)
        with self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), self.original)
        with self.store.lock(recovery=True):
            self.assertEqual(self.store.recover(), 'Bekleyen işlem yok')

    def test_committed_cleanup_interruption_keeps_new_data(self):
        with patch.object(self.store, '_cleanup', side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt), self.store.lock():
                self.store.commit(self.changes, self.original)
        with self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), self.changes)

    def test_external_change_during_failure_is_never_overwritten(self):
        def external_then_fail(path, content):
            if path.name == 'STATUS.md':
                path.write_bytes(b'other writer data')
                raise OSError('write failed')
            atomic_write(path, content)
        self.store.write = external_then_fail
        with self.assertRaisesRegex(RuntimeError, 'Dış değişiklik'), self.store.lock():
            self.store.commit(self.changes, self.original)
        mixed = self.files()
        self.assertEqual(mixed['memory/STATUS.md'], b'other writer data')
        with self.assertRaisesRegex(RuntimeError, 'Dış değişiklik'), self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), mixed)
        self.assertTrue(self.store.pending.exists())

    def test_corrupt_backup_prevents_any_recovery_write(self):
        self.interrupted()
        before = self.files()
        (self.store.pending/'old-1').write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'Kurtarma kopyası'), self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), before)

    def test_rollback_failure_retains_recoverable_journal(self):
        def fail_rollback(path, content):
            if content == self.original['memory/SESSIONS.md']:
                raise OSError('rollback disk error')
            atomic_write(path, content)
        self.store.write = fail_rollback
        def invalid():
            raise ValueError('invalid result')
        with self.assertRaises(OSError), self.store.lock():
            self.store.commit(self.changes, self.original, invalid)
        self.assertTrue(self.store.pending.exists())
        self.store.write = atomic_write
        with self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), self.original)

    def test_staging_disk_error_does_not_touch_live_files(self):
        from memory_storage import atomic_write as real_write
        def fail_stage(path, content):
            if path.name == 'new-1':
                raise OSError('staging disk full')
            real_write(path, content)
        with patch('memory_storage.atomic_write', side_effect=fail_stage):
            with self.assertRaises(OSError), self.store.lock():
                self.store.commit(self.changes, self.original)
        self.assertEqual(self.files(), self.original)
        with self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), self.original)
        self.assertFalse(self.store.pending.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction test')
    def test_windows_junction_memory_directory_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='memory-junction-') as temp:
            external = Path(temp)/'external'
            external.mkdir()
            sentinel = external/'sentinel'
            sentinel.write_bytes(b'unchanged')
            project = Path(temp)/'project'
            project.mkdir()
            destination = project/'memory'
            quote = lambda path: str(path).replace("'", "''")
            command = "New-Item -ItemType Junction -Path '" + quote(destination) + "' -Target '" + quote(external) + "' | Out-Null"
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with self.assertRaisesRegex(RuntimeError, 'gerçek bir proje'), MemoryStore(project).lock():
                self.fail('junction must not be followed')
            self.assertEqual(sentinel.read_bytes(), b'unchanged')

    def test_corrupt_manifest_cannot_escape_project(self):
        self.interrupted()
        path = self.store.pending/'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['entries'][0]['path'] = '../outside.md'
        path.write_text(json.dumps(manifest))
        before = self.files()
        with self.assertRaisesRegex(RuntimeError, 'Geçersiz hafıza yolu'), self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(self.files(), before)

    def test_duplicate_manifest_destinations_are_rejected(self):
        self.interrupted()
        path = self.store.pending/'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['entries'][1]['path'] = manifest['entries'][0]['path']
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, 'kayıtları'), self.store.lock(recovery=True):
            self.store.recover()

    def test_live_owner_lock_cannot_be_reclaimed_even_if_old(self):
        with self.store.lock():
            original_lock = self.store.lock_path.read_bytes()
            os.utime(self.store.lock_path, (1, 1))
            with self.assertRaisesRegex(RuntimeError, 'hâlâ çalışıyor'), MemoryStore(self.root).lock(recovery=True):
                self.fail('must not steal live lock')
            self.assertEqual(self.store.lock_path.read_bytes(), original_lock)

    def test_unknown_owner_lock_is_preserved(self):
        self.store.lock_path.write_bytes(b'legacy or corrupt owner')
        with self.assertRaises(ValueError), self.store.lock(recovery=True):
            pass
        self.assertEqual(self.store.lock_path.read_bytes(), b'legacy or corrupt owner')

    def test_foreign_lock_is_not_removed_on_exit(self):
        with self.store.lock():
            self.store.lock_path.write_bytes(b'foreign owner')
        self.assertEqual(self.store.lock_path.read_bytes(), b'foreign owner')

    def test_linked_destination_cannot_modify_outside_file(self):
        external = self.root/'external.md'
        external.write_bytes(b'external')
        path = self.root/'memory/STATUS.md'
        path.unlink()
        try:
            path.symlink_to(external)
        except OSError:
            self.skipTest('symlink creation unavailable')
        with self.assertRaisesRegex(RuntimeError, 'Bağlantılı'), self.store.lock():
            self.store.commit(self.changes, self.original)
        self.assertEqual(external.read_bytes(), b'external')

    def test_linked_journal_is_not_followed_or_deleted(self):
        external = self.root/'external-dir'
        external.mkdir()
        sentinel = external/'manifest.json'
        sentinel.write_bytes(b'sentinel')
        try:
            self.store.pending.symlink_to(external, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('symlink creation unavailable')
            quote = lambda path: str(path).replace("'", "''")
            command = "New-Item -ItemType Junction -Path '" + quote(self.store.pending) + "' -Target '" + quote(external) + "' | Out-Null"
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaisesRegex(RuntimeError, 'Geçersiz işlem'), self.store.lock(recovery=True):
            self.store.recover()
        self.assertEqual(sentinel.read_bytes(), b'sentinel')


class CrashIntegrationTests(unittest.TestCase):
    def test_real_process_exit_and_dead_lock_recovery(self):
        with tempfile.TemporaryDirectory(prefix='memory-crash-') as temp:
            project = Path(temp)/'proje ğüşö'
            initialized = subprocess.run([sys.executable, str(SKILL/'scripts/init_project_memory.py'), str(project)], capture_output=True)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            original = {p.name:p.read_bytes() for p in (project/'memory').glob('*.md')}
            code = """import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools'))
from memory_storage import MemoryStore,atomic_write
root=Path(sys.argv[1])
def crash(path,content):
 atomic_write(path,content)
 os._exit(73)
store=MemoryStore(root,write=crash)
with store.lock():
 names=['memory/SESSIONS.md','memory/STATUS.md']
 before=store.snapshot(names)
 store.commit({name:before[name]+b'\\nnew data' for name in names},before)
"""
            child = subprocess.run([sys.executable, '-c', code, str(project)], capture_output=True)
            self.assertEqual(child.returncode, 73, child.stderr)
            self.assertTrue((project/'memory/.lock').exists())
            checked = subprocess.run([sys.executable, str(project/'tools/memory_check.py'), '--json'], capture_output=True)
            self.assertEqual(checked.returncode, 1)
            self.assertIn('Tamamlanmamış', checked.stdout.decode('utf-8'))
            recover = subprocess.run([sys.executable, str(project/'tools/memory_close.py'), '--recover'], capture_output=True)
            self.assertEqual(recover.returncode, 0, recover.stderr + recover.stdout)
            self.assertEqual({p.name:p.read_bytes() for p in (project/'memory').glob('*.md')}, original)
            self.assertFalse((project/'memory/.lock').exists())
            self.assertFalse((project/'memory/.transaction').exists())
            normal = subprocess.run([sys.executable, str(project/'tools/memory_close.py'), '--summary', 'doğrulandı', '--next', 'devam'], capture_output=True)
            self.assertEqual(normal.returncode, 0, normal.stderr + normal.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
