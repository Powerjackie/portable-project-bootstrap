from __future__ import annotations

import datetime as dt
from pathlib import Path

from .models import BootstrapRequest, ProjectPaths, WorkspaceContext


REPO_README_TEMPLATE = """# {project_name}

{project_summary}

## Getting Started

- Bootstrapped with a profile-driven workspace bootstrap flow.
- Repo-external agent memory lives outside this repository.
- Review `examples/README.md` for local adaptation notes.

## Development

{development_lines}

## Repository Notes

- Project slug: `{project_slug}`
- Repo visibility: `{repo_visibility}`
- Project type: `{project_type}`
- Tech stack:
{tech_stack_bullets}

## Repo-External Memory

- Agent-facing project memory lives outside the repo at `{memory_path}`.
- Reserved backup path: `{backup_path}`.
"""

GITIGNORE_TEMPLATE = """# Python caches
__pycache__/
*.py[cod]

# Virtual environments
.venv/
venv/

# Test and coverage output
.pytest_cache/
.coverage
coverage.xml

# Build output
build/
dist/
*.egg-info/

# Editors and OS files
.idea/
.vscode/
.DS_Store
Thumbs.db

# Logs and temp files
*.log
*.tmp
"""

CONTRIBUTING_TEMPLATE = """# Contributing

Thanks for contributing to {project_name}.

## Before Opening A Change

1. Read `README.md`.
2. Review the examples under `examples/`.
3. Keep agent-facing project memory outside the repo.

## Local Validation

{validation_lines}

## Notes

- Avoid overwriting non-empty project files without review.
- Keep human-facing docs in the repo and agent-facing docs outside the repo.
"""

LICENSE_TEMPLATE = """MIT License

Copyright (c) {year} {project_name}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

PYPROJECT_TEMPLATE = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_slug}"
version = "0.1.0"
description = "{project_summary}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[tool.setuptools]
package-dir = {{"": "src"}}

[tool.setuptools.packages.find]
where = ["src"]
"""

TEST_SMOKE_TEMPLATE = """from __future__ import annotations

import unittest


class SmokeTests(unittest.TestCase):
    def test_placeholder(self) -> None:
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
"""

EXAMPLES_README_TEMPLATE = """# Examples

This directory contains human-facing examples for `{project_name}`.

Suggested uses:

- usage snippets
- local setup notes
- sample inputs or sample outputs

Replace placeholder content with real project examples as implementation evolves.
"""

START_HERE_TEMPLATE = """# {project_name} External Agent Memory

This directory is the repo-external agent memory for `{project_name}`.

- Canonical repo path: `{repo_path}`
- Reserved backup path: `{backup_path}`
- Memory root: `{memory_path}`

## Scope

Use this memory when the task is specifically about `{project_name}`.

## Read Order

1. Read `PROJECT_RULES.md`.
2. If current state matters, read `AI_HANDOVER.md`.
3. If architecture or durable technical decisions matter, read `AGENT_DESIGN.md`.
4. If a fixed session bootstrap is needed and the file exists, read `SESSION_BOOTSTRAP.txt`.

## Hard Rules

- Do not create agent-facing docs inside the repo.
- Keep project-specific agent rules, state, and design notes in this memory root.
- Use `{documentation_update_playbook_path}` for future writeback routing.
"""

PROJECT_RULES_TEMPLATE = """# {project_name} Project Rules

## Canonical Paths

- Canonical repo path: `{repo_path}`
- Memory root: `{memory_path}`
- Reserved backup path: `{backup_path}`

## Boundary

- This memory is only for `{project_name}`.
- Keep project-specific agent rules here, not in the repo.

## Execution Guardrails

- Inherit cross-project rules from `{workspace_rules_path}`.
- Keep project-specific durable rules here only when they are truly project-specific.

## Project Memory Discipline

- Current state belongs in `AI_HANDOVER.md`.
- Long-term rules belong in `PROJECT_RULES.md`.
- Architecture belongs in `AGENT_DESIGN.md`.
- Session-only reminders belong in `SESSION_BOOTSTRAP.txt` when that file exists.

## Project-Specific Rules

TBD
"""

