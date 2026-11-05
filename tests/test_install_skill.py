"""Cross-provider installation tests; never touch the real user profile."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skill_installer", ROOT / "install_skill.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallSkillTests(unittest.TestCase):
    def test_both_providers_preserve_rules_backup_and_uninstall(self):
        for provider in ("codex", "claude"):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as directory:
                home = Path(directory) / "Türkçe kullanıcı"
                root = home / f".{provider}"
                root.mkdir(parents=True)
                rules = root / ("CLAUDE.md" if provider == "claude" else "AGENTS.md")
                rules.write_bytes("# Özel kural\r\n".encode())
                installer.manage("install", provider, home)
                target = root / "skills/project-memory"
                self.assertEqual(installer.fingerprint(target), installer.fingerprint(installer.SOURCE))
                custom = target / "custom.txt"
                custom.write_bytes(b"keep custom content")
                with self.assertRaises(FileExistsError):
                    installer.manage("install", provider, home)
                self.assertTrue(custom.exists())
                backup = installer.manage("install", provider, home, force=True)
                self.assertEqual((backup / "custom.txt").read_bytes(), b"keep custom content")
                self.assertNotIn(root / "skills", backup.parents)
                removed = installer.manage("uninstall", provider, home)
                self.assertFalse(target.exists())
                self.assertTrue((removed / "SKILL.md").exists())
                self.assertEqual(rules.read_bytes(), "# Özel kural\r\n".encode())
                self.assertIsNone(installer.manage("uninstall", provider, home))

    def test_activation_failure_restores_previous_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installer.manage("install", "claude", home)
            target = home / ".claude/skills/project-memory"
            (target / "custom").write_bytes(b"original")
            before = installer.fingerprint(target)
            rename = Path.rename

            def fail_activation(path, destination):
                if path.name.startswith(".project-memory.installing-"):
                    raise OSError("injected activation failure")
                return rename(path, destination)

            with patch.object(Path, "rename", fail_activation), self.assertRaises(OSError):
                installer.manage("install", "claude", home, force=True)
            self.assertEqual(installer.fingerprint(target), before)
            self.assertEqual(list(target.parent.glob(".project-memory.installing-*")), [])
            self.assertFalse((target.parent / ".project-memory.install.lock").exists())

    def test_existing_lock_and_linked_target_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            skills = home / ".claude/skills"
            skills.mkdir(parents=True)
            lock = skills / ".project-memory.install.lock"
            lock.write_bytes(b"other owner")
            with self.assertRaises(FileExistsError):
                installer.manage("install", "claude", home)
            self.assertEqual(lock.read_bytes(), b"other owner")
            lock.unlink()
            outside = home / "outside"
            outside.mkdir()
            target = skills / "project-memory"
            try:
                target.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Directory symlinks unavailable")
            with self.assertRaises(ValueError):
                installer.manage("install", "claude", home, force=True)
            with self.assertRaises(ValueError):
                installer.manage("uninstall", "claude", home)
            self.assertTrue(outside.exists())

    def test_invalid_source_does_not_replace_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installer.manage("install", "codex", home)
            target = home / ".codex/skills/project-memory"
            before = installer.fingerprint(target)
            with self.assertRaises(ValueError):
                installer.manage("install", "codex", home, True, home / "missing")
            self.assertEqual(installer.fingerprint(target), before)

    def test_installed_claude_skill_initializes_a_portable_project(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "profile"
            installer.manage("install", "claude", home)
            script = home / ".claude/skills/project-memory/scripts/init_project_memory.py"
            project = Path(directory) / "Yeni proje"
            for command in ([sys.executable, str(script), str(project)],
                            [sys.executable, str(project / "tools/memory_check.py")]):
                result = subprocess.run(command, capture_output=True, env={**os.environ, "PYTHONUTF8": "1"})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((project / "memory/CURRENT.md").is_file())

    def test_unix_entrypoints_from_other_directory(self):
        if os.name == "nt" or not shutil.which("sh"):
            self.skipTest("Unix shell entrypoints run on Linux/macOS")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "Türkçe kullanıcı"
            for script in ("install.sh", "uninstall.sh"):
                result = subprocess.run(
                    ["sh", str(ROOT / script), "--provider", "claude", "--user-home", str(home)],
                    cwd=directory, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((home / ".claude/skills/project-memory").exists())

    def test_cli_requires_provider_and_runs_in_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(ROOT / "install_skill.py"), "install"]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            result = subprocess.run(command + ["--provider", "claude", "--user-home", directory],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(directory) / ".claude/skills/project-memory/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
