"""
Phoenix Agent - Tools Base
==========================

Base class pour les tools Phoenix.

v0.3: Structure prête, sans implémentation.
v1+: Implémentation complète avec exécution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import asyncio


class ToolResult(BaseModel):
    """Résultat d'exécution d'un tool."""
    success: bool = True
    output: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolParameter(BaseModel):
    """Définition d'un paramètre de tool."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None


class Tool(ABC):
    """
    Base class pour les tools Phoenix.
    
    Un tool est une capacité que l'agent peut utiliser
    pendant le cycle Think → Act → Observe.
    
    Example:
        class WeatherTool(Tool):
            name = "weather"
            description = "Get weather for a city"
            
            async def execute(self, city: str) -> ToolResult:
                weather = await fetch_weather(city)
                return ToolResult(output=f"Weather in {city}: {weather}")
    """
    
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Exécute le tool.
        
        Args:
            **kwargs: Arguments du tool
            
        Returns:
            ToolResult
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Retourne le schema JSON du tool.
        
        Format compatible avec LLM tool calling.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }
    
    def __repr__(self) -> str:
        return f"Tool(name={self.name})"


# ==========================================
# EXAMPLE TOOL (v1+)
# ==========================================

class EchoTool(Tool):
    """Tool simple pour tests - echo l'input."""
    
    name = "echo"
    description = "Echo back the input text"
    parameters = [
        ToolParameter(
            name="text",
            type="string",
            description="Text to echo back",
            required=True
        )
    ]
    
    async def execute(self, text: str) -> ToolResult:
        return ToolResult(output=f"Echo: {text}")
