"""Portable project behavior across paths, zip transport and interrupted saves."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/project-memory/skills/project-memory'
sys.path.insert(0, str(SKILL/'assets/project-memory/tools'))
from memory_storage import MemoryStore, atomic_write


def run(*args):
    return subprocess.run([str(arg) for arg in args], capture_output=True,
                          encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='memory-portable-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base/'İlk kullanıcı'/'Türkçe proje ğüşöçıİ'
        result = run(sys.executable, SKILL/'scripts/init_project_memory.py', self.project)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.record = '# Kararlar\r\n\r\n## DEC-801 Taşınabilir karar\r\n- Gerekçe: Türkçe içerik korunacak.\r\n'.encode('utf-8')
        (self.project/'memory/DECISIONS.md').write_bytes(self.record)

    def check(self, project):
        result = run(sys.executable, project/'tools/memory_check.py', '--json')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['result'], 'BAŞARILI')

    def test_zip_transport_and_portable_initializer_preserve_private_records(self):
        original = hashes(self.project)
        archive = self.base/'transfer.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for path in self.project.rglob('*'):
                if path.is_file(): z.write(path, path.relative_to(self.project))
        destination = self.base/'İkinci konum'/'Taşınmış proje'
        with zipfile.ZipFile(archive) as z: z.extractall(destination)
        self.assertTrue(self.project.resolve().is_relative_to(self.base.resolve()))
        shutil.rmtree(self.project)  # Verified temporary test fixture only.
        self.assertEqual(hashes(destination), original)
        self.check(destination)
        new_project = self.base/'Yeni proje'
        result = run(sys.executable, destination/'tools/init_memory.py', new_project)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.check(new_project)
        self.assertNotIn('DEC-801', (new_project/'memory/DECISIONS.md').read_text(encoding='utf-8'))
        self.assertEqual((destination/'memory/DECISIONS.md').read_bytes(), self.record)

    def test_close_after_move_keeps_history_prefix_and_other_records(self):
        prior = (self.project/'memory/SESSIONS.md').read_bytes()
        destination = self.base/'Başka klasör ı'
        shutil.move(str(self.project), str(destination))
        result = run(sys.executable, destination/'tools/memory_close.py', '--summary',
                     'Türkçe taşıma kabulü', '--next', 'Doğrula')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertTrue((destination/'memory/SESSIONS.md').read_bytes().startswith(prior))
        self.assertEqual((destination/'memory/DECISIONS.md').read_bytes(), self.record)
        self.check(destination)

    def test_interrupted_transaction_recovers_after_directory_move(self):
        expected = {name: (self.project/name).read_bytes()
                    for name in ['memory/STATUS.md', 'memory/SESSIONS.md']}
        changes = {name: raw+b'\nInterrupted change\n' for name,raw in expected.items()}
        def crash(path, content):
            atomic_write(path, content)
            raise KeyboardInterrupt('simulated interruption')
        store = MemoryStore(self.project, write=crash)
        with self.assertRaises(KeyboardInterrupt), store.lock():
            store.commit(changes, expected)
        destination = self.base/'Kurtarma konumu ü'
        shutil.move(str(self.project), str(destination))
        result = run(sys.executable, destination/'tools/memory_close.py', '--recover')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        for name,raw in expected.items(): self.assertEqual((destination/name).read_bytes(), raw)
        self.assertFalse((destination/'memory/.transaction').exists())
        self.assertEqual((destination/'memory/DECISIONS.md').read_bytes(), self.record)
        self.check(destination)


if __name__ == '__main__': unittest.main()
