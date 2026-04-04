# Portable Project Bootstrap

Portable Project Bootstrap is a portable workspace suite for validating a workspace, bootstrapping brand-new projects, and routing existing-project work without baking one machine's paths into the runtime.

## Quick Start

The recommended public entrypoint is:

```powershell
python -m portable_project_bootstrap --help
```

Validate a workspace first:

```powershell
python -m portable_project_bootstrap.validator `
  --workspace-root <workspace_root> `
  --profile-name <profile_name>
```

Run a brand-new bootstrap dry-run:

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --dry-run
```

Route an existing project:

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-slug <project_slug>
```

## What This Project Is

This repository provides a small workspace suite with clear boundaries:

- `workspace-validator`
  Checks whether the current workspace and profile are usable.
- bootstrap runtime
  Initializes brand-new projects and safe fill-missing repairs.
- `workspace-router`
  Resolves existing-project repo and memory surfaces without invoking bootstrap.
- live wrapper
  Owns bootstrap mode selection for `new`, `legacy`, and `shadow`.

For Python-first projects, the bootstrap runtime now produces a development-ready starter repo by default. In addition to repo and memory skeletons, it can initialize git, create a `.gitignore`, write a human-facing `README.md`, generate a minimal `pyproject.toml`, and scaffold `tests/`, `examples/`, `LICENSE`, and `CONTRIBUTING.md`.

The suite is built around a few hard rules:

- use profile-driven paths instead of hardcoded machine paths
- keep repo content separate from repo-external memory
- fail closed when required context is missing or invalid
- report manual patch output instead of auto-applying unsafe structured edits
- never silently fall back from `new` to `legacy`

## Recommended Public Entrypoints

For public use, prefer the repo-local module surfaces:

- bootstrap:
  - `python -m portable_project_bootstrap ...`
- validator:
  - `python -m portable_project_bootstrap.validator ...`
- router:
  - `python -m portable_project_bootstrap.router ...`

An external skill wrapper can still forward into this repository, but that is an optional integration pattern for users who already operate a local skill environment. The public docs in this repository assume the repo-local Python module entrypoints first.

## Suite Workflow

### Brand-New Project Workflow

1. Load profile and workspace context.
2. Run `workspace-validator`.
3. Run bootstrap in `--dry-run` mode.
4. Review `status`, `project_index_result`, manual patch signals, `project_index_status`, and `bootstrap_log_status`.
5. If the dry-run is clean, rerun with `--execute`.
6. If behavior looks suspicious, use `--mode shadow`.
7. Use `--mode legacy` only when explicit rollback or containment is required.

### Existing Project Workflow

1. Load profile and workspace context.
2. Run `workspace-validator`.
3. Run `workspace-router` with an exact slug, exact project name, or another strong routing input.
4. Read the returned `read_first_files`.
5. Continue project work only after the route is unambiguous.

## CLI Usage

### Bootstrap

Show help:

```powershell
python -m portable_project_bootstrap --help
```

Brand-new project dry-run:

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --tech-stack Markdown `
  --dry-run
```

Real execution:

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --execute
```

Default Python-oriented repo outputs now include:

- `.gitignore`
- `README.md`
- `pyproject.toml` when Python metadata generation is enabled
- `tests/test_smoke.py`
- `examples/README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- git initialization unless disabled

### Validator

```powershell
python -m portable_project_bootstrap.validator `
  --workspace-root <workspace_root> `
  --profile-name <profile_name>
```

Behavior:

- returns `status: ok`, `status: partial`, or `status: error`
- exits `0` for `ok` or `partial`
- exits `1` for fail-closed validation errors

### Router

Exact slug route:

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-slug <project_slug>
```

Exact project-name route:

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>"
```

Behavior:

- returns `status: ok` for one safe match
- returns `status: partial` for ambiguity with safe candidates
- returns `status: error` when routing cannot proceed safely
- exits `0` for `ok` or `partial`
- exits `1` for fail-closed routing errors

## Modes

### `new`

- default bootstrap path
- use it for normal bootstrap operation
- fails explicitly if something is wrong
- does not silently fall back to `legacy`

### `legacy`

- explicit rollback and containment path
- keep it for emergency use, not as the normal operating mode

### `shadow`

- compare-only bootstrap validation
- use it when you need parity or drift checks without writes
- it must not perform real writes

## Required Inputs

Bootstrap runs usually require:

- `--workspace-root`
- `--profile-name`
- `--project-name`
- `--project-slug`
- `--project-summary`
- `--tech-stack`

Router runs usually require:

- `--workspace-root`
- `--profile-name`
- one routing query such as `--project-slug`, `--project-name`, `--route-signal`, `--repo-path`, or `--memory-path`

Useful bootstrap toggles:

- `--no-init-git`
- `--no-create-license`
- `--no-create-contributing`
- `--no-create-tests`
- `--no-create-examples`
- `--no-create-stack-metadata`

## Profile Protocol

Official protocol:

