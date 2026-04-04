from __future__ import annotations

import json
from pathlib import Path

from .errors import ProfileLoadError
from .models import WorkspaceContext, WorkspaceProfile


PRIMARY_PROFILE_DIR = Path(".agent-memory") / "machine-profiles"
COMPATIBILITY_PROFILE_PATH = Path(".codex") / "workspace-profile" / "PROFILE.json"
CURRENT_PROFILE_SCHEMA_VERSION = 1


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
    workspace_start_here_path = _optional_absolute_file_path(
        document,
        "workspace_start_here_path",
        fallback=profile.memory_root / "WORKSPACE_START_HERE.md",
    )
    workspace_rules_path = _optional_absolute_file_path(
        document,
        "workspace_rules_path",
        fallback=profile.memory_root / "WORKSPACE_RULES.md",
    )
    return WorkspaceContext(
        profile=profile,
        project_index_path=project_index_path,
        workspace_start_here_path=workspace_start_here_path,
        workspace_rules_path=workspace_rules_path,
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
