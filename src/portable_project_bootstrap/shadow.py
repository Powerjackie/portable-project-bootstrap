from __future__ import annotations

from .bridge import run_compatibility_bridge
from .direct_entry import run_explicit_entry
from .errors import ShadowModeError
from .models import (
    CompatibilityBridgeRequest,
    CompatibilityBridgeResult,
    ExplicitEntrypointRequest,
    ShadowComparisonResult,
)


def run_shadow_mode(args: CompatibilityBridgeRequest) -> ShadowComparisonResult:
    if args.execute:
        raise ShadowModeError("shadow mode is compare-only; rerun without execute=true")
    operator_result = run_compatibility_bridge(args)
    explicit_result = run_explicit_entry(_explicit_request_from_operator_result(operator_result))
    differences = _compare_results(operator_result=operator_result, explicit_result=explicit_result)
    return ShadowComparisonResult(
        operator_result=operator_result,
        explicit_result=explicit_result,
        differences=differences,
    )


def format_shadow_result_lines(result: ShadowComparisonResult) -> list[str]:
    lines = ["shadow_mode: true", f"shadow_matched: {str(result.matched).lower()}"]
    lines.extend(result.operator_result.planning_result.summary.lines())
    if result.operator_result.manual_patch_output:
        lines.append("manual_patch_output:")
        for snippet in result.operator_result.manual_patch_output:
            lines.append(snippet.rstrip())
    if result.differences:
        lines.append("shadow_differences:")
        lines.extend(result.differences)
    return lines


def _explicit_request_from_operator_result(result: CompatibilityBridgeResult) -> ExplicitEntrypointRequest:
    context = result.context
    request = result.request
    return ExplicitEntrypointRequest(
        profile_name=context.profile.profile_name,
        repo_root=context.profile.repo_root,
        memory_root=context.profile.memory_root,
        backup_root=context.profile.backup_root,
        project_index_path=context.project_index_path,
        workspace_doc_path=context.workspace_doc_path,
        project_name=request.project_name,
        project_slug=request.project_slug,
        project_summary=request.project_summary,
        tech_stack=request.tech_stack,
        create_session_bootstrap=request.create_session_bootstrap,
        update_project_index=request.update_project_index,
        dry_run=request.dry_run,
        force=request.force,
        repo_visibility=request.repo_visibility,
        project_type=request.project_type,
        routing_keyword_strong=request.routing_keyword_strong,
        routing_keyword_weak=request.routing_keyword_weak,
        init_git=request.init_git,
        create_license=request.create_license,
        create_contributing=request.create_contributing,
        create_tests=request.create_tests,
        create_examples=request.create_examples,
        create_stack_metadata=request.create_stack_metadata,
        execute=False,
    )


def _compare_results(
    *,
    operator_result: CompatibilityBridgeResult,
    explicit_result: CompatibilityBridgeResult,
) -> tuple[str, ...]:
    differences: list[str] = []
    if operator_result.planning_result.summary.lines() != explicit_result.planning_result.summary.lines():
        differences.append("summary lines differ")
    if _action_signature(operator_result) != _action_signature(explicit_result):
        differences.append("planned action signature differs")
    if operator_result.planning_result.rendered_files != explicit_result.planning_result.rendered_files:
        differences.append("rendered file content differs")
    if operator_result.planning_result.index_update_plan.result != explicit_result.planning_result.index_update_plan.result:
        differences.append("project index result differs")
    if operator_result.manual_patch_output != explicit_result.manual_patch_output:
        differences.append("manual patch output differs")
    return tuple(differences)


def _action_signature(
    result: CompatibilityBridgeResult,
) -> tuple[tuple[str, str, str, tuple[str, ...], str | None, str | None, str | None], ...]:
    return tuple(
        (
            action.kind.value,
            action.target_kind.value,
            str(action.target_path),
            action.details,
            action.render_content,
            action.patch_content,
            action.expected_content,
        )
        for action in result.planning_result.actions
    )