AI_HANDOVER_TEMPLATE = """# {project_name} AI Handover

This file lives in repo-external memory at `{memory_path}\\AI_HANDOVER.md`.

## Canonical Working Copy

- Canonical repo path: `{repo_path}`
- Reserved backup path: `{backup_path}`

## Project Identity

- Name: `{project_name}`
- Summary: {project_summary}
- Repo visibility: `{repo_visibility}`
- Project type: `{project_type}`

## Current State

- Bootstrap status: initialized
- Implementation status: not yet documented
- Known blockers: none recorded yet

## Next Notes

- Future agents should update this file when project state materially changes.
"""

AGENT_DESIGN_TEMPLATE = """# {project_name} Agent Design

This file lives in repo-external memory at `{memory_path}\\AGENT_DESIGN.md`.

## Purpose

Capture durable architecture, interfaces, contracts, and technical decisions for `{project_name}`.

## Project Summary

{project_summary}

## Tech Stack

{tech_stack_bullets}

## Structure Overview

TBD

## Interfaces and Contracts

TBD

## Durable Decisions

TBD

## Update Rule

When durable architecture or interface assumptions change, update this file and `AI_HANDOVER.md` together if current project state is also affected.
"""

BOOTSTRAP_LOG_TEMPLATE = """# Bootstrap Log

This file records `project-bootstrap` runs for `{project_name}`.

## Entries
"""

SESSION_BOOTSTRAP_TEMPLATE = """{project_name}
Session bootstrap placeholder.
"""

PROJECT_INDEX_ENTRY_TEMPLATE = """## {project_slug}

- Purpose: {project_summary}
- Canonical repo / runtime surface:
  - `{repo_path}`
- Backup path:
  - `{backup_path}`
- Memory root:
  - `{memory_path}`
- Read-first files:
  - `{memory_path}\\START_HERE.md`
  - `{memory_path}\\PROJECT_RULES.md`
- Optional files:
  - `{memory_path}\\AI_HANDOVER.md`
  - `{memory_path}\\AGENT_DESIGN.md`
{session_bootstrap_index_line}- Strong match signals:
  - explicit repo path `{repo_path}`
  - explicit memory path `{memory_path}`
  - project slug `{project_slug}`
  - project name `{project_name}`
{strong_keyword_lines}- Weak hints only:
{weak_keyword_lines}- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Repo and project-profile surface for {project_name}.
"""

MEMORY_FILE_NAMES = {
    "START_HERE.md",
    "PROJECT_RULES.md",
    "AI_HANDOVER.md",
    "AGENT_DESIGN.md",
    "BOOTSTRAP_LOG.md",
    "SESSION_BOOTSTRAP.txt",
}


def render_template_set(context: WorkspaceContext, request: BootstrapRequest, paths: ProjectPaths) -> dict[str, str]:
    data = _template_context(context=context, request=request, paths=paths)
    files: dict[str, str] = {
        "README.md": REPO_README_TEMPLATE.format(**data).rstrip() + "\n",
        ".gitignore": GITIGNORE_TEMPLATE.rstrip() + "\n",
        "START_HERE.md": START_HERE_TEMPLATE.format(**data).rstrip() + "\n",
        "PROJECT_RULES.md": PROJECT_RULES_TEMPLATE.format(**data).rstrip() + "\n",
        "AI_HANDOVER.md": AI_HANDOVER_TEMPLATE.format(**data).rstrip() + "\n",
        "AGENT_DESIGN.md": AGENT_DESIGN_TEMPLATE.format(**data).rstrip() + "\n",
        "BOOTSTRAP_LOG.md": BOOTSTRAP_LOG_TEMPLATE.format(**data).rstrip() + "\n",
    }
    if request.create_license:
        files["LICENSE"] = LICENSE_TEMPLATE.format(**data).rstrip() + "\n"
    if request.create_contributing:
        files["CONTRIBUTING.md"] = CONTRIBUTING_TEMPLATE.format(**data).rstrip() + "\n"
    if request.create_tests:
        files["tests/test_smoke.py"] = TEST_SMOKE_TEMPLATE.rstrip() + "\n"
    if request.create_examples:
        files["examples/README.md"] = EXAMPLES_README_TEMPLATE.format(**data).rstrip() + "\n"
    if request.create_stack_metadata and _python_enabled(request):
        files["pyproject.toml"] = PYPROJECT_TEMPLATE.format(**data).rstrip() + "\n"
    if request.create_session_bootstrap:
        files["SESSION_BOOTSTRAP.txt"] = SESSION_BOOTSTRAP_TEMPLATE.format(**data).rstrip() + "\n"
    return files


