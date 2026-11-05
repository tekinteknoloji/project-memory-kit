#!/usr/bin/env python3
"""Trusted Git release manager. Downloaded scripts are never executed by it."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import urlsplit
import uuid
import zipfile

import skill_install

SCRIPTS = Path(__file__).resolve().parent
SKILL_PATH = "plugins/project-memory/skills/project-memory"
ORIGIN = ".project-memory-origin.json"
STABLE = re.compile(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
spec = importlib.util.spec_from_file_location("git_project_updater", SCRIPTS / "update_project_memory.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, timeout=120,
                            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
                                 "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})
    if result.returncode:
        # Avoid reflecting credentials/proxy configuration from Git error output.
        raise ValueError("Git operation failed; check repository access/network/ref")
    return result.stdout


def repository_url(url, allow_local=False):
    parts = urlsplit(url)
    if parts.scheme == "https" and parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment:
        return url.rstrip("/")
    if allow_local and Path(url).is_absolute() and Path(url).is_dir():
        return str(Path(url).resolve())
    raise ValueError("Use an HTTPS Git repository URL without credentials; local paths are test-only")


def versions(url):
    tags = []
    for line in git("ls-remote", "--tags", "--refs", url).decode().splitlines():
        name = line.split()[1].removeprefix("refs/tags/")
        match = STABLE.fullmatch(name)
        if match:
            tags.append((tuple(map(int, match.groups())), name))
    return sorted(tags, reverse=True)


def descriptor(skill, version):
    return declaration(skill_install.fingerprint(skill), version)


def declaration(files, version):
    if not STABLE.fullmatch(version):
        raise ValueError("A stable X.Y.Z release version is required")
    return {"schema": 1, "product": "project-memory-kit", "version": version.removeprefix("v"),
            "procedure": "memory-tools-v1", "files": files}


def prepare_release(root, version):
    if not (root / "git_install.py").is_file():
        raise ValueError("Prepare releases only from the product package checkout")
    prefix = ("-c", "safe.directory=" + root.as_posix(), "-C", str(root))
    if git(*prefix, "status", "--porcelain"):
        raise ValueError("Commit/review product changes before preparing a release")
    # Hash committed blobs, not Windows checkout line endings.
    files = {}
    with zipfile.ZipFile(io.BytesIO(git(*prefix, "archive", "--format=zip", "HEAD", SKILL_PATH))) as zipped:
        for entry in zipped.infolist():
            if not entry.is_dir():
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError("Linked release files are not supported")
                name = entry.filename.removeprefix(SKILL_PATH + "/")
                files[name] = hashlib.sha256(zipped.read(entry)).hexdigest()
    with (root / "release.json").open("x", encoding="utf-8") as stream:
        json.dump(declaration(files, version), stream, indent=2)


def archive_path(name):
    path = PurePosixPath(name)
    devices = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if (path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
            or path.as_posix() != name.rstrip("/")
            or any(part.rstrip(" .") != part or part.split(".")[0].upper() in devices for part in path.parts)):
        raise ValueError("Unsafe/nonportable archive path")
    return path


def download(url, ref, destination):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", ref) or ".." in ref:
        raise ValueError("Invalid ref")
    destination.mkdir(parents=True, mode=0o700)
    bare = destination / "git"
    git("init", "--bare", str(bare))
    git("-C", str(bare), "-c", "protocol.file.allow=always", "fetch", "--depth=1", url, ref)
    commit = git("-C", str(bare), "rev-parse", "FETCH_HEAD^{commit}").decode().strip()
    archive = git("-C", str(bare), "archive", "--format=zip", "FETCH_HEAD")
    skill = destination / "skill"
    manifest = None
    seen = set()
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        for entry in zipped.infolist():
            name = entry.filename
            archive_path(name)
            if name.casefold() in seen:
                raise ValueError("Unsafe/duplicate archive path")
            seen.add(name.casefold())
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Linked release files are not supported")
            if name == "release.json":
                manifest = json.loads(zipped.read(entry))
            elif name.startswith(SKILL_PATH + "/") and not entry.is_dir():
                target = skill / name.removeprefix(SKILL_PATH + "/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zipped.read(entry))
    if not isinstance(manifest, dict) or manifest != descriptor(skill, manifest.get("version", "")):
        raise ValueError("Missing/invalid release.json or package hashes; release is not supported")
    if STABLE.fullmatch(ref) and ref.removeprefix("v") != manifest["version"]:
        raise ValueError("Release tag/version mismatch")
    for path in skill.rglob("*.py"):
        compile(path.read_bytes(), str(path.relative_to(skill)), "exec")
    updater.package(skill / "assets/project-memory")
    updater.save(destination / "release.json", manifest)
    origin = {"repository": url, "ref": ref, "commit": commit, "version": manifest["version"],
              "archive": str(skill), "files": manifest["files"], "procedure": manifest["procedure"]}
    updater.save(destination / "origin.json", origin)
    return origin


def cached_baseline(project, incoming, roots):
    """Projects may lag behind the globally installed skill. Check retained origins."""
    candidates = []
    for root in set(roots):
        updater.safe(root)
        for path in root.glob("run-*/*/origin.json"):
            data = updater.load_json(path)
            if data.get("repository") != incoming["repository"]:
                continue
            archive = Path(data["archive"])
            if archive != path.parent / "skill" or skill_install.fingerprint(archive) != data["files"]:
                continue
            version = tuple(map(int, data["version"].split(".")))
            if version <= tuple(map(int, incoming["version"].split("."))):
                candidates.append((version, archive / "assets/project-memory"))
    for _, baseline in sorted(candidates, key=lambda item: item[0], reverse=True):
        if not any(e["status"] == "conflict" for e in updater.plan(project, baseline)["entries"]):
            return baseline
    return None


def read_origin(target):
    path = target / ORIGIN
    if not path.exists():
        return None
    skill_install.reject_links(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or value.get("product") != "project-memory-kit":
        raise ValueError("Unknown installed provenance")
    return value


@contextmanager
def source_assets(path):
    previous = updater.ASSETS
    updater.ASSETS = path
    try:
        yield
    finally:
        updater.ASSETS = previous


def manage(url, provider, home, project=None, state=None, ref=None, baseline_ref=None, allow_local=False):
    url = repository_url(url, allow_local)
    if provider not in ("codex", "claude"):
        raise ValueError("Unsupported provider")
    home = Path(home).absolute()
    target = home / f".{provider}/skills/project-memory"
    if project:
        project = Path(project).absolute()
    state = Path(state).absolute() if state else (project.parent if project else home) / ".project-memory-manager"
    skill_install.reject_links(target)
    updater.outside(state, target)
    updater.safe(state)
    for parent in (state, *state.parents):
        if (parent / ".git").exists():
            raise ValueError("Private manager state must be outside Git working trees")
    if project:
        updater.outside(state, project)
        updater.plan(project)  # Read-only preflight: blocks pending writes/links.
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    # One manager operation per state root, across both hosts/projects.
    with skill_install.installation_lock(state):
        available = versions(url)
        if not ref:
            if not available:
                raise ValueError("No stable release tag found; branch HEAD is never installed implicitly")
            ref = available[0][1]
        run = state / ("run-" + uuid.uuid4().hex)
        run.mkdir(mode=0o700)
        result = {"schema": 1, "state": "preparing", "run": str(run)}
        updater.save(run / "result.json", result)
        try:
            incoming = download(url, ref, run / "source")
            before = skill_install.fingerprint(target) if target.exists() else {}
            old = read_origin(target) if target.exists() else None
            installed_files = {k: v for k, v in before.items() if k != ORIGIN}
            if old:
                if old["repository"] != url or old["files"] != installed_files:
                    raise ValueError("Installed skill has a different origin or custom changes; preserved")
                if tuple(map(int, incoming["version"].split("."))) < tuple(map(int, old["version"].split("."))):
                    raise ValueError("Automatic downgrade refused")
                if incoming["version"] == old["version"] and (incoming["files"] != old["files"] or incoming["commit"] != old["commit"]):
                    raise ValueError("Same release version has different content; preserved")
            elif before and installed_files != incoming["files"]:
                if not baseline_ref:
                    raise ValueError("Legacy skill lacks provenance; supply a verified --baseline-ref; preserved")
                legacy = download(url, baseline_ref, run / "legacy")
                if legacy["files"] != installed_files:
                    raise ValueError("Legacy skill differs from baseline; custom changes preserved")
                old = legacy
            if old and tuple(map(int, incoming["version"].split("."))) < tuple(map(int, old["version"].split("."))):
                raise ValueError("Automatic downgrade refused")
            with source_assets(Path(incoming["archive"]) / "assets/project-memory"):
                actual_plan = None
                if project:
                    baseline = None
                    if baseline_ref:
                        baseline = Path(download(url, baseline_ref, run / "baseline")["archive"]) / "assets/project-memory"
                    elif old:
                        archive = Path(old["archive"])
                        if skill_install.fingerprint(archive) != old["files"]:
                            raise ValueError("Cached baseline differs; preserved")
                        baseline = archive / "assets/project-memory"
                    actual_plan = updater.plan(project, baseline)
                    if not baseline_ref and any(e["status"] == "conflict" for e in actual_plan["entries"]):
                        roots = [state, home / ".project-memory-manager"]
                        if old:
                            roots.append(Path(old["archive"]).parents[2])
                        matched = cached_baseline(project, incoming, roots)
                        if matched:
                            baseline = matched
                            actual_plan = updater.plan(project, baseline)
                    if any(e["status"] == "conflict" for e in actual_plan["entries"]):
                        updater.save(run / "conflicts.json", actual_plan)
                        raise ValueError("Custom/unknown project tools; inspect conflicts.json; nothing applied")
                    # Full private copy first. Reject links before copytree can follow them.
                    updater.tree(project, ignore_cache=False)
                    candidate = run / "project-copy"
                    shutil.copytree(project, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
                    trial = updater.plan(candidate, baseline)
                    updater.save(run / "trial-plan.json", trial)
                    updater.apply(run / "trial-plan.json", run / "trial-backup")
                    if updater.plan(project, baseline) != actual_plan:
                        raise ValueError("Original project changed during copy test")
                    updater.save(run / "project-plan.json", actual_plan)
                    updater.apply(run / "project-plan.json", run / "project-backup")
                    result["project"] = str(project)
                    result["project_backup"] = str(run / "project-backup") if (run / "project-backup").exists() else None
                    result["state"] = "project_applied"
                    updater.save(run / "result.json", result)
                metadata = {"schema": 1, "product": "project-memory-kit", **incoming}
                same = old and old.get("commit") == incoming["commit"] and old["files"] == incoming["files"] and ORIGIN in before
                try:
                    if (skill_install.fingerprint(target) if target.exists() else {}) != before:
                        raise ValueError("Installed skill changed during copy tests")
                    if not same:
                        backup = skill_install.manage("install", provider, home, bool(before),
                            Path(incoming["archive"]), json.dumps(metadata, ensure_ascii=False).encode(), before)
                        result["skill_backup"] = str(backup) if backup else None
                except Exception:
                    if project and (run / "project-backup/receipt.json").exists():
                        updater.restore(project, run / "project-backup")
                        result["state"] = "project_rolled_back"
                    raise
            result.update(state="complete", repository=url, commit=incoming["commit"], version=incoming["version"],
                          skill="unchanged" if same else "installed", provider=provider)
            updater.save(run / "result.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        except Exception as error:
            result["error"] = str(error)
            updater.save(run / "result.json", result)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?")
    parser.add_argument("--provider", choices=["codex", "claude"], default="codex")
    parser.add_argument("--user-home", type=Path, default=Path.home())
    parser.add_argument("--project", type=Path, help="Explicit existing project; omission changes only the skill")
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--ref", help="Explicit tag/ref; otherwise highest stable version tag")
    parser.add_argument("--baseline-ref", help="Known release for a legacy skill/project")
    parser.add_argument("--prepare-release", metavar="VERSION", help="Generate release.json for the local package")
    args = parser.parse_args()
    try:
        if args.prepare_release:
            root = SCRIPTS.parents[4]
            prepare_release(root, args.prepare_release)
        else:
            if not args.repository:
                parser.error("repository is required")
            manage(args.repository, args.provider, args.user_home, args.project, args.state_dir,
                   args.ref, args.baseline_ref)
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired, zipfile.BadZipFile) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
