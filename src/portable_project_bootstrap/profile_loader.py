from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .errors import ProfileLoadError
from .models import WorkspaceContext, WorkspaceProfile


PRIMARY_PROFILE_DIR = Path(".agent-memory") / "machine-profiles"
COMPATIBILITY_PROFILE_PATH = Path(".codex") / "workspace-profile" / "PROFILE.json"
CURRENT_PROFILE_SCHEMA_VERSION = 1
COMPATIBILITY_SUPPORT_END_DATE = "2026-06-30"
_PATH_TOKEN_RE = re.compile(r"\$\{([^}]+)\}")


def discover_profile_path(workspace_root: Path, profile_name: str) -> Path:
    path, _ = discover_profile_path_with_source(workspace_root, profile_name)
    return path


def discover_profile_path_with_source(workspace_root: Path, profile_name: str) -> tuple[Path, str]:
    _validate_workspace_root(workspace_root)
    cleaned_name = profile_name.strip()
    if not cleaned_name:
        raise ProfileLoadError("profile_name must not be empty")
    primary_path = workspace_root / PRIMARY_PROFILE_DIR / f"{cleaned_name}.json"
    if primary_path.exists():
        if not primary_path.is_file():
            raise ProfileLoadError(f"profile path must be a file: {primary_path}")
        return primary_path, "primary"
    compatibility_path = workspace_root / COMPATIBILITY_PROFILE_PATH
    if compatibility_path.exists():
        if not compatibility_path.is_file():
            raise ProfileLoadError(f"profile path must be a file: {compatibility_path}")
        return compatibility_path, "compatibility"
    raise ProfileLoadError(
        "profile file does not exist in either supported location: "
        f"{primary_path} or {compatibility_path}"
    )


def compatibility_profile_warning() -> str:
    return (
        "compatibility profile path is in use; prefer the primary "
        "`.agent-memory/machine-profiles/<profile>.json` path. "
        f"This compatibility path is supported only through {COMPATIBILITY_SUPPORT_END_DATE}."
    )


def normalize_path_for_compare(value: str) -> str:
    """Normalize a path-like string for cross-platform comparison only."""
    if not value:
        return ""
    return os.path.normpath(str(value)).casefold()


def expand_path(
    value: str,
    profile: WorkspaceProfile,
    *,
    workspace_root: Path,
) -> str:
    """Expand `${repo_root}` / `${memory_root}` / `${backup_root}` / `${workspace_root}` tokens."""
    if not isinstance(value, str) or not value.strip():
        raise ProfileLoadError("path value must be a non-empty string")
    replacements = {
        "repo_root": profile.repo_root.as_posix(),
        "memory_root": profile.memory_root.as_posix(),
        "backup_root": profile.backup_root.as_posix(),
        "workspace_root": workspace_root.as_posix(),
    }

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in replacements:
            raise ProfileLoadError(f"unsupported path token `{token}`")
        return replacements[token]

    return _PATH_TOKEN_RE.sub(replace_token, value.strip())


def load_workspace_profile(
    *,
    workspace_root: Path,
    profile_name: str,
    profile_path: Path | None = None,
) -> WorkspaceProfile:
    resolved_profile_path, _ = resolve_profile_path(
        workspace_root=workspace_root,
        profile_name=profile_name,
        profile_path=profile_path,
    )
    document = _load_profile_document(resolved_profile_path)
    return WorkspaceProfile(
        profile_name=_required_string(document, "profile_name", expected=profile_name),
        schema_version=_required_schema_version(document),
        repo_root=_required_absolute_dir_path(document, "repo_root"),
        memory_root=_required_absolute_dir_path(document, "memory_root"),
        backup_root=_required_absolute_dir_path(document, "backup_root"),
        memory_mode=_optional_memory_mode(document),
    )


def load_workspace_context(
    *,
    workspace_root: Path,
    profile_name: str,
    profile_path: Path | None = None,
) -> WorkspaceContext:
    resolved_profile_path, resolved_profile_source = resolve_profile_path(
        workspace_root=workspace_root,
        profile_name=profile_name,
        profile_path=profile_path,
    )
    profile = load_workspace_profile(
        workspace_root=workspace_root,
        profile_name=profile_name,
        profile_path=resolved_profile_path,
    )
    document = _load_profile_document(resolved_profile_path)
    project_index_path = _optional_absolute_file_path(
        document,
        "project_index_path",
        fallback=profile.memory_root / "PROJECT_INDEX.md",
    )
    workspace_doc_path = _workspace_doc_path(document=document, memory_root=profile.memory_root)
    return WorkspaceContext(
        profile=profile,
        project_index_path=project_index_path,
        workspace_doc_path=workspace_doc_path,
        resolved_profile_path=resolved_profile_path,
        resolved_profile_source=resolved_profile_source,
    )


