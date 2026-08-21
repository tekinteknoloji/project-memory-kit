#!/usr/bin/env python3
"""Dependency-free repository and portable-memory integration tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-memory"
SKILL = PLUGIN / "skills" / "project-memory"
INITIALIZER = SKILL / "scripts" / "init_project_memory.py"
PYTHON_ENV = {**os.environ, "PYTHONUTF8": "1"}


class PackageTests(unittest.TestCase):
    def test_manifest_and_marketplace_are_consistent(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "project-memory")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        entries = [item for item in marketplace["plugins"] if item["name"] == manifest["name"]]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"]["path"], "./plugins/project-memory")

    def test_skill_and_distribution_files_exist(self) -> None:
        required = [
            SKILL / "SKILL.md",
            SKILL / "references" / "protocol.md",
            INITIALIZER,
            ROOT / "install.ps1",
            ROOT / "uninstall.ps1",
            ROOT / "PROJECT-MEMORY-KUR.cmd",
            ROOT / "PROJECT-MEMORY-GUNCELLE.cmd",
            ROOT / "PROJECT-MEMORY-KALDIR.cmd",
            ROOT / "global" / "AGENTS.snippet.md",
        ]
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        self.assertEqual(missing, [])
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: project-memory\n"))

    def test_repository_contains_no_machine_specific_user_path(self) -> None:
        forbidden = (
            "C:\\Users\\" + "TekinTeknoloji",
            "D:\\" + "Chatgpt",
            "TEKIN" + "T~1",
        )
        matches: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix.lower() not in {".md", ".py", ".ps1", ".cmd", ".json", ".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(value in text for value in forbidden):
                matches.append(str(path.relative_to(ROOT)))
        self.assertEqual(matches, [])

    def test_initializer_and_health_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="project-memory-test-") as directory:
            target = Path(directory) / "sample-project"
            initialized = subprocess.run(
                [sys.executable, str(INITIALIZER), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=PYTHON_ENV,
                check=False,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            checked = subprocess.run(
                [sys.executable, str(target / "tools" / "memory_check.py")],
                cwd=target,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=PYTHON_ENV,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("19/19", checked.stdout)

    def test_initializer_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="project-memory-conflict-") as directory:
            target = Path(directory) / "sample-project"
            target.mkdir()
            sentinel = target / "AGENTS.md"
            sentinel.write_text("keep-me", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INITIALIZER), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=PYTHON_ENV,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep-me")


if __name__ == "__main__":
    unittest.main(verbosity=2)
