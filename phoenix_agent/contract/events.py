"""
Phoenix Agent - Events
======================

Event types pour l'Agent Loop interne.

Phoenix utilise un système d'événements pour tracer le cycle:
    Think → Act → Observe → Complete/Error

Ces events permettent:
    - Logging structuré
    - Observabilité
    - SSE streaming
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


# ==========================================
# EVENT TYPES
# ==========================================

class EventType(str, Enum):
    """Types d'événements dans le cycle agent."""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    COMPLETE = "complete"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


# ==========================================
# BASE EVENT
# ==========================================

class AgentEvent(BaseModel):
    """
    Event de base pour l'agent loop.
    
    Tous les événements héritent de cette structure.
    """
    event_type: str = Field(..., description="Type of event")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    iteration: int = Field(default=0, ge=0, description="Current iteration")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    
    class Config:
        use_enum_values = True


# ==========================================
# SPECIFIC EVENTS
# ==========================================

class ThinkEvent(AgentEvent):
    """
    Event émis pendant la phase Think.
    
    Data contient:
        - reasoning: Le raisonnement de l'agent
        - context_summary: Résumé du contexte utilisé
    """
    event_type: str = Field(default=EventType.THINK)
    
    @classmethod
    def create(
        cls,
        session_id: str,
        iteration: int,
        reasoning: str,
        context_summary: Optional[str] = None
    ) -> "ThinkEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "reasoning": reasoning,
                "context_summary": context_summary
            }
        )


class ActEvent(AgentEvent):
    """
    Event émis pendant la phase Act.
    
    Data contient:
        - action_type: "llm_call" | "tool_call"
        - action_details: Détails de l'action
    """
    event_type: str = Field(default=EventType.ACT)
    
    @classmethod
    def create_llm_call(
        cls,
        session_id: str,
        iteration: int,
        model: str,
        prompt_length: int
    ) -> "ActEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "action_type": "llm_call",
                "model": model,
                "prompt_length": prompt_length
            }
        )
    
    @classmethod
    def create_tool_call(
        cls,
        session_id: str,
        iteration: int,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> "ActEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "action_type": "tool_call",
                "tool_name": tool_name,
                "tool_args": tool_args
            }
        )


class ObserveEvent(AgentEvent):
    """
    Event émis pendant la phase Observe.
    
    Data contient:
        - observation_type: "llm_response" | "tool_result" | "error"
        - observation: Le résultat observé
    """
    event_type: str = Field(default=EventType.OBSERVE)
    
    @classmethod
    def create_llm_response(
        cls,
        session_id: str,
        iteration: int,
        response: str,
        latency_ms: float,
        cached: bool = False
    ) -> "ObserveEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "observation_type": "llm_response",
                "response": response,
                "latency_ms": latency_ms,
                "cached": cached
            }
        )
    
    @classmethod
    def create_error(
        cls,
        session_id: str,
        iteration: int,
        error_code: str,
        error_message: str
    ) -> "ObserveEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "observation_type": "error",
                "error_code": error_code,
                "error_message": error_message
            }
        )


class CompleteEvent(AgentEvent):
    """
    Event émis quand le cycle est terminé.
    
    Data contient:
        - status: "completed" | "max_iterations"
        - final_response: La réponse finale
        - total_iterations: Nombre total d'itérations
    """
    event_type: str = Field(default=EventType.COMPLETE)
    
    @classmethod
    def create(
        cls,
        session_id: str,
        status: str,
        final_response: str,
        total_iterations: int,
        total_tokens: int = 0
    ) -> "CompleteEvent":
        return cls(
            session_id=session_id,
            iteration=total_iterations,
            data={
                "status": status,
                "final_response": final_response,
                "total_iterations": total_iterations,
                "total_tokens": total_tokens
            }
        )


class ErrorEvent(AgentEvent):
    """
    Event émis en cas d'erreur fatale.
    
    Data contient:
        - error_code: Code d'erreur
        - error_message: Message d'erreur
        - recoverable: Si l'erreur est récupérable
    """
    event_type: str = Field(default=EventType.ERROR)
    
    @classmethod
    def create(
        cls,
        session_id: str,
        iteration: int,
        error_code: str,
        error_message: str,
        recoverable: bool = False
    ) -> "ErrorEvent":
        return cls(
            session_id=session_id,
            iteration=iteration,
            data={
                "error_code": error_code,
                "error_message": error_message,
                "recoverable": recoverable
            }
        )


# ==========================================
# EVENT HELPERS
# ==========================================

def event_to_sse(event: AgentEvent) -> str:
    """
    Convertit un event en format SSE.
    
    Format: data: {json}\n\n
    """
    import json
    return f"data: {event.model_dump_json()}\n\n"


def event_to_dict(event: AgentEvent) -> Dict[str, Any]:
    """Convertit un event en dict."""
    return event.model_dump()
