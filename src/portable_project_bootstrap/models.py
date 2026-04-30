from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .errors import PlanningError


class ActionKind(StrEnum):
    CREATE = "create"
    SKIP = "skip"
    SAFE_PATCH = "safe_patch"
    MANUAL_PATCH = "manual_patch"


class TargetKind(StrEnum):
    DIRECTORY = "directory"
    FILE = "file"
    STRUCTURED_FILE = "structured_file"
    OPERATION = "operation"


class ExecutionStatus(StrEnum):
    WOULD_APPLY = "would_apply"
    APPLIED = "applied"
    SKIPPED = "skipped"
    REPORTED = "reported"


class OverallStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass(frozen=True)
class WorkspaceProfile:
    profile_name: str
    repo_root: Path
    memory_root: Path
    backup_root: Path
    schema_version: int = 1
    memory_mode: str = "inline"

    def __post_init__(self) -> None:
        if not self.profile_name.strip():
            raise PlanningError("profile_name must not be empty")
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise PlanningError("schema_version must be a positive integer")
        if self.memory_mode not in {"inline", "external"}:
            raise PlanningError("memory_mode must be one of: inline, external")
        for field_name in ("repo_root", "memory_root", "backup_root"):
            path = getattr(self, field_name)
            if not isinstance(path, Path):
                raise PlanningError(f"{field_name} must be a pathlib.Path")
            if not str(path).strip():
                raise PlanningError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class WorkspaceContext:
    profile: WorkspaceProfile
    project_index_path: Path
    workspace_doc_path: Path | None = None
    resolved_profile_path: Path | None = None
    resolved_profile_source: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.project_index_path, Path):
            raise PlanningError("project_index_path must be a pathlib.Path")
        if not str(self.project_index_path).strip():
            raise PlanningError("project_index_path must not be empty")
        for field_name in (
            "workspace_doc_path",
            "resolved_profile_path",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, Path):
                raise PlanningError(f"{field_name} must be a pathlib.Path when provided")
        if self.resolved_profile_source is not None and not self.resolved_profile_source.strip():
            raise PlanningError("resolved_profile_source must not be empty when provided")


@dataclass(frozen=True)
class BootstrapRequest:
    project_name: str
    project_slug: str
    project_summary: str
    tech_stack: tuple[str, ...] = ()
    create_session_bootstrap: bool = False
    update_project_index: bool = True
    dry_run: bool = False
    force: bool = False
    repo_visibility: str = "private"
    project_type: str = "generic"
    routing_keyword_strong: tuple[str, ...] = ()
    routing_keyword_weak: tuple[str, ...] = ()
    init_git: bool = True
    create_license: bool = True
    create_contributing: bool = True
    create_tests: bool = True
    create_examples: bool = True
    create_stack_metadata: bool = True

    def __post_init__(self) -> None:
        if not self.project_name.strip():
            raise PlanningError("project_name must not be empty")
        if not self.project_summary.strip():
            raise PlanningError("project_summary must not be empty")
        slug = self.project_slug.strip()
        if not slug:
            raise PlanningError("project_slug must not be empty")
        if len(slug) > 63:
            raise PlanningError("project_slug must be 63 characters or fewer")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        if slug[0] == "-" or any(char not in allowed for char in slug):
            raise PlanningError("project_slug must use lowercase letters, numbers, and hyphens only")
        if "--" in slug or slug.endswith("-"):
            raise PlanningError("project_slug must not contain repeated or trailing hyphens")
        if self.repo_visibility not in {"private", "internal", "public"}:
            raise PlanningError("repo_visibility must be one of: private, internal, public")
        if self.project_type not in {"generic", "node", "python", "docs", "hybrid"}:
            raise PlanningError("project_type must be one of: generic, node, python, docs, hybrid")
        for field_name in ("tech_stack", "routing_keyword_strong", "routing_keyword_weak"):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise PlanningError(f"{field_name} must be a tuple of strings")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise PlanningError(f"{field_name} must contain only non-empty strings")


@dataclass(frozen=True)
class ProjectPaths:
    repo_path: Path
    memory_path: Path
    backup_path: Path


