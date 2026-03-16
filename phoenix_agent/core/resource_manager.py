"""
Phoenix Agent - Resource Manager
================================

Contrôle des ressources runtime - ÉVITE les délégations incontrôlées.

Sans ResourceManager:
    - Délégation storm (trop de sub-agents)
    - Budget tokens explosé
    - Temps d'exécution non borné
    - Memory leak dans les slots agents
    - Cascade failures

Avec ResourceManager:
    - Budgets stricts avec enforcement
    - Allocation intelligente des ressources
    - Throttling automatique
    - Prévention des storms
    - Monitoring en temps réel

RESSOURCES CONTRÔLÉES:
    - agent_slots: Nombre max de sub-agents simultanés
    - token_budget: Budget de tokens LLM
    - time_budget: Temps d'exécution max
    - delegation_budget: Nombre max de délégations
    - memory_budget: Mémoire allouée
    - iteration_budget: Itérations max

STRATÉGIES:
    - HARD: Refuser si limite atteinte
    - SOFT: Warning mais autoriser
    - ADAPTIVE: Ajuster dynamiquement

Version: 1.0.0 (Runtime Resource Control)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import uuid


logger = logging.getLogger("phoenix.resource_manager")


# ==========================================
# ENFORCEMENT STRATEGY
# ==========================================

class EnforcementStrategy(str, Enum):
    """Stratégie d'application des limites."""
    HARD = "hard"           # Refuser si limite atteinte
    SOFT = "soft"           # Warning mais autoriser
    ADAPTIVE = "adaptive"   # Ajuster dynamiquement


class ResourceType(str, Enum):
    """Types de ressources."""
    AGENT_SLOTS = "agent_slots"         # Sub-agents simultanés
    TOKENS = "tokens"                   # LLM tokens
    TIME = "time"                       # Temps d'exécution
    DELEGATIONS = "delegations"         # Nombre de délégations
    MEMORY = "memory"                   # Mémoire (bytes)
    ITERATIONS = "iterations"           # Itérations
    TASKS = "tasks"                     # Tâches actives
    MESSAGES = "messages"               # Messages inter-agents


class AllocationStatus(str, Enum):
    """Status d'une allocation."""
    GRANTED = "granted"         # Alloué avec succès
    DENIED = "denied"           # Refusé (limite dure)
    THROTTLED = "throttled"     # Retardé (rate limiting)
    PARTIAL = "partial"         # Alloué partiellement
    QUEUED = "queued"           # En file d'attente


# ==========================================
# RESOURCE BUDGET
# ==========================================

@dataclass
class ResourceBudget:
    """Budget pour un type de ressource."""
    resource_type: ResourceType
    max_value: float
    current_value: float = 0.0
    
    # Strategy
    enforcement: EnforcementStrategy = EnforcementStrategy.HARD
    
    # Reserved for critical operations
    reserved: float = 0.0
    
    # Warning threshold (percentage)
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95
    
    # Tracking
    allocations_count: int = 0
    denials_count: int = 0
    
    @property
    def available(self) -> float:
        """Quantité disponible."""
        return max(0.0, self.max_value - self.current_value - self.reserved)
    
    @property
    def utilization(self) -> float:
        """Taux d'utilisation."""
        if self.max_value == 0:
            return 0.0
        return self.current_value / self.max_value
    
    @property
    def is_exhausted(self) -> bool:
        """Ressource épuisée."""
        return self.available <= 0
    
    @property
    def is_warning(self) -> bool:
        """Seuil de warning atteint."""
        return self.utilization >= self.warning_threshold
    
    @property
    def is_critical(self) -> bool:
        """Seuil critique atteint."""
        return self.utilization >= self.critical_threshold
    
    def can_allocate(self, amount: float) -> bool:
        """Vérifie si on peut allouer."""
        return amount <= self.available
    
    def allocate(self, amount: float) -> bool:
        """Alloue la ressource."""
        if not self.can_allocate(amount):
            self.denials_count += 1
            return False
        
        self.current_value += amount
        self.allocations_count += 1
        return True
    
    def release(self, amount: float) -> None:
        """Libère la ressource."""
        self.current_value = max(0.0, self.current_value - amount)
    
    def reset(self) -> None:
        """Réinitialise le budget."""
        self.current_value = 0.0
        self.allocations_count = 0
        self.denials_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type.value,
            "max_value": self.max_value,
            "current_value": self.current_value,
            "available": self.available,
            "utilization": f"{self.utilization:.1%}",
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "enforcement": self.enforcement.value,
        }


