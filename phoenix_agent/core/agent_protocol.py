"""
Phoenix Agent - Agent Communication Protocol
=============================================

Protocole de communication standardisé entre agents.

Sans protocole standardisé:
    - Communication ad-hoc
    - Incompatibilités entre agents
    - Difficile à scaler
    - Pas de tracing

Avec ce protocole:
    - Communication structurée
    - Interopérabilité garantie
    - Traçabilité complète
    - Scalabilité multi-agent

Architecture:
    Agent A → AgentMessage → Agent B → Response

STANDARDS:
    - AgentMessage: Message standard entre agents
    - MessageHeader: En-tête avec métadonnées
    - MessagePayload: Contenu du message
    - MessageAck: Accusé de réception

Similaire à:
    - AutoGen messages
    - LangGraph state messages
    - CrewAI task delegation

Version: 0.6.0 (Agent Communication Protocol)
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
import json


logger = logging.getLogger("phoenix.protocol")


# ==========================================
# MESSAGE TYPE
# ==========================================

class MessageType(str, Enum):
    """Types de messages entre agents."""
    # Task
    TASK_REQUEST = "task_request"           # Demande d'exécution
    TASK_RESULT = "task_result"             # Résultat de tâche
    TASK_STATUS = "task_status"             # Statut de tâche
    
    # Delegation
    DELEGATE_REQUEST = "delegate_request"   # Demande de délégation
    DELEGATE_ACCEPT = "delegate_accept"     # Acceptation
    DELEGATE_REJECT = "delegate_reject"     # Refus
    DELEGATE_RESULT = "delegate_result"     # Résultat délégué
    
    # Query
    QUERY = "query"                         # Question
    QUERY_RESPONSE = "query_response"       # Réponse
    
    # Coordination
    HANDSHAKE = "handshake"                 # Établissement connexion
    HEARTBEAT = "heartbeat"                 # Keep-alive
    SYNC = "sync"                           # Synchronisation
    
    # Control
    PAUSE = "pause"                         # Pause
    RESUME = "resume"                       # Reprise
    CANCEL = "cancel"                       # Annulation
    ABORT = "abort"                         # Abandon
    
    # Feedback
    FEEDBACK = "feedback"                   # Retour
    ERROR = "error"                         # Erreur
    WARNING = "warning"                     # Avertissement
    
    # Context
    CONTEXT_SHARE = "context_share"         # Partage de contexte
    CONTEXT_REQUEST = "context_request"     # Demande de contexte
    CONTEXT_UPDATE = "context_update"       # Mise à jour contexte
    
    # Memory
    MEMORY_SNAPSHOT = "memory_snapshot"     # Snapshot mémoire
    MEMORY_RESTORE = "memory_restore"       # Restauration mémoire


# ==========================================
# MESSAGE PRIORITY
# ==========================================

class MessagePriority(str, Enum):
    """Priorité des messages."""
    CRITICAL = "critical"    # Traitement immédiat
    HIGH = "high"            # Haute priorité
    NORMAL = "normal"        # Priorité normale
    LOW = "low"              # Basse priorité
    BACKGROUND = "background"  # En arrière-plan


# ==========================================
# MESSAGE STATUS
# ==========================================

class MessageStatus(str, Enum):
    """Statut d'un message."""
    PENDING = "pending"        # En attente
    SENT = "sent"              # Envoyé
    DELIVERED = "delivered"    # Délivré
    ACKNOWLEDGED = "acknowledged"  # Accusé réception
    PROCESSING = "processing"  # En traitement
    COMPLETED = "completed"    # Traité
    FAILED = "failed"          # Échec
    TIMEOUT = "timeout"        # Timeout


# ==========================================
# MESSAGE HEADER
# ==========================================

@dataclass
class MessageHeader:
    """
    En-tête d'un message.
    
    Contient les métadonnées de routage et traçabilité.
    """
    # Identity
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Routing
    sender: str = ""
    receiver: str = ""
    
    # Conversation
    conversation_id: Optional[str] = None
    in_reply_to: Optional[str] = None  # ID du message auquel on répond
    correlation_id: Optional[str] = None  # Pour corréler requêtes/réponses
    
    # Type
    message_type: MessageType = MessageType.QUERY
    priority: MessagePriority = MessagePriority.NORMAL
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None  # Time-to-live
    timeout_ms: Optional[float] = None  # Timeout de réponse
    
    # Version
    protocol_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "message_id": self.message_id,
            "trace_id": self.trace_id,
            "sender": self.receiver,
            "receiver": self.receiver,
            "conversation_id": self.conversation_id,
            "in_reply_to": self.in_reply_to,
            "correlation_id": self.correlation_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "timeout_ms": self.timeout_ms,
            "protocol_version": self.protocol_version,
        }