@dataclass(frozen=True)
class PlannedAction:
    kind: ActionKind
    target_kind: TargetKind
    target_path: Path
    reason: str
    render_content: str | None = None
    patch_content: str | None = None
    expected_content: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectIndexUpdatePlan:
    result: str
    action: PlannedAction
    rendered_entry: str | None = None
    manual_patch: str | None = None
    update_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class BootstrapSummary:
    project_name: str
    project_slug: str
    repo_path: str
    memory_path: str
    backup_path: str
    update_project_index: bool
    dry_run: bool
    project_index_result: str
    project_index_update_reasons: tuple[str, ...] = ()
    create_targets: tuple[str, ...] = ()
    skip_targets: tuple[str, ...] = ()
    safe_patch_targets: tuple[str, ...] = ()
    manual_patch_targets: tuple[str, ...] = ()
    manual_follow_up: str = "none"
    status: str = "ok"

    def lines(self) -> list[str]:
        return [
            f"project_name: {self.project_name}",
            f"project_slug: {self.project_slug}",
            f"repo_path: {self.repo_path}",
            f"memory_path: {self.memory_path}",
            f"backup_path: {self.backup_path}",
            f"update_project_index: {str(self.update_project_index).lower()}",
            f"project_index_result: {self.project_index_result}",
            f"project_index_update_reasons: {format_list(self.project_index_update_reasons)}",
            f"dry_run: {str(self.dry_run).lower()}",
            f"create_targets: {format_list(self.create_targets)}",
            f"skip_targets: {format_list(self.skip_targets)}",
            f"safe_patch_targets: {format_list(self.safe_patch_targets)}",
            f"manual_patch_targets: {format_list(self.manual_patch_targets)}",
            f"manual_follow_up: {self.manual_follow_up}",
            f"status: {self.status}",
        ]


