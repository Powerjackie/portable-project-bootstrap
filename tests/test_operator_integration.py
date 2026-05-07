from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION
from portable_project_bootstrap.operator_cli import main as operator_main


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "workspaces"


class OperatorIntegrationTests(unittest.TestCase):
    def test_brand_new_fixture_executes_full_chain(self) -> None:
        with self._materialized_fixture("brand_new") as workspace_root:
            exit_code, stdout, stderr = self._run_operator(
                workspace_root=workspace_root,
                profile_name="default",
                execute=True,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("project_index_result: added", stdout)
            self.assertIn("project_index_status: applied", stdout)
            self.assertTrue(
                (workspace_root / "repos" / "portable-project-bootstrap" / "README.md").exists()
            )
            self.assertIn(
                "## portable-project-bootstrap",
                (workspace_root / ".agent-memory" / "PROJECT_INDEX.md").read_text(encoding="utf-8"),
            )
            self.assertTrue(
                (workspace_root / "repos" / "portable-project-bootstrap" / ".agent-memory" / "PROJECT.md").exists()
            )

    def test_partial_force_fixture_requires_force_then_executes(self) -> None:
        with self._materialized_fixture("partial_force") as workspace_root:
            exit_code, _, stderr = self._run_operator(
                workspace_root=workspace_root,
                profile_name="default",
                execute=True,
            )
            self.assertEqual(1, exit_code)
            self.assertIn("partial bootstrap state detected", stderr)

            exit_code, stdout, stderr = self._run_operator(
                workspace_root=workspace_root,
                profile_name="default",
                execute=True,
                force=True,
            )
            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("bootstrap_log_status: applied", stdout)
            self.assertTrue(
                (workspace_root / "repos" / "portable-project-bootstrap" / ".agent-memory" / "PROJECT.md").exists()
            )

    def test_multi_profile_fixture_covers_manual_patch_and_alt_profile_variant(self) -> None:
        with self._materialized_fixture("multi_profile") as workspace_root:
            exit_code, stdout, stderr = self._run_operator(
                workspace_root=workspace_root,
                profile_name="default",
                execute=True,
            )
            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("project_index_result: manual_patch_required", stdout)
            self.assertIn("manual_patch_output:", stdout)
            self.assertEqual(
                "## broken\n- Purpose: missing required fields\n",
                (workspace_root / ".agent-memory" / "PROJECT_INDEX.md").read_text(encoding="utf-8"),
            )

            exit_code, stdout, stderr = self._run_operator(
                workspace_root=workspace_root,
                profile_name="alt",
                execute=True,
            )
            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr)
            self.assertIn("project_index_status: applied", stdout)
            self.assertTrue(
                (workspace_root / "repos-alt" / "portable-project-bootstrap" / "README.md").exists()
            )
            self.assertTrue(
                (workspace_root / ".agent-memory-alt" / "portable-project-bootstrap" / "PROJECT.md").exists()
            )

    def _run_operator(
        self,
        *,
        workspace_root: Path,
        profile_name: str,
        execute: bool,
        force: bool = False,
    ) -> tuple[int, str, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        argv = [
            "--workspace-root",
            str(workspace_root),
            "--profile-name",
            profile_name,
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
        if execute:
            argv.append("--execute")
        if force:
            argv.append("--force")
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = operator_main(argv)
        return exit_code, stdout_buffer.getvalue(), stderr_buffer.getvalue()

    def _materialized_fixture(self, name: str):
        class _FixtureContext:
            def __init__(self, outer: OperatorIntegrationTests, fixture_name: str) -> None:
                self.outer = outer
                self.fixture_name = fixture_name
                self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
                self.workspace_root: Path | None = None

            def __enter__(self) -> Path:
                self.temp_dir = tempfile.TemporaryDirectory()
                self.workspace_root = Path(self.temp_dir.name) / self.fixture_name
                shutil.copytree(FIXTURE_ROOT / self.fixture_name, self.workspace_root)
                self.outer._write_profiles(self.workspace_root, self.fixture_name)
                return self.workspace_root

            def __exit__(self, exc_type, exc, tb) -> None:
                assert self.temp_dir is not None
                self.temp_dir.cleanup()

        return _FixtureContext(self, name)

    def _write_profiles(self, workspace_root: Path, fixture_name: str) -> None:
        profile_dir = workspace_root / ".agent-memory" / "machine-profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._write_profile(
            profile_dir / "default.json",
            profile_name="default",
            repo_root=workspace_root / "repos",
            memory_root=workspace_root / ".agent-memory",
            backup_root=workspace_root / "backups",
            memory_mode="inline",
        )
        if fixture_name == "multi_profile":
            self._write_profile(
                profile_dir / "alt.json",
                profile_name="alt",
                repo_root=workspace_root / "repos-alt",
                memory_root=workspace_root / ".agent-memory-alt",
                backup_root=workspace_root / "backups-alt",
                memory_mode="external",
            )

    def _write_profile(
        self,
        path: Path,
        *,
        profile_name: str,
        repo_root: Path,
        memory_root: Path,
        backup_root: Path,
        memory_mode: str,
    ) -> None:
        path.write_text(
            json.dumps(
                {
                    "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                    "profile_name": profile_name,
                    "repo_root": str(repo_root),
                    "memory_root": str(memory_root),
                    "backup_root": str(backup_root),
                    "memory_mode": memory_mode,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()

