<!-- project-memory:start -->
## Global Project Memory

- When a writable, substantive project does not contain `memory/`, use the `project-memory` skill to initialize portable project memory unless the user opts out.
- Do not initialize memory for disposable experiments, unrelated one-off tasks, or read-only inspections.
- Treat the project directory as the portability boundary. Project-critical instructions and memory must remain inside it.
- At task start, load only `memory/INDEX.md`, `memory/CURRENT.md`, and the few topic files directly relevant to the task.
- At task end, persist only verified information likely to affect future work. Never store secrets, full conversations, source code, or large logs in memory.
<!-- project-memory:end -->
