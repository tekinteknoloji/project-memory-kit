# Safe storage and explicit recovery

The close command uses one dependency-free `MemoryStore` for the session and receipt files. It does not rewrite decisions, requirements or conversation archives.

## Write protocol

Under an exclusively created project lock, read the original bytes and run the initial health check. Stage original and proposed bytes in `memory/.transaction/`, with paths and SHA-256 hashes in a manifest. Only after preparation is complete may live files be replaced. Read them back, run the final health check, mark committed, then clean the journal. No success receipt is printed until this completes.

The phases are `preparing`, `prepared`, `committed`, and `rolled_back`. A caught failure attempts rollback only when all destinations still match a recorded before/after version. Recovery copies are verified before any restoration. A conflicting edit blocks the entire rollback; it must not be overwritten with an older snapshot. A rollback failure preserves its journal for another explicit attempt.

## Recovery

Run `python tools/memory_check.py` first. A pending journal is an error, including a committed journal whose cleanup was interrupted. Then run `python tools/memory_close.py --recover`. Recovery does not append another session or claim a new save.

- Preparing: discard staging only if all live destinations still match their original hashes.
- Prepared: verify snapshots and destinations, then restore exact original bytes.
- Committed/rolled back: verify the selected final state and finish cleanup; do not undo a committed save.
- Missing/malformed manifest, unknown journal files, corrupt snapshots or external changes: stop and preserve the evidence. Do not delete files merely to silence the health check.

Recovery acquires a project lock. If another lock exists, it reclaims it only after explicitly verifying that its recorded process has exited. A live/reused PID, access-denied check, legacy lock text or malformed owner blocks recovery. Normal save never reclaims locks by age. Recovery attempts serialize through a separate marker; an interrupted recovery marker also requires review. No process is terminated by recovery.

If automatic recovery is refused, preserve the project and journal before any manual resolution. Compare the external edits and the journal's paths/hashes. Missing initial metadata or changed lock ownership cannot be safely guessed. Never force-copy old snapshots over unknown edits.

## Bounds and compatibility

Cooperating writers must use the same lock; readers must honor the pending-transaction error before trusting a receipt. A raw text editor can observe intermediate files. Hash checks detect observed external modifications but are not an operating-system atomic compare-and-swap against uncooperative writers. Old tools that ignore the journal must not write concurrently.

Individual replacement and file fsync are used; multi-file atomic visibility, full directory/power-loss durability, ACL preservation and network-filesystem semantics are not promised. Malicious writers that race filesystem checks are outside the lock cooperation model. Linked/reparse-point paths are rejected at checked boundaries. Hardware and Windows/Linux behavior still require their respective acceptance runs.

Private snapshots stay local and are ignored by generated project Git rules. They can contain the same sensitive information as the source Markdown; do not publish the journal, backup or real memory as a test fixture. A journal is short-lived transaction protection, not an independent backup.

The portable initializer distributes the new helper. Existing project tools are not silently upgraded; compare project customizations and migrate them separately. The health checker now expects 20 required files. `--transaction-id` is an internal health-check acknowledgement used only by the owning close command during post-write validation; ordinary users should not pass it to suppress a pending-journal error.

## Git receipt semantics

A close records `Git durumu` as an explicitly dated **pre-close** observation (`Git ölçüm anı: Kapanış öncesi`, `Git ölçüm zamanı`). The save itself can dirty a clean repository. A later check reports the actual current Git state separately; it does not compare a dated historical observation as if it were current. No tracked session/receipt or user files are excluded from Git status.

Older receipts retain their previous comparison behavior until replaced by a verified close. Only the identified obsolete Git-receipt warning is resolved by the new receipt format. Any unexpected warning-set change or health-check error after writing still aborts and restores the original save. An invalid/missing measurement timestamp is an error. Git execution/access failure is reported as unknown, not as absence of a repository; an unrecognized/localized non-repository error also remains conservatively unknown.
