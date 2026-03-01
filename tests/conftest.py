import importlib.util

REQUIRED_MODULES = ("mlx", "mlx_lm", "zmq")
MISSING_MODULES = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]


def pytest_ignore_collect(collection_path, config):
    if MISSING_MODULES:
        filename = getattr(collection_path, "name", None)
        if filename and filename != "test_dependency_check.py":
            return True
    return False
