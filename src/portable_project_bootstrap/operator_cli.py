from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bridge import run_compatibility_bridge
from .errors import BridgeError, ExecutionError, PlanningError, ProfileLoadError, ShadowModeError
from .models import CompatibilityBridgeRequest, CompatibilityBridgeResult
from .shadow import format_shadow_result_lines, run_shadow_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operator-facing entrypoint for portable project bootstrap runs."
    )
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--profile-name", required=True)
    parser.add_argument("--profile-path")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--project-summary", required=True)
    parser.add_argument("--tech-stack", action="append", default=[])
    parser.add_argument("--create-session-bootstrap", action="store_true", default=False)
    parser.add_argument("--update-project-index", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--force", action="store_true", default=False)
    parser.add_argument("--repo-visibility", default="private")
    parser.add_argument("--project-type", default="generic")
    parser.add_argument("--routing-keyword-strong", action="append", default=[])
    parser.add_argument("--routing-keyword-weak", action="append", default=[])
    parser.add_argument("--init-git", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--create-license", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--create-contributing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--create-tests", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--create-examples", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--create-stack-metadata", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--shadow-mode", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bridge_request = CompatibilityBridgeRequest(
        workspace_root=Path(args.workspace_root),
        profile_name=args.profile_name,
        profile_path=Path(args.profile_path) if args.profile_path else None,
        project_name=args.project_name,
        project_slug=args.project_slug,
        project_summary=args.project_summary,
        tech_stack=tuple(_normalize_list(args.tech_stack)),
        create_session_bootstrap=args.create_session_bootstrap,
        update_project_index=args.update_project_index,
        dry_run=args.dry_run,
        force=args.force,
        repo_visibility=args.repo_visibility,
        project_type=args.project_type,
        routing_keyword_strong=tuple(_normalize_list(args.routing_keyword_strong)),
        routing_keyword_weak=tuple(_normalize_list(args.routing_keyword_weak)),
        init_git=args.init_git,
        create_license=args.create_license,
        create_contributing=args.create_contributing,
        create_tests=args.create_tests,
        create_examples=args.create_examples,
        create_stack_metadata=args.create_stack_metadata,
        execute=args.execute,
    )
    try:
        if args.shadow_mode:
            result = run_shadow_mode(bridge_request)
            for line in format_shadow_result_lines(result):
                print(line)
            return 0
        result = run_compatibility_bridge(bridge_request)
    except (BridgeError, ExecutionError, PlanningError, ProfileLoadError, ShadowModeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for line in format_bridge_result_lines(result):
        print(line)
    return 0


def format_bridge_result_lines(result: CompatibilityBridgeResult) -> list[str]:
    lines = list(result.planning_result.summary.lines())
    if result.execution_result is not None:
        lines.extend(
            [
                f"execution_dry_run: {str(result.execution_result.dry_run).lower()}",
                f"project_index_status: {result.execution_result.project_index_status}",
                f"project_index_message: {result.execution_result.project_index_message}",
                f"bootstrap_log_status: {result.execution_result.bootstrap_log_status}",
                f"bootstrap_log_message: {result.execution_result.bootstrap_log_message}",
            ]
        )
    if result.manual_patch_output:
        lines.append("manual_patch_output:")
        for snippet in result.manual_patch_output:
            lines.append(snippet.rstrip())
    return lines


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        for piece in value.split(","):
            item = piece.strip()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
    return normalized