def render_project_index_entry(context: WorkspaceContext, request: BootstrapRequest, paths: ProjectPaths) -> str:
    data = _template_context(context=context, request=request, paths=paths)
    return PROJECT_INDEX_ENTRY_TEMPLATE.format(**data).rstrip()


def is_memory_file_key(name: str) -> bool:
    return Path(name).name in MEMORY_FILE_NAMES and Path(name).parent == Path(".")


def _template_context(context: WorkspaceContext, request: BootstrapRequest, paths: ProjectPaths) -> dict[str, str]:
    return {
        "project_name": request.project_name.strip(),
        "project_slug": request.project_slug.strip(),
        "project_summary": request.project_summary.strip(),
        "repo_visibility": request.repo_visibility,
        "project_type": request.project_type,
        "repo_path": str(paths.repo_path),
        "memory_path": str(paths.memory_path),
        "backup_path": str(paths.backup_path),
        "tech_stack_bullets": _bullets(request.tech_stack, fallback="TBD"),
        "strong_keyword_lines": _strong_keyword_lines(request.routing_keyword_strong),
        "weak_keyword_lines": _keyword_lines(request.routing_keyword_weak, fallback="none"),
        "session_bootstrap_index_line": _session_bootstrap_index_line(
            enabled=request.create_session_bootstrap,
            memory_path=str(paths.memory_path),
        ),
        "workspace_rules_path": str(context.workspace_rules_path or ""),
        "documentation_update_playbook_path": _documentation_update_playbook_path(context),
        "development_lines": _development_lines(request),
        "validation_lines": _validation_lines(request),
        "year": str(dt.datetime.now().year),
    }


def _python_enabled(request: BootstrapRequest) -> bool:
    return request.project_type == "python" or any(value.lower() == "python" for value in request.tech_stack)


def _development_lines(request: BootstrapRequest) -> str:
    lines = ["- Review the files under `tests/` and `examples/` before adding project-specific code."]
    if _python_enabled(request) and request.create_stack_metadata:
        lines.extend(
            [
                "- Create a virtual environment for Python development.",
                "- Install the project in editable mode: `python -m pip install -e .`",
                "- Run the tests with: `python -m unittest discover -s tests -v`",
            ]
        )
    else:
        lines.append("- Add stack-specific setup instructions here as the project implementation evolves.")
    return "\n".join(lines)


def _validation_lines(request: BootstrapRequest) -> str:
    if _python_enabled(request) and request.create_stack_metadata and request.create_tests:
        return "1. Run `python -m unittest discover -s tests -v`."
    return "1. Add the stack-appropriate validation command for this project."


def _bullets(values: tuple[str, ...], fallback: str) -> str:
    if not values:
        return f"- {fallback}"
    return "\n".join(f"- {value}" for value in values)


def _keyword_lines(values: tuple[str, ...], fallback: str) -> str:
    if not values:
        return f"  - `{fallback}`\n"
    return "".join(f"  - `{value}`\n" for value in values)


def _strong_keyword_lines(values: tuple[str, ...]) -> str:
    if not values:
        return ""
    return "".join(f"  - explicit routing keyword `{value}`\n" for value in values)


def _session_bootstrap_index_line(*, enabled: bool, memory_path: str) -> str:
    if not enabled:
        return ""
    return (
        f"  - `{memory_path}\\SESSION_BOOTSTRAP.txt` "
        "(`session-only`, `operator-only`, not part of normal default reading path)\n"
    )


def _documentation_update_playbook_path(context: WorkspaceContext) -> str:
    if context.workspace_start_here_path is None:
        return "DOCUMENTATION_UPDATE_PLAYBOOK.md"
    return str(context.workspace_start_here_path.parent / "DOCUMENTATION_UPDATE_PLAYBOOK.md")
