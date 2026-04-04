from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import CURRENT_PROFILE_SCHEMA_VERSION


SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


class RouterSubprocessTests(unittest.TestCase):
    def test_router_subprocess_exact_slug_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=["--project-slug", "alpha-project"],
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("status: ok", result.stdout)
            self.assertIn("matched_project_slug: alpha-project", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertFalse((workspace_root / "repos" / "portable-project-bootstrap").exists())

    def test_router_subprocess_ambiguous_query_returns_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=["--route-signal", "shared-suite"],
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("status: partial", result.stdout)
            self.assertIn("candidate_projects: [alpha-project, beta-project]", result.stdout)
            self.assertIn("ambiguity_reason:", result.stdout)

    def test_router_subprocess_missing_index_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))
            (workspace_root / ".agent-memory" / "PROJECT_INDEX.md").unlink()

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=["--project-slug", "alpha-project"],
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("status: error", result.stdout)
            self.assertIn("PROJECT_INDEX", result.stderr)

    def test_router_subprocess_missing_profile_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))
            (workspace_root / ".agent-memory" / "machine-profiles" / "default.json").unlink()

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=["--project-slug", "alpha-project"],
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("status: error", result.stdout)
            self.assertIn("profile file does not exist", result.stderr)

    def test_router_subprocess_weak_hint_does_not_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=["--route-signal", "alpha-hint"],
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("status: error", result.stdout)
            self.assertIn("strongly enough to route safely", result.stderr)

    def test_router_subprocess_requires_a_route_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = self._create_workspace(Path(temp_dir))

            result = self._run_router(
                workspace_root=workspace_root,
                profile_name="default",
                extra_args=[],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("workspace route query must include at least one routing input", result.stderr)

    def _run_router(
        self,
        *,
        workspace_root: Path,
        profile_name: str,
        extra_args: list[str],
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_ROOT)
        command = [
            sys.executable,
            "-m",
            "portable_project_bootstrap.router",
            "--workspace-root",
            str(workspace_root),
            "--profile-name",
            profile_name,
            *extra_args,
        ]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=workspace_root,
            env=env,
            check=False,
        )

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
