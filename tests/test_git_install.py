"""One-address install/update acceptance using local, disposable Git releases."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/project-memory/skills/project-memory"
sys.path.insert(0, str(SKILL / "scripts"))
spec = importlib.util.spec_from_file_location("git_manager_test", SKILL / "scripts/install_from_git.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
from memory_init import initialize


class GitInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_temp = tempfile.TemporaryDirectory(prefix="git-releases-")
        cls.addClassCleanup(cls.fixture_temp.cleanup)
        cls.fixture = Path(cls.fixture_temp.name) / "repository"
        cls.remote_skill = cls.fixture / manager.SKILL_PATH
        shutil.copytree(SKILL, cls.remote_skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        cls.old = Path(cls.fixture_temp.name) / "old-skill"
        checker = cls.remote_skill / "assets/project-memory/tools/memory_check.py"
        checker.write_bytes(b"# Previous released checker\n" + checker.read_bytes())
        shutil.copytree(cls.remote_skill, cls.old)
        cls.git_fixture("init")
        cls.git_fixture("config", "user.email", "fixture@example.invalid")
        cls.git_fixture("config", "user.name", "Release fixture")
        cls.publish("1.0.0")
        checker.write_bytes((SKILL / "assets/project-memory/tools/memory_check.py").read_bytes())
        # This file must never be executed by the release manager.
        (cls.remote_skill / "scripts/remote_installer.py").write_text("raise RuntimeError('REMOTE SCRIPT EXECUTED')\n")
        cls.publish("1.1.0")
        cls.git_fixture("tag", "v9.0.0-rc.1")

    @classmethod
    def git_fixture(cls, *args):
        result = subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(cls.fixture), *args], capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return result.stdout

    @classmethod
    def publish(cls, version):
        (cls.fixture / "release.json").write_text(json.dumps(manager.descriptor(cls.remote_skill, version)))
        cls.git_fixture("add", ".")
        cls.git_fixture("commit", "-m", "Fixture release " + version)
        cls.git_fixture("tag", "v" + version)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-manager-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "Türkçe kullanıcı"
        self.repo = self.root / "repo"
        shutil.copytree(self.fixture, self.repo)
        self.project = self.root / "project-copy"
        self.target = self.home / ".claude/skills/project-memory"

    def run_manager(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return manager.manage(str(self.repo), "claude", self.home, allow_local=True, **kwargs)

    def install_old(self):
        return self.run_manager(ref="v1.0.0")

    def old_project(self):
        initialize(self.old / "assets/project-memory", self.old / "assets/project-memory/tools", self.project)
        (self.project / "memory/DECISIONS.md").write_bytes("# Kararlar\r\n\r\nÖzel bilgi.\r\n".encode())
        (self.project / "tools/source_snapshot.py").write_bytes(b"# Custom control\r\n")

    def test_latest_stable_first_install_then_noop_with_provenance(self):
        result = self.run_manager()
        self.assertEqual(result["version"], "1.1.0")
        origin = manager.read_origin(self.target)
        self.assertEqual(origin["commit"], result["commit"])
        before = manager.skill_install.fingerprint(self.target)
        again = self.run_manager()
        self.assertEqual(again["skill"], "unchanged")
        self.assertEqual(manager.skill_install.fingerprint(self.target), before)
        self.assertTrue(Path(origin["archive"]).exists())

    def test_skill_and_project_upgrade_test_copy_then_preserve_archives(self):
        self.install_old()
        before_skill = manager.skill_install.fingerprint(self.target)
        self.old_project()
        before_records = manager.updater.protected(self.project)
        result = self.run_manager(project=self.project)
        self.assertEqual(result["version"], "1.1.0")
        self.assertTrue((Path(result["run"]) / "project-copy/memory/CURRENT.md").exists())
        self.assertEqual(manager.updater.protected(self.project), before_records)
        self.assertEqual((self.project / "tools/source_snapshot.py").read_bytes(), b"# Custom control\r\n")
        self.assertEqual(manager.skill_install.fingerprint(Path(result["skill_backup"])), before_skill)
        self.assertTrue((Path(result["project_backup"]) / "old-tools/memory_check.py").exists())

    def test_custom_project_or_skill_blocks_updates(self):
        self.install_old()
        self.old_project()
        checker = self.project / "tools/memory_check.py"
        checker.write_bytes(checker.read_bytes() + b"\n# Custom validation\n")
        before = manager.updater.tree(self.project)
        skill_before = manager.skill_install.fingerprint(self.target)
        with self.assertRaisesRegex(ValueError, "Custom/unknown project"):
            self.run_manager(project=self.project)
        self.assertEqual(manager.updater.tree(self.project), before)
        self.assertEqual(manager.skill_install.fingerprint(self.target), skill_before)
        (self.target / "custom.txt").write_bytes(b"Keep me")
        with self.assertRaisesRegex(ValueError, "custom changes"):
            self.run_manager()
        self.assertEqual((self.target / "custom.txt").read_bytes(), b"Keep me")

    def test_project_can_lag_behind_an_already_updated_global_skill(self):
        self.install_old()
        self.old_project()
        records = manager.updater.protected(self.project)
        self.run_manager()  # Global skill now new, project intentionally still old.
        result = self.run_manager(project=self.project)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["skill"], "unchanged")
        self.assertEqual(manager.updater.protected(self.project), records)
        self.assertTrue((Path(result["project_backup"]) / "old-tools/memory_check.py").exists())

    def test_skill_activation_failure_restores_project_tools(self):
        self.install_old()
        self.old_project()
        before = manager.updater.tree(self.project)
        with patch.object(manager.skill_install, "manage", side_effect=OSError("activation failed")):
            with self.assertRaises(OSError):
                self.run_manager(project=self.project)
        self.assertEqual(manager.updater.tree(self.project), before)
        self.assertEqual(manager.read_origin(self.target)["version"], "1.0.0")

    def test_legacy_skill_requires_exact_explicit_baseline(self):
        manager.skill_install.manage("install", "claude", self.home, source=self.old)
        before = manager.skill_install.fingerprint(self.target)
        with self.assertRaisesRegex(ValueError, "lacks provenance"):
            self.run_manager()
        self.assertEqual(manager.skill_install.fingerprint(self.target), before)
        self.assertEqual(self.run_manager(baseline_ref="v1.0.0")["version"], "1.1.0")

    def test_downgrade_rejected(self):
        self.run_manager()
        with self.assertRaisesRegex(ValueError, "downgrade"):
            self.run_manager(ref="v1.0.0")
        self.assertEqual(manager.read_origin(self.target)["version"], "1.1.0")

    def test_changed_same_version_release_is_rejected(self):
        self.run_manager()
        skill = self.repo / manager.SKILL_PATH
        (skill / "SKILL.md").write_bytes((skill / "SKILL.md").read_bytes() + b"\nChanged release\n")
        (self.repo / "release.json").write_text(json.dumps(manager.descriptor(skill, "1.1.0")))
        for args in (("add", "."), ("commit", "-m", "Mutated release"), ("tag", "-f", "v1.1.0")):
            manager.git("-C", str(self.repo), *args)
        before = manager.skill_install.fingerprint(self.target)
        with self.assertRaisesRegex(ValueError, "Same release"):
            self.run_manager()
        self.assertEqual(manager.skill_install.fingerprint(self.target), before)

    def test_publisher_manifest_from_committed_source(self):
        manager.git("-C", str(self.repo), "rm", "release.json")
        (self.repo / "git_install.py").write_bytes(b"# Publisher fixture\n")
        manager.git("-C", str(self.repo), "add", ".")
        manager.git("-C", str(self.repo), "commit", "-m", "Prepare source")
        manager.prepare_release(self.repo, "1.2.0")
        data = json.loads((self.repo / "release.json").read_text())
        self.assertEqual(data["version"], "1.2.0")
        self.assertEqual(data["files"], manager.skill_install.fingerprint(self.repo / manager.SKILL_PATH))
        manager.git("-C", str(self.repo), "add", "release.json")
        manager.git("-C", str(self.repo), "commit", "-m", "Release descriptor")
        manager.git("-C", str(self.repo), "tag", "-a", "v1.2.0", "-m", "Annotated release")
        result = self.run_manager()
        self.assertEqual(result["version"], "1.2.0")
        commit = manager.git("-C", str(self.repo), "rev-parse", "v1.2.0^{commit}").decode().strip()
        self.assertEqual(result["commit"], commit)
        with self.assertRaises((ValueError, FileExistsError)):
            manager.prepare_release(self.repo, "1.3.0")
        (self.repo / manager.SKILL_PATH / "SKILL.md").write_bytes(b"Uncommitted changes")
        with self.assertRaisesRegex(ValueError, "Commit/review"):
            manager.prepare_release(self.repo, "1.3.0")

    def test_untrusted_urls_or_unknown_procedures_rejected(self):
        for url in ("https://user:password@example.com/repo", "file:///tmp/repo", "--upload-pack=bad", "http://example.com/repo"):
            with self.assertRaises(ValueError):
                manager.repository_url(url)
        manifest = json.loads((self.repo / "release.json").read_text())
        manifest["procedure"] = "run-an-arbitrary-script"
        (self.repo / "release.json").write_text(json.dumps(manifest))
        for args in (("add", "."), ("commit", "-m", "Unsupported procedure"), ("tag", "v2.0.0")):
            manager.git("-C", str(self.repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args)
        with self.assertRaisesRegex(ValueError, "release.json"):
            self.run_manager()
        self.assertFalse(self.target.exists())

    def test_archive_paths_are_portable(self):
        manager.archive_path("plugins/project-memory/skills/project-memory/SKILL.md")
        for name in ("../escape", "/absolute", "tools/.. /escape", "tools/CON", "tools/NUL.py",
                     "tools/x.", "tools/./duplicate", "tools\\escape", "C:/escape"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                manager.archive_path(name)


if __name__ == "__main__":
    unittest.main()
