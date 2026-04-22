from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from portable_project_bootstrap import (
    CURRENT_PROFILE_SCHEMA_VERSION,
    CompatibilityBridgeRequest,
    run_compatibility_bridge,
    ShadowModeError,
    format_shadow_result_lines,
    run_shadow_mode,
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
  - `X:\\memory\\existing-project\\PROJECT.md`
  - `X:\\memory\\existing-project\\PROJECT.md`
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


class ShadowModeTests(unittest.TestCase):
    def test_shadow_mode_reports_match_for_compare_only_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            result = run_shadow_mode(self._request(workspace_root=workspace_root))

            self.assertTrue(result.matched)
            self.assertEqual((), result.differences)
            self.assertIn("shadow_matched: true", "\n".join(format_shadow_result_lines(result)))

    def test_shadow_mode_rejects_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            with self.assertRaisesRegex(ShadowModeError, "compare-only"):
                run_shadow_mode(self._request(workspace_root=workspace_root, execute=True))

    def test_shadow_compare_detects_action_content_differences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)
            request = self._request(workspace_root=workspace_root)
            result = run_compatibility_bridge(request)
            shadow_module = importlib.import_module("portable_project_bootstrap.shadow")

            changed_action = replace(
                result.planning_result.actions[0],
                render_content=(result.planning_result.actions[0].render_content or "") + "drift",
            )
            changed_planning_result = replace(
                result.planning_result,
                actions=(changed_action, *result.planning_result.actions[1:]),
            )
            changed_result = replace(result, planning_result=changed_planning_result)

            differences = shadow_module._compare_results(
                operator_result=result,
                explicit_result=changed_result,
            )

            self.assertIn("planned action signature differs", differences)

    def _request(self, *, workspace_root: Path, execute: bool = False) -> CompatibilityBridgeRequest:
        return CompatibilityBridgeRequest(
            workspace_root=workspace_root,
            profile_name="default",
            project_name="Portable Project Bootstrap",
            project_slug="portable-project-bootstrap",
            project_summary="A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
            tech_stack=("Python", "Markdown", "JSON"),
            dry_run=True,
            execute=execute,
        )

    def _write_workspace_profile(self, workspace_root: Path) -> None:
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "PROJECT_INDEX.md").write_text(sample_project_index(), encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("start\n", encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("rules\n", encoding="utf-8")
        profile_dir = memory_root / "machine-profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "default.json").write_text(
            json.dumps(
                {
                    "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                    "profile_name": "default",
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

