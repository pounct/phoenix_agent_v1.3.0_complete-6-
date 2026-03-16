"""
Phoenix Agent - Configuration
============================

Configuration globale pour Phoenix Agent Runtime.

Phoenix = Agent Runtime minimal
Gateway = LLM Provider externe

Variables d'environnement:
    PHOENIX_GATEWAY_URL       - URL de la gateway
    PHOENIX_GATEWAY_API_KEY   - Clé API
    PHOENIX_GATEWAY_TIMEOUT   - Timeout en secondes
    PHOENIX_MAX_ITERATIONS    - Max itérations agent loop
    PHOENIX_ENABLE_THINKING   - Activer phase think
    PHOENIX_DEBUG             - Mode debug
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ==========================================
# LOG LEVEL
# ==========================================

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ==========================================
# GATEWAY CONFIG
# ==========================================

@dataclass
class GatewayConfig:
    """
    Configuration de connexion à la LLM Gateway.
    
    Phoenix se connecte à la gateway EXISTANTE.
    """
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout_seconds: float = 120.0
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> "GatewayConfig":
        return cls(
            base_url=os.getenv("PHOENIX_GATEWAY_URL", "http://localhost:8000"),
            api_key=os.getenv("PHOENIX_GATEWAY_API_KEY"),
            timeout_seconds=float(os.getenv("PHOENIX_GATEWAY_TIMEOUT", "120")),
            max_retries=int(os.getenv("PHOENIX_GATEWAY_MAX_RETRIES", "3")),
        )


# ==========================================
# AGENT CONFIG
# ==========================================

@dataclass
class AgentConfig:
    """Configuration de l'Agent Loop."""
    max_iterations: int = 10
    enable_thinking: bool = True
    enable_tools: bool = False  # v1+
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_iterations=int(os.getenv("PHOENIX_MAX_ITERATIONS", "10")),
            enable_thinking=os.getenv("PHOENIX_ENABLE_THINKING", "true").lower() == "true",
            enable_tools=os.getenv("PHOENIX_ENABLE_TOOLS", "false").lower() == "true",
        )


# ==========================================
# PHOENIX CONFIG
# ==========================================

@dataclass
class PhoenixConfig:
    """
    Configuration principale Phoenix.
    
    Phoenix est un Agent Runtime minimal.
    """
    app_name: str = "Phoenix Agent"
    version: str = "0.3.0"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    
    @classmethod
    def from_env(cls) -> "PhoenixConfig":
        config = cls()
        
        if os.getenv("PHOENIX_DEBUG", "false").lower() == "true":
            config.debug = True
            config.log_level = LogLevel.DEBUG
        
        if os.getenv("PHOENIX_LOG_LEVEL"):
            config.log_level = LogLevel(os.getenv("PHOENIX_LOG_LEVEL"))
        
        config.gateway = GatewayConfig.from_env()
        config.agent = AgentConfig.from_env()
        
        return config


# ==========================================
# GLOBAL CONFIG
# ==========================================

_config: Optional[PhoenixConfig] = None


def get_config() -> PhoenixConfig:
    """Récupère la configuration globale."""
    global _config
    if _config is None:
        _config = PhoenixConfig.from_env()
    return _config


def set_config(config: PhoenixConfig) -> None:
    """Définit la configuration globale."""
    global _config
    _config = config


def reset_config() -> None:
    """Réinitialise la configuration."""
    global _config
    _config = None
