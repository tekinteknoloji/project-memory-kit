#!/usr/bin/env python3
"""Initialize portable project memory from bundled templates without overwriting files."""

from __future__ import annotations
import argparse, shutil, sys
from datetime import datetime
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "templates" / "project-memory"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("target", type=Path); args = parser.parse_args()
    target = args.target.resolve()
    if not SOURCE.is_dir():
        print(f"HATA: Şablon bulunamadı: {SOURCE}", file=sys.stderr); return 1
    conflicts = [path.relative_to(SOURCE) for path in SOURCE.rglob("*") if path.is_file() and (target / path.relative_to(SOURCE)).exists()]
    if conflicts:
        print("HATA: Var olan dosyaların üzerine yazılmadı:", file=sys.stderr)
        for conflict in conflicts: print(f"- {conflict}", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)
    for source in SOURCE.rglob("*"):
        destination = target / source.relative_to(SOURCE)
        if source.is_dir(): destination.mkdir(parents=True, exist_ok=True)
        else: destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
    replacements = {"{{TIMESTAMP}}": datetime.now().astimezone().isoformat(sep=" ", timespec="seconds"), "{{PROJECT_NAME}}": target.name}
    for path in target.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items(): text = text.replace(old, new)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Proje hafızası oluşturuldu: {target}"); return 0


if __name__ == "__main__": sys.exit(main())
