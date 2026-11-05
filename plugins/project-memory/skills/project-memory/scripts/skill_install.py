#!/usr/bin/env python3
"""Install the shared skill for Codex or Claude Code without changing projects."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
from pathlib import Path
import shutil
import sys
import uuid

SOURCE = Path(__file__).resolve().parents[1]


def reject_links(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError(f"Linked installation path is not supported: {item}")


def fingerprint(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if "__pycache__" in path.relative_to(root).parts or path.suffix == ".pyc":
            continue
        reject_links(path)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif not path.is_dir():
            raise ValueError(f"Unsupported file: {path}")
    return result


@contextmanager
def installation_lock(skills: Path):
    lock = skills / ".project-memory.install.lock"
    # Exclusive creation: never delete another installer's lock.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write("Install/uninstall in progress; do not remove while running.\n")
    try:
        yield
    finally:
        lock.unlink()


def manage(action: str, provider: str, user_home: Path, force: bool = False,
           source: Path = SOURCE, metadata: bytes | None = None,
           expected_current: dict[str, str] | None = None) -> Path | None:
    if provider not in {"codex", "claude"} or action not in {"install", "uninstall"}:
        raise ValueError("Unknown provider or action")
    home = user_home.absolute()
    skills = home / (".codex" if provider == "codex" else ".claude") / "skills"
    target = skills / "project-memory"
    reject_links(target)
    if action == "uninstall" and not target.exists():
        print(f"Not installed: {target}")
        return None
    if action == "install":
        reject_links(source)
        if not (source / "SKILL.md").is_file():
            raise ValueError("Invalid package: SKILL.md is missing")
        expected = fingerprint(source)
    skills.mkdir(parents=True, exist_ok=True)
    with installation_lock(skills):
        reject_links(target)
        if expected_current is not None and (fingerprint(target) if target.exists() else {}) != expected_current:
            raise ValueError("Installed skill changed during preparation")
        if target.exists() and not target.is_dir():
            raise ValueError(f"Target is not a directory: {target}")
        backup_root = skills.parent / "project-memory-backups"
        reject_links(backup_root)
        backup = backup_root / f"project-memory-{uuid.uuid4().hex}"
        if action == "uninstall":
            # Retain custom installed files; removal from discovery needs only a rename.
            backup_root.mkdir(exist_ok=True)
            target.rename(backup)
            print(f"Uninstalled; retained backup: {backup}")
            return backup
        if target.exists() and not force:
            raise FileExistsError(f"Already installed: {target}; use --force to update with a backup")
        stage = target.with_name(f".project-memory.installing-{uuid.uuid4().hex}")
        had_backup = False
        try:
            shutil.copytree(source, stage, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            if fingerprint(stage) != expected:
                raise ValueError("Staged copy differs from package")
            if metadata is not None:
                with (stage / ".project-memory-origin.json").open("xb") as stream:
                    stream.write(metadata)
            if target.exists():
                backup_root.mkdir(exist_ok=True)
                target.rename(backup)
                had_backup = True
            try:
                stage.rename(target)
            except BaseException:
                if had_backup and not target.exists():
                    backup.rename(target)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        print(f"Installed {provider}: {target}")
        if had_backup:
            print(f"Previous installation retained: {backup}")
        return backup if had_backup else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "uninstall"])
    parser.add_argument("--provider", required=True, choices=["codex", "claude"])
    parser.add_argument("--force", action="store_true", help="Update and retain the previous skill")
    parser.add_argument("--user-home", type=Path, default=Path.home(),
                        help="Explicit user home (default: current OS user; useful for isolated testing)")
    args = parser.parse_args()
    try:
        manage(args.action, args.provider, args.user_home, args.force)
    except (OSError, ValueError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