- primary path:
  - `<workspace_root>/.agent-memory/machine-profiles/<profile_name>.json`
- compatibility fallback path:
  - `<workspace_root>/.codex/workspace-profile/PROFILE.json`

Discovery order:

1. explicit `--profile-path`
2. primary profile path
3. compatibility fallback path

Profile rules:

- `schema_version` is required
- only `schema_version = 1` is currently supported
- required fields:
  - `schema_version`
  - `profile_name`
  - `repo_root`
  - `memory_root`
  - `backup_root`
- unsupported schema versions fail closed
- missing required fields fail closed
- invalid or non-absolute path shapes fail closed
- missing required workspace files fail closed

See [examples/default.profile.json](examples/default.profile.json) for a public sample profile.

## Example Workspace Layout

See [examples/workspace-layout.md](examples/workspace-layout.md) for a generic workspace layout and the standard brand-new vs existing-project flows.

## Development

This repository itself is now set up as a development-ready project repository:

- it is intended to live in its own git repository
- Python packaging metadata lives in [pyproject.toml](pyproject.toml)
- tests live under [tests](tests)
- public examples live under [examples](examples)

To start local development:

1. Review this README and [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md).
2. Optionally install the project in editable mode: `python -m pip install -e .`
3. Run the test suite: `python -m unittest discover -s tests -v`
4. Review [examples/default.profile.json](examples/default.profile.json) and [examples/workspace-layout.md](examples/workspace-layout.md)

## Optional External Skill Integration

If you already run a local skill environment, you can point an external wrapper at this repository. Treat that as an integration layer, not the primary public entrypoint.

For example, a local wrapper might expose a script like:

```text
<skill_path>/scripts/bootstrap_project.py
```

That wrapper should forward into this repository's guarded bootstrap wrapper instead of owning bootstrap logic itself.

## Safety Rules

- do not overwrite non-empty files automatically
- do not auto-apply manual patch output
- do not silently fall back from `new` to `legacy`
- do not let `shadow` perform real writes
- do not let validator or router silently turn into bootstrap
- fail closed when required profile or workspace state is missing or invalid

## Observation After Cutover

This project is in long-run observation and legacy deprecation-readiness assessment.

Watch these fields by suite surface:

- validator:
  - `status`
  - `profile_source`
  - `problems`
  - `warnings`
  - `return_code`
- router:
  - `status`
  - `matched_project_slug`
  - `candidate_projects`
  - `ambiguity_reason`
  - `return_code`
- bootstrap:
  - `status`
  - `project_index_result`
  - `manual_follow_up`
  - `manual_patch_output`
  - `project_index_status`
  - `bootstrap_log_status`
  - `return_code`

If something drifts unexpectedly:

1. identify whether the fault begins in profile loading, validator, router, or bootstrap
2. use `--mode shadow` only when the suspected issue is bootstrap-specific semantics
3. use `--mode legacy` only when explicit bootstrap rollback or containment is required

## Deprecation Readiness

`legacy` is still retained as an explicit emergency rollback path.

The near-term goal is not deletion. The next decision point is whether `legacy` can enter a formal deprecation-preparation window. In short:

- a long-run observation window must be complete
- only real operator runs count toward that window
- bootstrap execute-path evidence must include at least 3 non-identical real runs
- if `legacy` is still solving real incidents, keep it
- if the window is complete and `legacy` is not materially needed, move it into deprecation preparation
- if evidence is still thin or mixed, keep gathering evidence

See [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md) for the full Phase 14 exit criteria.

## Operational Classification

Treat suite issues as one of these classes first:

- profile/config issues
- validator issues
- router issues
- bootstrap issues

See [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md) for the detailed triage and response playbooks.

## Architecture At A Glance

- `profile_loader`
  Reads and validates workspace profiles.
- `workspace-validator`
  Checks readiness before bootstrap or routing.
- `bridge`
  Maps runtime input into the bootstrap request model.
- `planner`
  Decides what to do.
- `executor`
  Decides how to apply the already-planned actions.
- `workspace-router`
  Resolves existing-project repo and memory surfaces from `PROJECT_INDEX.md`.
- `live_wrapper`
  Centralizes mode selection for `new`, `legacy`, and `shadow`.

The key boundary is intentional:

- planner decides what to do
- executor decides how to do it

## Driving This Project With Agents

Any coding or automation agent can drive this project as long as it has:

- repository access
- file read or edit access
- shell or command execution access

If an agent lacks local repo access or shell execution, it can still help with reading or drafting, but it cannot safely run the full workflow.

### Tool-Agnostic Workflow

1. Open the repository and read this `README.md`.
2. Read the main runtime entrypoints:
   - `src/portable_project_bootstrap/live_wrapper.py`
   - `src/portable_project_bootstrap/profile_loader.py`
   - `src/portable_project_bootstrap/validator.py`
   - `src/portable_project_bootstrap/router.py`
