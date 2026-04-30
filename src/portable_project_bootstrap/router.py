from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ProfileLoadError, ProjectIndexParseError
from .models import (
    OverallStatus,
    RouteCandidate,
    WorkspaceRouteQuery,
    WorkspaceRouteResult,
)
from .profile_loader import (
    compatibility_profile_warning,
    load_workspace_context,
    normalize_path_for_compare,
)
from .project_index import load_project_index_document


def route_workspace(
    *,
    workspace_root: Path,
    profile_name: str,
    profile_path: Path | None = None,
    query: WorkspaceRouteQuery,
) -> WorkspaceRouteResult:
    resolved_paths = {"workspace_root": str(workspace_root)}
    warnings: list[str] = []
    try:
        context = load_workspace_context(
            workspace_root=workspace_root,
            profile_name=profile_name,
            profile_path=profile_path,
        )
    except ProfileLoadError as exc:
        return WorkspaceRouteResult(
            status=OverallStatus.ERROR,
            problems=(str(exc),),
            next_steps=("Fix the workspace profile before attempting to route an existing project.",),
            resolved_paths=resolved_paths,
        )

    resolved_paths.update(
        {
            "profile_name": context.profile.profile_name,
            "profile_path": str(context.resolved_profile_path) if context.resolved_profile_path else "unknown",
            "profile_source": context.resolved_profile_source or "unknown",
            "project_index_path": str(context.project_index_path),
        }
    )
    if context.resolved_profile_source == "compatibility":
        warnings.append(compatibility_profile_warning())

    try:
        document = load_project_index_document(
            context.project_index_path,
            profile=context.profile,
            workspace_root=workspace_root,
        )
    except ProjectIndexParseError as exc:
        return WorkspaceRouteResult(
            status=OverallStatus.ERROR,
            problems=(str(exc),),
            warnings=tuple(warnings),
            next_steps=("Repair PROJECT_INDEX.md before attempting to route an existing project.",),
            resolved_paths=resolved_paths,
        )

    candidates = list(document.records)
    reasons: dict[str, list[str]] = {record.project_slug: [] for record in candidates}

    candidates, error = _apply_exact_filter(
        candidates,
        reasons,
        query.project_slug,
        "exact slug match",
        lambda record, value: record.project_slug == value,
        "no project matched the requested project_slug",
    )
    if error:
        return _error_route_result(error, warnings, resolved_paths)

    candidates, error = _apply_exact_filter(
        candidates,
        reasons,
        query.project_name,
        "exact project name match",
        lambda record, value: value.casefold() in {name.casefold() for name in record.project_names},
        "no project matched the requested project_name",
    )
    if error:
        return _error_route_result(error, warnings, resolved_paths)

    candidates, error = _apply_path_filter(
        candidates,
        reasons,
        query.repo_path,
        "exact repo path match",
        lambda record, value: any(_same_path_text(path, value) for path in record.canonical_repo_paths),
        "no project matched the requested repo_path",
    )
    if error:
        return _error_route_result(error, warnings, resolved_paths)

    candidates, error = _apply_path_filter(
        candidates,
        reasons,
        query.memory_path,
        "exact memory path match",
        lambda record, value: record.memory_root is not None and _same_path_text(record.memory_root, value),
        "no project matched the requested memory_path",
    )
    if error:
        return _error_route_result(error, warnings, resolved_paths)

    if query.route_signal is not None:
        strong_matches = [
            record for record in candidates if any(_signal_matches(signal, query.route_signal) for signal in record.strong_match_signals)
        ]
        if strong_matches:
            candidates = strong_matches
            for record in candidates:
                reasons[record.project_slug].append("strong route signal match")
                if any(_signal_matches(signal, query.route_signal) for signal in record.weak_hints):
                    reasons[record.project_slug].append("weak hint match")
        elif not reasons_with_exact_match(reasons, candidates):
            return _error_route_result(
                "no project matched the provided route signal strongly enough to route safely",
                warnings,
                resolved_paths,
            )

    if not candidates:
        return _error_route_result(
            "no project could be routed from the provided workspace context and route query",
            warnings,
            resolved_paths,
        )

    route_candidates = tuple(_to_route_candidate(record, reasons[record.project_slug]) for record in candidates)
    if len(route_candidates) > 1:
        return WorkspaceRouteResult(
            status=OverallStatus.PARTIAL,
            candidates=route_candidates,
            ambiguity_reason="multiple projects matched the provided routing inputs; choose one explicitly",
            warnings=tuple(warnings),
            next_steps=("Narrow the query with an exact slug, project name, repo path, or memory path.",),
            resolved_paths=resolved_paths,
        )

    matched = route_candidates[0]
    return WorkspaceRouteResult(
        status=OverallStatus.OK if not warnings else OverallStatus.PARTIAL,
        matched_project=matched,
        candidates=route_candidates,
        warnings=tuple(warnings),
        next_steps=tuple(
            [f"Read `{path}` first." for path in matched.read_first_files]
            or ("Read the project memory PROJECT.md file first.",)
        ),
        resolved_paths=resolved_paths,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Route an existing workspace project without invoking brand-new bootstrap."
    )
    parser.add_argument("--workspace-root", required=True, help="Workspace root that owns the project index.")
    parser.add_argument("--profile-name", required=True, help="Profile name to discover or validate.")
    parser.add_argument(
        "--profile-path",
        help="Optional explicit profile path. Overrides profile discovery when provided.",
    )
    parser.add_argument("--project-slug", help="Exact project slug to route.")
    parser.add_argument("--project-name", help="Exact project name to route.")
    parser.add_argument("--route-signal", help="Free-form routing signal text.")
    parser.add_argument("--repo-path", help="Exact repo path to route.")
    parser.add_argument("--memory-path", help="Exact memory path to route.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        query = WorkspaceRouteQuery(
            project_slug=args.project_slug,
            project_name=args.project_name,
            route_signal=args.route_signal,
            repo_path=Path(args.repo_path) if args.repo_path else None,
            memory_path=Path(args.memory_path) if args.memory_path else None,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    result = route_workspace(
        workspace_root=Path(args.workspace_root),
        profile_name=args.profile_name,
        profile_path=Path(args.profile_path) if args.profile_path else None,
        query=query,
    )
    for line in result.lines():
        print(line)
    if result.status == OverallStatus.ERROR:
        if result.problems:
            print(f"error: {result.problems[0]}", file=sys.stderr)
        return 1
    return 0


def _apply_exact_filter(
    candidates,
    reasons,
    value,
    reason_label,
    matcher,
    error_message,
):
    if value is None:
        return candidates, None
    filtered = [record for record in candidates if matcher(record, value.strip())]
    if not filtered:
        return candidates, error_message
    for record in filtered:
        reasons[record.project_slug].append(reason_label)
    return filtered, None


def _apply_path_filter(
    candidates,
    reasons,
    value,
    reason_label,
    matcher,
    error_message,
):
    if value is None:
        return candidates, None
    filtered = [record for record in candidates if matcher(record, value)]
    if not filtered:
        return candidates, error_message
    for record in filtered:
        reasons[record.project_slug].append(reason_label)
    return filtered, None


def _error_route_result(
    problem: str,
    warnings: list[str],
    resolved_paths: dict[str, str],
) -> WorkspaceRouteResult:
    return WorkspaceRouteResult(
        status=OverallStatus.ERROR,
        problems=(problem,),
        warnings=tuple(warnings),
        next_steps=("Refine the route query or repair the workspace context before retrying.",),
        resolved_paths=resolved_paths,
    )


def _to_route_candidate(record, reason_labels: list[str]) -> RouteCandidate:
    return RouteCandidate(
        project_slug=record.project_slug,
        project_name=record.project_names[0] if record.project_names else None,
        repo_path=record.canonical_repo_paths[0] if record.canonical_repo_paths else None,
        memory_path=record.memory_root,
        read_first_files=record.read_first_files,
        summary=record.summary,
        match_reasons=tuple(dict.fromkeys(reason_labels)),
        route_type="remote-ssh" if record.route_type == "ssh" else "local",
        remote_host=record.remote_host,
    )


def _same_path_text(left: str, right: Path) -> bool:
    return _normalize_path_text(left) == _normalize_path_text(str(right))


def _normalize_path_text(value: str) -> str:
    return normalize_path_for_compare(value)


def _signal_matches(candidate_signal: str, query_value: str) -> bool:
    candidate = candidate_signal.casefold()
    query = query_value.strip().casefold()
    return bool(query) and (query in candidate or candidate in query)


def reasons_with_exact_match(reasons, candidates) -> bool:
    exact_labels = {
        "exact slug match",
        "exact project name match",
        "exact repo path match",
        "exact memory path match",
    }
    return any(
        any(label in exact_labels for label in reasons.get(record.project_slug, ()))
        for record in candidates
    )


if __name__ == "__main__":
    raise SystemExit(main())
