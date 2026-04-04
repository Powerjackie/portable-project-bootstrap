from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "workspaces"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REAL_CALLER = Path.home() / ".codex" / "skills" / "project-bootstrap" / "scripts" / "bootstrap_project.py"
REAL_CALLER = Path(os.environ.get("PORTABLE_PROJECT_BOOTSTRAP_REAL_CALLER", str(DEFAULT_REAL_CALLER)))


class RealCallerSubprocessTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_CALLER.is_file():
            self.skipTest(f"real caller is not available: {REAL_CALLER}")

    def test_real_caller_shadow_reports_match_without_writing(self) -> None:
        with self._materialized_fixture("brand_new") as workspace_root:
            result = self._run_caller(
                workspace_root=workspace_root,
                profile_name="default",
                mode="shadow",
                extra_args=["--dry-run"],
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("live_wrapper_mode: shadow", result.stdout)
            self.assertIn("shadow_matched: true", result.stdout)
            self.assertFalse((workspace_root / "repos" / "portable-project-bootstrap").exists())

    def test_real_caller_new_executes_successfully(self) -> None:
        with self._materialized_fixture("brand_new") as workspace_root:
            result = self._run_caller(
                workspace_root=workspace_root,
                profile_name="default",
                mode="new",
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("live_wrapper_mode: new", result.stdout)
            self.assertIn("project_index_status: applied", result.stdout)
            self.assertTrue((workspace_root / "repos" / "portable-project-bootstrap" / "README.md").exists())

    def test_real_caller_profile_validation_failure_remains_fail_closed(self) -> None:
        with self._materialized_fixture("brand_new") as workspace_root:
            profile_path = workspace_root / ".agent-memory" / "machine-profiles" / "default.json"
            document = json.loads(profile_path.read_text(encoding="utf-8"))
            document["schema_version"] = CURRENT_PROFILE_SCHEMA_VERSION + 1
            profile_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

            result = self._run_caller(
                workspace_root=workspace_root,
                profile_name="default",
                mode="new",
                extra_args=["--dry-run"],
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("unsupported profile schema_version", result.stderr)

    def _run_caller(
        self,
        *,
        workspace_root: Path,
        profile_name: str,
        mode: str,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PORTABLE_PROJECT_BOOTSTRAP_IMPL_ROOT"] = str(REPO_ROOT)
        command = [
            sys.executable,
            str(REAL_CALLER),
            "--workspace-root",
            str(workspace_root),
            "--profile-name",
            profile_name,
            "--mode",
            mode,
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
        if extra_args:
            command.extend(extra_args)
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            env=env,
            check=False,
        )

    def _materialized_fixture(self, name: str):
        class _FixtureContext:
            def __init__(self, outer: RealCallerSubprocessTests, fixture_name: str) -> None:
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
        )
        if fixture_name == "multi_profile":
            self._write_profile(
                profile_dir / "alt.json",
                profile_name="alt",
                repo_root=workspace_root / "repos-alt",
                memory_root=workspace_root / ".agent-memory-alt",
                backup_root=workspace_root / "backups-alt",
            )

    def _write_profile(
        self,
        path: Path,
        *,
        profile_name: str,
        repo_root: Path,
        memory_root: Path,
        backup_root: Path,
    ) -> None:
        path.write_text(
            json.dumps(
                {
                    "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                    "profile_name": profile_name,
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
