"""Mock hardware dependencies (mlx, mlx_lm, torch, zmq) for test environments.

Import this module BEFORE importing any scheduling/parallax modules to stub
out mlx and related native libraries that are unavailable in CI/test.
"""

from __future__ import annotations

import importlib.util
import sys
from unittest.mock import MagicMock

_MOCKS_INSTALLED = False


def install_mocks() -> None:
    """Install mock modules for mlx, mlx_lm, and related packages."""
    global _MOCKS_INSTALLED
    if _MOCKS_INSTALLED:
        return

    def _make_mock_module(name: str) -> MagicMock:
        """Create a MagicMock that acts as a module with __spec__ = None."""
        m = MagicMock()
        m.__name__ = name
        # Set __spec__ to None so importlib.util.find_spec doesn't raise ValueError.
        # find_spec will see __spec__ = None and return None (module not truly installed).
        m.__spec__ = None
        m.__path__ = []
        m.__file__ = None
        m.__loader__ = None
        m.__package__ = name
        return m

    # Only mock if real modules are not available
    def _spec_missing(name: str) -> bool:
        if name in sys.modules:
            return False  # already loaded (real or stub)
        try:
            return importlib.util.find_spec(name) is None
        except (ModuleNotFoundError, ValueError):
            return True

    if _spec_missing("mlx"):
        mlx_root = _make_mock_module("mlx")
        mlx_core = _make_mock_module("mlx.core")
        mlx_nn = _make_mock_module("mlx.nn")
        mlx_utils = _make_mock_module("mlx.utils")

        mlx_root.core = mlx_core
        mlx_root.nn = mlx_nn
        mlx_root.utils = mlx_utils

        sys.modules["mlx"] = mlx_root
        sys.modules["mlx.core"] = mlx_core
        sys.modules["mlx.nn"] = mlx_nn
        sys.modules["mlx.utils"] = mlx_utils

    if _spec_missing("mlx_lm"):
        mlx_lm = _make_mock_module("mlx_lm")
        mlx_lm_tuner = _make_mock_module("mlx_lm.tuner")
        mlx_lm_tuner_utils = _make_mock_module("mlx_lm.tuner.utils")
        mlx_lm_utils = _make_mock_module("mlx_lm.utils")
        mlx_lm_tokenizer_utils = _make_mock_module("mlx_lm.tokenizer_utils")

        mlx_lm.tuner = mlx_lm_tuner
        mlx_lm.tuner.utils = mlx_lm_tuner_utils
        mlx_lm.utils = mlx_lm_utils
        mlx_lm.tokenizer_utils = mlx_lm_tokenizer_utils

        sys.modules["mlx_lm"] = mlx_lm
        sys.modules["mlx_lm.tuner"] = mlx_lm_tuner
        sys.modules["mlx_lm.tuner.utils"] = mlx_lm_tuner_utils
        sys.modules["mlx_lm.utils"] = mlx_lm_utils
        sys.modules["mlx_lm.tokenizer_utils"] = mlx_lm_tokenizer_utils

    # Ensure torch is available or mocked
    if _spec_missing("torch"):
        mock_torch = _make_mock_module("torch")
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.bfloat16 = "bfloat16"
        mock_torch.half = "half"
        mock_torch.int8 = "int8"
        sys.modules["torch"] = mock_torch

    _MOCKS_INSTALLED = True


# Auto-install on import
install_mocks()
