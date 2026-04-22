from __future__ import annotations

from .executor import execute_plan
from .models import (
    BootstrapRequest,
    CompatibilityBridgeResult,
    ExplicitEntrypointRequest,
    WorkspaceContext,
    WorkspaceProfile,
)
from .planner import plan_bootstrap


def run_explicit_entry(args: ExplicitEntrypointRequest) -> CompatibilityBridgeResult:
    context = WorkspaceContext(
        profile=WorkspaceProfile(
            profile_name=args.profile_name,
            repo_root=args.repo_root,
            memory_root=args.memory_root,
            backup_root=args.backup_root,
            memory_mode=args.memory_mode,
        ),
        project_index_path=args.project_index_path,
        workspace_doc_path=args.workspace_doc_path,
    )
    request = BootstrapRequest(
        project_name=args.project_name,
        project_slug=args.project_slug,
        project_summary=args.project_summary,
        tech_stack=args.tech_stack,
        create_session_bootstrap=args.create_session_bootstrap,
        update_project_index=args.update_project_index,
        dry_run=args.dry_run,
        force=args.force,
        repo_visibility=args.repo_visibility,
        project_type=args.project_type,
        routing_keyword_strong=args.routing_keyword_strong,
        routing_keyword_weak=args.routing_keyword_weak,
        init_git=args.init_git,
        create_license=args.create_license,
        create_contributing=args.create_contributing,
        create_tests=args.create_tests,
        create_examples=args.create_examples,
        create_stack_metadata=args.create_stack_metadata,
    )
    planning_result = plan_bootstrap(context=context, request=request)
    execution_result = execute_plan(planning_result) if args.execute else None
    return CompatibilityBridgeResult(
        context=context,
        request=request,
        planning_result=planning_result,
        execution_result=execution_result,
    )
