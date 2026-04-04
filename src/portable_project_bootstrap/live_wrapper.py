from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .bridge import run_compatibility_bridge
from .direct_entry import run_explicit_entry
from .errors import (
    BridgeError,
    ExecutionError,
    PlanningError,
    ProfileLoadError,
    ShadowModeError,
)
from .models import CompatibilityBridgeRequest, ExplicitEntrypointRequest
from .operator_cli import format_bridge_result_lines
from .profile_loader import load_workspace_context
from .shadow import format_shadow_result_lines, run_shadow_mode


MODE_ENV_VAR = "PORTABLE_PROJECT_BOOTSTRAP_MODE"
VALID_MODES = {"legacy", "shadow", "new"}
DEFAULT_MODE = "new"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guarded live wrapper for portable project bootstrap cutover."
    )
    parser.add_argument("--mode", choices=sorted(VALID_MODES))
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        mode = resolve_mode(cli_mode=args.mode, env=os.environ)
        if mode == "shadow":
            result = run_shadow_mode(_bridge_request(args=args, force_dry_run=True, force_execute=False))
            print(f"live_wrapper_mode: {mode}")
            for line in format_shadow_result_lines(result):
                print(line)
            return 0
        if mode == "new":
            result = run_compatibility_bridge(_bridge_request(args=args))
            print(f"live_wrapper_mode: {mode}")
            for line in format_bridge_result_lines(result):
                print(line)
            return 0
        result = run_explicit_entry(_explicit_request(args=args))
        print(f"live_wrapper_mode: {mode}")
        for line in format_bridge_result_lines(result):
            print(line)
        return 0
    except (BridgeError, ExecutionError, PlanningError, ProfileLoadError, ShadowModeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def resolve_mode(*, cli_mode: str | None, env: dict[str, str]) -> str:
    if cli_mode:
        return cli_mode
    env_mode = env.get(MODE_ENV_VAR, "").strip()
    if not env_mode:
        return DEFAULT_MODE
    if env_mode not in VALID_MODES:
        raise ValueError(
            f"invalid {MODE_ENV_VAR} value `{env_mode}`; expected one of: legacy, shadow, new"
        )
    return env_mode


def _bridge_request(
    *,
    args: argparse.Namespace,
    force_dry_run: bool | None = None,
    force_execute: bool | None = None,
) -> CompatibilityBridgeRequest:
    return CompatibilityBridgeRequest(
        workspace_root=Path(args.workspace_root),
        profile_name=args.profile_name,
        profile_path=Path(args.profile_path) if args.profile_path else None,
        project_name=args.project_name,
        project_slug=args.project_slug,
        project_summary=args.project_summary,
        tech_stack=tuple(_normalize_list(args.tech_stack)),
        create_session_bootstrap=args.create_session_bootstrap,
        update_project_index=args.update_project_index,
        dry_run=args.dry_run if force_dry_run is None else force_dry_run,
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
        execute=args.execute if force_execute is None else force_execute,
    )


def _explicit_request(*, args: argparse.Namespace) -> ExplicitEntrypointRequest:
    context = load_workspace_context(
        workspace_root=Path(args.workspace_root),
        profile_name=args.profile_name,
        profile_path=Path(args.profile_path) if args.profile_path else None,
    )
    return ExplicitEntrypointRequest(
        profile_name=context.profile.profile_name,
        repo_root=context.profile.repo_root,
        memory_root=context.profile.memory_root,
        backup_root=context.profile.backup_root,
        project_index_path=context.project_index_path,
        workspace_start_here_path=context.workspace_start_here_path,
        workspace_rules_path=context.workspace_rules_path,
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
