from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from portable_project_bootstrap import (
    COMPATIBILITY_SUPPORT_END_DATE,
    CURRENT_PROFILE_SCHEMA_VERSION,
    OverallStatus,
)
from portable_project_bootstrap.validator import main as validator_main
from portable_project_bootstrap.validator import validate_workspace


class WorkspaceValidatorTests(unittest.TestCase):
    def test_valid_primary_profile_returns_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.OK, result.status)
            self.assertEqual((), result.problems)
            self.assertEqual("primary", result.resolved_paths["profile_source"])

    def test_missing_required_profile_field_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            profile_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
            document = json.loads(profile_path.read_text(encoding="utf-8"))
            document.pop("memory_root")
            profile_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("memory_root" in item for item in result.problems))

    def test_missing_required_workspace_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            (workspace_root / ".agent-memory" / "WORKSPACE.md").unlink()

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("workspace_doc_path" in item for item in result.problems))

    def test_invalid_path_shape_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            profile_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
            document = json.loads(profile_path.read_text(encoding="utf-8"))
            document["repo_root"] = "relative\\repo-root"
            profile_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.ERROR, result.status)
            self.assertTrue(any("repo_root" in item for item in result.problems))

    def test_compatibility_profile_returns_partial_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="compatibility")

            result = validate_workspace(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(OverallStatus.PARTIAL, result.status)
            self.assertEqual("compatibility", result.resolved_paths["profile_source"])
            self.assertTrue(any("compatibility profile path" in item for item in result.warnings))
            self.assertTrue(any(COMPATIBILITY_SUPPORT_END_DATE in item for item in result.warnings))

    def test_validator_cli_prints_structured_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = validator_main(
                    [
                        "--workspace-root",
                        str(workspace_root),
                        "--profile-name",
                        "default",
                    ]
                )

            self.assertEqual(0, exit_code)
            output = stdout.getvalue()
            self.assertIn("status: ok", output)
            self.assertIn("profile_source: primary", output)
            self.assertIn("next_steps:", output)

    def test_current_real_workspace_smoke_returns_structured_result(self) -> None:
        workspace_root = Path("D:/workspace")
        profile_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
        if not workspace_root.exists() or not profile_path.exists():
            self.skipTest("current real workspace profile is not available in this environment")

        result = validate_workspace(workspace_root=workspace_root, profile_name="default")

        self.assertIn(result.status, {OverallStatus.OK, OverallStatus.PARTIAL})
        self.assertIn("profile_path", result.resolved_paths)
        self.assertIn("project_index_path", result.resolved_paths)

    def _create_workspace(self, temp_root: Path, *, profile_mode: str) -> Path:
        workspace_root = temp_root / "workspace"
        workspace_root.mkdir()
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "PROJECT_INDEX.md").write_text(self._project_index_text(), encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("workspace\n", encoding="utf-8")
        profile_document = {
            "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
            "profile_name": "default",
            "repo_root": str(repo_root),
            "memory_root": str(memory_root),
            "backup_root": str(backup_root),
        }
        if profile_mode == "primary":
            profile_dir = workspace_root / ".agent-memory" / "machine-profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            (profile_dir / "default.json").write_text(
                json.dumps(profile_document, indent=2),
                encoding="utf-8",
            )
        elif profile_mode == "compatibility":
            compatibility_path = workspace_root / ".codex" / "workspace-profile" / "PROFILE.json"
            compatibility_path.parent.mkdir(parents=True, exist_ok=True)
            compatibility_path.write_text(
                json.dumps(profile_document, indent=2),
                encoding="utf-8",
            )
        else:
            raise ValueError(f"unsupported profile_mode: {profile_mode}")
        return workspace_root

    def _project_index_text(self) -> str:
        return """# Project Index

## example-project

- Purpose: Example existing project
- Canonical repo / runtime surface:
  - `C:\\example\\repo\\example-project`
- Backup path:
  - `C:\\example\\backup\\example-project`
- Memory root:
  - `C:\\example\\repo\\example-project\\.agent-memory`
- Read-first files:
  - `C:\\example\\repo\\example-project\\.agent-memory\\PROJECT.md`
- Optional files:
  - `C:\\example\\repo\\example-project\\.agent-memory\\AI_HANDOVER.md`
  - `C:\\example\\repo\\example-project\\.agent-memory\\AGENT_DESIGN.md`
- Strong match signals:
  - project slug `example-project`
  - project name `Example Project`
- Weak hints only:
  - `example`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Example existing project.
"""


if __name__ == "__main__":
    unittest.main()

