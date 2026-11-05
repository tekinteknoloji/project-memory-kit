# Existing project upgrades

Skill installation and project upgrades are separate operations. Updating the
global skill never silently updates existing project tools or records.

Use the new package's `scripts/update_project_memory.py`, not a script inside
the old project. Python 3.10+ is required. On macOS/Linux use `python3`.
The commands below are run from the package root; substitute real paths.

## First work on a copy

1. Stop other assistant/writer processes for the selected project. Make a full
   project copy outside its original folder. Do not start with the live project.
2. Keep the old trusted package separately. `--baseline` must point to its
   `plugins/project-memory/skills/project-memory/assets/project-memory` directory.
   Do not use a live project's private memory as a package baseline.
3. Generate an external review plan (this reads the project without changing it):

```sh
python plugins/project-memory/skills/project-memory/scripts/update_project_memory.py plan "project-copy" --baseline "old-package/plugins/project-memory/skills/project-memory/assets/project-memory" --output "../upgrade-plan.json"
```

The plan lists `unchanged`, `replace`, `add`, or `conflict` for managed files.
Exit 2 means conflicts; exit 1 means a technical error. Unknown old versions and
modified managed tools block the whole update. There is no force/ignore-conflict
switch. Without a baseline only already-current files and missing new files can
be accepted. A missing file that existed in the baseline is also a conflict.

4. Review the JSON, especially project path, file list and conflicts. Apply only
   an acceptable plan. Choose a **new**, private backup directory outside the
   project on the **same filesystem/volume** as its tools:

```sh
python plugins/project-memory/skills/project-memory/scripts/update_project_memory.py apply "../upgrade-plan.json" --backup-dir "../private-upgrade-backup"
python "project-copy/tools/memory_check.py" --json
```

Plan and backup destinations must be outside Git working trees. The plan becomes stale if protected records, tools, package or relevant baseline
change. Generate a fresh plan rather than editing hashes or conflict states.
The tool validates a candidate copy before swapping tool directories. Warnings
also stop activation; inspect `candidate-check.json` in the private backup.
The project directory, source, plan and backup paths must not use symlinks/junctions.

## What is preserved

- Live `memory/` files, their original bytes/history, and root `AGENTS.md`,
  `CLAUDE.md`, `README.md`, `.gitignore` are not rewritten.
- Extra project-specific files under `tools/`, such as `source_snapshot.py`,
  travel unchanged with the tool directory.
- Custom changes inside a managed tool (for example additional checks inside
  `memory_check.py`) cause a conflict. A human must merge the relevant changes
  into a separate candidate and test that adaptation; the updater cannot infer
  which old behavior is intentional.
- Only shipped Python tools and the neutral `tools/project_memory_template/`
  files are managed. Templates seed future new projects; they are not the live
  project's memory. Files removed from a newer package are flagged for review,
  never silently deleted.

Tool upgrade success does not prove an old project's instructions already adopt
the new lifecycle protocol. Review such documentation separately, preserving
local rules and recording any explicitly approved adaptation. Do not re-run the
initializer over an existing project.

Backups contain PRIVATE memory, custom tools and instructions. Never commit or
publish them; do not put them in the product repository. The updater preserves
them automatically and does not replace a full project/offsite backup. Git
commit, global skill installation and application/RAG behavior are separate.

## Recovery and undo

An interrupted tool swap leaves `memory/.transaction/project-update.json`.
Normal memory writers/checkers must stop while that directory exists. Use the
new package's updater, **not** `memory_close.py --recover`, for this journal:

```sh
python plugins/project-memory/skills/project-memory/scripts/update_project_memory.py recover "project-copy" --backup-dir "../private-upgrade-backup"
```

Recovery verifies owner liveness and old/new directory hashes before rollback.
It refuses corrupt backups or external changes; keep all artifacts for manual
inspection. Never remove the lock/journal to bypass recovery. Early preparation
interruptions or filesystem/disk failures can require manual recovery; this is
not a power-loss/multi-directory atomicity guarantee. Keep the package available
since a swap interruption may temporarily leave the project without `tools/`.

To undo a successful update:

```sh
python plugins/project-memory/skills/project-memory/scripts/update_project_memory.py restore "project-copy" --backup-dir "../private-upgrade-backup"
```

Restore only replaces tools whose entire directory still matches the update
receipt. It preserves all memory edits made since the upgrade. Changed tools
require manual adaptation. Backups and displaced tool copies are retained.

After copy acceptance, applying to a live project is a separate authorized step:
make a fresh copy/backup, plan against the actual project, review it, apply and
re-run its project-specific checks. Never reuse a plan whose target was the copy.

The plan reports separate project skill, tool and template baseline matches and the presence of legacy age-based lock guidance. These are observations only. Merge customized instructions and adopt explicit recovery separately from tool replacement.
