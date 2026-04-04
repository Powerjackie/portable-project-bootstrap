class PlanningError(ValueError):
    """Raised when bootstrap planning cannot proceed safely."""


class ExecutionError(RuntimeError):
    """Raised when execution cannot safely apply a precomputed plan."""


class ProfileLoadError(ValueError):
    """Raised when a workspace profile cannot be discovered or validated safely."""


class BridgeError(ValueError):
    """Raised when compatibility bridge inputs cannot be mapped safely."""


class ShadowModeError(ValueError):
    """Raised when shadow-mode comparison cannot be executed safely."""


class SkillCallerError(RuntimeError):
    """Raised when the external skill caller cannot safely hand off to the package."""


class ProjectIndexParseError(ValueError):
    """Raised when PROJECT_INDEX.md cannot be parsed into the expected stable shape."""


class RouterError(ValueError):
    """Raised when workspace routing cannot be resolved safely."""
