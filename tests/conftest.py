import importlib.util

REQUIRED_MODULES = ("mlx", "mlx_lm", "zmq")
MISSING_MODULES = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]

# Tests that can run without hardware dependencies (mlx, zmq)
_NO_HW_DEPS = {
    "test_dependency_check.py",
    "test_shared_state.py",
    "test_akiva_enhancements.py",
}


def pytest_ignore_collect(collection_path, config):
    if MISSING_MODULES:
        filename = getattr(collection_path, "name", None)
        if filename and filename not in _NO_HW_DEPS:
            return True
    return False