# ==========================================
# RESOURCE ALLOCATION
# ==========================================

@dataclass
class ResourceAllocation:
    """Une allocation de ressource."""
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    resource_type: ResourceType = ResourceType.TOKENS
    amount: float = 0.0
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    goal_id: str = ""
    
    # Status
    status: AllocationStatus = AllocationStatus.GRANTED
    
    # Timestamps
    allocated_at: datetime = field(default_factory=datetime.utcnow)
    released_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """L'allocation est active."""
        return self.released_at is None
    
    @property
    def duration_ms(self) -> float:
        """Durée de l'allocation."""
        if self.released_at:
            return (self.released_at - self.allocated_at).total_seconds() * 1000
        return (datetime.utcnow() - self.allocated_at).total_seconds() * 1000
    
    def release(self) -> None:
        """Libère l'allocation."""
        self.released_at = datetime.utcnow()
        self.status = AllocationStatus.GRANTED  # Completed


# ==========================================
# RESOURCE REQUEST
# ==========================================

@dataclass
class ResourceRequest:
    """Demande de ressources."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Resources needed
    resources: Dict[ResourceType, float] = field(default_factory=dict)
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    goal_id: str = ""
    
    # Priority (higher = more important)
    priority: int = 5  # 1-10
    
    # Can wait?
    deferrable: bool = True
    
    # Partial allocation ok?
    allow_partial: bool = False
    
    # Timestamp
    requested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "resources": {k.value: v for k, v in self.resources.items()},
            "priority": self.priority,
            "deferrable": self.deferrable,
        }


# ==========================================
# RESOURCE CONFIG
# ==========================================

@dataclass
class ResourceManagerConfig:
    """Configuration du ResourceManager."""
    # Default budgets
    default_agent_slots: int = 5
    default_token_budget: int = 100000
    default_time_budget_ms: float = 300000.0  # 5 minutes
    default_delegation_budget: int = 20
    default_memory_budget: int = 100 * 1024 * 1024  # 100 MB
    default_iteration_budget: int = 100
    default_task_budget: int = 50
    default_message_budget: int = 1000
    
    # Enforcement
    default_enforcement: EnforcementStrategy = EnforcementStrategy.HARD
    
    # Throttling
    enable_throttling: bool = True
    throttle_delay_ms: float = 100.0
    
    # Queuing
    enable_queuing: bool = True
    max_queue_size: int = 100
    
    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval_ms: float = 1000.0
    
    # Auto-adjustment
    enable_auto_adjustment: bool = False
    adjustment_interval_s: float = 60.0


# ==========================================
# RESOURCE MANAGER
# ==========================================

class ResourceManager:
    """
    Gestionnaire des ressources runtime.
    
    C'est LE composant qui répond à: "Ai-je assez de ressources pour ça?"
    
    Responsabilités:
        1. Allouer les ressources
        2. Enforcer les limites
        3. Prévenir les storms
        4. Monitorer l'utilisation
        5. Throttler si nécessaire
    
    Architecture:
        AgentRuntimeController
        │
        └── ResourceManager
                │
                ├── Budgets (tokens, time, agents, etc.)
                │
                ├── AllocationQueue
                │
                └── Throttler
    
    Example:
        manager = ResourceManager()
        
        # Initialize budgets
        manager.initialize_budgets()
        
        # Request resources
        request = ResourceRequest(
            resources={
                ResourceType.TOKENS: 1000,
                ResourceType.AGENT_SLOTS: 1,
            },
            task_id="task-001",
        )
        
        allocation = manager.request(request)
        
        if allocation.status == AllocationStatus.GRANTED:
            # Execute
            pass
        else:
            # Wait or fail
            pass
        
        # Release when done
        manager.release(allocation.allocation_id)
    """
    
    def __init__(self, config: Optional[ResourceManagerConfig] = None):
        self.config = config or ResourceManagerConfig()
        
        # Budgets
        self._budgets: Dict[ResourceType, ResourceBudget] = {}
        
        # Active allocations
        self._allocations: Dict[str, ResourceAllocation] = {}
        
        # Request queue
        self._request_queue: List[ResourceRequest] = []
        
        # History
        self._allocation_history: List[ResourceAllocation] = []
        self._denial_history: List[ResourceRequest] = []
        
        # Throttling state
        self._throttle_until: Optional[datetime] = None
        self._throttle_reason: str = ""
        
        # Callbacks
        self._on_exhausted: List[Callable[[ResourceType], None]] = []
        self._on_warning: List[Callable[[ResourceType, float], None]] = []
        self._on_throttle: List[Callable[[str], None]] = []
        
        # Stats
        self._total_requests = 0
        self._total_granted = 0
        self._total_denied = 0
        
        logger.info("ResourceManager initialized")
    
    # ==========================================
    # INITIALIZATION
    # ==========================================
    
    def initialize_budgets(self) -> None:
        """Initialise les budgets par défaut."""
        self._budgets = {
            ResourceType.AGENT_SLOTS: ResourceBudget(
                resource_type=ResourceType.AGENT_SLOTS,
                max_value=self.config.default_agent_slots,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.TOKENS: ResourceBudget(
                resource_type=ResourceType.TOKENS,
                max_value=self.config.default_token_budget,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.TIME: ResourceBudget(
                resource_type=ResourceType.TIME,
                max_value=self.config.default_time_budget_ms,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.DELEGATIONS: ResourceBudget(
                resource_type=ResourceType.DELEGATIONS,
                max_value=self.config.default_delegation_budget,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.MEMORY: ResourceBudget(
                resource_type=ResourceType.MEMORY,
                max_value=self.config.default_memory_budget,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.ITERATIONS: ResourceBudget(
                resource_type=ResourceType.ITERATIONS,
                max_value=self.config.default_iteration_budget,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.TASKS: ResourceBudget(
                resource_type=ResourceType.TASKS,
                max_value=self.config.default_task_budget,
                enforcement=self.config.default_enforcement,
            ),
            ResourceType.MESSAGES: ResourceBudget(
                resource_type=ResourceType.MESSAGES,
                max_value=self.config.default_message_budget,
                enforcement=self.config.default_enforcement,
            ),
        }
        
        logger.info(f"Initialized {len(self._budgets)} resource budgets")
    
    def set_budget(
        self,
        resource_type: ResourceType,
        max_value: float,
        enforcement: Optional[EnforcementStrategy] = None,
    ) -> None:
        """Définit un budget personnalisé."""
        if resource_type in self._budgets:
            self._budgets[resource_type].max_value = max_value
            if enforcement:
                self._budgets[resource_type].enforcement = enforcement
        else:
            self._budgets[resource_type] = ResourceBudget(
                resource_type=resource_type,
                max_value=max_value,
                enforcement=enforcement or self.config.default_enforcement,
            )
    
    # ==========================================
    # MAIN REQUEST
    # ==========================================
    
    def request(self, request: ResourceRequest) -> ResourceAllocation:
        """
        Demande des ressources.
        
        C'est LA méthode centrale du ResourceManager.
        
        Args:
            request: La demande de ressources
            
        Returns:
            ResourceAllocation avec le status
        """
        self._total_requests += 1
        
        # Check throttling
        if self._is_throttled():
            return self._create_throttled_allocation(request)
        
        # Check if can fulfill
        can_fulfill, partial_amounts = self._check_availability(request)
        
        if can_fulfill:
            return self._grant_allocation(request)
        elif request.allow_partial and partial_amounts:
            return self._grant_partial_allocation(request, partial_amounts)
        elif request.deferrable and self.config.enable_queuing:
            return self._queue_request(request)
        else:
            return self._deny_request(request)
    
    def _is_throttled(self) -> bool:
        """Vérifie si on est throttled."""
        if self._throttle_until is None:
            return False
        return datetime.utcnow() < self._throttle_until
    
    def _check_availability(
        self,
        request: ResourceRequest,
    ) -> tuple[bool, Dict[ResourceType, float]]:
        """Vérifie la disponibilité."""
        can_fulfill = True
        partial_amounts: Dict[ResourceType, float] = {}
        
        for resource_type, amount in request.resources.items():
            budget = self._budgets.get(resource_type)
            if not budget:
                continue
            
            if not budget.can_allocate(amount):
                can_fulfill = False
                
                # Check if partial available
                if budget.available > 0:
                    partial_amounts[resource_type] = budget.available
        
        return can_fulfill, partial_amounts
    
    def _grant_allocation(self, request: ResourceRequest) -> ResourceAllocation:
        """Accorde l'allocation."""
        # Allocate all resources
        for resource_type, amount in request.resources.items():
            budget = self._budgets.get(resource_type)
            if budget:
                budget.allocate(amount)
        
        # Create allocation record
        allocation = ResourceAllocation(
            resource_type=ResourceType.TOKENS,  # Primary
            amount=sum(request.resources.values()),
            agent_id=request.agent_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            status=AllocationStatus.GRANTED,
            metadata={"resources": {k.value: v for k, v in request.resources.items()}},
        )
        
        self._allocations[allocation.allocation_id] = allocation
        self._total_granted += 1
        
        # Check for warnings
        self._check_warnings()
        
        logger.debug(f"Granted allocation {allocation.allocation_id}")
        return allocation
    
    def _grant_partial_allocation(
        self,
        request: ResourceRequest,
        partial_amounts: Dict[ResourceType, float],
    ) -> ResourceAllocation:
        """Accorde une allocation partielle."""
        # Allocate partial amounts
        total = 0.0
        for resource_type, amount in partial_amounts.items():
            budget = self._budgets.get(resource_type)
            if budget and budget.can_allocate(amount):
                budget.allocate(amount)
                total += amount
        
        allocation = ResourceAllocation(
            resource_type=ResourceType.TOKENS,
            amount=total,
            agent_id=request.agent_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            status=AllocationStatus.PARTIAL,
            metadata={
                "requested": {k.value: v for k, v in request.resources.items()},
                "granted": {k.value: v for k, v in partial_amounts.items()},
            },
        )
        
        self._allocations[allocation.allocation_id] = allocation
        self._total_granted += 1
        
        logger.info(f"Granted partial allocation {allocation.allocation_id}")
        return allocation
    
    def _deny_request(self, request: ResourceRequest) -> ResourceAllocation:
        """Refuse la demande."""
        # Record denial
        self._denial_history.append(request)
        self._total_denied += 1
        
        # Update budget denial counts
        for resource_type in request.resources:
            budget = self._budgets.get(resource_type)
            if budget:
                budget.denials_count += 1
        
        allocation = ResourceAllocation(
            resource_type=ResourceType.TOKENS,
            amount=0.0,
            agent_id=request.agent_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            status=AllocationStatus.DENIED,
        )
        
        logger.warning(f"Denied allocation request {request.request_id}")
        return allocation
    
    def _queue_request(self, request: ResourceRequest) -> ResourceAllocation:
        """Met en file d'attente."""
        if len(self._request_queue) >= self.config.max_queue_size:
            return self._deny_request(request)
        
        self._request_queue.append(request)
        self._request_queue.sort(key=lambda r: r.priority, reverse=True)
        
        allocation = ResourceAllocation(
            resource_type=ResourceType.TOKENS,
            amount=0.0,
            agent_id=request.agent_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            status=AllocationStatus.QUEUED,
        )
        
        logger.info(f"Queued request {request.request_id}")
        return allocation
    
    def _create_throttled_allocation(self, request: ResourceRequest) -> ResourceAllocation:
        """Crée une allocation throttled."""
        allocation = ResourceAllocation(
            resource_type=ResourceType.TOKENS,
            amount=0.0,
            agent_id=request.agent_id,
            task_id=request.task_id,
            goal_id=request.goal_id,
            status=AllocationStatus.THROTTLED,
            metadata={"throttle_reason": self._throttle_reason},
        )
        
        return allocation
    
    # ==========================================
    # RELEASE
    # ==========================================
    
    def release(self, allocation_id: str) -> bool:
        """Libère une allocation."""
        allocation = self._allocations.get(allocation_id)
        if not allocation:
            return False
        
        # Get resources from metadata
        resources = allocation.metadata.get("resources", {})
        
        # Release each resource
        for resource_type_str, amount in resources.items():
            try:
                resource_type = ResourceType(resource_type_str)
                budget = self._budgets.get(resource_type)
                if budget:
                    budget.release(amount)
            except ValueError:
                pass
        
        # Mark allocation as released
        allocation.release()
        
        # Move to history
        self._allocation_history.append(allocation)
        del self._allocations[allocation_id]
        
        # Process queue
        self._process_queue()
        
        logger.debug(f"Released allocation {allocation_id}")
        return True
    
    def release_for_task(self, task_id: str) -> int:
        """Libère toutes les allocations d'une task."""
        count = 0
        to_release = [
            aid for aid, a in self._allocations.items()
            if a.task_id == task_id
        ]
        
        for aid in to_release:
            if self.release(aid):
                count += 1
        
        return count
    
    def release_all(self) -> int:
        """Libère toutes les allocations."""
        count = len(self._allocations)
        for allocation_id in list(self._allocations.keys()):
            self.release(allocation_id)
        return count
    
    # ==========================================
    # QUEUE PROCESSING
    # ==========================================
    
    def _process_queue(self) -> int:
        """Traite la file d'attente."""
        if not self._request_queue:
            return 0
        
        processed = 0
        remaining = []
        
        for request in self._request_queue:
            can_fulfill, _ = self._check_availability(request)
            
            if can_fulfill:
                self._grant_allocation(request)
                processed += 1
            else:
                remaining.append(request)
        
        self._request_queue = remaining
        return processed
    
    # ==========================================
    # THROTTLING
    # ==========================================
    
    def throttle(self, duration_ms: float, reason: str = "") -> None:
        """Active le throttling."""
        self._throttle_until = datetime.utcnow() + timedelta(milliseconds=duration_ms)
        self._throttle_reason = reason
        
        # Callbacks
        for callback in self._on_throttle:
            try:
                callback(reason)
            except Exception as e:
                logger.error(f"Throttle callback error: {e}")
        
        logger.warning(f"Throttled for {duration_ms}ms: {reason}")
    
    def clear_throttle(self) -> None:
        """Désactive le throttling."""
        self._throttle_until = None
        self._throttle_reason = ""
        logger.info("Throttle cleared")
    
    # ==========================================
    # MONITORING
    # ==========================================
    
    def _check_warnings(self) -> None:
        """Vérifie les seuils de warning."""
        for resource_type, budget in self._budgets.items():
            if budget.is_critical:
                for callback in self._on_exhausted:
                    try:
                        callback(resource_type)
                    except Exception as e:
                        logger.error(f"Exhausted callback error: {e}")
            
            elif budget.is_warning:
                for callback in self._on_warning:
                    try:
                        callback(resource_type, budget.utilization)
                    except Exception as e:
                        logger.error(f"Warning callback error: {e}")
    
    def get_utilization(self) -> Dict[ResourceType, float]:
        """Retourne l'utilisation de chaque ressource."""
        return {rt: budget.utilization for rt, budget in self._budgets.items()}
    
    def get_budget(self, resource_type: ResourceType) -> Optional[ResourceBudget]:
        """Récupère un budget."""
        return self._budgets.get(resource_type)
    
    def get_all_budgets(self) -> Dict[ResourceType, ResourceBudget]:
        """Retourne tous les budgets."""
        return self._budgets.copy()
    
    def get_active_allocations(self) -> List[ResourceAllocation]:
        """Retourne les allocations actives."""
        return list(self._allocations.values())
    
    def get_queue_size(self) -> int:
        """Taille de la file d'attente."""
        return len(self._request_queue)
    
    # ==========================================
    # CONVENIENCE METHODS
    # ==========================================
    
    def can_delegate(self) -> bool:
        """Vérifie si on peut déléguer."""
        slots = self._budgets.get(ResourceType.AGENT_SLOTS)
        delegations = self._budgets.get(ResourceType.DELEGATIONS)
        
        slots_ok = slots and slots.available > 0 if slots else True
        delegations_ok = delegations and delegations.available > 0 if delegations else True
        
        return slots_ok and delegations_ok
    
    def can_execute(self, estimated_tokens: int = 0) -> bool:
        """Vérifie si on peut exécuter."""
        tokens = self._budgets.get(ResourceType.TOKENS)
        iterations = self._budgets.get(ResourceType.ITERATIONS)
        
        tokens_ok = tokens and tokens.can_allocate(estimated_tokens) if tokens and estimated_tokens > 0 else True
        iterations_ok = iterations and iterations.available > 0 if iterations else True
        
        return tokens_ok and iterations_ok
    
    def allocate_tokens(self, amount: int, task_id: str = "") -> ResourceAllocation:
        """Alloue des tokens directement."""
        request = ResourceRequest(
            resources={ResourceType.TOKENS: amount},
            task_id=task_id,
            priority=5,
        )
        return self.request(request)
    
    def allocate_agent_slot(self, agent_id: str, task_id: str = "") -> ResourceAllocation:
        """Alloue un slot d'agent."""
        request = ResourceRequest(
            resources={ResourceType.AGENT_SLOTS: 1},
            agent_id=agent_id,
            task_id=task_id,
            priority=7,
        )
        return self.request(request)
    
    def record_delegation(self) -> bool:
        """Enregistre une délégation."""
        budget = self._budgets.get(ResourceType.DELEGATIONS)
        if budget and budget.can_allocate(1):
            budget.allocate(1)
            return True
        return False
    
    def record_iteration(self) -> bool:
        """Enregistre une itération."""
        budget = self._budgets.get(ResourceType.ITERATIONS)
        if budget and budget.can_allocate(1):
            budget.allocate(1)
            return True
        return False
    
    def record_time(self, duration_ms: float) -> None:
        """Enregistre du temps d'exécution."""
        budget = self._budgets.get(ResourceType.TIME)
        if budget:
            budget.allocate(duration_ms)
    
    # ==========================================
    # STATS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return {
            "total_requests": self._total_requests,
            "total_granted": self._total_granted,
            "total_denied": self._total_denied,
            "grant_rate": self._total_granted / self._total_requests if self._total_requests > 0 else 0,
            "active_allocations": len(self._allocations),
            "queued_requests": len(self._request_queue),
            "is_throttled": self._is_throttled(),
            "budgets": {k.value: v.to_dict() for k, v in self._budgets.items()},
        }
    
    # ==========================================
    # RESET
    # ==========================================
    
    def reset(self) -> None:
        """Réinitialise tous les budgets."""
        for budget in self._budgets.values():
            budget.reset()
        
        self._allocations.clear()
        self._request_queue.clear()
        self._throttle_until = None
        
        logger.info("ResourceManager reset")
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_exhausted(self, callback: Callable[[ResourceType], None]) -> None:
        """Callback pour ressource épuisée."""
        self._on_exhausted.append(callback)
    
    def on_warning(self, callback: Callable[[ResourceType, float], None]) -> None:
        """Callback pour warning de ressource."""
        self._on_warning.append(callback)
    
    def on_throttle(self, callback: Callable[[str], None]) -> None:
        """Callback pour throttling."""
        self._on_throttle.append(callback)


# ==========================================
# FACTORY
# ==========================================

def create_resource_manager(
    config: Optional[ResourceManagerConfig] = None,
) -> ResourceManager:
    """Factory pour créer un ResourceManager."""
    manager = ResourceManager(config=config)
    manager.initialize_budgets()
    return manager
