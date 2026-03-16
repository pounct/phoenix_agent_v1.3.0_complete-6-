"""
Phoenix Agent - Tool Registry
=============================

Registre des tools disponibles.

v0.3: Structure prête, sans implémentation active.
v1+: Chargement dynamique et exécution des tools.
"""

from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass, field

from .base import Tool, ToolResult


@dataclass
class ToolRegistry:
    """
    Registre des tools disponibles pour Phoenix.
    
    v0.3: Structure en place
    v1+: Chargement et exécution
    """
    
    _tools: Dict[str, Tool] = field(default_factory=dict)
    
    def register(self, tool: Tool) -> None:
        """Enregistre un tool."""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> bool:
        """Désenregistre un tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Tool]:
        """Récupère un tool par nom."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Liste les noms des tools."""
        return list(self._tools.keys())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Retourne les schemas de tous les tools."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Exécute un tool."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def clear(self) -> None:
        """Efface tous les tools."""
        self._tools.clear()


# ==========================================
# GLOBAL REGISTRY
# ==========================================

_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Récupère le registre global."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: Tool) -> None:
    """Enregistre un tool dans le registre global."""
    get_registry().register(tool)
