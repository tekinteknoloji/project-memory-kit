---
name: project-memory
description: Initialize, read, update, audit, compact, archive, or portability-check a project's self-contained Markdown memory while preserving consistency and minimizing context usage. Use for ongoing project work when a memory directory exists or the user asks for project memory or migration.
---

# Project Memory

Maintain a small, selective, file-based project memory. Treat the project directory as the portable boundary: all project-critical files, requirements, decisions, memory, and memory-use instructions must travel inside it. Global instructions and installed skills may help but must not be required to understand or continue the project.

Preserve user intent and do not treat memory as more authoritative than verified current project state.

## Start a task

When `memory/` exists:

1. Read the project-root instruction file, then `memory/INDEX.md` and `memory/CURRENT.md`.
2. Read `memory/README.md` when the memory protocol or file roles are not already clear.
3. Select only the one to three topic files directly relevant to the task.
4. Inspect the real project files needed to verify current state.

Do not load the archive or every memory file by default.

When a writable, substantive project lacks memory, read [references/protocol.md](references/protocol.md) and initialize it once unless the user opts out. Prefer `scripts/init_project_memory.py <project-root>` when available. Do not initialize disposable or unrelated one-off work, and never overwrite existing instruction or memory files.

## Finish a task

After verifying the work:

- Update `CURRENT.md` when the active goal, state, next action, or blockers changed.
- Persist only information likely to affect future work.
- Store each fact in one canonical topic file and link to it elsewhere when needed.
- Keep every project-critical record and instruction inside the project directory; do not rely on a machine-specific global file as its only source.
- Do not copy conversations, source code, large logs, secrets, credentials, or information easily rediscovered from the repository.
- If there is no durable change, do not edit memory.

## Status and session-close phrases

Treat user phrases equivalent to “son durum nedir?” as a memory status request. Read `memory/STATUS.md` and `memory/CURRENT.md`, then answer with the active goal, current state, next action, blockers, and the standard receipt below. Do not modify memory solely because status was requested.

Treat phrases equivalent to “bugünlük bu kadar”, “çalışmayı kapat”, or “hafızayı kaydet” as a session-close request. Before answering:

1. Verify completed work and update the applicable canonical memory files.
2. Bring `CURRENT.md` up to date.
3. Prefer the project-local `tools/memory_close.py` to acquire the lock, write `SESSIONS.md` and `STATUS.md` atomically, run health checks, and re-read the receipt. If it is unavailable, perform equivalent steps and disclose the fallback.
4. Inspect Git and backup status separately. Never equate a file write with a Git commit or backup.
5. Return this compact receipt:

```text
🧠 Proje Hafızası: DEVREDE
💾 Dosya kaydı: DOĞRULANDI | YENİ KALICI DEĞİŞİKLİK YOK | HATA
🔖 Git durumu: TEMİZ | KAYDEDİLMEMİŞ DEĞİŞİKLİKLER VAR | GIT YOK | KONTROL EDİLEMEDİ
📦 Yerel yedekleme: YEREL YEDEK DOĞRULANDI | DOĞRULANMADI
☁️ Harici yedekleme: DOĞRULANDI | DOĞRULANMADI
🔎 Hafıza kontrolü: BAŞARILI | UYARI | HATA
🕒 Son kontrol: <project-local recorded time>
📄 Güncellenenler: <relative paths or Yok>
➡️ Sonraki adım: <short next action>
```

Use an ISO-like local timestamp including numeric UTC offset. Never claim `DOĞRULANDI` for file saving until files have been written and re-read successfully. A local Git bundle is not an offsite backup. Never claim backup success without verifying the relevant destination. If saving fails, report `HATA` and the unresolved cause instead of presenting a success receipt.

## Authority and conflicts

Use this order: newest explicit user instruction; verified project files and tests; active requirements and decisions; older memory; labeled inference.

Do not silently overwrite conflicting history. Mark the old record invalid or superseded and link the replacement. Label unverified conclusions as `inference` or `unverified`.

## Maintenance and portability

For audits, compaction, migration, archive work, portability checks, or status-file recovery, read [references/protocol.md](references/protocol.md). Never invent decisions while summarizing. Preserve requirements, decision rationale, identifiers, unresolved risks, and useful links.

Scheduled low-reasoning maintenance is read-only: run health checks, identify compaction candidates, and report recommendations without changing memory. Semantic compaction or archival rewriting requires explicit user approval, a clean or recoverable Git state, and post-change verification.
