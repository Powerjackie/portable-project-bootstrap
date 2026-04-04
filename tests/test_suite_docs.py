from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class SuiteDocsTests(unittest.TestCase):
    def test_readme_documents_public_suite_roles_and_protocol(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("workspace-validator", readme)
        self.assertIn("workspace-router", readme)
        self.assertIn("python -m portable_project_bootstrap", readme)
        self.assertIn("<workspace_root>/.agent-memory/machine-profiles/<profile_name>.json", readme)
        self.assertIn("<workspace_root>/.codex/workspace-profile/PROFILE.json", readme)
        self.assertIn("Brand-New Project Workflow", readme)
        self.assertIn("Existing Project Workflow", readme)
        self.assertIn("Deprecation Readiness", readme)
        self.assertIn("Driving This Project With Agents", readme)
        self.assertIn("Examples And Supporting Files", readme)
        self.assertNotIn(r"C:\Users\G1942", readme)
        self.assertNotIn(r"D:\workspace", readme)

    def test_chinese_readme_documents_public_suite_roles_and_protocol(self) -> None:
        readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("workspace-validator", readme)
        self.assertIn("workspace-router", readme)
        self.assertIn("python -m portable_project_bootstrap", readme)
        self.assertIn("<workspace_root>/.agent-memory/machine-profiles/<profile_name>.json", readme)
        self.assertIn("<workspace_root>/.codex/workspace-profile/PROFILE.json", readme)
        self.assertIn("Brand-New Project Workflow", readme)
        self.assertIn("Existing Project Workflow", readme)
        self.assertIn("如何用 Agents 驱动这个项目", readme)
        self.assertIn("示例与公开材料", readme)
        self.assertNotIn(r"C:\Users\G1942", readme)
        self.assertNotIn(r"D:\workspace", readme)

    def test_suite_overview_documents_call_order_and_boundaries(self) -> None:
        overview = (REPO_ROOT / "docs" / "workspace-suite-overview.md").read_text(encoding="utf-8")

        self.assertIn("workspace-validator", overview)
        self.assertIn("workspace-router", overview)
        self.assertIn("Recommended Call Order", overview)
        self.assertIn("brand-new", overview)
        self.assertIn("existing project", overview)
        self.assertIn("Standard Workflows", overview)
        self.assertIn("Observation And Triage", overview)
        self.assertIn("Operational Classification", overview)
        self.assertIn("Standard Response Playbooks", overview)
        self.assertIn("Long-Run Observation Window", overview)
        self.assertIn("Legacy Deprecation Readiness Checklist", overview)
        self.assertIn("python -m portable_project_bootstrap", overview)

    def test_examples_and_open_source_files_exist(self) -> None:
        self.assertTrue((REPO_ROOT / "examples" / "default.profile.json").is_file())
        self.assertTrue((REPO_ROOT / "examples" / "workspace-layout.md").is_file())
        self.assertTrue((REPO_ROOT / "examples" / "README.md").is_file())
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())
        self.assertTrue((REPO_ROOT / "CONTRIBUTING.md").is_file())
        self.assertTrue((REPO_ROOT / ".gitignore").is_file())


if __name__ == "__main__":
    unittest.main()
