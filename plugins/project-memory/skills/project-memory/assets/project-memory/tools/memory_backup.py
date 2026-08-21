#!/usr/bin/env python3
"""Create and verify a local Git bundle outside the project directory."""

from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--destination", type=Path, default=ROOT.parent / f"{ROOT.name}-backups"); args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        print("HATA: Yedek hedefi proje klasörünün dışında olmalıdır.", file=sys.stderr); return 1
    head = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    if head.returncode != 0:
        print("HATA: Git commit'i olmadan bundle oluşturulamaz.", file=sys.stderr); return 1
    status = run(["git", "-C", str(ROOT), "status", "--short"])
    if status.returncode != 0 or status.stdout.strip():
        print("HATA: Yedekten önce Git çalışma ağacı temiz olmalıdır.", file=sys.stderr); return 1
    destination.mkdir(parents=True, exist_ok=True)
    temporary, bundle = destination / "latest.bundle.tmp", destination / "latest.bundle"
    created = run(["git", "-C", str(ROOT), "bundle", "create", str(temporary), "--all"])
    if created.returncode != 0:
        print(f"HATA: {created.stderr}", file=sys.stderr); return 1
    verified = run(["git", "-C", str(ROOT), "bundle", "verify", str(temporary)])
    if verified.returncode != 0:
        temporary.unlink(missing_ok=True); print(f"HATA: Bundle doğrulanamadı: {verified.stderr}", file=sys.stderr); return 1
    temporary.replace(bundle); digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    manifest = {"created_at": datetime.now().astimezone().isoformat(timespec="seconds"), "commit": head.stdout.strip(), "bundle": bundle.name, "sha256": digest, "verification": "successful", "scope": "local-only; not offsite"}
    (destination / "latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": sys.exit(main())
