from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION, OverallStatus, WorkspaceRouteQuery
from portable_project_bootstrap.router import route_workspace
from portable_project_bootstrap.validator import validate_workspace


class RemoteRouteTests(unittest.TestCase):
    def test_router_marks_ssh_projects_as_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), route_type="ssh:prompt-ide-vps")

            result = route_workspace(
                workspace_root=workspace_root,
                profile_name="default",
                query=WorkspaceRouteQuery(project_slug="qinglong"),
            )

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertIsNotNone(result.matched_project)
            assert result.matched_project is not None
            self.assertEqual("remote-ssh", result.matched_project.route_type)
            self.assertEqual("prompt-ide-vps", result.matched_project.remote_host)

    def test_validator_accepts_remote_ssh_route_without_local_fs_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), route_type="ssh:prompt-ide-vps")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual((), result.problems)
            self.assertEqual((), result.warnings)

    def test_validator_rejects_unknown_route_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), route_type="foobar")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("Route-Type" in item for item in result.problems))

    def _create_workspace(self, temp_root: Path, *, route_type: str) -> Path:
        workspace_root = temp_root / "workspace"
        workspace_root.mkdir()
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "WORKSPACE.md").write_text("workspace\n", encoding="utf-8")
        (memory_root / "PROJECT_INDEX.md").write_text(
            self._project_index_text(route_type),
            encoding="utf-8",
        )
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

    def _project_index_text(self, route_type: str) -> str:
        return f"""# Project Index

## qinglong

- Path: `${{repo_root}}/qinglong` | Memory: `${{memory_root}}/qinglong`
- Route-Type: `{route_type}`
- Read-first: `${{memory_root}}/qinglong/PROJECT.md`
- Signals: project slug `qinglong`, project name `QingLong`
- Note: Remote project route.
"""


if __name__ == "__main__":
    unittest.main()