@dataclass(frozen=True)
class PlanningResult:
    context: WorkspaceContext
    request: BootstrapRequest
    paths: ProjectPaths
    actions: tuple[PlannedAction, ...]
    index_update_plan: ProjectIndexUpdatePlan
    summary: BootstrapSummary
    rendered_files: dict[Path, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionExecutionRecord:
    action: PlannedAction
    status: ExecutionStatus
    message: str


@dataclass(frozen=True)
class ExecutionResult:
    planning_result: PlanningResult
    records: tuple[ActionExecutionRecord, ...]
    bootstrap_log_status: ExecutionStatus
    bootstrap_log_path: Path | None
    bootstrap_log_message: str
    project_index_status: ExecutionStatus
    project_index_message: str
    dry_run: bool

    @property
    def manual_patch_records(self) -> tuple[ActionExecutionRecord, ...]:
        return tuple(record for record in self.records if record.action.kind == ActionKind.MANUAL_PATCH)


@dataclass(frozen=True)
class CompatibilityBridgeRequest:
    workspace_root: Path
    profile_name: str
    profile_path: Path | None = None
    project_name: str = ""
    project_slug: str = ""
    project_summary: str = ""
    tech_stack: tuple[str, ...] = ()
    create_session_bootstrap: bool = False
    update_project_index: bool = True
    dry_run: bool = False
    force: bool = False
    repo_visibility: str = "private"
    project_type: str = "generic"
    routing_keyword_strong: tuple[str, ...] = ()
    routing_keyword_weak: tuple[str, ...] = ()
    init_git: bool = True
    create_license: bool = True
    create_contributing: bool = True
    create_tests: bool = True
    create_examples: bool = True
    create_stack_metadata: bool = True
    execute: bool = False


@dataclass(frozen=True)
class ExplicitEntrypointRequest:
    profile_name: str
    repo_root: Path
    memory_root: Path
    backup_root: Path
    project_index_path: Path
    workspace_doc_path: Path | None = None
    memory_mode: str = "inline"
    project_name: str = ""
    project_slug: str = ""
    project_summary: str = ""
    tech_stack: tuple[str, ...] = ()
    create_session_bootstrap: bool = False
    update_project_index: bool = True
    dry_run: bool = False
    force: bool = False
    repo_visibility: str = "private"
    project_type: str = "generic"
    routing_keyword_strong: tuple[str, ...] = ()
    routing_keyword_weak: tuple[str, ...] = ()
    init_git: bool = True
    create_license: bool = True
    create_contributing: bool = True
    create_tests: bool = True
    create_examples: bool = True
    create_stack_metadata: bool = True
    execute: bool = False


@dataclass(frozen=True)
class CompatibilityBridgeResult:
    context: WorkspaceContext
    request: BootstrapRequest
    planning_result: PlanningResult
    execution_result: ExecutionResult | None = None

    @property
    def manual_patch_output(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.planning_result.index_update_plan.manual_patch:
            values.append(self.planning_result.index_update_plan.manual_patch)
        if self.execution_result:
            for record in self.execution_result.manual_patch_records:
                if record.action.patch_content:
                    values.append(record.action.patch_content)
        return tuple(values)


@dataclass(frozen=True)
class ShadowComparisonResult:
    operator_result: CompatibilityBridgeResult
    explicit_result: CompatibilityBridgeResult
    differences: tuple[str, ...]

    @property
    def matched(self) -> bool:
        return not self.differences


def format_list(values: tuple[str, ...]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


@dataclass(frozen=True)
class ProjectIndexRecord:
    project_slug: str
    purpose: str
    canonical_repo_paths: tuple[str, ...]
    backup_paths: tuple[str, ...]
    memory_root: str | None
    read_first_files: tuple[str, ...]
    optional_files: tuple[str, ...]
    strong_match_signals: tuple[str, ...]
    weak_hints: tuple[str, ...]
    summary: str
    raw_section: str
    project_names: tuple[str, ...] = ()
    route_type: str = "local"
    remote_host: str | None = None


@dataclass(frozen=True)
class ProjectIndexDocument:
    preamble: str
    records: tuple[ProjectIndexRecord, ...]


@dataclass(frozen=True)
class WorkspaceValidationResult:
    status: OverallStatus
    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    resolved_paths: dict[str, str]
    next_steps: tuple[str, ...]

    def lines(self) -> list[str]:
        lines = [f"status: {self.status.value}"]
        for key in sorted(self.resolved_paths):
            lines.append(f"{key}: {self.resolved_paths[key]}")
        lines.append(f"problems: {format_list(self.problems)}")
        lines.append(f"warnings: {format_list(self.warnings)}")
        lines.append(f"next_steps: {format_list(self.next_steps)}")
        return lines


@dataclass(frozen=True)
class RouteCandidate:
    project_slug: str
    project_name: str | None
    repo_path: str | None
    memory_path: str | None
    read_first_files: tuple[str, ...]
    summary: str
    match_reasons: tuple[str, ...] = ()
    route_type: str = "local"
    remote_host: str | None = None


@dataclass(frozen=True)
class WorkspaceRouteResult:
    status: OverallStatus
    matched_project: RouteCandidate | None = None
    candidates: tuple[RouteCandidate, ...] = ()
    ambiguity_reason: str | None = None
    problems: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()
    resolved_paths: dict[str, str] = field(default_factory=dict)

    def lines(self) -> list[str]:
        lines = [f"status: {self.status.value}"]
        if self.matched_project is not None:
            lines.extend(
                [
                    f"matched_project_slug: {self.matched_project.project_slug}",
                    f"matched_project_name: {self.matched_project.project_name or 'none'}",
                    f"repo_path: {self.matched_project.repo_path or 'none'}",
                    f"memory_path: {self.matched_project.memory_path or 'none'}",
                    f"route_type: {self.matched_project.route_type}",
                    f"remote_host: {self.matched_project.remote_host or 'none'}",
                    f"read_first_files: {format_list(self.matched_project.read_first_files)}",
                    f"match_reasons: {format_list(self.matched_project.match_reasons)}",
                ]
            )
        else:
            lines.extend(
                [
                    "matched_project_slug: none",
                    "matched_project_name: none",
                    "repo_path: none",
                    "memory_path: none",
                    "route_type: none",
                    "remote_host: none",
                    "read_first_files: []",
                    "match_reasons: []",
                ]
            )
        lines.append(
            "candidate_projects: "
            + format_list(tuple(candidate.project_slug for candidate in self.candidates))
        )
        lines.append(f"ambiguity_reason: {self.ambiguity_reason or 'none'}")
        for key in sorted(self.resolved_paths):
            lines.append(f"{key}: {self.resolved_paths[key]}")
        lines.append(f"problems: {format_list(self.problems)}")
        lines.append(f"warnings: {format_list(self.warnings)}")
        lines.append(f"next_steps: {format_list(self.next_steps)}")
        return lines


@dataclass(frozen=True)
class WorkspaceRouteQuery:
    project_slug: str | None = None
    project_name: str | None = None
    route_signal: str | None = None
    repo_path: Path | None = None
    memory_path: Path | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                _has_text(self.project_slug),
                _has_text(self.project_name),
                _has_text(self.route_signal),
                self.repo_path is not None,
                self.memory_path is not None,
            )
        ):
            raise PlanningError("workspace route query must include at least one routing input")
        for field_name in ("project_slug", "project_name", "route_signal"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise PlanningError(f"{field_name} must not be blank when provided")
        for field_name in ("repo_path", "memory_path"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, Path):
                raise PlanningError(f"{field_name} must be a pathlib.Path when provided")


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())