# ==========================================
# MESSAGE PAYLOAD
# ==========================================

@dataclass
class MessagePayload:
    """
    Contenu d'un message.
    
    Structure flexible pour différents types de données.
    """
    # Content
    content: str = ""
    content_type: str = "text/plain"  # text/plain, application/json, etc.
    
    # Structured data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Attachments
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context to share
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Task info (for task messages)
    task_id: Optional[str] = None
    task_goal: Optional[str] = None
    task_context: Optional[str] = None
    
    # Result info (for result messages)
    result: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    
    # Confidence
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "content": self.content,
            "content_type": self.content_type,
            "data": self.data,
            "attachments": self.attachments,
            "context": self.context,
            "task_id": self.task_id,
            "task_goal": self.task_goal,
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "confidence": self.confidence,
        }


# ==========================================
# AGENT MESSAGE
# ==========================================

@dataclass
class AgentMessage:
    """
    Message standard entre agents Phoenix.
    
    C'est LE format de communication pour tout le système multi-agent.
    
    Architecture:
        Sender Agent
            │
            ├── Create AgentMessage
            │       │
            │       ├── header (routing, tracing)
            │       └── payload (content, data)
            │
            └── Send → Receiver Agent
                            │
                            ├── Validate
                            ├── Process
                            └── Respond
    
    Example:
        # Créer un message de délégation
        msg = AgentMessage.create_delegation(
            sender="orchestrator",
            receiver="coder-1",
            task_id="task-123",
            task_goal="Implement authentication",
            context="Use OAuth2 with JWT tokens"
        )
        
        # Envoyer
        response = await send_message(msg)
        
        # Créer une réponse
        reply = AgentMessage.create_response(
            original=msg,
            content="Authentication implemented",
            success=True
        )
    """
    # Header
    header: MessageHeader = field(default_factory=MessageHeader)
    
    # Payload
    payload: MessagePayload = field(default_factory=MessagePayload)
    
    # Status
    status: MessageStatus = MessageStatus.PENDING
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ==========================================
    # FACTORY METHODS
    # ==========================================
    
    @classmethod
    def create(
        cls,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: str = "",
        data: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ) -> "AgentMessage":
        """Factory pour créer un message."""
        header = MessageHeader(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            priority=priority,
        )
        
        payload = MessagePayload(
            content=content,
            data=data or {},
        )
        
        # Appliquer kwargs
        for key, value in kwargs.items():
            if hasattr(payload, key):
                setattr(payload, key, value)
        
        return cls(header=header, payload=payload)
    
    @classmethod
    def create_task_request(
        cls,
        sender: str,
        receiver: str,
        task_id: str,
        task_goal: str,
        task_context: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> "AgentMessage":
        """Crée un message de demande de tâche."""
        msg = cls.create(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.TASK_REQUEST,
            priority=priority,
        )
        msg.payload.task_id = task_id
        msg.payload.task_goal = task_goal
        msg.payload.task_context = task_context
        return msg
    
    @classmethod
    def create_delegation(
        cls,
        sender: str,
        receiver: str,
        task_id: str,
        task_goal: str,
        context: Optional[str] = None,
        priority: MessagePriority = MessagePriority.HIGH,
    ) -> "AgentMessage":
        """Crée un message de délégation."""
        msg = cls.create(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.DELEGATE_REQUEST,
            priority=priority,
        )
        msg.payload.task_id = task_id
        msg.payload.task_goal = task_goal
        msg.payload.task_context = context
        return msg
    
    @classmethod
    def create_response(
        cls,
        original: "AgentMessage",
        content: str = "",
        result: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> "AgentMessage":
        """Crée une réponse à un message."""
        # Déterminer le type de réponse
        if original.header.message_type == MessageType.DELEGATE_REQUEST:
            response_type = MessageType.DELEGATE_RESULT if success else MessageType.DELEGATE_REJECT
        elif original.header.message_type == MessageType.QUERY:
            response_type = MessageType.QUERY_RESPONSE
        elif original.header.message_type == MessageType.TASK_REQUEST:
            response_type = MessageType.TASK_RESULT
        else:
            response_type = MessageType.QUERY_RESPONSE
        
        msg = cls.create(
            sender=original.header.receiver,
            receiver=original.header.sender,
            message_type=response_type,
            content=content,
        )
        
        # Corrélation
        msg.header.in_reply_to = original.header.message_id
        msg.header.correlation_id = original.header.message_id
        msg.header.conversation_id = original.header.conversation_id
        msg.header.trace_id = original.header.trace_id
        
        # Payload
        msg.payload.result = result
        msg.payload.success = success
        msg.payload.error = error
        msg.payload.task_id = original.payload.task_id
        
        return msg
    
    @classmethod
    def create_error(
        cls,
        sender: str,
        receiver: str,
        error: str,
        original_message_id: Optional[str] = None,
    ) -> "AgentMessage":
        """Crée un message d'erreur."""
        msg = cls.create(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.ERROR,
            priority=MessagePriority.HIGH,
        )
        msg.payload.error = error
        msg.payload.success = False
        if original_message_id:
            msg.header.in_reply_to = original_message_id
        return msg
    
    @classmethod
    def create_heartbeat(
        cls,
        sender: str,
        receiver: str,
    ) -> "AgentMessage":
        """Crée un message heartbeat."""
        return cls.create(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.HEARTBEAT,
            priority=MessagePriority.LOW,
        )
    
    @classmethod
    def create_context_share(
        cls,
        sender: str,
        receiver: str,
        context: Dict[str, Any],
    ) -> "AgentMessage":
        """Crée un message de partage de contexte."""
        msg = cls.create(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.CONTEXT_SHARE,
        )
        msg.payload.context = context
        return msg
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    
    @property
    def message_id(self) -> str:
        """ID du message."""
        return self.header.message_id
    
    @property
    def sender(self) -> str:
        """Expéditeur."""
        return self.header.sender
    
    @property
    def receiver(self) -> str:
        """Destinataire."""
        return self.header.receiver
    
    @property
    def message_type(self) -> MessageType:
        """Type du message."""
        return self.header.message_type
    
    @property
    def is_request(self) -> bool:
        """Est une requête."""
        return self.header.message_type in [
            MessageType.TASK_REQUEST,
            MessageType.DELEGATE_REQUEST,
            MessageType.QUERY,
            MessageType.CONTEXT_REQUEST,
        ]
    
    @property
    def is_response(self) -> bool:
        """Est une réponse."""
        return self.header.message_type in [
            MessageType.TASK_RESULT,
            MessageType.DELEGATE_RESULT,
            MessageType.QUERY_RESPONSE,
            MessageType.DELEGATE_ACCEPT,
            MessageType.DELEGATE_REJECT,
        ]
    
    @property
    def is_error(self) -> bool:
        """Est une erreur."""
        return self.header.message_type == MessageType.ERROR or not self.payload.success
    
    @property
    def is_expired(self) -> bool:
        """Le message a expiré."""
        if self.header.ttl_seconds is None:
            return False
        age = (datetime.utcnow() - self.header.timestamp).total_seconds()
        return age > self.header.ttl_seconds
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "header": self.header.to_dict(),
            "payload": self.payload.to_dict(),
            "status": self.status.value,
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convertit en JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Crée un message depuis un dict."""
        header_data = data.get("header", {})
        payload_data = data.get("payload", {})
        
        header = MessageHeader(
            message_id=header_data.get("message_id", str(uuid.uuid4())),
            trace_id=header_data.get("trace_id", str(uuid.uuid4())),
            sender=header_data.get("sender", ""),
            receiver=header_data.get("receiver", ""),
            conversation_id=header_data.get("conversation_id"),
            in_reply_to=header_data.get("in_reply_to"),
            correlation_id=header_data.get("correlation_id"),
            message_type=MessageType(header_data.get("message_type", "query")),
            priority=MessagePriority(header_data.get("priority", "normal")),
            timestamp=datetime.fromisoformat(header_data["timestamp"]) if "timestamp" in header_data else datetime.utcnow(),
            ttl_seconds=header_data.get("ttl_seconds"),
            timeout_ms=header_data.get("timeout_ms"),
        )
        
        payload = MessagePayload(
            content=payload_data.get("content", ""),
            content_type=payload_data.get("content_type", "text/plain"),
            data=payload_data.get("data", {}),
            context=payload_data.get("context", {}),
            task_id=payload_data.get("task_id"),
            task_goal=payload_data.get("task_goal"),
            task_context=payload_data.get("task_context"),
            result=payload_data.get("result"),
            success=payload_data.get("success", True),
            error=payload_data.get("error"),
            confidence=payload_data.get("confidence"),
        )
        
        status = MessageStatus(data.get("status", "pending"))
        
        return cls(
            header=header,
            payload=payload,
            status=status,
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """Crée un message depuis JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


# ==========================================
# MESSAGE ACK
# ==========================================

@dataclass
class MessageAck:
    """
    Accusé de réception d'un message.
    """
    message_id: str
    ack_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Status
    received: bool = True
    processed: bool = False
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "ack_id": self.ack_id,
            "timestamp": self.timestamp.isoformat(),
            "received": self.received,
            "processed": self.processed,
            "success": self.success,
            "error": self.error,
        }


# ==========================================
# MESSAGE BUS INTERFACE
# ==========================================

class MessageBus:
    """
    Bus de messages pour la communication entre agents.
    
    Interface pour envoyer et recevoir des messages.
    
    v0.6: Interface avec implémentation in-memory
    v1.0: Implémentation avec vrai message broker (Redis, RabbitMQ)
    """
    
    def __init__(self):
        self._handlers: Dict[MessageType, List[Any]] = {}
        self._message_history: List[AgentMessage] = []
        self._pending_acks: Dict[str, MessageAck] = {}
    
    # ==========================================
    # REGISTRATION
    # ==========================================
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: Any,  # Callable[[AgentMessage], None]
    ) -> None:
        """Enregistre un handler pour un type de message."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
    
    def unregister_handler(
        self,
        message_type: MessageType,
        handler: Any,
    ) -> bool:
        """Désenregistre un handler."""
        if message_type in self._handlers:
            try:
                self._handlers[message_type].remove(handler)
                return True
            except ValueError:
                pass
        return False
    
    # ==========================================
    # SEND / RECEIVE
    # ==========================================
    
    async def send(self, message: AgentMessage) -> MessageAck:
        """
        Envoie un message.
        
        Args:
            message: Le message à envoyer
            
        Returns:
            MessageAck accusant réception
        """
        message.status = MessageStatus.SENT
        
        # Enregistrer dans l'historique
        self._message_history.append(message)
        
        # Créer l'ACK
        ack = MessageAck(message_id=message.message_id)
        self._pending_acks[message.message_id] = ack
        
        # Dispatcher aux handlers
        handlers = self._handlers.get(message.header.message_type, [])
        for handler in handlers:
            try:
                await self._dispatch(handler, message)
                ack.processed = True
            except Exception as e:
                ack.success = False
                ack.error = str(e)
                logger.error(f"Error processing message {message.message_id}: {e}")
        
        message.status = MessageStatus.DELIVERED
        ack.received = True
        
        logger.debug(f"Message {message.message_id} sent to {message.receiver}")
        
        return ack
    
    async def _dispatch(self, handler: Any, message: AgentMessage) -> None:
        """Dispatch à un handler."""
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)
    
    def receive(self, timeout_ms: Optional[float] = None) -> Optional[AgentMessage]:
        """
        Reçoit un message (non-bloquant pour l'instant).
        
        Args:
            timeout_ms: Timeout en ms
            
        Returns:
            AgentMessage ou None
        """
        # v0.6: Simple polling de l'historique
        # v1.0: True message queue
        if self._message_history:
            msg = self._message_history[-1]
            msg.status = MessageStatus.PROCESSING
            return msg
        return None
    
    # ==========================================
    # ACK MANAGEMENT
    # ==========================================
    
    def ack(self, message_id: str, success: bool = True, error: Optional[str] = None) -> bool:
        """Accuse réception d'un message."""
        if message_id in self._pending_acks:
            ack = self._pending_acks[message_id]
            ack.processed = True
            ack.success = success
            ack.error = error
            return True
        return False
    
    def get_ack(self, message_id: str) -> Optional[MessageAck]:
        """Récupère l'ACK d'un message."""
        return self._pending_acks.get(message_id)
    
    # ==========================================
    # HISTORY
    # ==========================================
    
    def get_history(
        self,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 10,
    ) -> List[AgentMessage]:
        """Récupère l'historique filtré."""
        messages = self._message_history
        
        if sender:
            messages = [m for m in messages if m.sender == sender]
        if receiver:
            messages = [m for m in messages if m.receiver == receiver]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        return messages[-limit:]
    
    def clear_history(self) -> None:
        """Efface l'historique."""
        self._message_history.clear()
        self._pending_acks.clear()
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du bus."""
        type_counts: Dict[str, int] = {}
        for msg in self._message_history:
            key = msg.message_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
        
        return {
            "total_messages": len(self._message_history),
            "pending_acks": len(self._pending_acks),
            "handlers_registered": sum(len(h) for h in self._handlers.values()),
            "message_types": type_counts,
        }


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_message(
    sender: str,
    receiver: str,
    message_type: MessageType,
    content: str = "",
    **kwargs
) -> AgentMessage:
    """Factory rapide pour créer un message."""
    return AgentMessage.create(
        sender=sender,
        receiver=receiver,
        message_type=message_type,
        content=content,
        **kwargs
    )


def create_delegation_message(
    sender: str,
    receiver: str,
    task_id: str,
    task_goal: str,
    context: Optional[str] = None,
) -> AgentMessage:
    """Factory rapide pour créer un message de délégation."""
    return AgentMessage.create_delegation(
        sender=sender,
        receiver=receiver,
        task_id=task_id,
        task_goal=task_goal,
        context=context,
    )


def create_response_message(
    original: AgentMessage,
    content: str = "",
    result: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> AgentMessage:
    """Factory rapide pour créer une réponse."""
    return AgentMessage.create_response(
        original=original,
        content=content,
        result=result,
        success=success,
        error=error,
    )
