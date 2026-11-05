#!/usr/bin/env python3
"""Plan/apply a baseline-verified tools upgrade; never rewrite live memory."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ASSETS = Path(__file__).resolve().parents[1] / "assets/project-memory"
sys.path.insert(0, str(ASSETS / "tools"))
from memory_storage import MemoryStore, atomic_write, linked


def safe(path):
    for parent in (path, *path.parents):
        if (parent.exists() or parent.is_symlink()) and linked(parent):
            raise ValueError(f"Linked path: {parent}")


def tree(root, ignore_cache=True):
    safe(root)
    if not root.is_dir():
        raise ValueError(f"Directory missing: {root}")
    result = {}
    for path in root.rglob("*"):
        safe(path)
        if ignore_cache and ("__pycache__" in path.relative_to(root).parts or path.suffix == ".pyc"):
            continue
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif not path.is_dir():
            raise ValueError(f"Unsupported path: {path}")
    return result


def package(assets):
    """Only shipped tools and neutral future-project templates are managed."""
    assets = Path(assets).absolute()
    safe(assets)
    result = {}
    for path in (assets / "tools").glob("*.py"):
        safe(path)
        result[path.relative_to(assets / "tools").as_posix()] = path.read_bytes()
    templates = [assets / name for name in ("AGENTS.md", "README.md", ".gitignore")]
    templates += [p for p in (assets / "memory").rglob("*") if p.is_file()]
    for path in templates:
        safe(path)
        result["project_memory_template/" + path.relative_to(assets).as_posix()] = path.read_bytes()
    if not result or "memory_check.py" not in result:
        raise ValueError("Not a project-memory assets directory")
    return result


def hashes(files):
    return {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}


def protected(project):
    result = {"memory/" + name: value for name, value in tree(project / "memory", ignore_cache=False).items()
              if name not in (".lock",) and not name.startswith(".transaction/")}
    for name in ("AGENTS.md", "CLAUDE.md", "README.md", ".gitignore"):
        path = project / name
        safe(path)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return result


def plan(project, baseline=None):
    project = Path(project).absolute()
    safe(project)
    if (project / "memory/.transaction").exists() or (project / "memory/.lock").exists():
        raise ValueError("Pending transaction or active lock; finish/recover it first")
    before = tree(project / "tools")
    current = hashes(package(ASSETS))
    old = hashes(package(baseline)) if baseline else {}
    entries = []
    for name in sorted(set(current) | set(old)):
        installed = before.get(name)
        if name not in current:
            status = "conflict"  # Never silently delete a formerly shipped file.
        elif installed == current[name]:
            status = "unchanged"
        elif name in old and installed == old[name]:
            status = "replace"
        elif installed is None and name not in old:
            status = "add"
        else:
            status = "conflict"
        entries.append({"path": name, "status": status, "before": installed,
                        "after": current.get(name)})
    return {"schema": 1, "project": str(project),
            "baseline": str(Path(baseline).absolute()) if baseline else None,
            "source": current, "tools_before": before, "protected": protected(project),
            "entries": entries}


def load_json(path):
    safe(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate(project, tools):
    """New checker + staged tool requirements; live read-only root for real links."""
    # The trusted running package supplies the validator, even when candidate
    # bytes came from Git. Never execute a downloaded installer/checker here.
    spec = importlib.util.spec_from_file_location("candidate_memory_check", ASSETS / "tools/memory_check.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    required_tools = [name for name in checker.REQUIRED_RELATIVE if name.startswith("tools/")]
    for name in required_tools:
        path = tools / name.removeprefix("tools/")
        safe(path)
        if not path.is_file():
            raise ValueError("Candidate tool missing: " + name)
    # Tool existence is checked against the candidate, records/links against the
    # actual copy. No copying of unrelated source trees or false broken links.
    checker.REQUIRED_RELATIVE = [name for name in checker.REQUIRED_RELATIVE if not name.startswith("tools/")]
    report = checker.audit(project)
    report["candidate_tools_checked"] = required_tools
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["errors"] else (2 if report["warnings"] else 0)


def save(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


def outside(path, project):
    safe(path)
    if path.resolve().is_relative_to(project.resolve()) or project.resolve().is_relative_to(path.resolve()):
        raise ValueError("Backup/plan location must be outside the project and not its ancestor")
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            raise ValueError("Private backup/plan must be outside Git working trees")


def rollback(project, backup, data):
    """Validate both complete directories before moving either. Keep every copy."""
    tools = project / "tools"
    old = backup / "old-tools"
    if old.exists():
        if tree(old) != data["tools_before"]:
            raise ValueError("Backup changed; manual recovery required")
        if tools.exists():
            if tree(tools) != data["tools_after"]:
                raise ValueError("External tools changes; preserved for manual recovery")
            tools.rename(backup / ("failed-tools-" + uuid.uuid4().hex))
        old.rename(tools)
    elif tree(tools) != data["tools_before"]:
        raise ValueError("Original tools cannot be verified; manual recovery required")


def recover(project, backup):
    project, backup = Path(project).absolute(), Path(backup).absolute()
    safe(project)
    outside(backup, project)
    journal = project / "memory/.transaction"
    data = load_json(journal / "project-update.json")
    if data.get("schema") != 1 or data.get("project") != str(project) or data.get("backup") != str(backup):
        raise ValueError("Project/backup does not match the update journal")
    store = MemoryStore(project)
    with store.lock(recovery=True):
        rollback(project, backup, data)
        save(backup / "recovery.json", {"state": "rolled_back"})
        (journal / "project-update.json").unlink()
        journal.rmdir()


def apply(plan_path, backup):
    reviewed = load_json(Path(plan_path))
    project = Path(reviewed["project"])
    if plan(project, reviewed["baseline"]) != reviewed:
        raise ValueError("Project/package/baseline changed since planning; create a fresh plan")
    if any(e["status"] == "conflict" for e in reviewed["entries"]):
        raise ValueError("Customized/unknown managed files; manual adaptation required; nothing applied")
    if all(e["status"] == "unchanged" for e in reviewed["entries"]):
        print("Already current; no changes")
        return
    backup = Path(backup).absolute()
    outside(backup, project)
    if backup.exists():
        raise ValueError("Backup destination must not exist")
    store = MemoryStore(project)
    with store.lock():
        if tree(project / "tools") != reviewed["tools_before"] or protected(project) != reviewed["protected"]:
            raise ValueError("Project changed before update")
        backup.mkdir(parents=True, mode=0o700)
        # Private, byte-preserving evidence, outside the project/Git tree.
        shutil.copytree(project / "memory", backup / "memory", ignore=shutil.ignore_patterns(".lock"))
        for name in ("AGENTS.md", "CLAUDE.md", "README.md", ".gitignore"):
            if (project / name).exists():
                shutil.copy2(project / name, backup / name)
        if protected(backup) != reviewed["protected"]:
            raise ValueError("Protected-file backup differs; no tools changed")
        staged = backup / "tools"
        shutil.copytree(project / "tools", staged)
        files = package(ASSETS)
        if hashes(files) != reviewed["source"]:
            raise ValueError("Package changed during staging")
        for name, content in files.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, content)
            if path.suffix == ".py":
                compile(content, name, "exec")
        if tree(staged) != {**reviewed["tools_before"], **reviewed["source"]}:
            raise ValueError("Staged tools do not match the reviewed plan")
        checked = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                  "_validate", str(project), str(staged)], capture_output=True,
                                 env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        (backup / "candidate-check.json").write_bytes(checked.stdout)
        if checked.returncode != 0:
            raise ValueError("Candidate health check failed/warned; inspect private backup; no tools changed")
        data = {**reviewed, "backup": str(backup), "tools_after": tree(staged)}
        save(backup / "receipt.json", data)
        journal = project / "memory/.transaction"
        journal.mkdir()
        save(journal / "project-update.json", data)
        try:
            if tree(project / "tools") != data["tools_before"] or protected(project) != data["protected"]:
                raise ValueError("Project changed during staging")
            (project / "tools").rename(backup / "old-tools")
            staged.rename(project / "tools")
            if tree(project / "tools") != data["tools_after"] or protected(project) != data["protected"]:
                raise ValueError("Post-update verification failed")
        except Exception:
            rollback(project, backup, data)
            (journal / "project-update.json").unlink()
            journal.rmdir()
            raise
        (journal / "project-update.json").unlink()
        journal.rmdir()
        save(backup / "result.json", {"state": "applied", "protected_files": "unchanged"})
    print(f"Tools updated; original memory/instructions preserved. Backup: {backup}")


def restore(project, backup):
    project, backup = Path(project).absolute(), Path(backup).absolute()
    safe(project)
    outside(backup, project)
    data = load_json(backup / "receipt.json")
    if data.get("schema") != 1 or data.get("project") != str(project) or data.get("backup") != str(backup):
        raise ValueError("Receipt does not match the project/backup")
    store = MemoryStore(project)
    with store.lock():
        if tree(project / "tools") != data["tools_after"] or tree(backup / "old-tools") != data["tools_before"]:
            raise ValueError("Tools/backup changed; automatic restore refused")
        journal = project / "memory/.transaction"
        journal.mkdir()
        save(journal / "project-update.json", data)
        rollback(project, backup, data)
        (journal / "project-update.json").unlink()
        journal.rmdir()
        save(backup / "restore.json", {"state": "restored_tools_only"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("_validate", help=argparse.SUPPRESS)
    p.add_argument("project", type=Path)
    p.add_argument("tools", type=Path)
    p = commands.add_parser("plan")
    p.add_argument("project", type=Path)
    p.add_argument("--baseline", type=Path, help="Old trusted package assets/project-memory directory")
    p.add_argument("--output", required=True, type=Path)
    p = commands.add_parser("apply")
    p.add_argument("plan", type=Path)
    p.add_argument("--backup-dir", required=True, type=Path)
    p = commands.add_parser("recover")
    p.add_argument("project", type=Path)
    p.add_argument("--backup-dir", required=True, type=Path)
    p = commands.add_parser("restore")
    p.add_argument("project", type=Path)
    p.add_argument("--backup-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "_validate":
            return validate_candidate(args.project, args.tools)
        if args.action == "plan":
            result = plan(args.project, args.baseline)
            outside(args.output.absolute(), args.project.absolute())
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
            for entry in result["entries"]:
                print(entry["status"] + ": tools/" + entry["path"])
            return 2 if any(e["status"] == "conflict" for e in result["entries"]) else 0
        if args.action == "apply":
            apply(args.plan, args.backup_dir)
        elif args.action == "recover":
            recover(args.project, args.backup_dir)
        else:
            restore(args.project, args.backup_dir)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
