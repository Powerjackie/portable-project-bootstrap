# Workspace Suite Overview

Portable Project Bootstrap now acts as the runtime center of a small workspace suite rather than a bootstrap-only package.

## Suite Components

- `profile_loader`
  Discovers and validates the workspace profile, then assembles `WorkspaceProfile` and `WorkspaceContext`.
- `workspace-validator`
  Checks whether the current machine, workspace, and profile combination is ready before bootstrap or routing.
- bootstrap runtime
  Handles brand-new project initialization through planning, execution, the guarded live wrapper, and a development-ready repo layer for Python-first projects.
- `workspace-router`
  Routes existing-project work to the correct repo and project-local `.agent-memory/` without invoking bootstrap.
- live wrapper
  Centralizes bootstrap mode selection for `new`, `legacy`, and `shadow`. The built-in default remains `new`.

## Official Profile Protocol

- primary path:
  - `workspace_root/.agent-memory/machine-profiles/<profile_name>.json`
- compatibility fallback path:
  - `workspace_root/.codex/workspace-profile/PROFILE.json`
- discovery order:
  1. explicit `profile_path`
  2. primary path
  3. compatibility fallback path

Compatibility window:

- retain compatibility profile discovery, legacy workspace-doc discovery, and deprecated explicit-entry workspace-doc aliases only through `2026-06-30`
- compatibility surfaces still in scope:
  - `workspace_root/.codex/workspace-profile/PROFILE.json`
  - implicit fallback from `WORKSPACE.md` to `WORKSPACE_RULES.md` or `WORKSPACE_START_HERE.md` when `workspace_doc_path` is absent
  - deprecated explicit-entry aliases `--workspace-start-here` and `--workspace-rules`
- validator and router should keep warning when the compatibility profile path is used during this window
- after `2026-06-30`, the intended steady state is the primary machine-profile path plus `WORKSPACE.md`

## Profile Schema

Required fields:

- `schema_version`
- `profile_name`
- `repo_root`
- `memory_root`
- `backup_root`

Rules:

- only `schema_version = 1` is currently supported
- unknown versions fail closed
- missing required fields fail closed
- invalid or non-absolute path shapes fail closed
- missing required workspace files fail closed

## Recommended Call Order

1. Load profile/context from the workspace profile protocol.
2. Run `workspace-validator` to confirm the workspace is ready.
3. For a brand-new project, use bootstrap through `python -m portable_project_bootstrap ...`.
4. For an existing project, use `workspace-router` to resolve repo path, memory path, and read-first files.

## Standard Workflows

### Brand-New Project Workflow

1. Load profile/context.
2. Run `workspace-validator`.
3. Run bootstrap in `--dry-run` first.
4. Check `status`, `project_index_result`, manual patch signals, `project_index_status`, and `bootstrap_log_status`.
5. Review the planned repo outputs, including dev-ready files such as `.gitignore`, `README.md`, stack metadata, `tests/`, `examples/`, and optional human-facing docs.
6. If clean, rerun with `--execute`.
7. If the issue appears bootstrap-specific, use `--mode shadow`.
8. If rollback or containment is needed, switch explicitly to `--mode legacy`.

### Existing Project Workflow

1. Load profile/context.
2. Run `workspace-validator`.
3. Run `workspace-router` with an exact slug, exact project name, exact path, or another strong routing input.
4. Read the returned `read_first_files`.
5. Continue project work only after the route is unambiguous.

## Role Boundaries

- bootstrap is for brand-new initialization and safe fill-missing repair only, including development-ready repo bootstrapping
- `workspace-router` is for existing project entry only
- `workspace-validator` is for readiness checks before either flow
- the live wrapper owns bootstrap mode selection
- the planner decides what to do
- the executor decides how to apply the already-planned actions

## Safety Defaults

- fail closed on unsafe or incomplete profile/workspace state
- do not overwrite non-empty files automatically
- do not auto-apply manual patch output
- do not silently fall back from `new` to `legacy`
- do not let `shadow` perform real writes
- do not let validator or router turn into bootstrap

## Public Operator Surfaces

Recommended public entrypoints:

- `python -m portable_project_bootstrap`
- `python -m portable_project_bootstrap.validator`
- `python -m portable_project_bootstrap.router`

Optional external wrappers may forward into these surfaces, but they are integration details rather than the main public contract.

## Dev-Ready Repo Layer

For Python-first projects, bootstrap now plans and applies a small development-ready repo layer on top of the workspace bootstrap layer.

Default repo outputs include:

