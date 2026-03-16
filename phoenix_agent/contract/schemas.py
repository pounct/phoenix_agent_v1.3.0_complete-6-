"""
Phoenix Agent - Contract Schemas
================================

Schémas de données ALIGNÉS sur la LLM Gateway externe.
Phoenix est un client NATIF de la gateway - pas de transformation intermédiaire.

Gateway Endpoints:
    POST /v1/generate  - Génération de texte (utilisé par Phoenix)
    GET  /v1/models    - Liste des modèles
    GET  /health       - Health check

RÈGLES:
    - Phoenix ne définit PAS ses propres schémas de requête LLM
    - Phoenix utilise directement GenerateRequest/GenerateResponse
    - Pas de double transformation
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ==========================================
# GATEWAY NATIVE TYPES (from llm-gateway-v3)
# ==========================================

class GenerateRequest(BaseModel):
    """
    Request pour POST /v1/generate.
    
    ALIGNÉ sur phoenix/api/schemas.py de la gateway.
    Phoenix envoie ce format DIRECTEMENT à la gateway.
    """
    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=50000, 
        description="User prompt (can include context)"
    )
    model: str = Field(
        default="llama3.2:latest", 
        description="Target model"
    )
    use_cache: bool = Field(
        default=True, 
        description="Enable/disable cache"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Explain quantum computing in simple terms",
                "model": "llama3.2:latest",
                "use_cache": True
            }
        }


class GenerateResponse(BaseModel):
    """
    Response de POST /v1/generate.
    
    ALIGNÉ sur phoenix/api/schemas.py de la gateway.
    Phoenix reçoit ce format DIRECTEMENT de la gateway.
    """
    response: str = Field(..., description="Generated text")
    latency_ms: float = Field(..., description="Total latency in milliseconds")
    cached: bool = Field(default=False, description="Whether response came from cache")
    model: str = Field(..., description="Model used for generation")
    provider: Optional[str] = Field(
        default=None, 
        description="Provider that handled the request"
    )
    request_id: Optional[str] = Field(
        default=None, 
        description="Unique request ID for tracing"
    )
    usage: Optional[Dict[str, int]] = Field(
        default=None, 
        description="Token usage: input_tokens, output_tokens"
    )
    
    @property
    def is_empty(self) -> bool:
        """Vérifie si la réponse est vide."""
        return not self.response or len(self.response.strip()) == 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Quantum computing uses quantum bits...",
                "latency_ms": 1234.56,
                "cached": False,
                "model": "llama3.2:latest",
                "provider": "ollama_free",
                "request_id": "req_1234567890",
                "usage": {"input_tokens": 15, "output_tokens": 150}
            }
        }


class ErrorResponse(BaseModel):
    """Structured error response from gateway."""
    error: Dict[str, Any] = Field(..., description="Error details")
    
    @property
    def code(self) -> str:
        return self.error.get("code", "UNKNOWN")
    
    @property
    def message(self) -> str:
        return self.error.get("message", "Unknown error")


# ==========================================
# PROVIDER TYPES
# ==========================================

ProviderName = Literal['ollama_free', 'ollama', 'openai', 'mock']

# Fallback chain (from gateway config)
FALLBACK_PROVIDERS: List[str] = ["ollama_free", "ollama", "openai"]

# Popular models par provider
POPULAR_MODELS: Dict[str, List[str]] = {
    "ollama_free": ["llama3.2:latest", "mistral:latest", "qwen2.5:latest"],
    "ollama": ["llama3.2:latest", "codellama:latest", "mixtral:latest"],
    "openai": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
}


# ==========================================
# DEFAULTS
# ==========================================

DEFAULT_MODEL = "llama3.2:latest"
DEFAULT_PROVIDER = "ollama_free"
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_TIMEOUT_SECONDS = 120
