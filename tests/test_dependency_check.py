import importlib.util

import pytest

REQUIRED_MODULES = ("mlx", "mlx_lm", "zmq")


def _spec_available(name: str) -> bool:
    """Check if a module has a real (non-mocked) spec."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ValueError, ModuleNotFoundError):
        return False


def test_optional_dependencies_present():
    missing = [name for name in REQUIRED_MODULES if not _spec_available(name)]
    if missing:
        pytest.skip(f"Missing optional runtime dependencies: {', '.join(missing)}")
