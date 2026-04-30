from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import ProjectIndexParseError
from .models import ProjectIndexDocument, ProjectIndexRecord, WorkspaceProfile
from .profile_loader import ProfileLoadError, expand_path


_SECTION_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


@dataclass(frozen=True)
class ProjectIndexComparison:
    changed_fields: tuple[str, ...] = ()
    path_conflict_fields: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_fields or self.path_conflict_fields)

    @property
    def all_reasons(self) -> tuple[str, ...]:
        return self.path_conflict_fields + self.changed_fields


def load_project_index_document(
    path: Path,
    *,
    profile: WorkspaceProfile | None = None,
    workspace_root: Path | None = None,
) -> ProjectIndexDocument:
    if not path.exists():
        raise ProjectIndexParseError(f"PROJECT_INDEX.md does not exist: {path}")
    if not path.is_file():
        raise ProjectIndexParseError(f"PROJECT_INDEX.md path must be a file: {path}")
    return parse_project_index_document(
        path.read_text(encoding="utf-8"),
        profile=profile,
        workspace_root=workspace_root,
    )


def parse_project_index_document(
    text: str,
    *,
    profile: WorkspaceProfile | None = None,
    workspace_root: Path | None = None,
) -> ProjectIndexDocument:
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        raise ProjectIndexParseError("PROJECT_INDEX.md could not be safely parsed")
    preamble = text[: matches[0].start()].rstrip()
    records: list[ProjectIndexRecord] = []
    for index, match in enumerate(matches):
        slug = match.group(1).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].rstrip()
        records.append(
            _parse_record(
                slug=slug,
                block=block,
                profile=profile,
                workspace_root=workspace_root,
            )
        )
    return ProjectIndexDocument(preamble=preamble, records=tuple(records))


def render_project_index_document(document: ProjectIndexDocument) -> str:
    body = "\n\n".join(record.raw_section.rstrip() for record in document.records)
    if document.preamble:
        return document.preamble.rstrip() + "\n\n" + body + "\n"
    return body + "\n"


def upsert_project_index_record(
    document: ProjectIndexDocument,
    *,
    project_slug: str,
    rendered_entry: str,
) -> str:
    records = {record.project_slug: record.raw_section.rstrip() for record in document.records}
    records[project_slug] = rendered_entry.rstrip()
    body = "\n\n".join(records[slug] for slug in sorted(records, key=str.lower))
    if document.preamble:
        return document.preamble.rstrip() + "\n\n" + body + "\n"
    return body + "\n"


def parse_project_index_record_block(block: str) -> ProjectIndexRecord:
    document = parse_project_index_document(block.strip() + "\n")
    if len(document.records) != 1:
        raise ProjectIndexParseError("expected exactly one project index record block")
    return document.records[0]


def compare_project_index_records(
    *,
    existing: ProjectIndexRecord,
    desired: ProjectIndexRecord,
) -> ProjectIndexComparison:
    if existing.project_slug != desired.project_slug:
        raise ProjectIndexParseError("cannot compare project index records with different slugs")

    path_conflict_fields: list[str] = []
    changed_fields: list[str] = []

    if existing.canonical_repo_paths != desired.canonical_repo_paths:
        path_conflict_fields.append("canonical_repo_paths")
    if existing.memory_root != desired.memory_root:
        path_conflict_fields.append("memory_root")

    for field_name in (
        "purpose",
        "read_first_files",
        "optional_files",
        "strong_match_signals",
        "weak_hints",
        "summary",
        "route_type",
        "remote_host",
    ):
        if not _field_values_match(
            field_name,
            getattr(existing, field_name),
            getattr(desired, field_name),
        ):
            changed_fields.append(field_name)

    return ProjectIndexComparison(
        changed_fields=tuple(changed_fields),
        path_conflict_fields=tuple(path_conflict_fields),
    )


def _parse_record(
    *,
    slug: str,
    block: str,
    profile: WorkspaceProfile | None,
    workspace_root: Path | None,
) -> ProjectIndexRecord:
    lines = block.splitlines()
    if any(line.startswith("- Path:") for line in lines):
        return _parse_compact_record(
            slug=slug,
            block=block,
            lines=lines,
            profile=profile,
            workspace_root=workspace_root,
        )
    return _parse_verbose_record(
        slug=slug,
        block=block,
        lines=lines,
        profile=profile,
        workspace_root=workspace_root,
    )


def _parse_verbose_record(
    *,
    slug: str,
    block: str,
    lines: list[str],
    profile: WorkspaceProfile | None,
    workspace_root: Path | None,
) -> ProjectIndexRecord:
    purpose = _extract_scalar(lines, "- Purpose:")
    canonical_repo_paths = _extract_path_list(
        lines,
        "- Canonical repo / runtime surface:",
        profile=profile,
        workspace_root=workspace_root,
    )
    backup_paths = _extract_path_list(
        lines,
        "- Backup path:",
        profile=profile,
        workspace_root=workspace_root,
    )
    memory_roots = _extract_path_list(
        lines,
        "- Memory root:",
        profile=profile,
        workspace_root=workspace_root,
    )
    read_first_files = _extract_path_list(
        lines,
        "- Read-first files:",
        profile=profile,
        workspace_root=workspace_root,
    )
    optional_files = _extract_path_list(
        lines,
        "- Optional files:",
        profile=profile,
        workspace_root=workspace_root,
    )
    strong_match_signals = _extract_list(lines, "- Strong match signals:")
    weak_hints = _extract_list(lines, "- Weak hints only:")
    summary = _extract_scalar(lines, "- Summary:")
    normalized_route_type, remote_host = _parse_route_type(_extract_optional_scalar(lines, "- Route-Type:"))
    return ProjectIndexRecord(
        project_slug=slug,
        purpose=purpose,
        canonical_repo_paths=canonical_repo_paths,
        backup_paths=backup_paths,
        memory_root=memory_roots[0] if memory_roots else None,
        read_first_files=read_first_files,
        optional_files=optional_files,
        strong_match_signals=strong_match_signals,
        weak_hints=weak_hints,
        summary=summary,
        raw_section=block,
        project_names=_project_names_from_signals(strong_match_signals),
        route_type=normalized_route_type,
        remote_host=remote_host,
    )


