from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import COMPATIBILITY_SUPPORT_END_DATE, CURRENT_PROFILE_SCHEMA_VERSION


SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


class ValidatorSubprocessTests(unittest.TestCase):
    def test_validator_subprocess_returns_ok_for_valid_primary_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")

            result = self._run_validator(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(0, result.returncode)
            self.assertIn("status: ok", result.stdout)
            self.assertIn("profile_source: primary", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertFalse((workspace_root / "repos" / "portable-project-bootstrap").exists())

    def test_validator_subprocess_returns_error_for_invalid_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            profile_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
            document = json.loads(profile_path.read_text(encoding="utf-8"))
            document["schema_version"] = CURRENT_PROFILE_SCHEMA_VERSION + 1
            profile_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

            result = self._run_validator(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(1, result.returncode)
            self.assertIn("status: error", result.stdout)
            self.assertIn("unsupported profile schema_version", result.stderr)

    def test_validator_subprocess_returns_error_for_missing_workspace_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            (workspace_root / ".agent-memory" / "WORKSPACE.md").unlink()

            result = self._run_validator(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(1, result.returncode)
            self.assertIn("status: error", result.stdout)
            self.assertIn("workspace_doc_path", result.stderr)

    def test_validator_subprocess_reports_partial_for_compatibility_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="compatibility")

            result = self._run_validator(workspace_root=workspace_root, profile_name="default")

            self.assertEqual(0, result.returncode)
            self.assertIn("status: partial", result.stdout)
            self.assertIn("profile_source: compatibility", result.stdout)
            self.assertIn("compatibility profile path is in use", result.stdout)
            self.assertIn(COMPATIBILITY_SUPPORT_END_DATE, result.stdout)

    def test_validator_subprocess_explicit_profile_path_overrides_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir), profile_mode="primary")
            broken_primary_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
            document = json.loads(broken_primary_path.read_text(encoding="utf-8"))
            document["schema_version"] = CURRENT_PROFILE_SCHEMA_VERSION + 1
            broken_primary_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
            explicit_profile_path = workspace_root / "custom-profile.json"
            explicit_profile_path.write_text(
                json.dumps(
                    {
                        "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                        "profile_name": "default",
                        "repo_root": str(workspace_root / "repos"),
                        "memory_root": str(workspace_root / ".agent-memory"),
                        "backup_root": str(workspace_root / "backups"),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = self._run_validator(
                workspace_root=workspace_root,
                profile_name="default",
                profile_path=explicit_profile_path,
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("status: ok", result.stdout)
            self.assertIn(f"profile_path: {explicit_profile_path}", result.stdout)
            self.assertIn("profile_source: explicit", result.stdout)

    def _run_validator(
        self,
        *,
        workspace_root: Path,
        profile_name: str,
        profile_path: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_ROOT)
        command = [
            sys.executable,
            "-m",
            "portable_project_bootstrap.validator",
            "--workspace-root",
            str(workspace_root),
            "--profile-name",
            profile_name,
        ]
        if profile_path is not None:
            command.extend(["--profile-path", str(profile_path)])
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            env=env,
            check=False,
        )

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
        (memory_root / "WORKSPACE.md").write_text("start\n", encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("rules\n", encoding="utf-8")
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
  - `C:\\example\\memory\\example-project`
- Read-first files:
  - `C:\\example\\memory\\example-project\\PROJECT.md`
  - `C:\\example\\memory\\example-project\\PROJECT.md`
- Optional files:
  - `C:\\example\\memory\\example-project\\AI_HANDOVER.md`
  - `C:\\example\\memory\\example-project\\AGENT_DESIGN.md`
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

