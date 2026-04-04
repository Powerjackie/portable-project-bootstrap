# Example Workspace Layout

This document shows a generic workspace layout for using Portable Project Bootstrap on your own machine.

## Example Layout

```text
<workspace_root>/
├── .agent-memory/
│   ├── machine-profiles/
│   │   └── <profile_name>.json
│   ├── WORKSPACE_START_HERE.md
│   ├── WORKSPACE_RULES.md
│   └── PROJECT_INDEX.md
├── backups/
└── ...

<repo_root>/
└── <project_slug>/
```

Optional compatibility profile path:

```text
<workspace_root>/.codex/workspace-profile/PROFILE.json
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

- Replace all placeholders with real absolute paths for your own machine.
- Do not copy another user's private path layout verbatim.
- Keep agent-facing project memory outside the repo.
