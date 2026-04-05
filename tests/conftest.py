import importlib.util

REQUIRED_MODULES = ("mlx", "mlx_lm", "zmq")
MISSING_MODULES = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]

# Tests that can run without hardware dependencies (mlx, zmq)
_NO_HW_DEPS = {
    "test_dependency_check.py",
    "test_shared_state.py",
    "test_akiva_enhancements.py",
    "test_model_info.py",
    "test_node_scheduling.py",
    "test_sampling_params.py",
    "test_request_metrics.py",
    "test_version_check.py",
    "test_layer_allocation.py",
    "test_routing_edge_cases.py",
    "test_ascii_utils.py",
    "test_health_endpoints.py",
}


def pytest_ignore_collect(collection_path, config):
    if MISSING_MODULES:
        filename = getattr(collection_path, "name", None)
        if filename and filename not in _NO_HW_DEPS:
            return True
    return False
