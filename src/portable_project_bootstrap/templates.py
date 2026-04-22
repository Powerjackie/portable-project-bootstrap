from __future__ import annotations

import datetime as dt
from pathlib import Path

from .models import BootstrapRequest, ProjectPaths, WorkspaceContext


REPO_README_TEMPLATE = """# {project_name}

{project_summary}

## Getting Started

- Bootstrapped with a profile-driven workspace bootstrap flow.
- Agent memory lives in a local-only workspace surface for this project.
- Review `examples/README.md` for local adaptation notes.

## Development

{development_lines}

## Repository Notes

- Project slug: `{project_slug}`
- Repo visibility: `{repo_visibility}`
- Project type: `{project_type}`
- Tech stack:
{tech_stack_bullets}

## Agent Memory

- {repo_readme_memory_line}
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

# Agent memory (local, not committed)
.agent-memory/
"""

CONTRIBUTING_TEMPLATE = """# Contributing

Thanks for contributing to {project_name}.

## Before Opening A Change

1. Read `README.md`.
2. Review the examples under `examples/`.
3. {contributing_memory_line}

## Local Validation

{validation_lines}

## Notes

- Avoid overwriting non-empty project files without review.
- Keep human-facing docs in the repo and agent memory local-only.
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

PROJECT_MEMORY_TEMPLATE = """# {project_name} Agent Memory

## Identity

- Canonical repo path: `{repo_path}`
- Backup path: `{backup_path}`
- Memory root: `{memory_root_display}`

## Scope

- Use this memory when the task is specifically about `{project_name}`.
- {project_memory_scope_line}

## Read Order

1. Read this file.
2. For current priorities or blockers, read `AI_HANDOVER.md` (same directory).
3. For architecture and durable contracts, read `AGENT_DESIGN.md` (same directory).
4. Read `SESSION_BOOTSTRAP.txt` only when it exists and a fixed operator bootstrap is explicitly needed.

## Dev Commands

- Stack: {stack_summary}
- Replace this section with concrete repo-specific commands once implementation exists.

## Project-Unique Rules

- Inherit workspace-wide rules from `{workspace_doc_path}`.
- Use `{memory_policy_path}` for writeback routing and file-home rules.
- Keep only project-unique durable constraints here.
"""

AI_HANDOVER_TEMPLATE = """# {project_name} AI Handover

This file lives at `{ai_handover_location}`.

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

This file lives at `{agent_design_location}`.

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
Read `PROJECT.md` first, then use this file only for session-specific operator notes.
"""

PROJECT_INDEX_ENTRY_TEMPLATE = """## {project_slug}

- Path: `{repo_path}` | Memory: `{project_index_memory_path}`
- Read-first: `PROJECT.md`
- Signals: slug `{project_slug}`, project name `{project_name}`{strong_signal_suffix}
"""

MEMORY_FILE_NAMES = {
    "PROJECT.md",
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
        "PROJECT.md": PROJECT_MEMORY_TEMPLATE.format(**data).rstrip() + "\n",
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
    inline_memory = _is_inline_memory(paths)
    repo_memory_path = paths.repo_path / ".agent-memory"
    return {
        "project_name": request.project_name.strip(),
        "project_slug": request.project_slug.strip(),
        "project_summary": request.project_summary.strip(),
        "repo_visibility": request.repo_visibility,
        "project_type": request.project_type,
        "repo_path": str(paths.repo_path),
        "memory_path": str(paths.memory_path),
        "memory_root_display": str(repo_memory_path if inline_memory else paths.memory_path),
        "backup_path": str(paths.backup_path),
        "tech_stack_bullets": _bullets(request.tech_stack, fallback="TBD"),
        "stack_summary": _stack_summary(request.tech_stack),
        "project_index_memory_path": _project_index_memory_path(context, paths),
        "strong_signal_suffix": _strong_signal_suffix(request.routing_keyword_strong),
        "workspace_doc_path": str(context.workspace_doc_path or ""),
        "memory_policy_path": _memory_policy_path(context),
        "development_lines": _development_lines(request),
        "validation_lines": _validation_lines(request),
        "repo_readme_memory_line": _repo_readme_memory_line(paths),
        "contributing_memory_line": _contributing_memory_line(paths),
        "project_memory_scope_line": _project_memory_scope_line(paths),
        "ai_handover_location": _memory_file_location(paths, "AI_HANDOVER.md"),
        "agent_design_location": _memory_file_location(paths, "AGENT_DESIGN.md"),
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


def _memory_policy_path(context: WorkspaceContext) -> str:
    if context.workspace_doc_path is None:
        return "MEMORY_POLICY.md"
    return str(context.workspace_doc_path.parent / "MEMORY_POLICY.md")


def _project_index_memory_path(context: WorkspaceContext, paths: ProjectPaths) -> str:
    return str(paths.memory_path)


def _strong_signal_suffix(values: tuple[str, ...]) -> str:
    if not values:
        return ""
    return "".join(f", `{value}`" for value in values)


def _stack_summary(values: tuple[str, ...]) -> str:
    if not values:
        return "TBD"
    return " / ".join(values)


def _is_inline_memory(paths: ProjectPaths) -> bool:
    return paths.memory_path == paths.repo_path / ".agent-memory"


def _repo_readme_memory_line(paths: ProjectPaths) -> str:
    if _is_inline_memory(paths):
        return "Agent-facing project memory lives at `.agent-memory/` inside this repo (gitignored, never pushed)."
    return f"Agent-facing project memory lives at `{paths.memory_path}` in external compatibility mode."


def _contributing_memory_line(paths: ProjectPaths) -> str:
    if _is_inline_memory(paths):
        return "Agent memory at `.agent-memory/` is gitignored - do not commit it."
    return "External compatibility-mode agent memory is local-only and must not be committed into the repo."


def _project_memory_scope_line(paths: ProjectPaths) -> str:
    if _is_inline_memory(paths):
        return "Agent memory lives inside the repo at `.agent-memory/` but is gitignored (never pushed to remote)."
    return f"Agent memory for this profile lives at `{paths.memory_path}` in external compatibility mode."


def _memory_file_location(paths: ProjectPaths, filename: str) -> str:
    if _is_inline_memory(paths):
        return f"{paths.repo_path}/.agent-memory/{filename} (gitignored, not committed)"
    return f"{paths.memory_path / filename} (external compatibility mode)"
