#!/usr/bin/env python3
"""Initialize a new project without copying the source project's records."""
from __future__ import annotations
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    # Embedded neutral assets are distributed beside this script.
    source = ROOT / "tools" / "project_memory_template"
    if not source.is_dir():
        print("HATA: project_memory_template bulunamadı.", file=sys.stderr)
        return 1
    files = [p for p in source.rglob("*") if p.is_file()]
    # Include the tools separately to avoid recursive template nesting.
    sources = [(p, p.relative_to(source)) for p in files]
    sources += [(ROOT / "tools" / name, Path("tools") / name)
                for name in ("init_memory.py", "memory_check.py", "memory_close.py", "memory_backup.py")]
    sources += [(p, Path("tools/project_memory_template") / p.relative_to(source)) for p in files]
    if any((target / relative).exists() for _, relative in sources):
        print("HATA: Var olan dosyaların üzerine yazılmadı.", file=sys.stderr)
        return 1
    replacements = {"{{TIMESTAMP}}": datetime.now().astimezone().isoformat(sep=" ", timespec="seconds"),
                    "{{PROJECT_NAME}}": target.name, "{{GIT_STATUS}}": "KONTROL EDİLEMEDİ"}
    for original, relative in sources:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if original.suffix == ".md" and not relative.is_relative_to("tools/project_memory_template"):
            text = original.read_text(encoding="utf-8")
            for old, new in replacements.items():
                text = text.replace(old, new)
            destination.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copy2(original, destination)
    print(f"Proje hafızası oluşturuldu: {target}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
