from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

from .errors import ExecutionError
from .models import (
    ActionExecutionRecord,
    ActionKind,
    ExecutionResult,
    ExecutionStatus,
    PlannedAction,
    PlanningResult,
    TargetKind,
)


class BootstrapExecutor:
    def execute(self, planning_result: PlanningResult) -> ExecutionResult:
        records: list[ActionExecutionRecord] = []
        dry_run = planning_result.request.dry_run

        for action in planning_result.actions:
            records.append(self._apply_action(action=action, dry_run=dry_run))

        bootstrap_log_path = self._bootstrap_log_path(planning_result)
        bootstrap_log_status, bootstrap_log_message = self._append_bootstrap_log(
            planning_result=planning_result,
            bootstrap_log_path=bootstrap_log_path,
            dry_run=dry_run,
        )
        project_index_status, project_index_message = self._project_index_result(
            planning_result=planning_result,
            records=tuple(records),
        )
        return ExecutionResult(
            planning_result=planning_result,
            records=tuple(records),
            bootstrap_log_status=bootstrap_log_status,
            bootstrap_log_path=bootstrap_log_path,
            bootstrap_log_message=bootstrap_log_message,
            project_index_status=project_index_status,
            project_index_message=project_index_message,
            dry_run=dry_run,
        )

    def _apply_action(self, *, action: PlannedAction, dry_run: bool) -> ActionExecutionRecord:
        if action.kind == ActionKind.SKIP:
            self._assert_skip_preconditions(action)
            return ActionExecutionRecord(
                action=action,
                status=ExecutionStatus.SKIPPED,
                message=action.reason,
            )
        if action.kind == ActionKind.MANUAL_PATCH:
            if not action.patch_content:
                raise ExecutionError(f"manual patch action is missing patch content: {action.target_path}")
            return ActionExecutionRecord(
                action=action,
                status=ExecutionStatus.REPORTED,
                message=action.reason,
            )
        if dry_run:
            return ActionExecutionRecord(
                action=action,
                status=ExecutionStatus.WOULD_APPLY,
                message=action.reason,
            )
        if action.kind == ActionKind.CREATE:
            self._apply_create(action)
            return ActionExecutionRecord(
                action=action,
                status=ExecutionStatus.APPLIED,
                message=action.reason,
            )
        if action.kind == ActionKind.SAFE_PATCH:
            self._apply_safe_patch(action)
            return ActionExecutionRecord(
                action=action,
                status=ExecutionStatus.APPLIED,
                message=action.reason,
            )
        raise ExecutionError(f"unsupported action kind: {action.kind}")

    def _apply_create(self, action: PlannedAction) -> None:
        if action.target_kind == TargetKind.DIRECTORY:
            if action.target_path.exists():
                raise ExecutionError(f"planned create target now exists: {action.target_path}")
            action.target_path.mkdir(parents=True, exist_ok=False)
            return
        if action.target_kind == TargetKind.OPERATION:
            self._apply_operation(action)
            return
        if action.target_kind in {TargetKind.FILE, TargetKind.STRUCTURED_FILE}:
            if action.render_content is None and action.patch_content is None:
                raise ExecutionError(f"create action is missing content: {action.target_path}")
            if action.target_path.exists():
                raise ExecutionError(f"planned create target now exists: {action.target_path}")
            if not action.target_path.parent.exists():
                raise ExecutionError(f"parent directory does not exist for create action: {action.target_path.parent}")
            content = action.render_content if action.render_content is not None else action.patch_content
            action.target_path.write_text(content, encoding="utf-8")
            return
        raise ExecutionError(f"unsupported create target kind: {action.target_kind}")

    def _apply_operation(self, action: PlannedAction) -> None:
        if "git_init" not in action.details:
            raise ExecutionError(f"unsupported operation action: {action.target_path}")
        repo_path = action.target_path.parent
        if action.target_path.exists():
            raise ExecutionError(f"planned git initialization target now exists: {action.target_path}")
        completed = subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            fallback = subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if fallback.returncode != 0:
                raise ExecutionError(
                    f"git init failed for {repo_path}: {completed.stderr.strip() or fallback.stderr.strip()}"
                )
            branch = subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if branch.returncode != 0:
                raise ExecutionError(
                    f"git branch rename failed for {repo_path}: {branch.stderr.strip()}"
                )
        if not action.target_path.is_dir():
            raise ExecutionError(f"git initialization did not create expected .git directory: {action.target_path}")

    def _apply_safe_patch(self, action: PlannedAction) -> None:
        if action.target_kind == TargetKind.FILE:
            if action.render_content is None:
                raise ExecutionError(f"safe patch action is missing rendered content: {action.target_path}")
            if not action.target_path.exists():
                raise ExecutionError(f"planned safe patch target is missing: {action.target_path}")
            if action.target_path.is_dir():
                raise ExecutionError(f"planned safe patch target is a directory: {action.target_path}")
            if action.target_path.stat().st_size != 0:
                raise ExecutionError(f"planned safe patch target is no longer empty: {action.target_path}")
            action.target_path.write_text(action.render_content, encoding="utf-8")
            return
        if action.target_kind == TargetKind.STRUCTURED_FILE:
            if action.patch_content is None:
                raise ExecutionError(f"structured safe patch action is missing patch content: {action.target_path}")
            if action.expected_content is None:
                raise ExecutionError(f"structured safe patch action is missing expected content: {action.target_path}")
            if not action.target_path.exists():
                raise ExecutionError(f"planned structured file is missing: {action.target_path}")
            if action.target_path.is_dir():
                raise ExecutionError(f"planned structured safe patch target is a directory: {action.target_path}")
            current_content = action.target_path.read_text(encoding="utf-8")
            if current_content != action.expected_content:
                raise ExecutionError(
                    f"planned structured safe patch target changed since planning: {action.target_path}"
                )
            action.target_path.write_text(action.patch_content, encoding="utf-8")
            return
        raise ExecutionError(f"unsupported safe patch target kind: {action.target_kind}")

    def _assert_skip_preconditions(self, action: PlannedAction) -> None:
        if "disabled" in action.details:
            return
        if not action.target_path.exists():
            raise ExecutionError(f"planned skip target no longer exists: {action.target_path}")
        if "directory" in action.details and not action.target_path.is_dir():
            raise ExecutionError(f"planned skip directory is no longer a directory: {action.target_path}")
        if "git_init" in action.details:
            if not action.target_path.is_dir():
                raise ExecutionError(f"planned git skip target is not a directory: {action.target_path}")
            return
        if "file" in action.details and action.target_path.is_dir():
            raise ExecutionError(f"planned skip file is now a directory: {action.target_path}")
        if "nonempty" in action.details and action.target_path.stat().st_size == 0:
            raise ExecutionError(f"planned skip file is no longer non-empty: {action.target_path}")

    def _bootstrap_log_path(self, planning_result: PlanningResult) -> Path | None:
        for action in planning_result.actions:
            if action.target_path.name == "BOOTSTRAP_LOG.md":
                return action.target_path
        return None

    def _append_bootstrap_log(
        self,
        *,
        planning_result: PlanningResult,
        bootstrap_log_path: Path | None,
        dry_run: bool,
    ) -> tuple[ExecutionStatus, str]:
        if bootstrap_log_path is None:
            return ExecutionStatus.SKIPPED, "bootstrap log target not present in planning result"
        if dry_run:
            return ExecutionStatus.WOULD_APPLY, "dry-run preserved; bootstrap log append not executed"
        if not bootstrap_log_path.exists():
            raise ExecutionError(f"bootstrap log target is missing after action application: {bootstrap_log_path}")
        if bootstrap_log_path.is_dir():
            raise ExecutionError(f"bootstrap log target is a directory: {bootstrap_log_path}")
        entry = self._bootstrap_log_entry(planning_result)
        existing = bootstrap_log_path.read_text(encoding="utf-8").rstrip()
        bootstrap_log_path.write_text(existing + "\n" + entry + "\n", encoding="utf-8")
        return ExecutionStatus.APPLIED, "bootstrap log entry appended"

    def _bootstrap_log_entry(self, planning_result: PlanningResult) -> str:
        timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        manual_patch_required = str(
            planning_result.index_update_plan.action.kind == ActionKind.MANUAL_PATCH
        ).lower()
        return (
            f"- {timestamp} | action=`bootstrap` | dry_run=`{str(planning_result.request.dry_run).lower()}` | "
            f"project_index_result=`{planning_result.summary.project_index_result}` | "
            f"manual_patch_required=`{manual_patch_required}` | "
            f"status=`{planning_result.summary.status}`"
        )

    def _project_index_result(
        self,
        *,
        planning_result: PlanningResult,
        records: tuple[ActionExecutionRecord, ...],
    ) -> tuple[ExecutionStatus, str]:
        target_path = planning_result.context.project_index_path
        for record in records:
            if record.action.target_path != target_path:
                continue
            if record.action.kind == ActionKind.MANUAL_PATCH:
                return ExecutionStatus.REPORTED, "manual patch retained; project index not auto-updated"
            if record.action.kind == ActionKind.SKIP:
                return ExecutionStatus.SKIPPED, record.message
            if record.status == ExecutionStatus.WOULD_APPLY:
                return ExecutionStatus.WOULD_APPLY, "dry-run preserved; project index patch not executed"
            return ExecutionStatus.APPLIED, record.message
        return ExecutionStatus.SKIPPED, "project index action not found in planning result"


def execute_plan(planning_result: PlanningResult) -> ExecutionResult:
    return BootstrapExecutor().execute(planning_result)
