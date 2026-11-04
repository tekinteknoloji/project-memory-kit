"""Two entry points must preserve data and honor one observable scan policy."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'plugins/project-memory/skills/project-memory'
ASSETS=SKILL/'assets/project-memory'
ENV={**os.environ,'PYTHONUTF8':'1'}


def run(*args):
    return subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',env=ENV)


class InitializationScanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='memory-m2-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.project=self.base/'sample'
        r=run(sys.executable,SKILL/'scripts/init_project_memory.py',self.project)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def checker(self):
        spec=importlib.util.spec_from_file_location('scan_test',self.project/'tools/memory_check.py')
        module=importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(self.project/'tools'), *sys.path]):
            spec.loader.exec_module(module)
        return module

    def test_both_entry_points_measure_git_after_creating_files(self):
        for initializer,name in [(SKILL/'scripts/init_project_memory.py','skill'),(self.project/'tools/init_memory.py','portable')]:
            with self.subTest(name=name):
                target=self.base/name
                target.mkdir()
                self.assertEqual(run('git','-C',target,'init').returncode,0)
                result=run(sys.executable,initializer,target)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                status=(target/'memory/STATUS.md').read_text(encoding='utf-8')
                self.assertIn('- Git durumu: KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR',status)
                self.assertEqual(json.loads(run(sys.executable,target/'tools/memory_check.py','--json').stdout)['result'],'BAŞARILI')

    def test_canonical_template_update_survives_portable_generations(self):
        cloned=self.base/'kit'
        shutil.copytree(SKILL,cloned)
        current=cloned/'assets/project-memory/memory/CURRENT.md'
        with current.open('a',encoding='utf-8') as stream:stream.write('\nTemplate update sentinel.\n')
        first=self.base/'first'
        self.assertEqual(run(sys.executable,cloned/'scripts/init_project_memory.py',first).returncode,0)
        second=self.base/'second'
        result=run(sys.executable,first/'tools/init_memory.py',second)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Template update sentinel.',(second/'memory/CURRENT.md').read_text(encoding='utf-8'))
        self.assertIn('{{TIMESTAMP}}',(second/'tools/project_memory_template/memory/CURRENT.md').read_text(encoding='utf-8'))

    def test_missing_tool_is_detected_before_destination_writes(self):
        cloned=self.base/'kit'
        shutil.copytree(SKILL,cloned)
        (cloned/'assets/project-memory/tools/memory_storage.py').unlink()
        target=self.base/'missing'
        target.mkdir()
        sentinel=target/'private.txt';sentinel.write_bytes(b'user record')
        result=run(sys.executable,cloned/'scripts/init_project_memory.py',target)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual([p.name for p in target.iterdir()],['private.txt'])
        self.assertEqual(sentinel.read_bytes(),b'user record')

    def test_parent_file_conflict_is_detected_before_copying(self):
        for initializer,name in [(SKILL/'scripts/init_project_memory.py','skill'),(self.project/'tools/init_memory.py','portable')]:
            with self.subTest(name=name):
                target=self.base/name;target.mkdir()
                (target/'tools').write_bytes(b'keep existing file')
                result=run(sys.executable,initializer,target)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual([p.name for p in target.iterdir()],['tools'])
                self.assertEqual((target/'tools').read_bytes(),b'keep existing file')

    def test_invalid_git_directory_is_not_reported_as_no_git(self):
        target=self.base/'bad-git';target.mkdir();(target/'.git').mkdir()
        result=run(sys.executable,SKILL/'scripts/init_project_memory.py',target)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('- Git durumu: KONTROL EDİLEMEDİ',(target/'memory/STATUS.md').read_text(encoding='utf-8'))

    def test_dependency_directories_are_pruned_before_scandir(self):
        dependency=self.project/'node_modules'
        (dependency/'nested').mkdir(parents=True)
        (dependency/'nested/vendor.txt').write_text('not project source',encoding='utf-8')
        original=os.scandir
        def guarded(path):
            if isinstance(path,(str,bytes,os.PathLike)) and Path(path)==dependency:
                raise AssertionError('entered excluded directory')
            return original(path)
        module=self.checker()
        with patch('os.scandir',side_effect=guarded):
            report=module.audit(self.project)
        self.assertEqual(report['result'],'BAŞARILI')
        self.assertGreaterEqual(report['scan']['pruned_directories'],1)

    def test_source_secrets_remain_visible_but_values_are_not_reported(self):
        sentinel='ghp_'+'A'*32
        source=self.project/'src';source.mkdir()
        (source/'settings.env').write_text('API_KEY='+sentinel,encoding='utf-8')
        dependency=self.project/'node_modules';dependency.mkdir()
        (dependency/'vendor.txt').write_text(sentinel,encoding='utf-8')
        similar=self.project/'node_modules_notes';similar.mkdir()
        (similar/'source.txt').write_text(sentinel,encoding='utf-8')
        report=self.checker().audit(self.project)
        warnings='\n'.join(report['warnings'])
        self.assertIn('src/settings.env',warnings)
        self.assertIn('node_modules_notes/source.txt',warnings)
        self.assertNotIn('node_modules/vendor.txt',warnings)
        self.assertNotIn(sentinel,json.dumps(report))

    def test_each_text_file_is_read_once_per_audit(self):
        module=self.checker();calls=Counter();original=module.read_text
        def counted(path,errors):
            calls[str(path)]+=1
            return original(path,errors)
        with patch.object(module,'read_text',side_effect=counted):report=module.audit(self.project)
        self.assertEqual(report['result'],'BAŞARILI')
        self.assertTrue(calls)
        self.assertTrue(all(count==1 for count in calls.values()),calls)

    def test_archive_link_checks_are_preserved(self):
        archive=self.project/'memory/ARCHIVE/detail.md'
        archive.write_text('[missing](missing.md)',encoding='utf-8')
        report=self.checker().audit(self.project)
        self.assertTrue(any('ARCHIVE/detail.md' in error for error in report['errors']))


    def test_credential_bindings_skip_placeholders_and_hide_values(self):
        module=self.checker()
        examples=['password=example', 'token=${API_TOKEN}', 'api_key="<your-key>"',
                  'password: changeme', 'secret=os.getenv("SERVICE_SECRET")',
                  'A token is a word in this sentence.', 'password=**********']
        for example in examples:
            with self.subTest(example=example):self.assertFalse(module.has_secret(example))
        for example in ['password="canary-P4ssvalue"', 'CLOUDFLARE_API_TOKEN=canary-value-42',
                        'AKINSOFT_API_KEY=canary-value-99', '"password": "canary-P4ssvalue",']:
            with self.subTest(example=example):self.assertTrue(module.has_secret(example))
        secret='canary-P4ssvalue'
        (self.project/'service.env').write_text('password='+secret,encoding='utf-8')
        report=module.audit(self.project)
        self.assertTrue(any('service.env' in warning for warning in report['warnings']))
        self.assertNotIn(secret,json.dumps(report))


if __name__=='__main__':unittest.main(verbosity=2)
