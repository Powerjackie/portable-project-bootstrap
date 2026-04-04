from __future__ import annotations

from .errors import BridgeError
from .executor import execute_plan
from .models import (
    BootstrapRequest,
    CompatibilityBridgeRequest,
    CompatibilityBridgeResult,
)
from .planner import plan_bootstrap
from .profile_loader import load_workspace_context


def run_compatibility_bridge(args: CompatibilityBridgeRequest) -> CompatibilityBridgeResult:
    context = load_workspace_context(
        workspace_root=args.workspace_root,
        profile_name=args.profile_name,
        profile_path=args.profile_path,
    )
    request = _map_bridge_request(args)
    planning_result = plan_bootstrap(context=context, request=request)
    execution_result = execute_plan(planning_result) if args.execute else None
    return CompatibilityBridgeResult(
        context=context,
        request=request,
        planning_result=planning_result,
        execution_result=execution_result,
    )


def _map_bridge_request(args: CompatibilityBridgeRequest) -> BootstrapRequest:
    if not args.project_name.strip():
        raise BridgeError("project_name must not be empty")
    if not args.project_slug.strip():
        raise BridgeError("project_slug must not be empty")
    if not args.project_summary.strip():
        raise BridgeError("project_summary must not be empty")
    return BootstrapRequest(
        project_name=args.project_name,
        project_slug=args.project_slug,
        project_summary=args.project_summary,
        tech_stack=tuple(_normalize(args.tech_stack)),
        create_session_bootstrap=args.create_session_bootstrap,
        update_project_index=args.update_project_index,
        dry_run=args.dry_run,
        force=args.force,
        repo_visibility=args.repo_visibility,
        project_type=args.project_type,
        routing_keyword_strong=tuple(_normalize(args.routing_keyword_strong)),
        routing_keyword_weak=tuple(_normalize(args.routing_keyword_weak)),
        init_git=args.init_git,
        create_license=args.create_license,
        create_contributing=args.create_contributing,
        create_tests=args.create_tests,
        create_examples=args.create_examples,
        create_stack_metadata=args.create_stack_metadata,
    )


def _normalize(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        for piece in value.split(","):
            item = piece.strip()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
    return tuple(normalized)
