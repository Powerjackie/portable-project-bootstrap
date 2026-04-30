from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ProjectIndexParseError
from .models import OverallStatus, WorkspaceValidationResult
from .profile_loader import compatibility_profile_warning, load_workspace_context
from .project_index import load_project_index_document


def validate_workspace(
    *,
    workspace_root: Path,
    profile_name: str,
    profile_path: Path | None = None,
) -> WorkspaceValidationResult:
    resolved_paths = {"workspace_root": str(workspace_root)}
    problems: list[str] = []
    warnings: list[str] = []

    try:
        context = load_workspace_context(
            workspace_root=workspace_root,
            profile_name=profile_name,
            profile_path=profile_path,
        )
    except Exception as exc:  # fail-closed surface is reported structurally
        return WorkspaceValidationResult(
            status=OverallStatus.ERROR,
            problems=(str(exc),),
            warnings=(),
            resolved_paths=resolved_paths,
            next_steps=(
                "Fix the workspace profile or required workspace files before running bootstrap or router.",
            ),
        )

    resolved_paths.update(
        {
            "profile_name": context.profile.profile_name,
            "profile_path": str(context.resolved_profile_path) if context.resolved_profile_path else "unknown",
            "profile_source": context.resolved_profile_source or "unknown",
            "repo_root": str(context.profile.repo_root),
            "memory_root": str(context.profile.memory_root),
            "backup_root": str(context.profile.backup_root),
            "project_index_path": str(context.project_index_path),
            "workspace_doc_path": str(context.workspace_doc_path) if context.workspace_doc_path else "none",
        }
    )

    try:
        load_project_index_document(
            context.project_index_path,
            profile=context.profile,
            workspace_root=workspace_root,
        )
    except ProjectIndexParseError as exc:
        problems.append(str(exc))

    suite_repo_root = Path(__file__).resolve().parent.parent.parent
    package_root = Path(__file__).resolve().parent
    suite_overview_path = suite_repo_root / "docs" / "workspace-suite-overview.md"
    suite_entry_paths = {
        "suite_repo_root": suite_repo_root,
        "bootstrap_wrapper_module": package_root / "live_wrapper.py",
        "bootstrap_skill_caller_module": package_root / "skill_caller.py",
        "workspace_validator_module": package_root / "validator.py",
        "workspace_router_module": package_root / "router.py",
        "suite_overview_doc": suite_overview_path,
    }
    for key, path in suite_entry_paths.items():
        resolved_paths[key] = str(path)

    for key in (
        "bootstrap_wrapper_module",
        "bootstrap_skill_caller_module",
        "workspace_validator_module",
        "workspace_router_module",
    ):
        if not Path(resolved_paths[key]).is_file():
            problems.append(f"required suite entry is missing: {resolved_paths[key]}")

    if context.resolved_profile_source == "compatibility":
        warnings.append(compatibility_profile_warning())
    if not suite_overview_path.is_file():
        warnings.append(
            "suite overview documentation is missing at docs/workspace-suite-overview.md"
        )

    status = _status_from_issues(problems=problems, warnings=warnings)
    next_steps = _next_steps(status=status)
    return WorkspaceValidationResult(
        status=status,
        problems=tuple(problems),
        warnings=tuple(warnings),
        resolved_paths=resolved_paths,
        next_steps=next_steps,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate whether the current workspace/profile is ready for bootstrap or routing."
    )
    parser.add_argument("--workspace-root", required=True, help="Workspace root to validate.")
    parser.add_argument("--profile-name", required=True, help="Profile name to discover or validate.")
    parser.add_argument(
        "--profile-path",
        help="Optional explicit profile path. Overrides profile discovery when provided.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_workspace(
        workspace_root=Path(args.workspace_root),
        profile_name=args.profile_name,
        profile_path=Path(args.profile_path) if args.profile_path else None,
    )
    for line in result.lines():
        print(line)
    if result.status == OverallStatus.ERROR:
        if result.problems:
            print(f"error: {result.problems[0]}", file=sys.stderr)
        return 1
    return 0


def _status_from_issues(*, problems: list[str], warnings: list[str]) -> OverallStatus:
    if problems:
        return OverallStatus.ERROR
    if warnings:
        return OverallStatus.PARTIAL
    return OverallStatus.OK


def _next_steps(*, status: OverallStatus) -> tuple[str, ...]:
    if status == OverallStatus.ERROR:
        return (
            "Fix the reported profile or workspace issues before running bootstrap or router.",
        )
    return (
        "Run `python -m portable_project_bootstrap.router ...` for existing project entry.",
        "Run `project-bootstrap` or `python -m portable_project_bootstrap ...` for brand-new initialization.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
