from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import ProfileLoadError, WorkspaceProfile
from portable_project_bootstrap.profile_loader import expand_path


class PathExpansionTests(unittest.TestCase):
    def test_expand_path_resolves_supported_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            profile = WorkspaceProfile(
                profile_name="macos",
                repo_root=Path("/Users/example/Developer/workspace/repos"),
                memory_root=workspace_root / ".agent-memory",
                backup_root=workspace_root / "backups",
            )

            expanded = expand_path(
                "${repo_root}/prompt-ide",
                profile,
                workspace_root=workspace_root,
            )

            self.assertEqual("/Users/example/Developer/workspace/repos/prompt-ide", expanded)

    def test_expand_path_rejects_unknown_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            profile = WorkspaceProfile(
                profile_name="default",
                repo_root=workspace_root / "repos",
                memory_root=workspace_root / ".agent-memory",
                backup_root=workspace_root / "backups",
            )

            with self.assertRaisesRegex(ProfileLoadError, "unsupported path token"):
                expand_path("${unknown_root}/prompt-ide", profile, workspace_root=workspace_root)

    def test_expand_path_preserves_legacy_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            profile = WorkspaceProfile(
                profile_name="default",
                repo_root=workspace_root / "repos",
                memory_root=workspace_root / ".agent-memory",
                backup_root=workspace_root / "backups",
            )
            absolute_path = "C:/Users/example/Documents/GitHub/prompt-ide"

            expanded = expand_path(absolute_path, profile, workspace_root=workspace_root)

            self.assertEqual(absolute_path, expanded)


if __name__ == "__main__":
    unittest.main()
