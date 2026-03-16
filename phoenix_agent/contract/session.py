"""
Phoenix Agent - Contract Session Types
=====================================

Types pour la gestion de session Phoenix.

Une Session représente l'état complet d'une conversation.
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from .schemas import DEFAULT_MODEL


# ==========================================
# SESSION STATUS
# ==========================================

SessionStatus = Literal['initialized', 'running', 'completed', 'error', 'max_iterations']


# ==========================================
# MESSAGE
# ==========================================

class Message(BaseModel):
    """
    Message dans une conversation.
    
    Simple et direct.
    """
    role: Literal['system', 'user', 'assistant', 'tool']
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role='system', content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role='user', content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role='assistant', content=content)
    
    @classmethod
    def tool_result(cls, tool_name: str, result: str) -> "Message":
        return cls(
            role='tool',
            content=result,
            metadata={"tool_name": tool_name}
        )


# ==========================================
# SESSION
# ==========================================

class Session(BaseModel):
    """
    Session Phoenix - État complet d'une conversation.
    
    Contient:
        - Identité (session_id)
        - Historique des messages
        - Configuration
        - Métadonnées d'exécution
        - Statistiques
    """
    # Identité
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Configuration
    model: str = Field(default=DEFAULT_MODEL)
    max_iterations: int = Field(default=10)
    
    # Historique
    messages: List[Message] = Field(default_factory=list)
    
    # État d'exécution
    status: SessionStatus = Field(default='initialized')
    iteration: int = Field(default=0)
    
    # Statistiques
    total_tokens: int = Field(default=0)
    total_latency_ms: float = Field(default=0.0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Métadonnées
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # ==========================================
    # MESSAGE MANAGEMENT
    # ==========================================
    
    def add_message(self, message: Message) -> None:
        """Ajoute un message à l'historique."""
        self.messages.append(message)
        self._touch()
    
    def add_system(self, content: str) -> None:
        """Ajoute un message système."""
        self.add_message(Message.system(content))
    
    def add_user(self, content: str) -> None:
        """Ajoute un message utilisateur."""
        self.add_message(Message.user(content))
    
    def add_assistant(self, content: str) -> None:
        """Ajoute un message assistant."""
        self.add_message(Message.assistant(content))
    
    # ==========================================
    # STATE MANAGEMENT
    # ==========================================
    
    def start(self) -> None:
        """Démarre la session."""
        self.status = 'running'
        self._touch()
    
    def complete(self) -> None:
        """Termine la session."""
        self.status = 'completed'
        self._touch()
    
    def fail(self) -> None:
        """Marque la session en erreur."""
        self.status = 'error'
        self._touch()
    
    def increment_iteration(self) -> int:
        """Incrémente l'itération."""
        self.iteration += 1
        self._touch()
        return self.iteration
    
    def can_continue(self) -> bool:
        """Vérifie si on peut continuer."""
        return self.status == 'running' and self.iteration < self.max_iterations
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def add_tokens(self, tokens: int) -> None:
        """Ajoute des tokens."""
        self.total_tokens += tokens
        self._touch()
    
    def add_latency(self, latency_ms: float) -> None:
        """Ajoute de la latence."""
        self.total_latency_ms += latency_ms
        self._touch()
    
    # ==========================================
    # UTILITIES
    # ==========================================
    
    def _touch(self) -> None:
        """Met à jour le timestamp."""
        self.updated_at = datetime.utcnow()
    
    def get_context(self) -> str:
        """Construit le contexte pour la gateway."""
        if not self.messages:
            return ""
        
        parts = []
        for msg in self.messages:
            role_label = {
                'system': '[SYSTEM]',
                'user': '[USER]',
                'assistant': '[ASSISTANT]',
                'tool': f'[TOOL:{msg.metadata.get("tool_name", "unknown")}]'
            }.get(msg.role, f'[{msg.role}]')
            parts.append(f"{role_label}: {msg.content}")
        
        return "\n\n".join(parts)
    
    @property
    def message_count(self) -> int:
        """Nombre de messages."""
        return len(self.messages)


# ==========================================
# SESSION RESULT
# ==========================================

class SessionResult(BaseModel):
    """Résultat d'une session."""
    session_id: str
    status: SessionStatus
    response: str
    iterations: int
    total_tokens: int
    total_latency_ms: float
    model: str
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == 'completed'
