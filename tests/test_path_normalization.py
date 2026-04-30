from __future__ import annotations

import os
import unittest

from portable_project_bootstrap.profile_loader import normalize_path_for_compare


class PathNormalizationTests(unittest.TestCase):
    def test_normalize_path_for_compare_matches_equivalent_paths(self) -> None:
        host_specific_pairs = [
            (
                "mac-style path",
                "/Users/Foo/Developer/workspace/./repos/prompt-ide",
                "/Users/foo/Developer/workspace/repos/prompt-ide",
            ),
            (
                "same path different case",
                "/opt/Projects/Prompt-IDE",
                "/opt/projects/prompt-ide",
            ),
        ]
        if os.name == "nt":
            host_specific_pairs.extend(
                [
                    (
                        "windows-style path",
                        "C:/Users/Foo/Developer/workspace/repos/prompt-ide",
                        r"C:\Users\foo\Developer\workspace\repos\prompt-ide",
                    ),
                    (
                        "same path different separators",
                        "D:/workspace/repos/prompt-ide/.agent-memory",
                        r"D:\workspace\repos\prompt-ide\.agent-memory",
                    ),
                ]
            )
        else:
            host_specific_pairs.extend(
                [
                    (
                        "linux-style path",
                        "/srv/projects/prompt-ide/../prompt-ide",
                        "/srv/projects/prompt-ide",
                    ),
                    (
                        "same path different dot segments",
                        "/workspace/repos/prompt-ide/.agent-memory",
                        "/workspace/repos/./prompt-ide/.agent-memory",
                    ),
                ]
            )

        for label, left, right in host_specific_pairs:
            with self.subTest(label=label):
                self.assertEqual(
                    normalize_path_for_compare(left),
                    normalize_path_for_compare(right),
                )


if __name__ == "__main__":
    unittest.main()
