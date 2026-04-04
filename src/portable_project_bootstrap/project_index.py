from __future__ import annotations

import re
from pathlib import Path

from .errors import ProjectIndexParseError
from .models import ProjectIndexDocument, ProjectIndexRecord


_SECTION_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


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


def _parse_record(*, slug: str, block: str) -> ProjectIndexRecord:
    lines = block.splitlines()
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
