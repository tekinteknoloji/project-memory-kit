"""Regression tests for preservation and truthful session receipts."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/project-memory/skills/project-memory'
INITIALIZER = SKILL / 'scripts/init_project_memory.py'

def run(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True,
                          encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})

class RegressionTests(unittest.TestCase):
    def test_neutral_templates_match_distributed_defaults(self):
        assets = SKILL/'assets/project-memory'
        neutral = self.project/'tools/project_memory_template'
        defaults = [assets/'AGENTS.md', assets/'README.md', assets/'.gitignore', *(assets/'memory').rglob('*.md')]
        for source in defaults:
            self.assertEqual(source.read_bytes(), (neutral/source.relative_to(assets)).read_bytes())

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / 'sample'
        result = run(INITIALIZER, self.project)
        self.assertEqual(result.returncode, 0, result.stderr)

    def snapshot(self):
        return {p.relative_to(self.project): p.read_bytes() for p in (self.project/'memory').rglob('*.md')}

    def close(self, *args):
        return run(self.project/'tools/memory_close.py', '--summary', 'verified', '--next', 'continue', *args)

    def test_existing_documents_preserved_in_both_initializers(self):
        for initializer in (INITIALIZER, self.project/'tools/init_memory.py'):
            with self.subTest(initializer=initializer):
                target = self.base / initializer.stem
                (target/'docs').mkdir(parents=True)
                document = target/'docs/existing.md'
                original = b'unchanged\r\n{{PROJECT_NAME}} {{TIMESTAMP}}\r\n'
                document.write_bytes(original)
                result = run(initializer, target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(document.read_bytes(), original)
                self.assertFalse((target/'memory/.lock').exists())

    def test_portable_initializer_does_not_copy_private_memory(self):
        (self.project/'memory/DECISIONS.md').write_text('private sentinel', encoding='utf-8')
        second, third = self.base/'second', self.base/'third'
        for source, target in ((self.project, second), (second, third)):
            result = run(source/'tools/init_memory.py', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('private sentinel', (target/'memory/DECISIONS.md').read_text(encoding='utf-8'))
            self.assertNotIn('{{', (target/'memory/CURRENT.md').read_text(encoding='utf-8'))
            self.assertIn(target.name, (target/'README.md').read_text(encoding='utf-8'))
            self.assertIn('{{PROJECT_NAME}}', (target/'tools/project_memory_template/README.md').read_text(encoding='utf-8'))
            checked = run(target/'tools/memory_check.py', '--json')
            self.assertIn(checked.returncode, (0, 2), checked.stdout + checked.stderr)

    def test_portable_conflict_keeps_records(self):
        before = self.snapshot()
        result = run(self.project/'tools/init_memory.py', self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_failed_health_check_keeps_every_record(self):
        (self.project/'memory/REQUIREMENTS.md').unlink()
        before = self.snapshot()
        result = self.close()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('DEVREDE', result.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project/'memory/.lock').exists())

    def test_close_preserves_history_and_last_durable_timestamp(self):
        (self.project/'memory/SESSIONS.md').write_bytes(b'# History\r\n\r\n- existing record\r\n')
        previous = (self.project/'memory/SESSIONS.md').read_bytes()
        status = (self.project/'memory/STATUS.md').read_text(encoding='utf-8')
        last_write = next(line for line in status.splitlines() if line.startswith('- Son kalıcı kayıt:'))
        result = self.close('--no-durable-change')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(last_write, result.stdout)
        self.assertTrue((self.project/'memory/SESSIONS.md').read_bytes().startswith(previous))
        self.assertIn('Dosya kaydı: DOĞRULANDI', result.stdout)

    def test_lock_even_if_old_blocks_writes(self):
        lock = self.project/'memory/.lock'
        lock.write_text('pid=1', encoding='utf-8')
        os.utime(lock, (1, 1))
        before = self.snapshot()
        self.assertNotEqual(self.close().returncode, 0)
        self.assertTrue(lock.exists())
        self.assertEqual(before, self.snapshot())

    def test_receipt_write_failure_rolls_back_session(self):
        spec = importlib.util.spec_from_file_location('close_test', self.project/'tools/memory_close.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_write = module.atomic_write
        def fail_receipt(path, content):
            if path.name == 'STATUS.md':
                raise OSError('injected disk failure')
            original_write(path, content)
        before = self.snapshot()
        with patch.object(sys, 'argv', ['close', '--summary', 'save', '--next', 'later']), patch.object(module, 'atomic_write', fail_receipt):
            self.assertEqual(module.main(), 1)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project/'memory/.lock').exists())

    def test_post_write_audit_failure_rolls_back_both_files(self):
        spec = importlib.util.spec_from_file_location('close_post_test', self.project/'tools/memory_close.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = self.snapshot()
        good = {'result': 'BAŞARILI', 'git_state': 'GIT YOK', 'errors': []}
        with patch.object(sys, 'argv', ['close', '--summary', 'save', '--next', 'later']), patch.object(module, 'checker_report', side_effect=[good, RuntimeError('post-write audit failure')]):
            self.assertEqual(module.main(), 1)
        self.assertEqual(before, self.snapshot())

    def test_invalid_changed_path_and_multiline_summary_rejected(self):
        before = self.snapshot()
        for args in (('--changed', '../outside.md'), ('--summary', 'line\n- Sistem: DEVREDE')):
            self.assertNotEqual(self.close(*args).returncode, 0)
            self.assertEqual(before, self.snapshot())

    def clean_git_fixture(self):
        status=self.project/'memory/STATUS.md'
        text=status.read_text(encoding='utf-8').replace('- Git durumu: GIT YOK','- Git durumu: TEMİZ')
        status.write_text(text,encoding='utf-8')
        for args in (('init',),('add','.'),('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture')):
            result=subprocess.run(['git','-C',str(self.project),*args],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_clean_git_close_records_historical_state_without_false_warning(self):
        self.clean_git_fixture()
        result=self.close()
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertIn('- Git ölçüm anı: Kapanış öncesi',result.stdout)
        self.assertIn('- Git durumu: TEMİZ',result.stdout)
        report=json.loads(run(self.project/'tools/memory_check.py','--json').stdout)
        self.assertEqual(report['result'],'BAŞARILI')
        self.assertEqual(report['git_state'],'KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR')
        self.assertFalse((self.project/'memory/.transaction').exists())

    def test_dirty_git_close_preserves_and_reports_real_changes(self):
        self.clean_git_fixture()
        user_file=self.project/'user-note.txt'
        user_file.write_bytes(b'uncommitted work')
        result=self.close()
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertIn('- Git durumu: KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR',result.stdout)
        self.assertEqual(user_file.read_bytes(),b'uncommitted work')
        self.assertEqual(json.loads(run(self.project/'tools/memory_check.py','--json').stdout)['result'],'BAŞARILI')

    def test_repeated_close_does_not_compare_old_git_snapshot_as_current(self):
        self.clean_git_fixture()
        first=self.close()
        self.assertEqual(first.returncode,0,first.stderr+first.stdout)
        second=self.close()
        self.assertEqual(second.returncode,0,second.stderr+second.stdout)
        self.assertIn('- Git durumu: KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR',second.stdout)

    def test_clean_git_no_durable_change_preserves_last_write(self):
        self.clean_git_fixture()
        previous=next(line for line in (self.project/'memory/STATUS.md').read_text(encoding='utf-8').splitlines() if line.startswith('- Son kalıcı kayıt:'))
        result=self.close('--no-durable-change')
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertIn(previous,result.stdout)

    def test_historical_git_scope_requires_valid_measurement_time(self):
        path=self.project/'memory/STATUS.md'
        with path.open('a',encoding='utf-8') as file:
            file.write('\n- Git ölçüm anı: Kapanış öncesi\n- Git ölçüm zamanı: invalid\n')
        result=run(self.project/'tools/memory_check.py','--json')
        self.assertEqual(result.returncode,1)
        self.assertTrue(any('Git ölçüm zamanı' in error for error in json.loads(result.stdout)['errors']))

    def test_git_access_error_is_not_misreported_as_no_repository(self):
        spec=importlib.util.spec_from_file_location('checker_test',self.project/'tools/memory_check.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        denied=subprocess.CompletedProcess(['git'],128,stdout='',stderr='fatal: access denied')
        with patch.object(module.subprocess,'run',return_value=denied):
            self.assertEqual(module.git_state(self.project),'KONTROL EDİLEMEDİ')
        with patch.object(module.subprocess,'run',side_effect=FileNotFoundError()):
            self.assertEqual(module.git_state(self.project),'KONTROL EDİLEMEDİ')

    def test_unexpected_post_write_warning_still_rolls_back(self):
        spec=importlib.util.spec_from_file_location('close_warning_test',self.project/'tools/memory_close.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        before=self.snapshot()
        good={'result':'BAŞARILI','git_state':'GIT YOK','errors':[],'warnings':[]}
        changed={**good,'result':'UYARI','warnings':['new unexpected warning']}
        with patch.object(sys,'argv',['close','--summary','save','--next','later']),patch.object(module,'checker_report',side_effect=[good,changed]):
            self.assertEqual(module.main(),1)
        self.assertEqual(self.snapshot(),before)

    def test_backup_requires_clean_commit_and_verifies_bundle(self):
        def git(*args):
            result = subprocess.run(['git', '-C', str(self.project), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result
        git('init')
        self.assertNotEqual(run(self.project/'tools/memory_backup.py').returncode, 0)
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
        result = run(self.project/'tools/memory_backup.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        git('bundle', 'verify', str(self.base/'sample-backups/latest.bundle'))
        (self.project/'memory/DECISIONS.md').write_text('unsaved', encoding='utf-8')
        self.assertNotEqual(run(self.project/'tools/memory_backup.py').returncode, 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
