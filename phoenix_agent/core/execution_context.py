"""
Phoenix Agent - Execution Context
==================================

Contexte d'exécution pour le traçage des tâches et délégations.

Sans ExecutionContext:
    - Impossible de debugger
    - Impossible de contrôler la profondeur de délégation
    - Pas de traçabilité
    - Pas de corrélation entre tâches parent/enfant

Avec ExecutionContext:
    - Traçabilité complète
    - Contrôle de la délégation
    - Debug facilité
    - Corrélation des tâches

Architecture:
    Task → ExecutionContext → Execution Trace → Debug/Analytics

COMPOSANTS:
    - ExecutionContext: Contexte complet d'une exécution
    - ExecutionTrace: Trace des événements d'exécution
    - ExecutionSpan: Segment d'exécution (pour distributed tracing)
    - DelegationChain: Chaîne de délégation

Version: 0.6.0 (Execution Tracing)
"""

from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
import json


logger = logging.getLogger("phoenix.execution_context")


# ==========================================
# EXECUTION STATUS
# ==========================================

class ExecutionStatus(str, Enum):
    """Statut d'une exécution."""
    PENDING = "pending"           # En attente
    RUNNING = "running"           # En cours
    DELEGATING = "delegating"     # Délégation en cours
    WAITING = "waiting"           # Attente de résultats
    COMPLETED = "completed"       # Terminé avec succès
    FAILED = "failed"             # Échec
    CANCELLED = "cancelled"       # Annulé
    TIMEOUT = "timeout"           # Timeout


# ==========================================
# EXECUTION EVENT TYPE
# ==========================================

class ExecutionEventType(str, Enum):
    """Types d'événements d'exécution."""
    # Lifecycle
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    # Actions
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    
    # Delegation
    DELEGATE_START = "delegate_start"
    DELEGATE_END = "delegate_end"
    DELEGATE_FAILED = "delegate_failed"
    
    # Memory
    MEMORY_COMPRESS = "memory_compress"
    MEMORY_OVERFLOW = "memory_overflow"
    
    # Recovery
    RETRY = "retry"
    RECOVERY = "recovery"
    FALLBACK = "fallback"
    
    # Custom
    CUSTOM = "custom"


# ==========================================
# EXECUTION SPAN
# ==========================================

@dataclass
class ExecutionSpan:
    """
    Segment d'exécution pour distributed tracing.
    
    Similaire à OpenTelemetry Span.
    """
    span_id: str
    name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Parent
    parent_span_id: Optional[str] = None
    
    # Context
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Status
    status: ExecutionStatus = ExecutionStatus.RUNNING
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Durée en ms."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    @property
    def is_finished(self) -> bool:
        """Le span est terminé."""
        return self.end_time is not None
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Ajoute un événement au span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Définit un attribut."""
        self.attributes[key] = value
    
    def end(self, status: ExecutionStatus = ExecutionStatus.COMPLETED) -> None:
        """Termine le span."""
        self.end_time = datetime.utcnow()
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "parent_span_id": self.parent_span_id,
            "status": self.status.value,
            "attributes": self.attributes,
            "events_count": len(self.events),
        }


# ==========================================
# EXECUTION TRACE EVENT
# ==========================================

@dataclass
class ExecutionTraceEvent:
    """
    Événement dans la trace d'exécution.
    
    Capture un moment précis de l'exécution.
    """
    event_id: str
    event_type: ExecutionEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    span_id: Optional[str] = None
    
    # Details
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Result
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "span_id": self.span_id,
            "description": self.description,
            "success": self.success,
            "error": self.error,
        }


# ==========================================
# DELEGATION CHAIN
# ==========================================

@dataclass
class DelegationChain:
    """
    Chaîne de délégation.
    
    Trace la hiérarchie des délégations.
    """
    chain_id: str
    root_task_id: str
    
    # Chain
    delegations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Stats
    total_delegations: int = 0
    max_depth: int = 0
    
    def add_delegation(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        parent_task_id: Optional[str] = None,
        depth: int = 0,
    ) -> None:
        """Ajoute une délégation à la chaîne."""
        self.delegations.append({
            "from_agent": from_agent,
            "to_agent": to_agent,
            "task_id": task_id,
            "parent_task_id": parent_task_id,
            "depth": depth,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.total_delegations += 1
        self.max_depth = max(self.max_depth, depth)
    
    def get_delegation_tree(self) -> Dict[str, Any]:
        """Construit l'arbre de délégation."""
        # Construire un arbre simple
        tree: Dict[str, Any] = {
            "root": self.root_task_id,
            "children": [],
        }
        
        # Grouper par parent
        by_parent: Dict[Optional[str], List[Dict[str, Any]]] = {}
        for delegation in self.delegations:
            parent = delegation.get("parent_task_id")
            if parent not in by_parent:
                by_parent[parent] = []
            by_parent[parent].append(delegation)
        
        # Construire récursivement
        def build_tree(task_id: Optional[str]) -> List[Dict[str, Any]]:
            children = by_parent.get(task_id, [])
            result = []
            for child in children:
                node = {
                    "task_id": child["task_id"],
                    "from_agent": child["from_agent"],
                    "to_agent": child["to_agent"],
                    "depth": child["depth"],
                    "children": build_tree(child["task_id"]),
                }
                result.append(node)
            return result
        
        tree["children"] = build_tree(self.root_task_id)
        return tree
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "chain_id": self.chain_id,
            "root_task_id": self.root_task_id,
            "total_delegations": self.total_delegations,
            "max_depth": self.max_depth,
            "delegations": self.delegations,
        }


