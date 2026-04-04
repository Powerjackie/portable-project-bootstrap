from __future__ import annotations

import argparse
from pathlib import Path

from .direct_entry import run_explicit_entry
from .models import ExplicitEntrypointRequest
from .operator_cli import format_bridge_result_lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or execute a portable project bootstrap run.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--project-summary", required=True)
    parser.add_argument("--tech-stack", action="append", default=[])
    parser.add_argument("--profile-name", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--memory-root", required=True)
    parser.add_argument("--backup-root", required=True)
    parser.add_argument("--project-index-path", required=True)
    parser.add_argument("--workspace-start-here")
    parser.add_argument("--workspace-rules")
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
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Apply the already computed planning result to the filesystem.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_explicit_entry(
        ExplicitEntrypointRequest(
            profile_name=args.profile_name,
            repo_root=Path(args.repo_root),
            memory_root=Path(args.memory_root),
            backup_root=Path(args.backup_root),
            project_index_path=Path(args.project_index_path),
            workspace_start_here_path=Path(args.workspace_start_here) if args.workspace_start_here else None,
            workspace_rules_path=Path(args.workspace_rules) if args.workspace_rules else None,
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
    )
    for line in format_bridge_result_lines(result):
        print(line)
    return 0


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
