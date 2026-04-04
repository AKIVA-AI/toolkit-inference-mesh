"""
CLI command -> ToolSpec mapping for toolkit-inference-mesh.

Maps the 3 CLI subcommands (run, join, chat) to ToolSpec contracts with
appropriate permission scope and approval policy.

'run' and 'join' start long-running distributed serving processes and
require FULL_ACCESS + REQUIRE_APPROVAL (they bind ports and connect to
external peer networks).  'chat' starts a local chat server and also
requires explicit approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import ApprovalPolicy, AuthorityBoundary, PermissionScope, ToolSpec


@dataclass
class ToolkitCommandSpec:
    """Maps a CLI subcommand name to its ToolSpec and authority boundary."""

    command: str
    spec: ToolSpec
    boundary: AuthorityBoundary


def _make_spec(
    name: str,
    description: str,
    scope: PermissionScope = PermissionScope.FULL_ACCESS,
    input_schema: dict[str, Any] | None = None,
) -> ToolSpec:
    """Create a ToolSpec for an inference-mesh CLI command."""
    return ToolSpec(
        name=name,
        description=description,
        category="tool",
        version="0.1.2",
        owner="toolkit-inference-mesh",
        permission_scope=scope,
        input_schema=input_schema,
        output_schema=None,
        sandbox_requirement=None,
        aliases=None,
    )


_FULL_APPROVE = AuthorityBoundary(
    scope=PermissionScope.FULL_ACCESS,
    approval=ApprovalPolicy.REQUIRE_APPROVAL,
)

# -- Per-command specs ---------------------------------------------------------

TOOLKIT_TOOL_SPECS: dict[str, ToolkitCommandSpec] = {
    "run": ToolkitCommandSpec(
        command="run",
        spec=_make_spec(
            name="run",
            description=(
                "Start the Toolkit Inference Mesh scheduler node. Binds a port "
                "and participates in a distributed peer network. Requires approval."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name or path"},
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "num_nodes": {"type": "integer"},
                    "initial_peers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bootstrap peer multiaddresses",
                    },
                },
                "required": ["model"],
            },
        ),
        boundary=_FULL_APPROVE,
    ),
    "join": ToolkitCommandSpec(
        command="join",
        spec=_make_spec(
            name="join",
            description=(
                "Join an existing Toolkit Inference Mesh swarm as a worker node. "
                "Connects to peer network. Requires approval."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "initial_peers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "relay_peers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["model"],
            },
        ),
        boundary=_FULL_APPROVE,
    ),
    "chat": ToolkitCommandSpec(
        command="chat",
        spec=_make_spec(
            name="chat",
            description=(
                "Start the Toolkit Inference Mesh chat server (OpenAI-compatible "
                "HTTP endpoint). Requires approval."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["model"],
            },
        ),
        boundary=_FULL_APPROVE,
    ),
}


def get_tool_spec(command: str) -> ToolkitCommandSpec | None:
    """Return the ToolkitCommandSpec for a CLI subcommand, or None if unknown."""
    return TOOLKIT_TOOL_SPECS.get(command)


__all__ = ["TOOLKIT_TOOL_SPECS", "ToolkitCommandSpec", "get_tool_spec"]
