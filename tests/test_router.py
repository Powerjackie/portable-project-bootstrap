from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION, OverallStatus, WorkspaceRouteQuery
from portable_project_bootstrap.router import main as router_main
from portable_project_bootstrap.router import route_workspace


class WorkspaceRouterTests(unittest.TestCase):
    def test_exact_slug_routes_to_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(project_slug="alpha-project"),
            )

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual("alpha-project", result.matched_project.project_slug)
            self.assertEqual("C:\\workspace\\repos\\alpha-project", result.matched_project.repo_path)

    def test_exact_project_name_routes_to_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(project_name="Alpha Project"),
            )

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual("alpha-project", result.matched_project.project_slug)
            self.assertIn("exact project name match", result.matched_project.match_reasons)

    def test_ambiguous_route_signal_returns_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(route_signal="shared-suite"),
            )

            self.assertEqual(OverallStatus.PARTIAL, result.status)
            self.assertEqual({"alpha-project", "beta-project"}, {item.project_slug for item in result.candidates})
            self.assertIn("multiple projects matched", result.ambiguity_reason)

    def test_missing_project_index_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))
            (workspace_root / ".agent-memory" / "PROJECT_INDEX.md").unlink()

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(project_slug="alpha-project"),
            )

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("PROJECT_INDEX" in item for item in result.problems))

    def test_weak_hint_alone_does_not_route_a_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(route_signal="alpha-hint"),
            )

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("route signal" in item for item in result.problems))

    def test_router_does_not_trigger_bootstrap_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))
            repo_root = workspace_root / "repos"
            before = {path.relative_to(workspace_root) for path in workspace_root.rglob("*")}

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(project_slug="alpha-project"),
            )
            after = {path.relative_to(workspace_root) for path in workspace_root.rglob("*")}

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual(before, after)
            self.assertFalse((repo_root / "portable-project-bootstrap").exists())

    def test_router_cli_prints_structured_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = router_main(
                    [
                        "--workspace-root",
                        str(workspace_root),
                        "--profile-name",
                        "default",
                        "--project-slug",
                        "alpha-project",
                    ]
                )

            self.assertEqual(0, exit_code)
            output = stdout.getvalue()
            self.assertIn("status: ok", output)
            self.assertIn("matched_project_slug: alpha-project", output)
            self.assertIn("read_first_files:", output)

    def _create_workspace(self, temp_root: Path) -> Path:
        workspace_root = temp_root / "workspace"
        workspace_root.mkdir()
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "WORKSPACE_START_HERE.md").write_text("start\n", encoding="utf-8")
        (memory_root / "WORKSPACE_RULES.md").write_text("rules\n", encoding="utf-8")
        (memory_root / "PROJECT_INDEX.md").write_text(self._project_index_text(), encoding="utf-8")
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
        return workspace_root

    def _project_index_text(self) -> str:
        return """# Project Index

## alpha-project

- Purpose: Alpha existing project
- Canonical repo / runtime surface:
  - `C:\\workspace\\repos\\alpha-project`
- Backup path:
  - `C:\\workspace\\backups\\alpha-project`
- Memory root:
  - `C:\\workspace\\.agent-memory\\alpha-project`
- Read-first files:
  - `C:\\workspace\\.agent-memory\\alpha-project\\START_HERE.md`
  - `C:\\workspace\\.agent-memory\\alpha-project\\PROJECT_RULES.md`
- Optional files:
  - `C:\\workspace\\.agent-memory\\alpha-project\\AI_HANDOVER.md`
  - `C:\\workspace\\.agent-memory\\alpha-project\\AGENT_DESIGN.md`
- Strong match signals:
  - explicit repo path `C:\\workspace\\repos\\alpha-project`
  - explicit memory path `C:\\workspace\\.agent-memory\\alpha-project`
  - project slug `alpha-project`
  - project name `Alpha Project`
  - explicit routing keyword `shared-suite`
- Weak hints only:
  - `alpha-hint`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Alpha existing project.

## beta-project

- Purpose: Beta existing project
- Canonical repo / runtime surface:
  - `C:\\workspace\\repos\\beta-project`
- Backup path:
  - `C:\\workspace\\backups\\beta-project`
- Memory root:
  - `C:\\workspace\\.agent-memory\\beta-project`
- Read-first files:
  - `C:\\workspace\\.agent-memory\\beta-project\\START_HERE.md`
  - `C:\\workspace\\.agent-memory\\beta-project\\PROJECT_RULES.md`
- Optional files:
  - `C:\\workspace\\.agent-memory\\beta-project\\AI_HANDOVER.md`
  - `C:\\workspace\\.agent-memory\\beta-project\\AGENT_DESIGN.md`
- Strong match signals:
  - explicit repo path `C:\\workspace\\repos\\beta-project`
  - explicit memory path `C:\\workspace\\.agent-memory\\beta-project`
  - project slug `beta-project`
  - project name `Beta Project`
  - explicit routing keyword `shared-suite`
- Weak hints only:
  - `beta-hint`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Beta existing project.
"""


if __name__ == "__main__":
    unittest.main()
