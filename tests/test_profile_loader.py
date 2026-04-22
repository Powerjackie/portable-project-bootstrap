from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from portable_project_bootstrap import (
    COMPATIBILITY_PROFILE_PATH,
    CURRENT_PROFILE_SCHEMA_VERSION,
    PRIMARY_PROFILE_DIR,
    ProfileLoadError,
    discover_profile_path_with_source,
    load_workspace_context,
    load_workspace_profile,
    resolve_profile_path,
)


class ProfileLoaderTests(unittest.TestCase):
    def test_load_workspace_context_from_discovered_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            profile_path = self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
            )

            profile = load_workspace_profile(workspace_root=workspace_root, profile_name="test-profile")
            context = load_workspace_context(workspace_root=workspace_root, profile_name="test-profile")

            self.assertEqual("test-profile", profile.profile_name)
            self.assertEqual(CURRENT_PROFILE_SCHEMA_VERSION, profile.schema_version)
            self.assertEqual(repo_root, profile.repo_root)
            self.assertEqual(memory_root, profile.memory_root)
            self.assertEqual(backup_root, profile.backup_root)
            self.assertEqual("inline", profile.memory_mode)
            self.assertEqual(memory_root / "PROJECT_INDEX.md", context.project_index_path)
            self.assertEqual(memory_root / "WORKSPACE.md", context.workspace_doc_path)
            self.assertEqual(profile_path, context.resolved_profile_path)
            self.assertEqual("primary", context.resolved_profile_source)
            self.assertTrue(profile_path.exists())

    def test_profile_loader_uses_compatibility_fallback_when_primary_profile_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            compatibility_path = workspace_root / COMPATIBILITY_PROFILE_PATH
            compatibility_path.parent.mkdir(parents=True, exist_ok=True)
            compatibility_path.write_text(
                json.dumps(
                    {
                        "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                        "profile_name": "compat-profile",
                        "repo_root": str(repo_root),
                        "memory_root": str(memory_root),
                        "backup_root": str(backup_root),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            discovered_path, discovered_source = discover_profile_path_with_source(
                workspace_root, "compat-profile"
            )
            context = load_workspace_context(workspace_root=workspace_root, profile_name="compat-profile")

            self.assertEqual(compatibility_path, discovered_path)
            self.assertEqual("compatibility", discovered_source)
            self.assertEqual(compatibility_path, context.resolved_profile_path)
            self.assertEqual("compatibility", context.resolved_profile_source)

    def test_explicit_profile_path_overrides_discovered_profile_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            primary_path = self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
            )
            explicit_profile_path = workspace_root / "custom-profile.json"
            explicit_profile_path.write_text(
                json.dumps(
                    {
                        "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                        "profile_name": "test-profile",
                        "repo_root": str(repo_root),
                        "memory_root": str(memory_root),
                        "backup_root": str(backup_root),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            resolved_path, resolved_source = resolve_profile_path(
                workspace_root=workspace_root,
                profile_name="test-profile",
                profile_path=explicit_profile_path,
            )
            context = load_workspace_context(
                workspace_root=workspace_root,
                profile_name="test-profile",
                profile_path=explicit_profile_path,
            )

            self.assertEqual(primary_path, workspace_root / PRIMARY_PROFILE_DIR / "test-profile.json")
            self.assertEqual(explicit_profile_path, resolved_path)
            self.assertEqual("explicit", resolved_source)
            self.assertEqual(explicit_profile_path, context.resolved_profile_path)
            self.assertEqual("explicit", context.resolved_profile_source)

    def test_profile_loader_fails_closed_when_required_field_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
                remove_key="memory_root",
            )

            with self.assertRaisesRegex(ProfileLoadError, "memory_root"):
                load_workspace_profile(workspace_root=workspace_root, profile_name="test-profile")

    def test_profile_loader_fails_closed_when_required_workspace_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
            )
            (memory_root / "WORKSPACE.md").unlink()

            with self.assertRaisesRegex(ProfileLoadError, "workspace_doc_path"):
                load_workspace_context(workspace_root=workspace_root, profile_name="test-profile")

    def test_profile_loader_rejects_unknown_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
                schema_version=CURRENT_PROFILE_SCHEMA_VERSION + 1,
            )

            with self.assertRaisesRegex(ProfileLoadError, "unsupported profile schema_version"):
                load_workspace_profile(workspace_root=workspace_root, profile_name="test-profile")

    def test_profile_loader_reads_external_memory_mode_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
                memory_mode="external",
            )

            profile = load_workspace_profile(workspace_root=workspace_root, profile_name="test-profile")

            self.assertEqual("external", profile.memory_mode)

    def test_profile_loader_rejects_unknown_memory_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root, memory_root, backup_root = self._workspace_dirs(workspace_root)
            self._write_profile(
                workspace_root=workspace_root,
                profile_name="test-profile",
                repo_root=repo_root,
                memory_root=memory_root,
                backup_root=backup_root,
                memory_mode="invalid",
            )

            with self.assertRaisesRegex(ProfileLoadError, "memory_mode"):
                load_workspace_profile(workspace_root=workspace_root, profile_name="test-profile")

    def _workspace_dirs(self, workspace_root: Path) -> tuple[Path, Path, Path]:
        repo_root = workspace_root / "repos"
        memory_root = workspace_root / ".agent-memory"
        backup_root = workspace_root / "backups"
        repo_root.mkdir()
        memory_root.mkdir()
        backup_root.mkdir()
        (memory_root / "PROJECT_INDEX.md").write_text("# Project Index\n\n## sample\n\n- Purpose: Sample\n- Canonical repo / runtime surface:\n  - `X:\\repo\\sample`\n- Backup path:\n  - `X:\\backup\\sample`\n- Memory root:\n  - `X:\\memory\\sample`\n- Read-first files:\n  - `X:\\memory\\sample\\PROJECT.md`\n- Optional files:\n  - `X:\\memory\\sample\\AI_HANDOVER.md`\n  - `X:\\memory\\sample\\AGENT_DESIGN.md`\n- Strong match signals:\n  - project slug `sample`\n- Weak hints only:\n  - `none`\n- Weak hints must not trigger the project by themselves. Use them only when another strong project signal already exists.\n- Summary: Sample.\n", encoding="utf-8")
        (memory_root / "WORKSPACE.md").write_text("workspace\n", encoding="utf-8")
        return repo_root, memory_root, backup_root

    def _write_profile(
        self,
        *,
        workspace_root: Path,
        profile_name: str,
        repo_root: Path,
        memory_root: Path,
        backup_root: Path,
        remove_key: str | None = None,
        schema_version: int = CURRENT_PROFILE_SCHEMA_VERSION,
        memory_mode: str = "inline",
    ) -> Path:
        profile_dir = workspace_root / ".agent-memory" / "machine-profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": schema_version,
            "profile_name": profile_name,
            "repo_root": str(repo_root),
            "memory_root": str(memory_root),
            "backup_root": str(backup_root),
            "memory_mode": memory_mode,
        }
        if remove_key is not None:
            document.pop(remove_key)
        path = profile_dir / f"{profile_name}.json"
        path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()

