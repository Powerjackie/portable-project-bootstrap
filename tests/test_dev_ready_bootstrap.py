from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import (
    ActionKind,
    BootstrapRequest,
    ExecutionError,
    WorkspaceContext,
    WorkspaceProfile,
    execute_plan,
    plan_bootstrap,
)

from test_execution import sample_project_index


class DevReadyBootstrapTests(unittest.TestCase):
    def test_default_python_bootstrap_creates_dev_ready_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )

            self.assertIn(repo_root / "portable-project-bootstrap" / ".gitignore", planning_result.rendered_files)
            self.assertIn(repo_root / "portable-project-bootstrap" / "pyproject.toml", planning_result.rendered_files)
            self.assertIn(repo_root / "portable-project-bootstrap" / "tests" / "test_smoke.py", planning_result.rendered_files)
            self.assertIn(repo_root / "portable-project-bootstrap" / "examples" / "README.md", planning_result.rendered_files)

            execution_result = execute_plan(planning_result)
            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"

            self.assertTrue((repo_path / ".git").is_dir())
            self.assertTrue((repo_path / ".gitignore").is_file())
            self.assertTrue((repo_path / "README.md").is_file())
            self.assertTrue((repo_path / "pyproject.toml").is_file())
            self.assertTrue((repo_path / "LICENSE").is_file())
            self.assertTrue((repo_path / "CONTRIBUTING.md").is_file())
            self.assertTrue((repo_path / "tests" / "test_smoke.py").is_file())
            self.assertTrue((repo_path / "examples" / "README.md").is_file())
            self.assertTrue((memory_path / "PROJECT.md").is_file())
            self.assertEqual("applied", execution_result.project_index_status.value)

    def test_git_init_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, init_git=False),
            )
            git_actions = [action for action in planning_result.actions if action.target_path.name == ".git"]
            self.assertEqual(1, len(git_actions))
            self.assertEqual(ActionKind.SKIP, git_actions[0].kind)
            self.assertIn("disabled", git_actions[0].details)

            execute_plan(planning_result)
            self.assertFalse((repo_root / "portable-project-bootstrap" / ".git").exists())

    def test_optional_dev_ready_docs_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(
                    dry_run=False,
                    create_license=False,
                    create_contributing=False,
                    create_examples=False,
                    create_tests=False,
                ),
            )

            repo_path = repo_root / "portable-project-bootstrap"
            self.assertNotIn(repo_path / "LICENSE", planning_result.rendered_files)
            self.assertNotIn(repo_path / "CONTRIBUTING.md", planning_result.rendered_files)
            self.assertNotIn(repo_path / "examples" / "README.md", planning_result.rendered_files)
            self.assertNotIn(repo_path / "tests" / "test_smoke.py", planning_result.rendered_files)

            execute_plan(planning_result)
            self.assertFalse((repo_path / "LICENSE").exists())
            self.assertFalse((repo_path / "CONTRIBUTING.md").exists())
            self.assertFalse((repo_path / "examples").exists())
            self.assertFalse((repo_path / "tests").exists())

    def test_non_python_stack_skips_pyproject_when_stack_metadata_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=BootstrapRequest(
                    project_name="Docs Project",
                    project_slug="docs-project",
                    project_summary="A documentation-first project.",
                    tech_stack=("Markdown",),
                    create_stack_metadata=True,
                    dry_run=True,
                ),
            )

            self.assertNotIn(repo_root / "docs-project" / "pyproject.toml", planning_result.rendered_files)
            action_paths = {action.target_path for action in planning_result.actions}
            self.assertNotIn(repo_root / "docs-project" / "pyproject.toml", action_paths)

    def test_nonempty_repo_file_still_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            (repo_path / "README.md").write_text("custom readme\n", encoding="utf-8")
            (repo_path / ".gitignore").write_text("custom ignore\n", encoding="utf-8")
            for name in ("PROJECT.md", "AI_HANDOVER.md", "AGENT_DESIGN.md"):
                (memory_path / name).write_text("existing\n", encoding="utf-8")
            (memory_path / "BOOTSTRAP_LOG.md").write_text("", encoding="utf-8")
            (repo_path / ".git").mkdir()

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, force=True),
            )

            kind_by_path = {action.target_path: action.kind for action in planning_result.actions}
            self.assertEqual(ActionKind.SKIP, kind_by_path[repo_path / "README.md"])
            self.assertEqual(ActionKind.SKIP, kind_by_path[repo_path / ".gitignore"])
            self.assertEqual(ActionKind.SKIP, kind_by_path[repo_path / ".git"])

            execute_plan(planning_result)
            self.assertEqual("custom readme\n", (repo_path / "README.md").read_text(encoding="utf-8"))
            self.assertEqual("custom ignore\n", (repo_path / ".gitignore").read_text(encoding="utf-8"))

    def test_git_skip_fails_closed_if_existing_git_dir_disappears_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root, memory_root, backup_root, project_index_path = self._roots(Path(temp_dir))
            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            (repo_path / ".git").mkdir()
            (repo_path / "README.md").write_text("existing readme\n", encoding="utf-8")
            (repo_path / ".gitignore").write_text("existing ignore\n", encoding="utf-8")
            for name in ("PROJECT.md", "AI_HANDOVER.md", "AGENT_DESIGN.md"):
                (memory_path / name).write_text("existing\n", encoding="utf-8")
            (memory_path / "BOOTSTRAP_LOG.md").write_text("", encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, force=True),
            )
            (repo_path / ".git").rmdir()

            with self.assertRaisesRegex(ExecutionError, "planned skip target no longer exists"):
                execute_plan(planning_result)

    def _roots(self, temp_root: Path) -> tuple[Path, Path, Path, Path]:
        repo_root = temp_root / "repos"
        memory_root = temp_root / "memory"
        backup_root = temp_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        project_index_path = memory_root / "PROJECT_INDEX.md"
        project_index_path.write_text(sample_project_index(), encoding="utf-8")
        return repo_root, memory_root, backup_root, project_index_path

    def _context(
        self,
        repo_root: Path,
        memory_root: Path,
        backup_root: Path,
        project_index_path: Path,
    ) -> WorkspaceContext:
        return WorkspaceContext(
            profile=WorkspaceProfile(
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
            ),
            project_index_path=project_index_path,
            workspace_doc_path=memory_root / "WORKSPACE.md",
        )

    def _request(
        self,
        *,
        dry_run: bool,
        force: bool = False,
        init_git: bool = True,
        create_license: bool = True,
        create_contributing: bool = True,
        create_tests: bool = True,
        create_examples: bool = True,
        create_stack_metadata: bool = True,
    ) -> BootstrapRequest:
        return BootstrapRequest(
            project_name="Portable Project Bootstrap",
            project_slug="portable-project-bootstrap",
            project_summary="A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
            tech_stack=("Python", "Markdown", "JSON"),
            dry_run=dry_run,
            force=force,
            init_git=init_git,
            create_license=create_license,
            create_contributing=create_contributing,
            create_tests=create_tests,
            create_examples=create_examples,
            create_stack_metadata=create_stack_metadata,
        )


if __name__ == "__main__":
    unittest.main()

