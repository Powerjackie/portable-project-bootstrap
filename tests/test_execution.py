from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import (
    ActionKind,
    BootstrapRequest,
    ExecutionError,
    ExecutionStatus,
    PlanningError,
    WorkspaceContext,
    WorkspaceProfile,
    execute_plan,
    plan_bootstrap,
)


def sample_project_index() -> str:
    return """# Project Index

## existing-project

- Purpose: Existing project
- Canonical repo / runtime surface:
  - `X:\\repo\\existing-project`
- Backup path:
  - `X:\\backup\\existing-project`
- Memory root:
  - `X:\\repo\\existing-project\\.agent-memory`
- Read-first files:
  - `X:\\repo\\existing-project\\.agent-memory\\PROJECT.md`
- Optional files:
  - `X:\\repo\\existing-project\\.agent-memory\\AI_HANDOVER.md`
  - `X:\\repo\\existing-project\\.agent-memory\\AGENT_DESIGN.md`
- Strong match signals:
  - project slug `existing-project`
- Weak hints only:
  - `none`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Existing project.
"""


def multi_section_project_index() -> str:
    return """# Project Index

## alpha-project

- Purpose: Alpha project
- Canonical repo / runtime surface:
  - `X:\\repo\\alpha-project`
- Backup path:
  - `X:\\backup\\alpha-project`
- Memory root:
  - `X:\\repo\\alpha-project\\.agent-memory`
- Read-first files:
  - `X:\\repo\\alpha-project\\.agent-memory\\PROJECT.md`
- Optional files:
  - `X:\\repo\\alpha-project\\.agent-memory\\AI_HANDOVER.md`
  - `X:\\repo\\alpha-project\\.agent-memory\\AGENT_DESIGN.md`
- Strong match signals:
  - project slug `alpha-project`
- Weak hints only:
  - `none`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Alpha project.

## zeta-project

- Purpose: Zeta project
- Canonical repo / runtime surface:
  - `X:\\repo\\zeta-project`
- Backup path:
  - `X:\\backup\\zeta-project`
- Memory root:
  - `X:\\repo\\zeta-project\\.agent-memory`
- Read-first files:
  - `X:\\repo\\zeta-project\\.agent-memory\\PROJECT.md`
- Optional files:
  - `X:\\repo\\zeta-project\\.agent-memory\\AI_HANDOVER.md`
  - `X:\\repo\\zeta-project\\.agent-memory\\AGENT_DESIGN.md`
- Strong match signals:
  - project slug `zeta-project`
- Weak hints only:
  - `none`
- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.
- Summary: Zeta project.
"""


