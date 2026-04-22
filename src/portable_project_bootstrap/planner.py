from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import PlanningError, ProjectIndexParseError
from .models import (
    ActionKind,
    BootstrapRequest,
    BootstrapSummary,
    PlannedAction,
    PlanningResult,
    ProjectIndexUpdatePlan,
    ProjectPaths,
    TargetKind,
    WorkspaceContext,
)
from .project_index import (
    compare_project_index_records,
    parse_project_index_document,
    parse_project_index_record_block,
    upsert_project_index_record,
)
from .templates import is_memory_file_key, render_project_index_entry, render_template_set


MANUAL_PATCH_MESSAGE = (
    "manual patch required for project index; review emitted snippet and apply it manually"
)


@dataclass(frozen=True)
class _ExistingFileState:
    path: Path
    exists: bool
    is_empty: bool


class BootstrapPlanner:
    def plan(self, context: WorkspaceContext, request: BootstrapRequest) -> PlanningResult:
        self._validate_context(context=context, request=request)
        paths = self._project_paths(context=context, request=request)
        rendered_files = render_template_set(context=context, request=request, paths=paths)
        actions: list[PlannedAction] = []

        actions.extend(self._plan_directory_targets(paths=paths, rendered_files=rendered_files))
        actions.extend(
            self._plan_file_targets(
                repo_path=paths.repo_path,
                memory_path=paths.memory_path,
                rendered_files=rendered_files,
            )
        )
        actions.append(self._plan_git_initialization(paths=paths, request=request))
        index_plan = self._plan_project_index(context=context, request=request, paths=paths)
        actions.append(index_plan.action)

        self._enforce_force_rules(request=request, paths=paths, actions=tuple(actions), context=context)
        summary = self._build_summary(
            request=request,
            paths=paths,
            actions=tuple(actions),
            index_plan=index_plan,
        )
        return PlanningResult(
            context=context,
            request=request,
            paths=paths,
            actions=tuple(actions),
            index_update_plan=index_plan,
            summary=summary,
            rendered_files={
                (paths.memory_path / Path(name) if is_memory_file_key(name) else paths.repo_path / Path(name)): content
                for name, content in rendered_files.items()
            },
        )

    def _validate_context(self, *, context: WorkspaceContext, request: BootstrapRequest) -> None:
        for root_name in ("repo_root", "memory_root", "backup_root"):
            root = getattr(context.profile, root_name)
            if not root.exists():
                raise PlanningError(f"{root_name} does not exist: {root}")
            if not root.is_dir():
                raise PlanningError(f"{root_name} must be a directory: {root}")
        if request.update_project_index and not context.project_index_path.exists():
            raise PlanningError(f"project_index_path does not exist: {context.project_index_path}")
        if request.update_project_index and not context.project_index_path.is_file():
            raise PlanningError(f"project_index_path must be a file: {context.project_index_path}")

    def _project_paths(self, *, context: WorkspaceContext, request: BootstrapRequest) -> ProjectPaths:
        slug = request.project_slug.strip()
        repo_path = context.profile.repo_root / slug
        if context.profile.memory_mode == "inline":
            memory_path = repo_path / ".agent-memory"
        else:
            memory_path = context.profile.memory_root / slug
        return ProjectPaths(
            repo_path=repo_path,
            memory_path=memory_path,
            backup_path=context.profile.backup_root / slug,
        )

    def _plan_directory_targets(self, *, paths: ProjectPaths, rendered_files: dict[str, str]) -> list[PlannedAction]:
        targets: list[Path] = [paths.repo_path, paths.memory_path]
        repo_subdirs = {
            paths.repo_path / Path(name).parent
            for name in rendered_files
            if not is_memory_file_key(name) and Path(name).parent != Path(".")
        }
        targets.extend(sorted(repo_subdirs, key=str))
        return [self._classify_directory(path) for path in targets]

    def _classify_directory(self, path: Path) -> PlannedAction:
        if not path.exists():
            return PlannedAction(
                kind=ActionKind.CREATE,
                target_kind=TargetKind.DIRECTORY,
                target_path=path,
                reason="directory does not exist",
                details=("must_not_exist", "directory"),
            )
        if not path.is_dir():
            raise PlanningError(f"expected directory path but found non-directory: {path}")
        return PlannedAction(
            kind=ActionKind.SKIP,
            target_kind=TargetKind.DIRECTORY,
            target_path=path,
            reason="directory already exists",
            details=("must_exist", "directory"),
        )

    def _plan_file_targets(
        self,
        *,
        repo_path: Path,
        memory_path: Path,
        rendered_files: dict[str, str],
    ) -> list[PlannedAction]:
        actions: list[PlannedAction] = []
        for name, content in rendered_files.items():
            target_root = memory_path if is_memory_file_key(name) else repo_path
            actions.append(
                self._classify_file(
                    path=target_root / Path(name),
                    content=content,
                )
            )
        return actions

    def _plan_git_initialization(self, *, paths: ProjectPaths, request: BootstrapRequest) -> PlannedAction:
        git_dir = paths.repo_path / ".git"
        if not request.init_git:
            return PlannedAction(
                kind=ActionKind.SKIP,
                target_kind=TargetKind.OPERATION,
                target_path=git_dir,
                reason="git initialization is disabled by request",
                details=("git_init", "disabled"),
            )
        if not git_dir.exists():
            return PlannedAction(
                kind=ActionKind.CREATE,
                target_kind=TargetKind.OPERATION,
                target_path=git_dir,
                reason="git repository is not initialized yet",
                details=("git_init",),
            )
        if not git_dir.is_dir():
            raise PlanningError(f"expected .git to be a directory when present: {git_dir}")
        return PlannedAction(
            kind=ActionKind.SKIP,
            target_kind=TargetKind.OPERATION,
            target_path=git_dir,
            reason="git repository is already initialized",
            details=("git_init", "existing"),
        )

    def _classify_file(self, *, path: Path, content: str) -> PlannedAction:
        state = self._existing_file_state(path)
        if not state.exists:
            return PlannedAction(
                kind=ActionKind.CREATE,
                target_kind=TargetKind.FILE,
                target_path=path,
                reason="file does not exist",
                render_content=content,
                details=("must_not_exist", "file"),
            )
        if state.is_empty:
            return PlannedAction(
                kind=ActionKind.SAFE_PATCH,
                target_kind=TargetKind.FILE,
                target_path=path,
                reason="file is empty and can be safely filled without overwriting non-empty content",
                render_content=content,
                details=("must_exist", "file", "empty"),
            )
        return PlannedAction(
            kind=ActionKind.SKIP,
            target_kind=TargetKind.FILE,
            target_path=path,
            reason="non-empty file already exists and must not be overwritten",
            details=("must_exist", "file", "nonempty"),
        )

    def _existing_file_state(self, path: Path) -> _ExistingFileState:
        if not path.exists():
            return _ExistingFileState(path=path, exists=False, is_empty=False)
        if path.is_dir():
            raise PlanningError(f"expected file path but found directory: {path}")
        return _ExistingFileState(path=path, exists=True, is_empty=path.stat().st_size == 0)

    def _plan_project_index(
        self,
        *,
        context: WorkspaceContext,
        request: BootstrapRequest,
        paths: ProjectPaths,
    ) -> ProjectIndexUpdatePlan:
        if not request.update_project_index:
            action = PlannedAction(
                kind=ActionKind.SKIP,
                target_kind=TargetKind.STRUCTURED_FILE,
                target_path=context.project_index_path,
                reason="project index updates are disabled by request",
                details=("must_exist", "file"),
            )
            return ProjectIndexUpdatePlan(result="skipped", action=action)

        text = context.project_index_path.read_text(encoding="utf-8")
        entry = render_project_index_entry(context=context, request=request, paths=paths)
        try:
            document = parse_project_index_document(text)
            desired_record = parse_project_index_record_block(entry)
        except ProjectIndexParseError:
            manual_patch = self._manual_patch_text(entry=entry, project_index_path=context.project_index_path)
            action = PlannedAction(
                kind=ActionKind.MANUAL_PATCH,
                target_kind=TargetKind.STRUCTURED_FILE,
                target_path=context.project_index_path,
                reason="project index could not be safely parsed for auto-update",
                patch_content=manual_patch,
                details=("must_exist", "file"),
            )
            return ProjectIndexUpdatePlan(
                result="manual_patch_required",
                action=action,
                rendered_entry=entry,
                manual_patch=manual_patch,
                update_reasons=("project_index_parse_failed",),
            )

        existing_records = {record.project_slug: record for record in document.records}
        existing_record = existing_records.get(request.project_slug)
        if existing_record is None:
            updated_content = upsert_project_index_record(
                document,
                project_slug=request.project_slug,
                rendered_entry=entry,
            )
            action = PlannedAction(
                kind=ActionKind.SAFE_PATCH,
                target_kind=TargetKind.STRUCTURED_FILE,
                target_path=context.project_index_path,
                reason="project index is parseable and missing the requested slug entry",
                patch_content=updated_content,
                expected_content=text,
                details=("must_exist", "file"),
            )
            return ProjectIndexUpdatePlan(
                result="added",
                action=action,
                rendered_entry=entry,
                update_reasons=("missing_slug_entry",),
            )

        comparison = compare_project_index_records(existing=existing_record, desired=desired_record)
        if not comparison.has_changes:
            action = PlannedAction(
                kind=ActionKind.SKIP,
                target_kind=TargetKind.STRUCTURED_FILE,
                target_path=context.project_index_path,
                reason="project index already contains a matching entry for this slug",
                details=("must_exist", "file"),
            )
            return ProjectIndexUpdatePlan(
                result="unchanged",
                action=action,
                rendered_entry=entry,
            )

        if not comparison.path_conflict_fields:
            updated_content = upsert_project_index_record(
                document,
                project_slug=request.project_slug,
                rendered_entry=entry,
            )
            action = PlannedAction(
                kind=ActionKind.SAFE_PATCH,
                target_kind=TargetKind.STRUCTURED_FILE,
                target_path=context.project_index_path,
                reason="project index entry paths still match and can be refreshed safely",
                patch_content=updated_content,
                expected_content=text,
                details=("must_exist", "file"),
            )
            return ProjectIndexUpdatePlan(
                result="updated",
                action=action,
                rendered_entry=entry,
                update_reasons=comparison.changed_fields,
            )

        manual_patch = self._manual_patch_text(
            entry=entry,
            project_index_path=context.project_index_path,
            project_slug=request.project_slug,
            replace_existing=True,
        )
        action = PlannedAction(
            kind=ActionKind.MANUAL_PATCH,
            target_kind=TargetKind.STRUCTURED_FILE,
            target_path=context.project_index_path,
            reason="existing project index entry conflicts with computed repo or memory paths",
            patch_content=manual_patch,
            details=("must_exist", "file"),
        )
        return ProjectIndexUpdatePlan(
            result="manual_patch_required",
            action=action,
            rendered_entry=entry,
            manual_patch=manual_patch,
            update_reasons=comparison.all_reasons,
        )

    def _manual_patch_text(
        self,
        *,
        entry: str,
        project_index_path: Path,
        project_slug: str | None = None,
        replace_existing: bool = False,
    ) -> str:
        if replace_existing and project_slug:
            return (
                f"Replace the existing `## {project_slug}` section in `{project_index_path}` "
                "with this block:\n\n"
                f"{entry}\n"
            )
        return (
            f"Insert this section into `{project_index_path}` in slug-sorted order:\n\n"
            f"{entry}\n"
        )

    def _enforce_force_rules(
        self,
        *,
        request: BootstrapRequest,
        paths: ProjectPaths,
        actions: tuple[PlannedAction, ...],
        context: WorkspaceContext,
    ) -> None:
        if request.force:
            return
        relevant_actions = tuple(
            action
            for action in actions
            if action.target_path != context.project_index_path
            and (
                action.target_path == paths.repo_path
                or action.target_path == paths.memory_path
                or paths.repo_path in action.target_path.parents
                or paths.memory_path in action.target_path.parents
            )
        )
        has_create = any(action.kind == ActionKind.CREATE for action in relevant_actions)
        has_existing = any(
            action.kind in {ActionKind.SKIP, ActionKind.SAFE_PATCH} and "disabled" not in action.details
            for action in relevant_actions
        )
        if has_create and has_existing:
            raise PlanningError("partial bootstrap state detected; rerun with force=true to plan repair mode")

    def _build_summary(
        self,
        *,
        request: BootstrapRequest,
        paths: ProjectPaths,
        actions: tuple[PlannedAction, ...],
        index_plan: ProjectIndexUpdatePlan,
    ) -> BootstrapSummary:
        create_targets = tuple(str(action.target_path) for action in actions if action.kind == ActionKind.CREATE)
        skip_targets = tuple(str(action.target_path) for action in actions if action.kind == ActionKind.SKIP)
        safe_patch_targets = tuple(
            str(action.target_path) for action in actions if action.kind == ActionKind.SAFE_PATCH
        )
        manual_patch_targets = tuple(
            str(action.target_path) for action in actions if action.kind == ActionKind.MANUAL_PATCH
        )
        manual_follow_up = "none"
        status = "ok"
        if manual_patch_targets:
            manual_follow_up = MANUAL_PATCH_MESSAGE
            status = "partial"
        return BootstrapSummary(
            project_name=request.project_name,
            project_slug=request.project_slug,
            repo_path=str(paths.repo_path),
            memory_path=str(paths.memory_path),
            backup_path=str(paths.backup_path),
            update_project_index=request.update_project_index,
            dry_run=request.dry_run,
            project_index_result=index_plan.result,
            project_index_update_reasons=index_plan.update_reasons,
            create_targets=create_targets,
            skip_targets=skip_targets,
            safe_patch_targets=safe_patch_targets,
            manual_patch_targets=manual_patch_targets,
            manual_follow_up=manual_follow_up,
            status=status,
        )


def plan_bootstrap(context: WorkspaceContext, request: BootstrapRequest) -> PlanningResult:
    return BootstrapPlanner().plan(context=context, request=request)
