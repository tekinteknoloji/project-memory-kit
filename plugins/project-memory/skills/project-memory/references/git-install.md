# Install or update from a Git address

User request example: “Bu Git adresinden proje hafızasını yükle; kuruluysa
güvenli güncelle: https://example.com/owner/project-memory-kit.git”.

Use the **already trusted** installed manager `scripts/install_from_git.py`.
In a reviewed product package the equivalent entry point is `git_install.py`.
For first bootstrap, obtain/review the package and these instructions before
running the manager; a URL alone is not a mechanism for an unconfigured agent
to discover/execute arbitrary software. Python 3.10+ and Git are required.

Choose the host (`codex` or `claude`) from the current session. If an existing
project is explicitly in scope, read its instructions and include its path via
`--project`. Respect exclusions such as a user forbidding changes to a bot/live
project. Do not silently infer an additional project or global-rule change.
Without `--project` only the host skill is installed/updated.

```sh
python git_install.py https://example.com/owner/project-memory-kit.git --provider claude
# Existing project explicitly included in the user's request:
python git_install.py https://example.com/owner/project-memory-kit.git --provider claude --project "../project-copy"
```

On macOS/Linux use `python3`. From an installed skill use the absolute path to
`scripts/install_from_git.py` instead of the root entry point. Run from outside
the skill directory being replaced. Never use administrator/root elevation.

## Release contract

The manager selects the numerically highest stable `vX.Y.Z`/`X.Y.Z` Git tag;
prerelease tags are excluded. It fetches into a bare repository and records the
actual commit. It does not implicitly install branch HEAD. No automatic fallback
to an older release occurs if the selected release is invalid. `--ref` is an
explicit advanced choice, still subject to package verification/downgrade rules.

The tag must contain root `release.json` with schema 1, product
`project-memory-kit`, matching version, procedure `memory-tools-v1`, and the exact
SHA-256 map of the complete skill tree. This is a declarative supported procedure,
not a shell command. Unknown procedures, hashes, archive links/path escapes or
tag/version mismatches stop the operation. HTTPS repository addresses without
embedded credentials are supported; local Git paths are used only by tests.

The trusted local manager/validator applies the known procedure; it does not run
downloaded installers, hooks, tests, or candidate checker code. Downloaded Python
is syntax-checked. The existing project's candidate validation uses the local
trusted checker and candidate required-file checks. This is structural/record
acceptance, not proof of new tool/model/application behavior. Inspect release
changes before adopting a new procedure/manager version. Repository selection is
the user's trust decision; hashes alone do not authenticate a publisher.

## Normal update

- Origin metadata is installed with the staged skill, including repository, tag,
  commit, version, hashes and retained source archive. Current files must match.
- A matching same commit is a skill no-op. Downgrades, changed same-version
  releases, repository switches and local skill edits are refused.
- For an explicitly selected existing project, the verified old archive supplies
  the baseline. If the project lags behind the global skill, retained same-repository
  source archives are hash-checked to find a matching baseline. First a full private project copy (excluding `.git` and Python
  caches) is tested; only then is a fresh plan applied to the original target.
  Memory/instructions and extra project checks are preserved. Customized managed
  tools block the entire operation, including the skill update.
- Previous skill and tool versions are retained; archives are never pruned
  automatically. If the final skill activation fails, project tools are restored
  when their hashes still permit it. External edits are never overwritten to
  force a rollback.

The existing-project path expects initialized `memory/` and `tools/`. For a new
project, install the skill first and use the initializer under its no-overwrite
contract. This command does not silently initialize or migrate project records.

## Legacy installations

An installation lacking origin metadata can be adopted if its files already
match the requested package exactly. Otherwise it stops safely. A known older
release can be supplied with `--baseline-ref vX.Y.Z`; it must have a valid release
descriptor and match the legacy skill exactly. A project-only legacy baseline
can likewise be selected explicitly. Customized legacy projects require the
manual adaptation workflow in [upgrading.md](upgrading.md), not a force switch.
Older tags predating `release.json` are not automatically trusted/adopted.

## Private state and interrupted operations

Default private state is `~/.project-memory-manager` for skill-only work; for a
project it is a sibling `.project-memory-manager` next to the project so tool
swaps stay on the same volume. `--state-dir` can select another private location
on that volume. State/plans/backups must remain outside Git working trees and
outside the project/skill targets. Each run retains the Git snapshot, trial copy,
plans, backup directories and `result.json`; these may contain PRIVATE DATA.
Do not publish them. This is not an offsite backup.

Successful result receipts identify version/commit, skill backup and project
backup. `state=preparing`, `project_applied` or `project_rolled_back` plus an error
means the operation did not complete; report the actual state and receipt path.
After a hard interruption inspect the manager lock and receipt; never delete a
possibly live lock or retry blindly. Use the trusted package's project updater
`recover`/`restore` for its tool transaction, as described in upgrading.md.
No whole-project+skill power-loss atomicity or unattended hard-crash recovery is
promised. Cached origins must still match their hashes before use.

## Publisher preparation (last, after acceptance)

Do not publish a version while acceptance gates remain open. Once the product
changes have been reviewed, tested and committed, run from a clean product tree:

```sh
python git_install.py --prepare-release X.Y.Z
```

Substitute the decided release number. The command exclusively creates
`release.json` from committed skill blobs, preserving Git line-ending semantics;
it refuses a dirty checkout or existing descriptor. For a subsequent release,
remove the old descriptor in a reviewed commit first, then generate the new one.
Review/commit the generated descriptor without changing skill files afterward;
validate source/package agreement and CI, then create the matching stable tag
and publish as the final step. Preparing the descriptor does not push/tag/release.

The repository's old releases will not support this workflow until a new accepted
release containing this contract is published. Do not claim an arbitrary pasted
URL already supports it.