def _parse_compact_record(
    *,
    slug: str,
    block: str,
    lines: list[str],
    profile: WorkspaceProfile | None,
    workspace_root: Path | None,
) -> ProjectIndexRecord:
    path_line = _extract_scalar(lines, "- Path:")
    if " | Memory: " not in path_line:
        raise ProjectIndexParseError("compact PROJECT_INDEX path line must include `| Memory:`")
    repo_text, memory_text = path_line.split(" | Memory: ", 1)
    read_first = (
        _expand_path_value(
            _normalize_item(_extract_scalar(lines, "- Read-first:")),
            profile=profile,
            workspace_root=workspace_root,
        ),
    )
    signals = _split_compact_signals(_extract_scalar(lines, "- Signals:"))
    note = _extract_optional_scalar(lines, "- Note:")
    normalized_route_type, remote_host = _parse_route_type(_extract_optional_scalar(lines, "- Route-Type:"))
    return ProjectIndexRecord(
        project_slug=slug,
        purpose="",
        canonical_repo_paths=(
            _expand_path_value(
                _normalize_item(repo_text.strip()),
                profile=profile,
                workspace_root=workspace_root,
            ),
        ),
        backup_paths=(),
        memory_root=_expand_path_value(
            _normalize_item(memory_text.strip()),
            profile=profile,
            workspace_root=workspace_root,
        ),
        read_first_files=read_first,
        optional_files=(),
        strong_match_signals=signals,
        weak_hints=(),
        summary=note or "",
        raw_section=block,
        project_names=_project_names_from_signals(signals),
        route_type=normalized_route_type,
        remote_host=remote_host,
    )


def _extract_scalar(lines: list[str], header: str) -> str:
    prefix = f"{header} "
    for line in lines:
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if value:
                return value
    raise ProjectIndexParseError(f"PROJECT_INDEX.md is missing required field `{header}`")


def _extract_list(lines: list[str], header: str) -> tuple[str, ...]:
    try:
        start_index = lines.index(header)
    except ValueError as exc:
        raise ProjectIndexParseError(f"PROJECT_INDEX.md is missing required field `{header}`") from exc
    values: list[str] = []
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        if line.startswith("- "):
            break
        if line.startswith("  - "):
            values.append(_normalize_item(line[4:].strip()))
        elif line.strip():
            raise ProjectIndexParseError(
                f"PROJECT_INDEX.md list field `{header}` has unsupported line shape: {line}"
            )
        index += 1
    if not values:
        raise ProjectIndexParseError(f"PROJECT_INDEX.md list field `{header}` must not be empty")
    return tuple(values)


def _extract_path_list(
    lines: list[str],
    header: str,
    *,
    profile: WorkspaceProfile | None,
    workspace_root: Path | None,
) -> tuple[str, ...]:
    values = _extract_list(lines, header)
    return tuple(
        _expand_path_value(value, profile=profile, workspace_root=workspace_root) for value in values
    )


def _normalize_item(value: str) -> str:
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def _expand_path_value(
    value: str,
    *,
    profile: WorkspaceProfile | None,
    workspace_root: Path | None,
) -> str:
    if profile is None or workspace_root is None or "${" not in value:
        return value
    try:
        return expand_path(value, profile, workspace_root=workspace_root)
    except ProfileLoadError as exc:
        raise ProjectIndexParseError(str(exc)) from exc


def _parse_route_type(value: str | None) -> tuple[str, str | None]:
    if value is None:
        return "local", None
    cleaned = _normalize_item(value).strip()
    if not cleaned or cleaned == "local":
        return "local", None
    if cleaned.startswith("ssh:"):
        host = cleaned.split(":", 1)[1].strip()
        if not host:
            raise ProjectIndexParseError("Route-Type `ssh:` must include a non-empty host alias")
        return "ssh", host
    raise ProjectIndexParseError(
        "Route-Type must be `local` or `ssh:<host_alias>`"
    )


def _project_names_from_signals(signals: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for signal in signals:
        for match in re.finditer(r"project name `([^`]+)`", signal, flags=re.IGNORECASE):
            project_name = match.group(1).strip()
            if project_name and project_name.casefold() not in seen:
                seen.add(project_name.casefold())
                values.append(project_name)
    return tuple(values)


def _extract_optional_scalar(lines: list[str], header: str) -> str | None:
    prefix = f"{header} "
    for line in lines:
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            return value or None
    return None


def _split_compact_signals(value: str) -> tuple[str, ...]:
    signals = tuple(_normalize_item(part.strip()) for part in value.split(",") if part.strip())
    if not signals:
        raise ProjectIndexParseError("compact PROJECT_INDEX signals must not be empty")
    return signals


def _field_values_match(field_name: str, left, right) -> bool:
    if field_name in {"strong_match_signals", "weak_hints"}:
        return _normalized_unordered_values(left) == _normalized_unordered_values(right)
    return left == right


def _normalized_unordered_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted((value.strip() for value in values if value.strip().casefold() != "none"), key=str.casefold))