def resolve_profile_path(
    *,
    workspace_root: Path,
    profile_name: str,
    profile_path: Path | None = None,
) -> tuple[Path, str]:
    _validate_workspace_root(workspace_root)
    cleaned_name = profile_name.strip()
    if not cleaned_name:
        raise ProfileLoadError("profile_name must not be empty")
    if profile_path is not None:
        if not profile_path.is_absolute():
            raise ProfileLoadError("profile_path must be an absolute path")
        if not profile_path.exists():
            raise ProfileLoadError(f"profile file does not exist: {profile_path}")
        if not profile_path.is_file():
            raise ProfileLoadError(f"profile path must be a file: {profile_path}")
        return profile_path, "explicit"
    return discover_profile_path_with_source(workspace_root, cleaned_name)


def _validate_workspace_root(workspace_root: Path) -> None:
    if not workspace_root.exists():
        raise ProfileLoadError(f"workspace_root does not exist: {workspace_root}")
    if not workspace_root.is_dir():
        raise ProfileLoadError(f"workspace_root must be a directory: {workspace_root}")


def _load_profile_document(profile_path: Path) -> dict[str, object]:
    if not profile_path.exists():
        raise ProfileLoadError(f"profile file does not exist: {profile_path}")
    if not profile_path.is_file():
        raise ProfileLoadError(f"profile path must be a file: {profile_path}")
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileLoadError(f"profile file is not valid JSON: {profile_path}") from exc
    if not isinstance(data, dict):
        raise ProfileLoadError(f"profile document must be a JSON object: {profile_path}")
    return data


def _required_string(document: dict[str, object], key: str, *, expected: str | None = None) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileLoadError(f"profile field `{key}` must be a non-empty string")
    cleaned = value.strip()
    if expected is not None and cleaned != expected:
        raise ProfileLoadError(f"profile field `{key}` does not match requested profile name")
    return cleaned


def _required_schema_version(document: dict[str, object]) -> int:
    value = document.get("schema_version")
    if not isinstance(value, int):
        raise ProfileLoadError("profile field `schema_version` must be an integer")
    if value != CURRENT_PROFILE_SCHEMA_VERSION:
        raise ProfileLoadError(
            f"unsupported profile schema_version `{value}`; expected `{CURRENT_PROFILE_SCHEMA_VERSION}`"
        )
    return value


def _required_absolute_dir_path(document: dict[str, object], key: str) -> Path:
    raw_value = _required_string(document, key)
    path = Path(raw_value)
    if not path.is_absolute():
        raise ProfileLoadError(f"profile field `{key}` must be an absolute path")
    if not path.exists():
        raise ProfileLoadError(f"profile directory does not exist for `{key}`: {path}")
    if not path.is_dir():
        raise ProfileLoadError(f"profile field `{key}` must point to a directory: {path}")
    return path


def _optional_absolute_file_path(document: dict[str, object], key: str, *, fallback: Path) -> Path:
    raw_value = document.get(key)
    path = fallback
    if raw_value is not None:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ProfileLoadError(f"profile field `{key}` must be a non-empty string when provided")
        path = Path(raw_value.strip())
    if not path.is_absolute():
        raise ProfileLoadError(f"profile field `{key}` must resolve to an absolute path")
    if not path.exists():
        raise ProfileLoadError(f"required workspace file is missing for `{key}`: {path}")
    if not path.is_file():
        raise ProfileLoadError(f"profile field `{key}` must point to a file: {path}")
    return path


def _optional_memory_mode(document: dict[str, object]) -> str:
    value = document.get("memory_mode", "inline")
    if not isinstance(value, str) or not value.strip():
        raise ProfileLoadError("profile field `memory_mode` must be a non-empty string when provided")
    cleaned = value.strip()
    if cleaned not in {"inline", "external"}:
        raise ProfileLoadError("profile field `memory_mode` must be one of: inline, external")
    return cleaned


def _workspace_doc_path(*, document: dict[str, object], memory_root: Path) -> Path:
    explicit_path = document.get("workspace_doc_path")
    if explicit_path is not None:
        return _optional_absolute_file_path(document, "workspace_doc_path", fallback=memory_root / "WORKSPACE.md")

    # Keep legacy workspace document names only during the current migration window.
    candidates = (
        memory_root / "WORKSPACE.md",
        memory_root / "WORKSPACE_RULES.md",
        memory_root / "WORKSPACE_START_HERE.md",
    )
    for candidate in candidates:
        if candidate.exists():
            if not candidate.is_file():
                raise ProfileLoadError(f"workspace document path must point to a file: {candidate}")
            return candidate
    raise ProfileLoadError(
        "required workspace file is missing for `workspace_doc_path`: "
        f"{memory_root / 'WORKSPACE.md'}"
    )