3. Check that the target profile exists.
4. Run `workspace-validator` first.
5. Use bootstrap with `--dry-run` before any write.
6. Review the key status fields.
7. Only then decide whether to run with `--execute`.
8. Use `--mode shadow` for bootstrap comparison if needed.
9. Use `--mode legacy` only for explicit bootstrap rollback.

### Generic Agent Prompt Template

```text
Open the repository at <repo_root>/portable-project-bootstrap.
Read README.md plus these files first:
- src/portable_project_bootstrap/live_wrapper.py
- src/portable_project_bootstrap/profile_loader.py
- src/portable_project_bootstrap/validator.py
- src/portable_project_bootstrap/router.py

Check whether the profile exists at <workspace_root>/.agent-memory/machine-profiles/<profile_name>.json.
Run workspace validation first.
Then run a bootstrap dry-run through the repo-local entrypoint.
Report these fields exactly:
- status
- project_index_result
- manual_follow_up or manual_patch_output
- project_index_status
- bootstrap_log_status
- return code

If the dry-run looks unsafe or inconsistent, do not execute.
If needed, rerun with --mode shadow for compare-only validation.
If rollback is required, rerun explicitly with --mode legacy.
For an existing project entry task, use workspace-router instead of bootstrap.
```

### Dry-Run Example For An Agent

```text
Use python -m portable_project_bootstrap.
Run workspace validation first for workspace-root <workspace_root> and profile-name <profile_name>.
Then run a dry-run for a brand-new project with:
- project-name "<project_name>"
- project-slug <project_slug>
- project-summary "<project_summary>"
- tech-stack Python and Markdown

Do not execute writes. Report:
- status
- project_index_result
- manual_follow_up or manual_patch_output
- project_index_status
- bootstrap_log_status
- return code
```

### Explicit Legacy Rollback Example For An Agent

```text
Use the same bootstrap input with --mode legacy.
Treat this as rollback or containment, not as the default path.
After the run, report:
- why rollback was used
- status
- project_index_result
- manual patch signals
- return code
- whether further shadow comparison is needed
```

### Shadow Comparison Example For An Agent

```text
Use the same bootstrap input with --mode shadow.
Do not allow writes.
Report:
- shadow_matched
- any shadow_differences
- status
- project_index_result
- manual_patch_output
- return code
If shadow_differences appear, stop and recommend whether to stay on new, investigate further, or temporarily use legacy.
```

### Codex / Codex CLI

```text
Open <repo_root>/portable-project-bootstrap, read README.md and the wrapper/profile-loader/validator/router files, confirm the target profile exists, run workspace validation, then run a bootstrap dry-run and report status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
If anything looks suspicious, use --mode shadow before suggesting --execute.
If rollback is needed, use --mode legacy explicitly and explain why.
For existing-project entry, use workspace-router and report repo path, memory path, and read-first files.
```

### Claude Code

```text
In this repo, first read README.md plus src/portable_project_bootstrap/live_wrapper.py, profile_loader.py, validator.py, and router.py.
Check the target profile under <workspace_root>/.agent-memory/machine-profiles/<profile_name>.json.
Run workspace validation first.
Run a bootstrap dry-run only after validation passes.
Do not execute writes until you summarize status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
Use --mode shadow for compare-only checks if needed.
Use --mode legacy only for explicit rollback.
Use workspace-router for existing-project entry work.
```

### Cursor

```text
Read README.md and the wrapper, validator, and router entrypoints first.
Verify the profile file exists.
Run workspace-validator in the integrated terminal.
Run a bootstrap dry-run only after validation succeeds.
Summarize status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code before proposing execute.
If results are unclear, run --mode shadow.
If rollback is needed, run --mode legacy and explain the trigger.
For existing projects, run workspace-router instead of guessing paths.
```

### OpenClaw Or Other General Agents

For OpenClaw or another general agent, use the same flow only if it already has:

- local repo access
- file read or edit access
- local command execution access

```text
Use the local repository at <repo_root>/portable-project-bootstrap.
Read README.md first, verify the profile exists, run workspace validation, run a bootstrap dry-run, and report status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
If the dry-run looks suspicious, switch to --mode shadow.
If rollback is required, use --mode legacy explicitly and record why.
For existing-project entry, use workspace-router and report the resolved repo path, memory path, and read-first files.
```

## Examples And Supporting Files

- [examples/default.profile.json](examples/default.profile.json)
  Public sample profile with placeholder paths.
- [examples/workspace-layout.md](examples/workspace-layout.md)
  Generic workspace layout and flow guide.
- [examples/README.md](examples/README.md)
  Notes on how to adapt the examples to your own machine.
- [CONTRIBUTING.md](CONTRIBUTING.md)
  Minimal contribution guide.
- [LICENSE](LICENSE)
  Open-source license for this repository.

## Current Status

- the bootstrap default mode is `new`
- `legacy` remains an explicit emergency rollback path
- `shadow` remains compare-only
- `workspace-validator` and `workspace-router` are part of the suite
- the project is in long-run observation and legacy deprecation-readiness assessment
