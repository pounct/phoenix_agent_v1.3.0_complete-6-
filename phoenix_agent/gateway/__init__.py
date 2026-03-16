"""
Phoenix Agent - Gateway Module
=============================

Gateway adapters pour communiquer avec le LLM Gateway externe.

Phoenix consomme la gateway comme un service externe.
Phoenix ne contient PAS de logique LLM.
"""

from .adapter import (
    GatewayAdapter,
    HTTPGatewayAdapter,
    MockGatewayAdapter,
    create_gateway_adapter,
)


__all__ = [
    "GatewayAdapter",
    "HTTPGatewayAdapter",
    "MockGatewayAdapter",
    "create_gateway_adapter",
]
