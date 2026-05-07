"""Tests for the "empty workspace is legal" first-run experience.

A brand-new workspace contains a `PROJECT_INDEX.md` with no `## <slug>` sections.
Before this feature, that state failed `parse_project_index_document` with
`ProjectIndexParseError` and forced a manual_patch dance for the very first
project. These tests pin the new contract:

1. `# Project Index` (or empty) parses to a document with zero records.
2. `validate_workspace` on such a workspace returns OverallStatus.OK.
3. The first `--execute` bootstrap auto-inserts the slug section via SAFE_PATCH.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import (
    CURRENT_PROFILE_SCHEMA_VERSION,
    OverallStatus,
)
from portable_project_bootstrap.bridge import run_compatibility_bridge
from portable_project_bootstrap.models import ActionKind, CompatibilityBridgeRequest
from portable_project_bootstrap.project_index import parse_project_index_document
from portable_project_bootstrap.validator import validate_workspace


PRESERVED_PREAMBLE = "# Project Index\n"


class EmptyProjectIndexParserTests(unittest.TestCase):
    def test_preamble_only_index_parses_to_empty_records(self) -> None:
        document = parse_project_index_document(PRESERVED_PREAMBLE)

        self.assertEqual((), document.records)
        self.assertEqual("# Project Index", document.preamble)

    def test_completely_empty_index_parses_to_empty_records(self) -> None:
        document = parse_project_index_document("")

        self.assertEqual((), document.records)
        self.assertEqual("", document.preamble)


class EmptyWorkspaceValidatorTests(unittest.TestCase):
    def test_validator_treats_empty_index_as_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = _create_workspace(Path(temp_dir), index_text=PRESERVED_PREAMBLE)

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual((), result.problems)


class FirstProjectAutoInsertTests(unittest.TestCase):
    def test_first_project_execute_inserts_section_via_safe_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = _create_workspace(Path(temp_dir), index_text=PRESERVED_PREAMBLE)
            index_path = workspace_root / ".agent-memory" / "PROJECT_INDEX.md"

            result = run_compatibility_bridge(
                CompatibilityBridgeRequest(
                    workspace_root=workspace_root,
                    profile_name="default",
                    project_name="My App",
                    project_slug="my-app",
                    project_summary="first project in a fresh workspace",
                    tech_stack=("Python",),
                    dry_run=False,
                    execute=True,
                    init_git=False,
                )
            )

            self.assertIsNotNone(result.execution_result)
            updated_text = index_path.read_text(encoding="utf-8")
            self.assertIn("## my-app", updated_text)
            self.assertIn("# Project Index", updated_text)
            self.assertEqual(
                ActionKind.SAFE_PATCH,
                result.planning_result.index_update_plan.action.kind,
            )
            self.assertEqual((), result.manual_patch_output)
            self.assertNotIn(
                "project_index_parse_failed",
                result.planning_result.index_update_plan.update_reasons,
            )


def _create_workspace(temp_root: Path, *, index_text: str) -> Path:
    workspace_root = temp_root / "workspace"
    workspace_root.mkdir()
    repo_root = workspace_root / "repos"
    memory_root = workspace_root / ".agent-memory"
    backup_root = workspace_root / "backups"
    repo_root.mkdir()
    memory_root.mkdir()
    backup_root.mkdir()
    (memory_root / "PROJECT_INDEX.md").write_text(index_text, encoding="utf-8")
    (memory_root / "WORKSPACE.md").write_text("workspace\n", encoding="utf-8")
    profile_document = {
        "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
        "profile_name": "default",
        "repo_root": str(repo_root),
        "memory_root": str(memory_root),
        "backup_root": str(backup_root),
    }
    profile_dir = memory_root / "machine-profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "default.json").write_text(
        json.dumps(profile_document, indent=2),
        encoding="utf-8",
    )
    return workspace_root


if __name__ == "__main__":
    unittest.main()
