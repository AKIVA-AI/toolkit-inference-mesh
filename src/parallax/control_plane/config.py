"""
Config hierarchy contract for toolkit-inference-mesh.

Three-tier hierarchy (mirrors Akiva platform pattern):
  Level 0 -- Platform defaults (global Akiva CLI conventions)
  Level 1 -- Toolkit config (pyproject.toml / config file)
  Level 2 -- CLI overrides (argv flags)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolkitConfigContract:
    """
    Resolved configuration contract for toolkit-inference-mesh.

    All fields represent resolved values after applying the three-tier
    hierarchy (platform defaults -> toolkit config -> CLI overrides).
    """

    # -- Identity --------------------------------------------------------------
    toolkit_id: str = "TK-IM"
    toolkit_name: str = "toolkit-inference-mesh"
    version: str = "0.1.2"

    # -- Runtime behaviour -----------------------------------------------------
    log_format: str = "json"          # 'json' | 'text'
    structured_logging: bool = True
    output_format: str = "json"       # 'json' | 'text'

    # -- Mesh / serving --------------------------------------------------------
    scheduler_host: str = "0.0.0.0"
    scheduler_port: int = 7589
    chat_port: int = 30000
    num_nodes: int = 1

    # -- Extension -------------------------------------------------------------
    extra: dict[str, Any] = field(default_factory=dict)


# Config hierarchy levels -- mirrors the TypeScript CONFIG_HIERARCHY_LEVELS pattern
# used in HubZone and Website adapters.
CONFIG_LEVELS = {
    "platform_default": 0,
    "toolkit_config": 1,
    "cli_override": 2,
}


def build_config_hierarchy(
    toolkit_config: dict[str, Any] | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> ToolkitConfigContract:
    """
    Merge config tiers into a resolved ToolkitConfigContract.

    Priority: CLI overrides > toolkit config > platform defaults.

    Parameters
    ----------
    toolkit_config:
        Values loaded from pyproject.toml [tool.toolkit-inference-mesh]
        or equivalent config file.
    cli_overrides:
        Values parsed from CLI argv.

    Returns
    -------
    ToolkitConfigContract
        Fully resolved configuration contract.
    """
    # Start with platform defaults
    resolved: dict[str, Any] = {
        "toolkit_id": "TK-IM",
        "toolkit_name": "toolkit-inference-mesh",
        "version": "0.1.2",
        "log_format": "json",
        "structured_logging": True,
        "output_format": "json",
        "scheduler_host": "0.0.0.0",
        "scheduler_port": 7589,
        "chat_port": 30000,
        "num_nodes": 1,
        "extra": {},
    }

    # Layer 1: toolkit config
    if toolkit_config:
        for k, v in toolkit_config.items():
            if k in resolved:
                resolved[k] = v
            else:
                resolved["extra"][k] = v

    # Layer 2: CLI overrides (highest priority)
    if cli_overrides:
        for k, v in cli_overrides.items():
            if k in resolved:
                resolved[k] = v
            else:
                resolved["extra"][k] = v

    return ToolkitConfigContract(**{k: v for k, v in resolved.items()})


__all__ = ["ToolkitConfigContract", "CONFIG_LEVELS", "build_config_hierarchy"]
