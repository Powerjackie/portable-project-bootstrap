from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import (
    ActionKind,
    CompatibilityBridgeRequest,
    CURRENT_PROFILE_SCHEMA_VERSION,
    ExecutionStatus,
    run_compatibility_bridge,
)


def sample_project_index() -> str:
    return """# Project Index

## existing-project

- Purpose: Existing project
- Canonical repo / runtime surface:
  - `X:\\repo\\existing-project`
- Backup path:
  - `X:\\backup\\existing-project`
- Memory root:
  - `X:\\memory\\existing-project`
- Read-first files:
  - `X:\\memory\\existing-project\\START_HERE.md`
  - `X:\\memory\\existing-project\\PROJECT_RULES.md`
- Optional files:
  - `X:\\memory\\existing-project\\AI_HANDOVER.md`
  - `X:\\memory\\existing-project\\AGENT_DESIGN.md`
- Strong match signals:
  - project slug `existing-project`
- Weak hints only:
  - `none`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Existing project.
"""


class CompatibilityBridgeTests(unittest.TestCase):
    def test_bridge_maps_legacy_inputs_to_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            result = run_compatibility_bridge(
                CompatibilityBridgeRequest(
                    workspace_root=workspace_root,
                    profile_name="test-profile",
                    project_name="Portable Project Bootstrap",
                    project_slug="portable-project-bootstrap",
                    project_summary="A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
                    tech_stack=("Python", "Markdown, JSON"),
                    routing_keyword_strong=("portable-project-bootstrap, ppb",),
                    routing_keyword_weak=("bootstrap",),
                    dry_run=True,
                    execute=False,
                )
            )

            self.assertEqual("Portable Project Bootstrap", result.request.project_name)
            self.assertEqual(("Python", "Markdown", "JSON"), result.request.tech_stack)
            self.assertEqual(("portable-project-bootstrap", "ppb"), result.request.routing_keyword_strong)
            self.assertEqual(("bootstrap",), result.request.routing_keyword_weak)
            self.assertEqual("test-profile", result.context.profile.profile_name)

    def test_bridge_dry_run_and_execute_share_same_planning_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            dry_result = run_compatibility_bridge(
                self._bridge_request(workspace_root=workspace_root, dry_run=True, execute=False)
            )
            execute_result = run_compatibility_bridge(
                self._bridge_request(workspace_root=workspace_root, dry_run=False, execute=True)
            )

            dry_signature = [
                (action.kind, action.target_kind, action.target_path) for action in dry_result.planning_result.actions
            ]
            execute_signature = [
                (action.kind, action.target_kind, action.target_path)
                for action in execute_result.planning_result.actions
            ]
            self.assertEqual(dry_signature, execute_signature)
            self.assertIsNotNone(execute_result.execution_result)
            self.assertEqual(ExecutionStatus.APPLIED, execute_result.execution_result.project_index_status)

    def test_bridge_reports_manual_patch_without_auto_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root, broken_index=True)

            result = run_compatibility_bridge(
                self._bridge_request(workspace_root=workspace_root, dry_run=False, execute=True)
            )

            self.assertEqual(ActionKind.MANUAL_PATCH, result.planning_result.index_update_plan.action.kind)
            self.assertIsNotNone(result.execution_result)
            self.assertEqual(ExecutionStatus.REPORTED, result.execution_result.project_index_status)
            self.assertTrue(result.manual_patch_output)

    def _bridge_request(
        self,
        *,
        workspace_root: Path,
        dry_run: bool,
        execute: bool,
    ) -> CompatibilityBridgeRequest:
        return CompatibilityBridgeRequest(
            workspace_root=workspace_root,
            profile_name="test-profile",
            project_name="Portable Project Bootstrap",
            project_slug="portable-project-bootstrap",
            project_summary="A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
            tech_stack=("Python", "Markdown", "JSON"),
            dry_run=dry_run,
            execute=execute,
        )

    def _write_workspace_profile(self, workspace_root: Path, broken_index: bool = False) -> None:
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "PROJECT_INDEX.md").write_text(
            "# broken\n" if broken_index else sample_project_index(),
            encoding="utf-8",
        )
        (memory_root / "WORKSPACE_START_HERE.md").write_text("start\n", encoding="utf-8")
        (memory_root / "WORKSPACE_RULES.md").write_text("rules\n", encoding="utf-8")
        profile_dir = memory_root / "machine-profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "test-profile.json").write_text(
            json.dumps(
                {
                    "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                    "profile_name": "test-profile",
                    "repo_root": str(repo_root),
                    "memory_root": str(memory_root),
                    "backup_root": str(backup_root),
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