- `.gitignore`
- `README.md`
- `pyproject.toml` when Python stack metadata is enabled
- `tests/test_smoke.py`
- `examples/README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- git initialization unless disabled

Recommended toggles stay intentionally small:

- `--no-init-git`
- `--no-create-license`
- `--no-create-contributing`
- `--no-create-tests`
- `--no-create-examples`
- `--no-create-stack-metadata`

This layer stays inside bootstrap. It does not change router or validator responsibilities.

## Observation And Triage

Track these signals by surface:

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
  - `manual_follow_up` or `manual_patch_output`
  - `project_index_status`
  - `bootstrap_log_status`
  - `return_code`

Recommended triage order:

1. decide whether the issue starts in profile loading, validator, router, or bootstrap
2. fix profile/validator issues before touching router or bootstrap behavior
3. use `shadow` only for bootstrap compare-only investigation
4. use `legacy` only for explicit bootstrap rollback or containment

## Operational Classification

- profile/config issues
  - missing profile
  - unsupported schema version
  - missing required fields
  - invalid path shapes
  - missing required workspace files
- validator issues
  - unexpected `status: error`
  - unexpected warnings
  - inconsistent resolved paths
  - compatibility profile used more often than expected
- router issues
  - no safe route
  - too many ambiguous candidates
  - weak hints surfacing too often
  - project index missing or unparseable
  - route result differs from operator expectation
- bootstrap issues
  - unexpected `project_index_result`
  - manual patch frequency rising unexpectedly
  - abnormal `bootstrap_log_status`
  - `new` path behavior drift
  - explicit `legacy` rollback events

## Standard Response Playbooks

### Validator

1. Check the resolved profile path and schema.
2. Check required fields and required workspace files.
3. Stop there until the validation issue is understood.

### Router

1. Check profile/context first.
2. Check `PROJECT_INDEX.md` next.
3. Narrow the query before treating ambiguity as a bug.
4. Never fall back to bootstrap.

### Bootstrap

1. Check whether the issue is really upstream in profile, validator, or router.
2. Use `shadow` only if the remaining suspicion is bootstrap-specific semantics.
3. Use `legacy` only for explicit rollback or containment.

## Long-Run Observation Window

For long-run suite judgment, use a combined window rather than a one-off sample burst.

Window requirements:

- at least `30` calendar days of real operator usage
- at least `24` real suite samples total
- at least `6` validator samples
- at least `6` router samples
- at least `6` bootstrap samples
- at least `3` bootstrap execute-path samples

Only count real samples:

- non-fixture
- triggered from the real caller or the repo-local formal operator surface
- not plain unit tests
- not fixture subprocess runs
- not documentation example runs

Bootstrap execute-path evidence must also satisfy:

- at least `3` real execute-path samples
- not all from the exact same input set
- preferably covering at least two different project slugs or project contexts

Keep the fixed observation fields stable so samples stay comparable across the full window.

Compatibility cleanup is gated separately from `legacy` rollback retention. The compatibility surfaces above exist only to complete the workspace-document migration; they do not justify keeping `legacy` longer than the rollback evidence requires.

## Legacy Deprecation Readiness Checklist

Evaluate these gates at the end of each long-run window:

1. Bootstrap drift
   No non-expected bootstrap drift has appeared in the window.
2. Legacy dependence
   `legacy` is not still required as an active recovery path for real incidents.
3. Shadow discipline
   `shadow` is still used mainly for diagnosis, not as a routine operating mode.
4. Suite stability
   Validator, router, and bootstrap status distributions remain stable and understandable.
5. Compatibility profile usage
   Compatibility profile use stays in an expected low-frequency warning band.
6. Unresolved operator anomalies
   No meaningful real operator anomaly remains open without triage or containment.
7. Operator docs
   Documentation remains sufficient for normal operations without depending on `legacy`.

Checklist result values:

- `ready`
  All gates pass and the observation window is complete.
- `not ready`
  One or more gates clearly fail.
- `needs more evidence`
  The window is incomplete or evidence is still too thin to call.

## Phase 14 Exit Criteria

Use the checklist only after the long-run window is complete.

Final interpretations:

- keep `legacy`
  - real `legacy` usage still appears in justified recovery or containment scenarios
  - or bootstrap drift or unresolved incidents still make `legacy` operationally necessary
- enter deprecation preparation
  - the long-run window is complete
  - `legacy` is not materially required in real incidents
  - validator, router, and bootstrap remain stable
  - `shadow` remains diagnostic rather than routine
  - compatibility profile use stays within an acceptable warning band
- needs more evidence
  - the window is not complete
  - or execute-path evidence is too thin or too repetitive
  - or the sample set is still too small to separate habit from true operational dependence

The observation window must be extended when:

- the time or sample threshold is not met
- bootstrap execute-path evidence is still too narrow
- new bootstrap drift appears
- manual patch frequency rises unexpectedly
- `legacy` is still being used in real recovery work
- `shadow` starts looking like a routine path instead of a diagnostic tool
- compatibility profile usage rises beyond the expected low-frequency warning band
- unresolved operator anomalies remain open
