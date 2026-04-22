from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION, MODE_ENV_VAR, DEFAULT_MODE, resolve_mode
from portable_project_bootstrap.live_wrapper import main as live_wrapper_main


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


class LiveWrapperTests(unittest.TestCase):
    def test_resolve_mode_defaults_to_new(self) -> None:
        self.assertEqual(DEFAULT_MODE, resolve_mode(cli_mode=None, env={}))

    def test_resolve_mode_prefers_cli_over_env(self) -> None:
        env = {MODE_ENV_VAR: "legacy"}
        self.assertEqual("new", resolve_mode(cli_mode="new", env=env))

    def test_shadow_mode_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            exit_code, stdout, stderr = self._run_wrapper(
                workspace_root=workspace_root,
                mode="shadow",
                execute=True,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("live_wrapper_mode: shadow", stdout)
            self.assertIn("shadow_matched: true", stdout)
            self.assertFalse((workspace_root / "repos" / "portable-project-bootstrap").exists())

    def test_new_mode_executes_successfully(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            exit_code, stdout, stderr = self._run_wrapper(
                workspace_root=workspace_root,
                mode="new",
                execute=True,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("live_wrapper_mode: new", stdout)
            self.assertIn("project_index_status: applied", stdout)
            self.assertTrue((workspace_root / "repos" / "portable-project-bootstrap" / "README.md").exists())

    def test_default_mode_without_mode_flag_runs_new(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            exit_code, stdout, stderr = self._run_wrapper(
                workspace_root=workspace_root,
                mode=None,
                execute=True,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("live_wrapper_mode: new", stdout)
            self.assertIn("project_index_status: applied", stdout)
            self.assertTrue((workspace_root / "repos" / "portable-project-bootstrap" / "README.md").exists())

    def test_new_mode_failure_does_not_silent_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            with patch("portable_project_bootstrap.live_wrapper.run_compatibility_bridge", side_effect=ValueError("boom")):
                exit_code, stdout, stderr = self._run_wrapper(
                    workspace_root=workspace_root,
                    mode="new",
                    execute=False,
                )

            self.assertEqual(1, exit_code)
            self.assertEqual("", stdout)
            self.assertIn("boom", stderr)
            self.assertFalse((workspace_root / "repos" / "portable-project-bootstrap").exists())

    def test_explicit_cutback_to_legacy_continues_to_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self._write_workspace_profile(workspace_root)

            with patch("portable_project_bootstrap.live_wrapper.run_compatibility_bridge", side_effect=ValueError("boom")):
                exit_code, _, stderr = self._run_wrapper(
                    workspace_root=workspace_root,
                    mode="new",
                    execute=False,
                )
            self.assertEqual(1, exit_code)
            self.assertIn("boom", stderr)

            exit_code, stdout, stderr = self._run_wrapper(
                workspace_root=workspace_root,
                mode="legacy",
                execute=True,
            )
            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("live_wrapper_mode: legacy", stdout)
            self.assertTrue((workspace_root / "repos" / "portable-project-bootstrap" / "README.md").exists())

    def _run_wrapper(
        self,
        *,
        workspace_root: Path,
        mode: str | None,
        execute: bool,
    ) -> tuple[int, str, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        argv = []
        if mode is not None:
            argv.extend(["--mode", mode])
        argv.extend(
            [
                "--workspace-root",
                str(workspace_root),
                "--profile-name",
                "default",
                "--project-name",
                "Portable Project Bootstrap",
                "--project-slug",
                "portable-project-bootstrap",
                "--project-summary",
                "A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
                "--tech-stack",
                "Python",
                "--tech-stack",
                "Markdown",
                "--tech-stack",
                "JSON",
            ]
        )
        if execute:
            argv.append("--execute")
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = live_wrapper_main(argv)
        return exit_code, stdout_buffer.getvalue(), stderr_buffer.getvalue()

    def _write_workspace_profile(self, workspace_root: Path) -> None:
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "PROJECT_INDEX.md").write_text(sample_project_index(), encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("workspace\n", encoding="utf-8")
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

