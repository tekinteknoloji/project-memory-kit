# Project memory protocol

## Portable project boundary

The project root is the portability boundary. Information required to understand, build, test, operate, or continue the project must be stored inside it. Keep the root instruction file and a vendor-neutral memory protocol with the project so it can move to another computer or AI system without depending on personal skills, global prompts, chat history, or machine-specific paths.

## Minimal structure

Create only files that have a clear role. The standard structure is:

- project-root `AGENTS.md`: task-entry and memory-routing instructions
- `memory/README.md`: vendor-neutral memory protocol and migration checklist
- `INDEX.md`: short routing map
- `CURRENT.md`: active goal, current state, next action, blockers
- `STATUS.md`: compact activation and last-save receipt
- `SESSIONS.md`: one concise line per explicit work-session close
- `REQUIREMENTS.md`: confirmed requirements
- `DECISIONS.md`: decisions and rationale
- `ARCHITECTURE.md`: stable system structure
- `CONVENTIONS.md`: project and memory conventions
- `ISSUES.md`: unresolved problems and risks
- `LEARNINGS.md`: reusable findings not obvious from the code
- `ARCHIVE/`: inactive detail excluded from normal reads
- project-local tools: health check, atomic close, initialization, and verified local Git bundle backup

## Durable-write test

Write a fact only when at least one is true:

- the user established a lasting preference or rule;
- a requirement or technical decision became confirmed;
- verified state will affect future tasks;
- a recurring failure and its validated resolution were discovered;
- the active goal, next action, or blocker changed.

Do not retain greetings, brainstorming that produced no decision, failed-attempt transcripts, copied code, raw logs, duplicate facts, or sensitive values.

## Record format

Use concise atomic entries. Include only useful fields: stable identifier when cross-references matter; status; date; statement or decision; rationale when losing it could cause a bad reversal; affected areas; and source.

## Status file

Keep `STATUS.md` short. Record the memory-system state, last close check with UTC offset, last durable write, file-write result, Git state, backup verification, health-check result, changed relative paths, and next action. A status request reads this file without changing it. A session-close request updates it after all other writes and then re-reads it before reporting success.

Use `DEVREDE` only when the root instructions, `INDEX.md`, `CURRENT.md`, and `STATUS.md` exist and are readable. Use `HATA` when a required write or verification fails. Do not hide partial saves.

File persistence, Git history, local bundle backup, and offsite backup are separate claims. Mark each independently. A verified sibling-directory Git bundle is local recovery only. Unless an offsite destination was actually inspected, use `DOĞRULANMADI` for external backup.

## Session history and health checks

Append one compact line to `SESSIONS.md` only for an explicit session close. Keep the newest entries readily readable and archive older entries when the file exceeds roughly 100 lines.

Prefer a project-local deterministic checker when present. It should verify required memory files, relative index targets, size thresholds, and likely embedded secrets without modifying files. Treat missing files or broken index targets as errors; excessive size and suspicious values as warnings that require review.

Use project-local locking and atomic replacement for multi-file close operations. If a fresh lock exists, stop rather than writing concurrently. A stale lock may be removed only after its age and target are verified.

Scheduled low-reasoning maintenance must remain read-only. It may recommend compaction but may not rewrite or archive semantic records without explicit user approval.

## Compaction triggers

Consider compaction when a file exceeds roughly 200 lines, more than five similar entries accumulate, a project phase completes, or inactive work obscures `CURRENT.md`.

During compaction:

1. Re-read the affected source records.
2. Merge exact repetition and move inactive detail to a dated archive file.
3. Preserve confirmed outcomes, rationale, constraints, identifiers, unresolved risks, and links.
4. Do not create new facts or silently resolve ambiguity.
5. Check the summary against current project files where practical.
6. Update `INDEX.md` only when routing or structure changed.

## Portability check

Before migration, verify that root instructions, memory, requirements, decisions, architecture, setup, run, and test guidance are inside the project; memory links are relative and valid; `CURRENT.md` is current; no critical rule exists only in a global file; machine-specific absolute paths are removed or documented as examples; and secrets are excluded.

## Maintenance report

Report changed memory files, what was compacted or archived, portability gaps, contradictions found, and any item requiring user judgment. Keep the report short when no issue is found.
