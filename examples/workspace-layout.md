# Example Workspace Layout

This document shows a generic workspace layout for using Portable Project Bootstrap on your own machine.

## Example Layout

```text
<workspace_root>/
鈹溾攢鈹€ .agent-memory/
鈹?  鈹溾攢鈹€ machine-profiles/
鈹?  鈹?  鈹斺攢鈹€ <profile_name>.json
鈹?  鈹溾攢鈹€ WORKSPACE.md
鈹?  鈹溾攢鈹€ 
鈹?  鈹斺攢鈹€ PROJECT_INDEX.md
鈹溾攢鈹€ backups/
鈹斺攢鈹€ ...

<repo_root>/
鈹斺攢鈹€ <project_slug>/
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
- Project-level agent memory now lives inside each repo at `.agent-memory/` and should be gitignored.