# ==========================================
# EXECUTION CONTEXT
# ==========================================

@dataclass
class ExecutionContext:
    """
    Contexte complet d'exécution d'une tâche.
    
    C'est LE composant qui permet de:
        - Tracer l'exécution
        - Contrôler la délégation
        - Debugger les problèmes
        - Corréler les tâches parent/enfant
    
    Architecture:
        PhoenixOrchestrator
            │
            ├── ExecutionContext (créé pour chaque tâche)
            │       │
            │       ├── task_id, parent_task_id
            │       ├── delegation_depth
            │       ├── execution_trace
            │       ├── memory_snapshot
            │       │
            │       └── spawned_agents
            │
            └── AgentLoop
                    │
                    └── ExecutionContext.add_event(...)
    
    Example:
        # Créer un contexte
        ctx = ExecutionContext(
            task_id="task-123",
            agent_id="agent-main",
        )
        
        # Tracer l'exécution
        ctx.start()
        ctx.add_event(ExecutionEventType.THINK, "Analyzing task")
        ctx.add_event(ExecutionEventType.ACT, "Calling LLM")
        
        # Déléguer
        delegate_ctx = ctx.create_child_context(
            task_id="task-456",
            agent_id="agent-specialist"
        )
        
        # Terminer
        ctx.complete()
    """
    # Identity
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    agent_id: str = ""
    
    # Parent relationship
    parent_task_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    
    # Delegation
    delegation_depth: int = 0
    max_delegation_depth: int = 5
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Trace
    trace: List[ExecutionTraceEvent] = field(default_factory=list)
    spans: List[ExecutionSpan] = field(default_factory=list)
    current_span: Optional[ExecutionSpan] = None
    
    # Delegation chain
    delegation_chain: Optional[DelegationChain] = None
    
    # Spawned agents
    spawned_agents: List[str] = field(default_factory=list)
    
    # Retry
    retry_count: int = 0
    max_retries: int = 3
    
    # Memory snapshot
    memory_snapshot: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Durée totale en ms."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
    
    @property
    def is_running(self) -> bool:
        """L'exécution est en cours."""
        return self.status == ExecutionStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """L'exécution est terminée."""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        ]
    
    @property
    def can_delegate(self) -> bool:
        """Peut encore déléguer."""
        return self.delegation_depth < self.max_delegation_depth
    
    @property
    def can_retry(self) -> bool:
        """Peut encore retry."""
        return self.retry_count < self.max_retries
    
    # ==========================================
    # LIFECYCLE
    # ==========================================
    
    def start(self) -> None:
        """Démarre l'exécution."""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()
        
        # Créer le span racine
        self.current_span = ExecutionSpan(
            span_id=str(uuid.uuid4()),
            name=f"task-{self.task_id}",
        )
        self.spans.append(self.current_span)
        
        # Ajouter l'événement
        self.add_event(
            ExecutionEventType.STARTED,
            f"Execution started for task {self.task_id}"
        )
        
        logger.info(f"ExecutionContext {self.context_id} started for task {self.task_id}")
    
    def complete(self, result: Optional[str] = None) -> None:
        """Termine l'exécution avec succès."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        
        # Terminer le span
        if self.current_span:
            self.current_span.end(ExecutionStatus.COMPLETED)
            if result:
                self.current_span.set_attribute("result", result[:200])
        
        self.add_event(
            ExecutionEventType.COMPLETED,
            "Execution completed successfully"
        )
        
        logger.info(f"ExecutionContext {self.context_id} completed")
    
    def fail(self, error: str) -> None:
        """Termine l'exécution avec erreur."""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        
        # Terminer le span
        if self.current_span:
            self.current_span.end(ExecutionStatus.FAILED)
            self.current_span.set_attribute("error", error)
        
        self.add_event(
            ExecutionEventType.FAILED,
            f"Execution failed: {error}",
            error=error,
            success=False,
        )
        
        logger.error(f"ExecutionContext {self.context_id} failed: {error}")
    
    def cancel(self, reason: str = "") -> None:
        """Annule l'exécution."""
        self.status = ExecutionStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        if self.current_span:
            self.current_span.end(ExecutionStatus.CANCELLED)
        
        self.add_event(
            ExecutionEventType.CANCELLED,
            f"Execution cancelled: {reason}"
        )
        
        logger.info(f"ExecutionContext {self.context_id} cancelled: {reason}")
    
    # ==========================================
    # EVENTS
    # ==========================================
    
    def add_event(
        self,
        event_type: ExecutionEventType,
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        success: bool = True,
    ) -> ExecutionTraceEvent:
        """
        Ajoute un événement à la trace.
        
        Args:
            event_type: Type d'événement
            description: Description
            data: Données additionnelles
            error: Message d'erreur si applicable
            success: Succès de l'événement
            
        Returns:
            ExecutionTraceEvent créé
        """
        event = ExecutionTraceEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            agent_id=self.agent_id,
            task_id=self.task_id,
            span_id=self.current_span.span_id if self.current_span else None,
            description=description,
            data=data or {},
            error=error,
            success=success,
        )
        
        self.trace.append(event)
        
        # Ajouter au span courant
        if self.current_span:
            self.current_span.add_event(event_type.value, {
                "description": description,
                "success": success,
            })
        
        return event
    
    # ==========================================
    # SPANS
    # ==========================================
    
    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> ExecutionSpan:
        """Démarre un nouveau span."""
        span = ExecutionSpan(
            span_id=str(uuid.uuid4()),
            name=name,
            parent_span_id=parent_span_id or (self.current_span.span_id if self.current_span else None),
        )
        self.spans.append(span)
        self.current_span = span
        return span
    
    def end_span(self, status: ExecutionStatus = ExecutionStatus.COMPLETED) -> Optional[ExecutionSpan]:
        """Termine le span courant."""
        if self.current_span:
            self.current_span.end(status)
            ended = self.current_span
            
            # Remonter au span parent
            if self.current_span.parent_span_id:
                parent = next(
                    (s for s in self.spans if s.span_id == self.current_span.parent_span_id),
                    None
                )
                self.current_span = parent
            else:
                self.current_span = None
            
            return ended
        return None
    
    # ==========================================
    # DELEGATION
    # ==========================================
    
    def create_child_context(
        self,
        task_id: str,
        agent_id: str,
    ) -> "ExecutionContext":
        """
        Crée un contexte enfant pour la délégation.
        
        Args:
            task_id: ID de la tâche enfant
            agent_id: ID de l'agent qui recevra la délégation
            
        Returns:
            Nouveau ExecutionContext pour l'enfant
        """
        child = ExecutionContext(
            task_id=task_id,
            agent_id=agent_id,
            parent_task_id=self.task_id,
            parent_context_id=self.context_id,
            delegation_depth=self.delegation_depth + 1,
            max_delegation_depth=self.max_delegation_depth,
        )
        
        # Enregistrer l'agent spawné
        self.spawned_agents.append(agent_id)
        
        # Initialiser la chaîne de délégation si nécessaire
        if self.delegation_chain is None:
            self.delegation_chain = DelegationChain(
                chain_id=str(uuid.uuid4()),
                root_task_id=self.task_id,
            )
        
        child.delegation_chain = self.delegation_chain
        
        # Ajouter à la chaîne
        self.delegation_chain.add_delegation(
            from_agent=self.agent_id,
            to_agent=agent_id,
            task_id=task_id,
            parent_task_id=self.task_id,
            depth=child.delegation_depth,
        )
        
        # Ajouter l'événement
        self.add_event(
            ExecutionEventType.DELEGATE_START,
            f"Delegating to {agent_id}",
            data={
                "child_task_id": task_id,
                "child_context_id": child.context_id,
                "delegation_depth": child.delegation_depth,
            }
        )
        
        logger.info(
            f"Created child context {child.context_id} for delegation to {agent_id} "
            f"(depth: {child.delegation_depth})"
        )
        
        return child
    
    def record_delegation_result(
        self,
        child_context: "ExecutionContext",
        success: bool,
        result: Optional[str] = None,
    ) -> None:
        """Enregistre le résultat d'une délégation."""
        self.add_event(
            ExecutionEventType.DELEGATE_END if success else ExecutionEventType.DELEGATE_FAILED,
            f"Delegation to {child_context.agent_id} {'completed' if success else 'failed'}",
            data={
                "child_task_id": child_context.task_id,
                "success": success,
                "result": result[:200] if result else None,
            },
            success=success,
        )
    
    # ==========================================
    # RETRY
    # ==========================================
    
    def increment_retry(self) -> bool:
        """
        Incrémente le compteur de retry.
        
        Returns:
            True si retry est encore possible
        """
        self.retry_count += 1
        self.add_event(
            ExecutionEventType.RETRY,
            f"Retry attempt {self.retry_count}/{self.max_retries}"
        )
        return self.can_retry
    
    # ==========================================
    # MEMORY SNAPSHOT
    # ==========================================
    
    def take_memory_snapshot(self, memory_data: Dict[str, Any]) -> None:
        """Prend un snapshot de la mémoire."""
        self.memory_snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": memory_data,
        }
        self.add_event(
            ExecutionEventType.MEMORY_OVERFLOW,
            "Memory snapshot taken",
            data={"snapshot_size": len(str(memory_data))}
        )
    
    def restore_memory_snapshot(self) -> Optional[Dict[str, Any]]:
        """Restaure le snapshot de mémoire."""
        if self.memory_snapshot:
            self.add_event(
                ExecutionEventType.MEMORY_COMPRESS,
                "Memory snapshot restored"
            )
            return self.memory_snapshot.get("data")
        return None
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "context_id": self.context_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "parent_task_id": self.parent_task_id,
            "parent_context_id": self.parent_context_id,
            "delegation_depth": self.delegation_depth,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "spawned_agents": self.spawned_agents,
            "trace_events": len(self.trace),
            "spans": len(self.spans),
            "has_memory_snapshot": self.memory_snapshot is not None,
            "can_delegate": self.can_delegate,
            "metadata": self.metadata,
        }
    
    def to_trace_dict(self) -> Dict[str, Any]:
        """Convertit en dict avec trace complète."""
        result = self.to_dict()
        result["trace"] = [e.to_dict() for e in self.trace]
        result["spans"] = [s.to_dict() for s in self.spans]
        if self.delegation_chain:
            result["delegation_chain"] = self.delegation_chain.to_dict()
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Convertit en JSON."""
        return json.dumps(self.to_trace_dict(), indent=indent, default=str)


# ==========================================
# CONTEXT MANAGER
# ==========================================

class ExecutionContextManager:
    """
    Gestionnaire de contextes d'exécution.
    
    Permet de gérer plusieurs contextes actifs.
    """
    
    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
        self._active_context: Optional[ExecutionContext] = None
    
    def create_context(
        self,
        task_id: str,
        agent_id: str,
        parent_context_id: Optional[str] = None,
    ) -> ExecutionContext:
        """Crée un nouveau contexte."""
        if parent_context_id and parent_context_id in self._contexts:
            parent = self._contexts[parent_context_id]
            context = parent.create_child_context(task_id, agent_id)
        else:
            context = ExecutionContext(
                task_id=task_id,
                agent_id=agent_id,
            )
        
        self._contexts[context.context_id] = context
        self._active_context = context
        return context
    
    def get_context(self, context_id: str) -> Optional[ExecutionContext]:
        """Récupère un contexte par ID."""
        return self._contexts.get(context_id)
    
    def get_active_context(self) -> Optional[ExecutionContext]:
        """Retourne le contexte actif."""
        return self._active_context
    
    def set_active_context(self, context_id: str) -> bool:
        """Définit le contexte actif."""
        if context_id in self._contexts:
            self._active_context = self._contexts[context_id]
            return True
        return False
    
    def list_active_contexts(self) -> List[ExecutionContext]:
        """Liste les contextes actifs."""
        return [
            ctx for ctx in self._contexts.values()
            if ctx.status == ExecutionStatus.RUNNING
        ]
    
    def cleanup_completed(self) -> int:
        """Nettoie les contextes terminés."""
        completed_ids = [
            ctx_id for ctx_id, ctx in self._contexts.items()
            if ctx.is_completed
        ]
        for ctx_id in completed_ids:
            del self._contexts[ctx_id]
        return len(completed_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        contexts = list(self._contexts.values())
        return {
            "total_contexts": len(contexts),
            "active_contexts": sum(1 for c in contexts if c.is_running),
            "completed_contexts": sum(1 for c in contexts if c.is_completed),
            "contexts_by_status": {
                status.value: sum(1 for c in contexts if c.status == status)
                for status in ExecutionStatus
            },
        }


# ==========================================
# FACTORY
# ==========================================

def create_execution_context(
    task_id: str,
    agent_id: str,
    max_delegation_depth: int = 5,
) -> ExecutionContext:
    """Factory pour créer un contexte d'exécution."""
    return ExecutionContext(
        task_id=task_id,
        agent_id=agent_id,
        max_delegation_depth=max_delegation_depth,
    )
