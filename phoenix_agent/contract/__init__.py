"""
Phoenix Agent - Contract Module
============================

Schémas de données alignés sur la LLM Gateway externe.
"""

from .schemas import (
    GenerateRequest,
    GenerateResponse,
    ErrorResponse,
    ProviderName,
    FALLBACK_PROVIDERS,
    POPULAR_MODELS,
    DEFAULT_MODEL,
)

from .events import (
    AgentEvent,
    ThinkEvent,
    ActEvent,
    ObserveEvent,
    CompleteEvent,
    ErrorEvent,
    EventType,
    event_to_sse,
)

from .session import (
    Message,
    Session,
    SessionStatus,
    SessionResult,
)


__all__ = [
    # Schemas
    "GenerateRequest",
    "GenerateResponse",
    "ErrorResponse",
    "ProviderName",
    "FALLBACK_PROVIDERS",
    "POPULAR_MODELS",
    "DEFAULT_MODEL",
    
    # Events
    "AgentEvent",
    "ThinkEvent",
    "ActEvent",
    "ObserveEvent",
    "CompleteEvent",
    "ErrorEvent",
    "EventType",
    "event_to_sse",
    
    # Session
    "Message",
    "Session",
    "SessionStatus",
    "SessionResult",
]
