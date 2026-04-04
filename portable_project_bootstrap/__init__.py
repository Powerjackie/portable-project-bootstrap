from __future__ import annotations

from pathlib import Path


_SRC_PACKAGE_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "portable_project_bootstrap"
)
_SRC_INIT = _SRC_PACKAGE_DIR / "__init__.py"

if not _SRC_INIT.is_file():
    raise ModuleNotFoundError(
        "portable_project_bootstrap source package is missing under src/portable_project_bootstrap"
    )

__path__ = [str(_SRC_PACKAGE_DIR)]
__file__ = str(_SRC_INIT)

exec(compile(_SRC_INIT.read_text(encoding="utf-8"), __file__, "exec"), globals(), globals())
