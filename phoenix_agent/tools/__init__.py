"""
Phoenix Agent - Tools Module
===========================

Tools system for Phoenix Agent.

v0.3: Structure préparée, sans implémentation active.
v1+: Implémentation complète avec exécution.
"""

from .base import (
    Tool,
    ToolResult,
    ToolParameter,
    EchoTool,
)

from .registry import (
    ToolRegistry,
    get_registry,
    register_tool,
)


__all__ = [
    "Tool",
    "ToolResult",
    "ToolParameter",
    "EchoTool",
    "ToolRegistry",
    "get_registry",
    "register_tool",
]