class ExecutionTests(unittest.TestCase):
    def test_dry_run_and_actual_run_share_action_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            dry_run_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )
            actual_run_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )

            dry_signature = [(action.kind, action.target_kind, action.target_path) for action in dry_run_result.actions]
            actual_signature = [
                (action.kind, action.target_kind, action.target_path) for action in actual_run_result.actions
            ]
            self.assertEqual(dry_signature, actual_signature)
            self.assertEqual(
                dry_run_result.index_update_plan.action.patch_content,
                actual_run_result.index_update_plan.action.patch_content,
            )

    def test_dry_run_preserves_plan_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )
            execution_result = execute_plan(planning_result)

            self.assertEqual(ExecutionStatus.WOULD_APPLY, execution_result.bootstrap_log_status)
            self.assertEqual(ExecutionStatus.WOULD_APPLY, execution_result.project_index_status)
            self.assertFalse((repo_root / "portable-project-bootstrap").exists())
            self.assertFalse((repo_root / "portable-project-bootstrap" / ".agent-memory").exists())
            self.assertEqual(
                len(planning_result.actions),
                len(execution_result.records),
            )

    def test_execute_applies_create_and_safe_patch_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )
            execution_result = execute_plan(planning_result)

            self.assertEqual(ExecutionStatus.APPLIED, execution_result.bootstrap_log_status)
            self.assertEqual(ExecutionStatus.APPLIED, execution_result.project_index_status)
            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            self.assertTrue((repo_path / "README.md").exists())
            self.assertTrue((memory_path / "BOOTSTRAP_LOG.md").exists())
            log_text = (memory_path / "BOOTSTRAP_LOG.md").read_text(encoding="utf-8")
            self.assertIn("action=`bootstrap`", log_text)
            index_text = project_index_path.read_text(encoding="utf-8")
            self.assertIn("## portable-project-bootstrap", index_text)
            self.assertLess(index_text.index("## existing-project"), index_text.index("## portable-project-bootstrap"))
            self.assertEqual(("missing_slug_entry",), planning_result.summary.project_index_update_reasons)

    def test_manual_patch_is_reported_without_index_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            broken_index_text = "## broken\n- Purpose: missing required fields\n"
            project_index_path.write_text(broken_index_text, encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )
            execution_result = execute_plan(planning_result)

            self.assertEqual(ExecutionStatus.REPORTED, execution_result.project_index_status)
            self.assertEqual(1, len(execution_result.manual_patch_records))
            self.assertEqual(broken_index_text, project_index_path.read_text(encoding="utf-8"))
            self.assertTrue((repo_root / "portable-project-bootstrap" / ".agent-memory" / "BOOTSTRAP_LOG.md").exists())

    def test_partial_state_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            (repo_path / "README.md").write_text("existing readme\n", encoding="utf-8")

            with self.assertRaisesRegex(PlanningError, "partial bootstrap state detected"):
                plan_bootstrap(
                    context=self._context(repo_root, memory_root, backup_root, project_index_path),
                    request=self._request(dry_run=True, force=False),
                )

    def test_partial_state_with_force_plans_repairs_without_replanning_in_executor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            (repo_path / "README.md").write_text("existing readme\n", encoding="utf-8")
            (memory_path / "BOOTSTRAP_LOG.md").write_text("", encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, force=True),
            )

            action_map = {action.target_path: action for action in planning_result.actions}
            self.assertEqual(ActionKind.SKIP, action_map[repo_path / "README.md"].kind)
            self.assertEqual(("must_exist", "file", "nonempty"), action_map[repo_path / "README.md"].details)
            self.assertEqual(ActionKind.SAFE_PATCH, action_map[memory_path / "BOOTSTRAP_LOG.md"].kind)
            self.assertEqual(("must_exist", "file", "empty"), action_map[memory_path / "BOOTSTRAP_LOG.md"].details)

            execution_result = execute_plan(planning_result)
            self.assertEqual(ExecutionStatus.APPLIED, execution_result.bootstrap_log_status)
            self.assertTrue((memory_path / "PROJECT.md").exists())
            self.assertIn("action=`bootstrap`", (memory_path / "BOOTSTRAP_LOG.md").read_text(encoding="utf-8"))

    def test_skip_nonempty_file_fails_closed_if_file_becomes_empty_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            readme_path = repo_path / "README.md"
            readme_path.write_text("existing readme\n", encoding="utf-8")
            for name in ("PROJECT.md", "AI_HANDOVER.md", "AGENT_DESIGN.md", "BOOTSTRAP_LOG.md"):
                (memory_path / name).write_text("existing\n", encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, force=True),
            )
            readme_path.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ExecutionError, "no longer non-empty"):
                execute_plan(planning_result)

    def test_create_action_fails_closed_if_target_appears_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )
            planned_repo_path = repo_root / "portable-project-bootstrap"
            planned_repo_path.mkdir()

            with self.assertRaisesRegex(ExecutionError, "planned create target now exists"):
                execute_plan(planning_result)

    def test_safe_patch_file_fails_closed_if_target_becomes_nonempty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            repo_path = repo_root / "portable-project-bootstrap"
            memory_path = repo_path / ".agent-memory"
            repo_path.mkdir()
            memory_path.mkdir()
            (repo_path / "README.md").write_text("existing readme\n", encoding="utf-8")
            for name in ("PROJECT.md", "AI_HANDOVER.md", "AGENT_DESIGN.md"):
                (memory_path / name).write_text("existing\n", encoding="utf-8")
            boot_log_path = memory_path / "BOOTSTRAP_LOG.md"
            boot_log_path.write_text("", encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False, force=True),
            )
            boot_log_path.write_text("now nonempty\n", encoding="utf-8")

            with self.assertRaisesRegex(ExecutionError, "no longer empty"):
                execute_plan(planning_result)

    def test_structured_safe_patch_fails_closed_if_index_file_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )
            project_index_path.unlink()

            with self.assertRaisesRegex(ExecutionError, "planned structured file is missing"):
                execute_plan(planning_result)

    def test_structured_safe_patch_fails_closed_if_index_file_changes_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(sample_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=False),
            )
            project_index_path.write_text(sample_project_index() + "\n## drifted\n", encoding="utf-8")

            with self.assertRaisesRegex(ExecutionError, "changed since planning"):
                execute_plan(planning_result)

    def test_project_index_safe_patch_inserts_slug_sorted_among_multiple_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(multi_section_project_index(), encoding="utf-8")

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )

            self.assertEqual("added", planning_result.index_update_plan.result)
            patch_content = planning_result.index_update_plan.action.patch_content or ""
            self.assertLess(patch_content.index("## alpha-project"), patch_content.index("## portable-project-bootstrap"))
            self.assertLess(patch_content.index("## portable-project-bootstrap"), patch_content.index("## zeta-project"))

    def test_project_index_matching_paths_refreshes_stale_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(
                f"""# Project Index

## portable-project-bootstrap

- Path: `{repo_root}\\portable-project-bootstrap` | Memory: `{repo_root}\\portable-project-bootstrap\\.agent-memory`
- Read-first: `PROJECT.md`
- Signals: slug `portable-project-bootstrap`
- Note: stale routing note
""",
                encoding="utf-8",
            )

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )

            self.assertEqual("updated", planning_result.index_update_plan.result)
            self.assertEqual(ActionKind.SAFE_PATCH, planning_result.index_update_plan.action.kind)
            self.assertEqual(
                ("strong_match_signals", "summary"),
                planning_result.index_update_plan.update_reasons,
            )
            self.assertEqual(
                ("strong_match_signals", "summary"),
                planning_result.summary.project_index_update_reasons,
            )
            self.assertIn(
                "project name `Portable Project Bootstrap`",
                planning_result.index_update_plan.action.patch_content or "",
            )

    def test_project_index_structured_match_ignores_formatting_only_differences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(
                f"""# Project Index

## portable-project-bootstrap

- Path: `{repo_root}\\portable-project-bootstrap` | Memory: `{repo_root}\\portable-project-bootstrap\\.agent-memory`
- Read-first: `PROJECT.md`
- Signals: project name `Portable Project Bootstrap`, slug `portable-project-bootstrap`
""",
                encoding="utf-8",
            )

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )

            self.assertEqual("unchanged", planning_result.index_update_plan.result)
            self.assertEqual(ActionKind.SKIP, planning_result.index_update_plan.action.kind)
            self.assertEqual((), planning_result.index_update_plan.update_reasons)
            self.assertEqual((), planning_result.summary.project_index_update_reasons)

    def test_project_index_conflicting_existing_slug_requires_manual_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repos"
            memory_root = temp_root / "memory"
            backup_root = temp_root / "backups"
            repo_root.mkdir()
            memory_root.mkdir()
            backup_root.mkdir()
            project_index_path = memory_root / "PROJECT_INDEX.md"
            project_index_path.write_text(
                sample_project_index().replace(
                    "## existing-project",
                    "## portable-project-bootstrap",
                ),
                encoding="utf-8",
            )

            planning_result = plan_bootstrap(
                context=self._context(repo_root, memory_root, backup_root, project_index_path),
                request=self._request(dry_run=True),
            )

            self.assertEqual("manual_patch_required", planning_result.index_update_plan.result)
            self.assertEqual("manual_patch", planning_result.index_update_plan.action.kind)
            self.assertEqual(
                (
                    "canonical_repo_paths",
                    "memory_root",
                    "purpose",
                    "read_first_files",
                    "optional_files",
                    "strong_match_signals",
                    "summary",
                ),
                planning_result.index_update_plan.update_reasons,
            )
            self.assertIn(
                "Replace the existing `## portable-project-bootstrap` section",
                planning_result.index_update_plan.manual_patch or "",
            )

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

    def _request(self, *, dry_run: bool, force: bool = False) -> BootstrapRequest:
        return BootstrapRequest(
            project_name="Portable Project Bootstrap",
            project_slug="portable-project-bootstrap",
            project_summary="A portable, profile-driven bootstrap skill for initializing brand-new projects across machines under the workspace system.",
            tech_stack=("Python", "Markdown", "JSON"),
            dry_run=dry_run,
            force=force,
        )


if __name__ == "__main__":
    unittest.main()

