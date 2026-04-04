from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .live_wrapper import VALID_MODES, main as live_wrapper_main


WORKSPACE_ROOT_ENV_VAR = "PORTABLE_PROJECT_BOOTSTRAP_WORKSPACE_ROOT"
PROFILE_NAME_ENV_VAR = "PORTABLE_PROJECT_BOOTSTRAP_PROFILE"
DEFAULT_WORKSPACE_ROOT = None
DEFAULT_PROFILE_NAME = "default"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compatibility caller for the project-bootstrap skill surface."
    )
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--project-summary", required=True)
    parser.add_argument("--tech-stack", action="append", default=[])
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
    parser.add_argument("--create-session-bootstrap", action="store_true", default=False)
    parser.add_argument("--update-project-index", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--force", action="store_true", default=False)
    parser.add_argument("--workspace-root")
    parser.add_argument("--profile-name", default=_default_profile_name())
    parser.add_argument("--profile-path")
    parser.add_argument("--mode", choices=sorted(VALID_MODES))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return live_wrapper_main(_build_live_wrapper_argv(args))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _build_live_wrapper_argv(args: argparse.Namespace) -> list[str]:
    forwarded = [
        "--workspace-root",
        _resolved_workspace_root(args.workspace_root),
        "--profile-name",
        args.profile_name,
        "--project-name",
        args.project_name,
        "--project-slug",
        args.project_slug,
        "--project-summary",
        args.project_summary,
        "--repo-visibility",
        args.repo_visibility,
        "--project-type",
        args.project_type,
    ]
    if args.mode:
        forwarded.extend(["--mode", args.mode])
    if args.profile_path:
        forwarded.extend(["--profile-path", args.profile_path])
    for value in args.tech_stack:
        forwarded.extend(["--tech-stack", value])
    for value in args.routing_keyword_strong:
        forwarded.extend(["--routing-keyword-strong", value])
    for value in args.routing_keyword_weak:
        forwarded.extend(["--routing-keyword-weak", value])
    if not args.init_git:
        forwarded.append("--no-init-git")
    if not args.create_license:
        forwarded.append("--no-create-license")
    if not args.create_contributing:
        forwarded.append("--no-create-contributing")
    if not args.create_tests:
        forwarded.append("--no-create-tests")
    if not args.create_examples:
        forwarded.append("--no-create-examples")
    if not args.create_stack_metadata:
        forwarded.append("--no-create-stack-metadata")
    if args.create_session_bootstrap:
        forwarded.append("--create-session-bootstrap")
    if not args.update_project_index:
        forwarded.append("--no-update-project-index")
    if args.force:
        forwarded.append("--force")
    if args.dry_run:
        forwarded.append("--dry-run")
    else:
        forwarded.append("--execute")
    return forwarded


def _resolved_workspace_root(configured_value: str | None) -> str:
    if configured_value:
        return configured_value
    configured = os.environ.get(WORKSPACE_ROOT_ENV_VAR)
    if configured:
        return configured
    discovered = _discover_workspace_root(Path.cwd())
    if discovered is not None:
        return str(discovered)
    raise ValueError(
        "workspace root is required; pass --workspace-root, set "
        f"{WORKSPACE_ROOT_ENV_VAR}, or run from inside a workspace root that contains .agent-memory"
    )


def _default_profile_name() -> str:
    return os.environ.get(PROFILE_NAME_ENV_VAR, DEFAULT_PROFILE_NAME)


def _discover_workspace_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".agent-memory").is_dir():
            return candidate
    return None
