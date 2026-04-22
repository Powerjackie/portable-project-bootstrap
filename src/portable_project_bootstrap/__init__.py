from .bridge import run_compatibility_bridge
from .direct_entry import run_explicit_entry
from .errors import (
    BridgeError,
    ExecutionError,
    PlanningError,
    ProfileLoadError,
    ShadowModeError,
    SkillCallerError,
)
from .executor import BootstrapExecutor, execute_plan
from .live_wrapper import DEFAULT_MODE, MODE_ENV_VAR, build_parser as build_live_wrapper_parser, resolve_mode
from .models import (
    ActionKind,
    ActionExecutionRecord,
    BootstrapRequest,
    BootstrapSummary,
    CompatibilityBridgeRequest,
    CompatibilityBridgeResult,
    ExplicitEntrypointRequest,
    ExecutionResult,
    ExecutionStatus,
    OverallStatus,
    PlannedAction,
    PlanningResult,
    ProjectIndexUpdatePlan,
    ProjectIndexDocument,
    ProjectIndexRecord,
    ProjectPaths,
    RouteCandidate,
    ShadowComparisonResult,
    TargetKind,
    WorkspaceRouteQuery,
    WorkspaceRouteResult,
    WorkspaceContext,
    WorkspaceProfile,
    WorkspaceValidationResult,
)
from .operator_cli import format_bridge_result_lines
from .profile_loader import (
    COMPATIBILITY_PROFILE_PATH,
    COMPATIBILITY_SUPPORT_END_DATE,
    CURRENT_PROFILE_SCHEMA_VERSION,
    PRIMARY_PROFILE_DIR,
    compatibility_profile_warning,
    discover_profile_path,
    discover_profile_path_with_source,
    load_workspace_context,
    load_workspace_profile,
    resolve_profile_path,
)
from .planner import BootstrapPlanner, plan_bootstrap
from .project_index import load_project_index_document, parse_project_index_document
from .skill_caller import (
    DEFAULT_PROFILE_NAME,
    DEFAULT_WORKSPACE_ROOT,
    PROFILE_NAME_ENV_VAR,
    WORKSPACE_ROOT_ENV_VAR,
    build_parser as build_skill_caller_parser,
)
from .shadow import format_shadow_result_lines, run_shadow_mode

__all__ = [
    "ActionKind",
    "ActionExecutionRecord",
    "BridgeError",
    "BootstrapExecutor",
    "BootstrapPlanner",
    "BootstrapRequest",
    "BootstrapSummary",
    "CompatibilityBridgeRequest",
    "CompatibilityBridgeResult",
    "DEFAULT_MODE",
    "DEFAULT_PROFILE_NAME",
    "DEFAULT_WORKSPACE_ROOT",
    "ExplicitEntrypointRequest",
    "CURRENT_PROFILE_SCHEMA_VERSION",
    "COMPATIBILITY_PROFILE_PATH",
    "COMPATIBILITY_SUPPORT_END_DATE",
    "ExecutionError",
    "ExecutionResult",
    "ExecutionStatus",
    "ProjectIndexDocument",
    "ProjectIndexRecord",
    "PlannedAction",
    "PlanningError",
    "PlanningResult",
    "PRIMARY_PROFILE_DIR",
    "ProfileLoadError",
    "ProjectIndexUpdatePlan",
    "ProjectPaths",
    "RouteCandidate",
    "MODE_ENV_VAR",
    "OverallStatus",
    "PROFILE_NAME_ENV_VAR",
    "ShadowComparisonResult",
    "ShadowModeError",
    "SkillCallerError",
    "TargetKind",
    "WORKSPACE_ROOT_ENV_VAR",
    "WorkspaceContext",
    "WorkspaceProfile",
    "WorkspaceRouteQuery",
    "WorkspaceRouteResult",
    "WorkspaceValidationResult",
    "discover_profile_path_with_source",
    "discover_profile_path",
    "build_skill_caller_parser",
    "compatibility_profile_warning",
    "execute_plan",
    "build_live_wrapper_parser",
    "format_bridge_result_lines",
    "format_shadow_result_lines",
    "load_workspace_context",
    "load_project_index_document",
    "load_workspace_profile",
    "parse_project_index_document",
    "plan_bootstrap",
    "resolve_profile_path",
    "resolve_mode",
    "route_workspace",
    "run_explicit_entry",
    "run_compatibility_bridge",
    "run_shadow_mode",
    "validate_workspace",
]


def validate_workspace(*args, **kwargs):
    from .validator import validate_workspace as _validate_workspace

    return _validate_workspace(*args, **kwargs)


def route_workspace(*args, **kwargs):
    from .router import route_workspace as _route_workspace

    return _route_workspace(*args, **kwargs)
