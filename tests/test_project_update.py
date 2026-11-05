"""Existing-project upgrade acceptance on disposable copies only."""
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
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/project-memory/skills/project-memory"
spec = importlib.util.spec_from_file_location("project_updater", SKILL / "scripts/update_project_memory.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
from memory_init import initialize


class ProjectUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="memory-upgrade-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.baseline = self.root / "old-assets"
        shutil.copytree(updater.ASSETS, self.baseline)
        checker = self.baseline / "tools/memory_check.py"
        checker.write_bytes(b"# Old released version\n" + checker.read_bytes())
        # Simulate an older release lacking a newly introduced tool.
        (self.baseline / "tools/memory_backup.py").unlink()
        # initializer requires all six tools; initialize then remove the legacy-missing file.
        shutil.copy2(updater.ASSETS / "tools/memory_backup.py", self.baseline / "tools/memory_backup.py")
        self.project = self.root / "Türkçe proje"
        initialize(self.baseline, self.baseline / "tools", self.project)
        (self.baseline / "tools/memory_backup.py").unlink()
        (self.project / "tools/memory_backup.py").unlink()
        (self.project / "memory/DECISIONS.md").write_bytes("# Kararlar\r\n\r\nÖzel bilgi korunur.\r\n".encode())
        (self.project / "CLAUDE.md").write_bytes(b"custom host instructions\r\n")
        (self.project / "tools/source_snapshot.py").write_bytes(b"# Private project check\r\n")
        (self.project / "docs").mkdir()
        (self.project / "docs/design.md").write_bytes(b"# Project design\n")
        record = self.project / "memory/CURRENT.md"
        record.write_bytes(record.read_bytes() + b"\n[design](../docs/design.md)\n")
        self.plan_file = self.root / "review.json"
        self.backup = self.root / "private-backup"

    def prepare(self):
        data = updater.plan(self.project, self.baseline)
        self.plan_file.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_read_only_plan_apply_and_restore_preserve_records_and_custom_tools(self):
        before = updater.tree(self.project)
        data = self.prepare()
        self.assertEqual(updater.tree(self.project), before)
        states = {e["path"]: e["status"] for e in data["entries"]}
        self.assertEqual(states["memory_check.py"], "replace")
        self.assertEqual(states["memory_backup.py"], "add")
        protected = updater.protected(self.project)
        old_tools = updater.tree(self.project / "tools")
        updater.apply(self.plan_file, self.backup)
        self.assertEqual(updater.protected(self.project), protected)
        self.assertEqual(updater.tree(self.backup / "old-tools"), old_tools)
        self.assertEqual((self.project / "tools/source_snapshot.py").read_bytes(), b"# Private project check\r\n")
        checked = subprocess.run([sys.executable, str(self.project / "tools/memory_check.py"), "--json"],
                                 capture_output=True, env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        (self.project / "memory/CURRENT.md").write_bytes(b"New work after upgrade\r\n")
        updater.restore(self.project, self.backup)
        self.assertEqual(updater.tree(self.project / "tools"), old_tools)
        self.assertEqual((self.project / "memory/CURRENT.md").read_bytes(), b"New work after upgrade\r\n")

    def test_customized_managed_check_blocks_whole_upgrade(self):
        checker = self.project / "tools/memory_check.py"
        checker.write_bytes(checker.read_bytes() + b"\n# custom source_snapshot validation\n")
        before = updater.tree(self.project)
        self.assertTrue(any(e["status"] == "conflict" for e in self.prepare()["entries"]))
        with self.assertRaises(ValueError):
            updater.apply(self.plan_file, self.backup)
        self.assertEqual(updater.tree(self.project), before)
        self.assertFalse(self.backup.exists())

    def test_unknown_legacy_version_requires_baseline(self):
        self.assertTrue(any(e["status"] == "conflict" for e in updater.plan(self.project)["entries"]))

    def test_candidate_check_failure_does_not_change_project(self):
        record = self.project / "memory/CURRENT.md"
        record.write_bytes(record.read_bytes() + b"\n[missing](nonexistent.md)\n")
        self.prepare()
        before = updater.tree(self.project)
        with self.assertRaisesRegex(ValueError, "Candidate health"):
            updater.apply(self.plan_file, self.backup)
        self.assertEqual(updater.tree(self.project), before)
        self.assertTrue((self.backup / "candidate-check.json").exists())

    def test_command_line_plan_and_apply(self):
        command = [sys.executable, str(SKILL / "scripts/update_project_memory.py")]
        env = {**os.environ, "PYTHONUTF8": "1"}
        before = updater.protected(self.project)
        planned = subprocess.run(command + ["plan", str(self.project), "--baseline", str(self.baseline),
                                           "--output", str(self.plan_file)], capture_output=True, env=env)
        self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
        applied = subprocess.run(command + ["apply", str(self.plan_file), "--backup-dir", str(self.backup)],
                                 capture_output=True, env=env)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual(updater.protected(self.project), before)

    def test_stale_or_tampered_plan_refused(self):
        for change in ("record", "plan", "baseline"):
            with self.subTest(change=change):
                self.prepare()
                if change == "record":
                    (self.project / "memory/CURRENT.md").write_bytes(b"external work")
                elif change == "plan":
                    data = json.loads(self.plan_file.read_text())
                    data["entries"][0]["path"] = "../../escape"
                    self.plan_file.write_text(json.dumps(data))
                else:
                    path = self.baseline / "tools/memory_check.py"
                    path.write_bytes(path.read_bytes() + b"\n# changed baseline\n")
                before = updater.tree(self.project)
                with self.assertRaises(ValueError):
                    updater.apply(self.plan_file, self.backup)
                self.assertEqual(updater.tree(self.project), before)

    def test_activation_failure_rolls_back(self):
        self.prepare()
        before = updater.tree(self.project)
        rename = Path.rename

        def fail(path, destination):
            if path == self.backup / "tools":
                raise OSError("injected activation failure")
            return rename(path, destination)

        with patch.object(Path, "rename", fail), self.assertRaises(OSError):
            updater.apply(self.plan_file, self.backup)
        self.assertEqual(updater.tree(self.project), before)

    def interrupt(self):
        self.prepare()
        rename = Path.rename

        def interrupt(path, destination):
            if path == self.backup / "tools":
                raise SystemExit("simulated process interruption")
            return rename(path, destination)

        with patch.object(Path, "rename", interrupt), self.assertRaises(SystemExit):
            updater.apply(self.plan_file, self.backup)

    def test_interrupted_swap_has_explicit_recovery(self):
        before = updater.tree(self.project)
        self.interrupt()
        self.assertFalse((self.project / "tools").exists())
        with self.assertRaises(ValueError):
            updater.plan(self.project, self.baseline)
        updater.recover(self.project, self.backup)
        self.assertEqual(updater.tree(self.project), before)

    def test_corrupt_backup_is_preserved_and_recovery_refused(self):
        self.interrupt()
        corrupt = self.backup / "old-tools/memory_check.py"
        corrupt.write_bytes(b"corrupt backup")
        with self.assertRaises(ValueError):
            updater.recover(self.project, self.backup)
        self.assertEqual(corrupt.read_bytes(), b"corrupt backup")
        self.assertTrue((self.project / "memory/.transaction").exists())

    def test_restore_refuses_to_overwrite_later_tool_changes(self):
        self.prepare()
        updater.apply(self.plan_file, self.backup)
        custom = self.project / "tools/source_snapshot.py"
        custom.write_bytes(b"new custom check")
        with self.assertRaises(ValueError):
            updater.restore(self.project, self.backup)
        self.assertEqual(custom.read_bytes(), b"new custom check")

    def test_pending_lock_and_linked_tools_refused(self):
        lock = self.project / "memory/.lock"
        lock.write_bytes(b"other process")
        with self.assertRaises(ValueError):
            updater.plan(self.project, self.baseline)
        self.assertEqual(lock.read_bytes(), b"other process")
        lock.unlink()
        try:
            (self.project / "tools/link").symlink_to(self.baseline, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink permission unavailable")
        with self.assertRaises(ValueError):
            updater.plan(self.project, self.baseline)

    def test_real_legacy_release_when_history_available(self):
        archived = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}",
                                   "-C", str(ROOT), "archive", "--format=zip",
                                   "d64f3914932f104f92174c054bf9c837798d198d"], capture_output=True)
        if archived.returncode:
            self.skipTest("Historical release is not available in this checkout")
        old = self.root / "real-old-release"
        with zipfile.ZipFile(io.BytesIO(archived.stdout)) as archive:
            for item in archive.infolist():
                self.assertFalse(Path(item.filename).is_absolute())
                self.assertNotIn("..", Path(item.filename).parts)
            archive.extractall(old)
        old_skill = old / "plugins/project-memory/skills/project-memory"
        project = self.root / "real-legacy-project"
        initialized = subprocess.run([sys.executable, str(old_skill / "scripts/init_project_memory.py"),
                                      str(project)], capture_output=True, env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        before = updater.protected(project)
        self.plan_file.write_text(json.dumps(updater.plan(project, old_skill / "assets/project-memory")))
        updater.apply(self.plan_file, self.backup)
        self.assertEqual(updater.protected(project), before)


if __name__ == "__main__":
    unittest.main()
