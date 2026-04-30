# Example Workspace Layout

This document shows a generic workspace layout for using Portable Project Bootstrap on your own machine.

## Example Layout

```text
<workspace_root>/
+-- .agent-memory/
|   +-- machine-profiles/
|   |   +-- <profile_name>.json
|   +-- WORKSPACE.md
|   +-- PROJECT_INDEX.md
+-- backups/
+-- repos/
    +-- <project_slug>/
        +-- .agent-memory/
```

Optional compatibility profile path:

```text
<workspace_root>/.codex/workspace-profile/PROFILE.json
```

## macOS Example

```text
/Users/example/Developer/workspace/
+-- .agent-memory/
+-- backups/
+-- repos/
    +-- prompt-ide/
        +-- .agent-memory/
```

## Recommended PROJECT_INDEX Path Style

Use profile-driven placeholders instead of machine-specific absolute paths when editing `PROJECT_INDEX.md`.

```markdown
## prompt-ide
- Path: `${repo_root}/prompt-ide` | Memory: `${repo_root}/prompt-ide/.agent-memory`
- Read-first: `${repo_root}/prompt-ide/.agent-memory/PROJECT.md`
- Signals: project slug `prompt-ide`, project name `Prompt IDE`
```

Optional backup and workspace-level references may also use `${memory_root}`, `${backup_root}`, and `${workspace_root}`.

For remote projects, add `Route-Type:` explicitly:

```markdown
## qinglong
- Path: `${repo_root}/qinglong` | Memory: `${memory_root}/qinglong`
- Route-Type: `ssh:prompt-ide-vps`
- Read-first: `${memory_root}/qinglong/PROJECT.md`
- Signals: project slug `qinglong`, project name `QingLong`
```

## Brand-New Project Flow

1. Create or update the active profile.
2. Run `workspace-validator`.
3. Run bootstrap in `--dry-run`.
4. Review the summary and any manual patch output.
5. Run bootstrap with `--execute` when the dry-run looks correct.

## Existing Project Flow

1. Create or update the active profile.
2. Run `workspace-validator`.
3. Run `workspace-router`.
4. Read the recommended files before continuing project work.

## Notes

- Replace all placeholders with real machine-local absolute roots in the profile, not in `PROJECT_INDEX.md`.
- Do not copy another user's private path layout verbatim.
- Project-level agent memory lives inside each repo at `.agent-memory/` and should be gitignored.
