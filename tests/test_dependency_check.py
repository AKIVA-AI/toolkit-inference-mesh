import importlib.util

import pytest


REQUIRED_MODULES = ("mlx", "mlx_lm", "zmq")


def test_optional_dependencies_present():
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        pytest.skip(f"Missing optional runtime dependencies: {', '.join(missing)}")
