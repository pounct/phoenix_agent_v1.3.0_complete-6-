"""
Phoenix Agent - Session State
============================

Gestion de l'état de session pour le runtime Phoenix.

State = Session + statistiques d'exécution
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..contract.session import Session, SessionStatus, Message
from ..contract.schemas import DEFAULT_MODEL


class SessionState:
    """
    État d'exécution d'une session Phoenix.
    
    Wrapper autour de Session avec des méthodes utilitaires
    pour le runtime.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_iterations: int = 10
    ):
        # Create session with proper ID
        sid = session_id or str(uuid.uuid4())
        self.session = Session(
            session_id=sid,
            model=model,
            max_iterations=max_iterations
        )
        self._events: list = []
    
    # ==========================================
    # PROPERTIES (delegate to session)
    # ==========================================
    
    @property
    def session_id(self) -> str:
        return self.session.session_id
    
    @property
    def status(self) -> SessionStatus:
        return self.session.status
    
    @property
    def iteration(self) -> int:
        return self.session.iteration
    
    @property
    def messages(self) -> List[Message]:
        return self.session.messages
    
    @property
    def total_tokens(self) -> int:
        return self.session.total_tokens
    
    # ==========================================
    # MESSAGE METHODS
    # ==========================================
    
    def add_message(self, message: Message) -> None:
        self.session.add_message(message)
    
    def add_system(self, content: str) -> None:
        self.session.add_system(content)
    
    def add_user(self, content: str) -> None:
        self.session.add_user(content)
    
    def add_assistant(self, content: str) -> None:
        self.session.add_assistant(content)
    
    # ==========================================
    # STATE METHODS
    # ==========================================
    
    def start(self) -> None:
        self.session.start()
    
    def complete(self) -> None:
        self.session.complete()
    
    def fail(self) -> None:
        self.session.fail()
    
    def increment_iteration(self) -> int:
        return self.session.increment_iteration()
    
    def can_continue(self) -> bool:
        return self.session.can_continue()
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def add_tokens(self, tokens: int) -> None:
        self.session.add_tokens(tokens)
    
    def add_latency(self, latency_ms: float) -> None:
        self.session.add_latency(latency_ms)
    
    # ==========================================
    # EVENTS
    # ==========================================
    
    def record_event(self, event: Any) -> None:
        self._events.append(event)
    
    def get_events(self) -> list:
        return self._events.copy()
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        return self.session.model_dump()


class SessionManager:
    """
    Gestionnaire de sessions.
    
    v0.3: Stockage en mémoire.
    v1+: Persistance Redis.
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
    
    def create(
        self,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_iterations: int = 10
    ) -> SessionState:
        state = SessionState(
            session_id=session_id,
            model=model,
            max_iterations=max_iterations
        )
        self._sessions[state.session_id] = state
        return state
    
    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)
    
    def get_or_create(
        self,
        session_id: str,
        model: str = DEFAULT_MODEL
    ) -> SessionState:
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self.create(session_id=session_id, model=model)
    
    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_all(self) -> List[str]:
        return list(self._sessions.keys())
    
    def clear(self) -> None:
        self._sessions.clear()
