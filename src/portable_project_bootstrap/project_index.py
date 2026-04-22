from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import ProjectIndexParseError
from .models import ProjectIndexDocument, ProjectIndexRecord


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


def load_project_index_document(path: Path) -> ProjectIndexDocument:
    if not path.exists():
        raise ProjectIndexParseError(f"PROJECT_INDEX.md does not exist: {path}")
    if not path.is_file():
        raise ProjectIndexParseError(f"PROJECT_INDEX.md path must be a file: {path}")
    return parse_project_index_document(path.read_text(encoding="utf-8"))


def parse_project_index_document(text: str) -> ProjectIndexDocument:
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
        records.append(_parse_record(slug=slug, block=block))
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


def _parse_record(*, slug: str, block: str) -> ProjectIndexRecord:
    lines = block.splitlines()
    if any(line.startswith("- Path:") for line in lines):
        return _parse_compact_record(slug=slug, block=block, lines=lines)
    return _parse_verbose_record(slug=slug, block=block, lines=lines)


def _parse_verbose_record(*, slug: str, block: str, lines: list[str]) -> ProjectIndexRecord:
    purpose = _extract_scalar(lines, "- Purpose:")
    canonical_repo_paths = _extract_list(lines, "- Canonical repo / runtime surface:")
    backup_paths = _extract_list(lines, "- Backup path:")
    memory_roots = _extract_list(lines, "- Memory root:")
    read_first_files = _extract_list(lines, "- Read-first files:")
    optional_files = _extract_list(lines, "- Optional files:")
    strong_match_signals = _extract_list(lines, "- Strong match signals:")
    weak_hints = _extract_list(lines, "- Weak hints only:")
    summary = _extract_scalar(lines, "- Summary:")
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
    )


def _parse_compact_record(*, slug: str, block: str, lines: list[str]) -> ProjectIndexRecord:
    path_line = _extract_scalar(lines, "- Path:")
    if " | Memory: " not in path_line:
        raise ProjectIndexParseError("compact PROJECT_INDEX path line must include `| Memory:`")
    repo_text, memory_text = path_line.split(" | Memory: ", 1)
    read_first = (_normalize_item(_extract_scalar(lines, "- Read-first:")),)
    signals = _split_compact_signals(_extract_scalar(lines, "- Signals:"))
    note = _extract_optional_scalar(lines, "- Note:")
    return ProjectIndexRecord(
        project_slug=slug,
        purpose="",
        canonical_repo_paths=(_normalize_item(repo_text.strip()),),
        backup_paths=(),
        memory_root=_normalize_item(memory_text.strip()),
        read_first_files=read_first,
        optional_files=(),
        strong_match_signals=signals,
        weak_hints=(),
        summary=note or "",
        raw_section=block,
        project_names=_project_names_from_signals(signals),
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


def _normalize_item(value: str) -> str:
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


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
