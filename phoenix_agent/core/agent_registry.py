"""
Phoenix Agent - Agent Registry
==============================

Registre des agents pour la gestion de population.

Un Agent OS ne gère pas des "instances techniques".
Il gère des **entités agents** avec identité, santé, et performance.

Sans AgentRegistry:
    - SubAgentPool reste basique
    - Pas de sélection intelligente d'agents
    - Pas de tracking de santé population-wide
    - Pas de load balancing entre agents

Avec AgentRegistry:
    - Population d'agents avec identités
    - Sélection par capability, load, trust
    - Health monitoring population-wide
    - Performance tracking par agent
    - Agent lifecycle management

C'est LA couche qui permet à Phoenix de gérer une **population d'agents**
et pas juste des appels de fonction.

IDENTITY MODEL:
    AgentIdentity:
        - agent_id: Unique identifier
        - role: Functional role
        - capabilities: What it can do
        - current_state: Runtime state
        - health: Health metrics
        - load: Current load
        - specialization: Domain expertise
        - trust_score: Historical reliability
        - performance_score: Efficiency rating

Version: 1.0.0 (Agent Identity Layer)
"""

from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import uuid


logger = logging.getLogger("phoenix.agent_registry")


# ==========================================
# AGENT HEALTH STATUS
# ==========================================

class AgentHealthStatus(str, Enum):
    """Status de santé d'un agent."""
    HEALTHY = "healthy"             # Fonctionne normalement
    DEGRADED = "degraded"           # Performance réduite
    STRESSED = "stressed"           # Sous forte charge
    RECOVERING = "recovering"       # En récupération
    UNHEALTHY = "unhealthy"         # Problèmes détectés
    OFFLINE = "offline"             # Non disponible
    UNKNOWN = "unknown"             # Status inconnu


class AgentRoleCategory(str, Enum):
    """Catégories de rôles d'agents."""
    ORCHESTRATOR = "orchestrator"   # Coordination
    SPECIALIST = "specialist"       # Expertise domaine
    WORKER = "worker"               # Exécution
    SUPERVISOR = "supervisor"       # Supervision
    DELEGATOR = "delegator"         # Délégation
    PLANNER = "planner"             # Planification
    REVIEWER = "reviewer"           # Révision
    VALIDATOR = "validator"         # Validation


# ==========================================
# AGENT CAPABILITY RECORD
# ==========================================

@dataclass
class AgentCapabilityRecord:
    """Enregistrement d'une capacité d'agent."""
    name: str
    description: str = ""
    
    # Proficiency (0.0 - 1.0)
    proficiency: float = 1.0
    
    # Task types this capability supports
    supported_task_types: List[str] = field(default_factory=list)
    
    # Performance metrics for this capability
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_completion_time_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Taux de succès pour cette capacité."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total
    
    def record_task(self, success: bool, time_ms: float) -> None:
        """Enregistre une tâche."""
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        # Update average time
        n = self.tasks_completed + self.tasks_failed
        self.avg_completion_time_ms = (
            (self.avg_completion_time_ms * (n - 1) + time_ms) / n
        )


# ==========================================
# AGENT IDENTITY
# ==========================================

@dataclass
class AgentIdentity:
    """
    Identité complète d'un agent dans le registre.
    
    C'est LE modèle d'entité agent pour un Agent OS.
    
    Un agent n'est pas juste un ID.
    C'est une entité avec:
        - Identité persistante
        - Capacités déclarées
        - Santé trackée
        - Performance historique
        - Niveau de confiance
    """
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Identity
    name: str = ""
    description: str = ""
    role: AgentRoleCategory = AgentRoleCategory.WORKER
    
    # Registration
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: Optional[datetime] = None
    
    # Capabilities
    capabilities: Dict[str, AgentCapabilityRecord] = field(default_factory=dict)
    specializations: List[str] = field(default_factory=list)  # Domain expertise
    
    # Current state
    is_active: bool = True
    is_accepting_tasks: bool = True
    
    # Load
    current_tasks: int = 0
    max_concurrent_tasks: int = 5
    current_load: float = 0.0  # 0.0 - 1.0
    
    # Health
    health_status: AgentHealthStatus = AgentHealthStatus.HEALTHY
    health_score: float = 1.0  # 0.0 - 1.0
    consecutive_failures: int = 0
    last_failure: Optional[datetime] = None
    last_failure_reason: str = ""
    
    # Trust
    trust_score: float = 1.0  # 0.0 - 1.0, based on reliability
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    
    # Performance
    performance_score: float = 1.0  # 0.0 - 1.0
    avg_response_time_ms: float = 0.0
    avg_success_rate: float = 1.0
    
    # Resource usage
    total_tokens_used: int = 0
    total_execution_time_ms: float = 0.0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """L'agent est disponible pour de nouvelles tâches."""
        return (
            self.is_active and
            self.is_accepting_tasks and
            self.health_status in [
                AgentHealthStatus.HEALTHY,
                AgentHealthStatus.DEGRADED,
            ] and
            self.current_load < 1.0
        )
    
    @property
    def can_accept_task(self) -> bool:
        """Peut accepter une tâche."""
        return self.is_available and self.current_tasks < self.max_concurrent_tasks
    
    @property
    def overall_score(self) -> float:
        """Score combiné pour la sélection."""
        # Combine trust, health, performance, inverse load
        return (
            self.trust_score * 0.3 +
            self.health_score * 0.3 +
            self.performance_score * 0.2 +
            (1.0 - self.current_load) * 0.2
        )
    
    @property
    def success_rate(self) -> float:
        """Taux de succès global."""
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 1.0
        return self.total_tasks_completed / total
    
    def add_capability(self, capability: AgentCapabilityRecord) -> None:
        """Ajoute une capacité."""
        self.capabilities[capability.name] = capability
    
    def has_capability(self, capability_name: str) -> bool:
        """Vérifie si l'agent a une capacité."""
        return capability_name in self.capabilities
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapabilityRecord]:
        """Récupère une capacité."""
        return self.capabilities.get(capability_name)
    
    def record_task_start(self) -> None:
        """Enregistre le début d'une tâche."""
        self.current_tasks += 1
        self.current_load = self.current_tasks / self.max_concurrent_tasks
        self.last_heartbeat = datetime.utcnow()
    
    def record_task_completion(
        self,
        success: bool,
        time_ms: float = 0.0,
        tokens: int = 0,
        capability: Optional[str] = None,
    ) -> None:
        """Enregistre la fin d'une tâche."""
        self.current_tasks = max(0, self.current_tasks - 1)
        self.current_load = self.current_tasks / self.max_concurrent_tasks
        self.last_heartbeat = datetime.utcnow()
        
        if success:
            self.total_tasks_completed += 1
            self.consecutive_failures = 0
            self._update_health(improvement=True)
        else:
            self.total_tasks_failed += 1
            self.consecutive_failures += 1
            self.last_failure = datetime.utcnow()
            self._update_health(improvement=False)
        
        # Update metrics
        self._update_trust_score()
        self._update_performance_score(time_ms)
        
        # Update capability
        if capability and capability in self.capabilities:
            self.capabilities[capability].record_task(success, time_ms)
        
        self.total_tokens_used += tokens
        self.total_execution_time_ms += time_ms
    
    def _update_health(self, improvement: bool) -> None:
        """Met à jour le score de santé."""
        if improvement:
            # Gradual recovery
            self.health_score = min(1.0, self.health_score + 0.1)
            
            if self.health_score > 0.9:
                self.health_status = AgentHealthStatus.HEALTHY
            elif self.health_score > 0.7:
                self.health_status = AgentHealthStatus.DEGRADED
        else:
            # Penalty for failure
            penalty = min(0.2, 0.05 * self.consecutive_failures)
            self.health_score = max(0.0, self.health_score - penalty)
            
            if self.health_score < 0.3:
                self.health_status = AgentHealthStatus.UNHEALTHY
            elif self.health_score < 0.5:
                self.health_status = AgentHealthStatus.RECOVERING
            elif self.health_score < 0.7:
                self.health_status = AgentHealthStatus.DEGRADED
        
        if self.current_load > 0.9:
            self.health_status = AgentHealthStatus.STRESSED
    
    def _update_trust_score(self) -> None:
        """Met à jour le score de confiance."""
        # Exponential moving average
        alpha = 0.1
        self.trust_score = (
            (1 - alpha) * self.trust_score +
            alpha * self.success_rate
        )
    
    def _update_performance_score(self, time_ms: float) -> None:
        """Met à jour le score de performance."""
        if time_ms > 0:
            # Update average response time
            n = self.total_tasks_completed + self.total_tasks_failed
            self.avg_response_time_ms = (
                (self.avg_response_time_ms * (n - 1) + time_ms) / n
            )
        
        # Performance based on speed and success
        # Lower time is better, higher success is better
        time_factor = 1.0
        if self.avg_response_time_ms > 0:
            # Normalize: assume 5000ms is "slow", 500ms is "fast"
            time_factor = max(0.0, min(1.0, 1.0 - (self.avg_response_time_ms - 500) / 4500))
        
        self.performance_score = (
            self.success_rate * 0.7 +
            time_factor * 0.3
        )
    
    def heartbeat(self) -> None:
        """Enregistre un heartbeat."""
        self.last_heartbeat = datetime.utcnow()
        self.is_active = True
    
    def check_stale(self, timeout_seconds: float = 60.0) -> bool:
        """Vérifie si l'agent est stale."""
        if self.last_heartbeat is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return elapsed > timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_available": self.is_available,
            "health_status": self.health_status.value,
            "health_score": self.health_score,
            "trust_score": self.trust_score,
            "performance_score": self.performance_score,
            "overall_score": self.overall_score,
            "current_load": f"{self.current_load:.1%}",
            "current_tasks": self.current_tasks,
            "success_rate": f"{self.success_rate:.1%}",
            "capabilities": list(self.capabilities.keys()),
            "specializations": self.specializations,
        }


# ==========================================
# AGENT REGISTRY CONFIG
# ==========================================

@dataclass
class AgentRegistryConfig:
    """Configuration du registre."""
    max_agents: int = 100
    
    # Health checking
    health_check_interval_s: float = 30.0
    heartbeat_timeout_s: float = 60.0
    stale_agent_removal_s: float = 300.0  # 5 minutes
    
    # Selection
    default_selection_strategy: str = "best_score"  # best_score, round_robin, least_loaded
    
    # Trust thresholds
    min_trust_for_critical_tasks: float = 0.8
    min_trust_for_delegation: float = 0.5
    
    # Recovery
    auto_disable_unhealthy: bool = True
    unhealthy_threshold: float = 0.3
    recovery_threshold: float = 0.7


# ==========================================
# AGENT REGISTRY
# ==========================================

class AgentRegistry:
    """
    Registre central des agents.
    
    C'est LE composant qui transforme des "instances" en "population".
    
    Responsabilités:
        1. Enregistrer les agents avec leur identité
        2. Tracker la santé population-wide
        3. Sélectionner le meilleur agent pour une tâche
        4. Load balancing entre agents
        5. Gérer le lifecycle des agents
    
    Architecture:
        SubAgentPool
                │
                └── AgentRegistry
                        │
                        ├── AgentIdentity[] (population)
                        │
                        ├── find_by_capability()
                        ├── find_best_candidate()
                        └── health_check()
    
    Example:
        registry = AgentRegistry()
        
        # Register an agent
        identity = AgentIdentity(
            name="python-specialist",
            role=AgentRoleCategory.SPECIALIST,
            specializations=["python", "testing"],
        )
        identity.add_capability(AgentCapabilityRecord(
            name="code_generation",
            proficiency=0.9,
        ))
        registry.register(identity)
        
        # Find best agent
        best = registry.find_best_candidate(
            required_capabilities=["code_generation"],
            required_specialization="python",
        )
        
        # Execute task
        if best:
            best.record_task_start()
            # ... execute ...
            best.record_task_completion(success=True, time_ms=1500)
    """
    
    def __init__(self, config: Optional[AgentRegistryConfig] = None):
        self.config = config or AgentRegistryConfig()
        
        # Registry
        self._agents: Dict[str, AgentIdentity] = {}
        self._active_agents: Set[str] = set()
        
        # Indices for fast lookup
        self._capability_index: Dict[str, Set[str]] = defaultdict(set)  # capability -> agent_ids
        self._specialization_index: Dict[str, Set[str]] = defaultdict(set)  # specialization -> agent_ids
        self._role_index: Dict[AgentRoleCategory, Set[str]] = defaultdict(set)  # role -> agent_ids
        
        # Selection state
        self._round_robin_idx: int = 0
        
        # Callbacks
        self._on_agent_registered: List[Callable[[AgentIdentity], None]] = []
        self._on_agent_unregistered: List[Callable[[AgentIdentity], None]] = []
        self._on_agent_health_change: List[Callable[[AgentIdentity, AgentHealthStatus], None]] = []
        
        # Stats
        self._total_registrations = 0
        self._total_selections = 0
        
        logger.info("AgentRegistry initialized")
    
    # ==========================================
    # REGISTRATION
    # ==========================================
    
    def register(self, identity: AgentIdentity) -> AgentIdentity:
        """
        Enregistre un agent dans le registre.
        
        Args:
            identity: L'identité de l'agent
            
        Returns:
            L'identité enregistrée
        """
        if len(self._agents) >= self.config.max_agents:
            # Try to remove stale agents first
            self._cleanup_stale()
            
            if len(self._agents) >= self.config.max_agents:
                raise ValueError(f"Max agents reached ({self.config.max_agents})")
        
        # Register
        self._agents[identity.agent_id] = identity
        self._active_agents.add(identity.agent_id)
        self._total_registrations += 1
        
        # Update indices
        for cap_name in identity.capabilities:
            self._capability_index[cap_name].add(identity.agent_id)
        
        for spec in identity.specializations:
            self._specialization_index[spec].add(identity.agent_id)
        
        self._role_index[identity.role].add(identity.agent_id)
        
        # Callbacks
        for callback in self._on_agent_registered:
            try:
                callback(identity)
            except Exception as e:
                logger.error(f"Registration callback error: {e}")
        
        logger.info(f"Registered agent: {identity.name} ({identity.agent_id})")
        
        return identity
    
    def unregister(self, agent_id: str) -> bool:
        """Désenregistre un agent."""
        identity = self._agents.get(agent_id)
        if not identity:
            return False
        
        # Remove from indices
        for cap_name in identity.capabilities:
            self._capability_index[cap_name].discard(agent_id)
        
        for spec in identity.specializations:
            self._specialization_index[spec].discard(agent_id)
        
        self._role_index[identity.role].discard(agent_id)
        
        # Remove from registry
        del self._agents[agent_id]
        self._active_agents.discard(agent_id)
        
        # Callbacks
        for callback in self._on_agent_unregistered:
            try:
                callback(identity)
            except Exception as e:
                logger.error(f"Unregistration callback error: {e}")
        
        logger.info(f"Unregistered agent: {agent_id}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Récupère un agent par ID."""
        return self._agents.get(agent_id)
    
    # ==========================================
    # QUERY
    # ==========================================
    
    def find_by_capability(
        self,
        capability: str,
        min_proficiency: float = 0.0,
        available_only: bool = True,
    ) -> List[AgentIdentity]:
        """Trouve les agents par capacité."""
        agent_ids = self._capability_index.get(capability, set())
        
        results = []
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if not agent:
                continue
            
            if available_only and not agent.is_available:
                continue
            
            cap = agent.get_capability(capability)
            if cap and cap.proficiency >= min_proficiency:
                results.append(agent)
        
        return results
    
    def find_by_specialization(
        self,
        specialization: str,
        available_only: bool = True,
    ) -> List[AgentIdentity]:
        """Trouve les agents par spécialisation."""
        agent_ids = self._specialization_index.get(specialization, set())
        
        results = []
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if agent and (not available_only or agent.is_available):
                results.append(agent)
        
        return results
    
    def find_by_role(
        self,
        role: AgentRoleCategory,
        available_only: bool = True,
    ) -> List[AgentIdentity]:
        """Trouve les agents par rôle."""
        agent_ids = self._role_index.get(role, set())
        
        results = []
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if agent and (not available_only or agent.is_available):
                results.append(agent)
        
        return results
    
    def find_best_candidate(
        self,
        required_capabilities: Optional[List[str]] = None,
        required_specialization: Optional[str] = None,
        preferred_role: Optional[AgentRoleCategory] = None,
        min_trust: float = 0.0,
        strategy: Optional[str] = None,
    ) -> Optional[AgentIdentity]:
        """
        Trouve le meilleur candidat pour une tâche.
        
        C'est LA méthode centrale de sélection d'agents.
        
        Args:
            required_capabilities: Capacités requises
            required_specialization: Spécialisation requise
            preferred_role: Rôle préféré
            min_trust: Score de confiance minimum
            strategy: Stratégie de sélection (best_score, round_robin, least_loaded)
            
        Returns:
            Le meilleur agent ou None
        """
        self._total_selections += 1
        strategy = strategy or self.config.default_selection_strategy
        
        # Start with all available agents
        candidates = [
            agent for agent in self._agents.values()
            if agent.is_available
        ]
        
        # Filter by capabilities
        if required_capabilities:
            for cap in required_capabilities:
                candidates = [
                    a for a in candidates
                    if a.has_capability(cap)
                ]
        
        # Filter by specialization
        if required_specialization:
            candidates = [
                a for a in candidates
                if required_specialization in a.specializations
            ]
        
        # Filter by role
        if preferred_role:
            role_candidates = [a for a in candidates if a.role == preferred_role]
            if role_candidates:
                candidates = role_candidates
        
        # Filter by trust
        if min_trust > 0:
            candidates = [a for a in candidates if a.trust_score >= min_trust]
        
        if not candidates:
            return None
        
        # Apply selection strategy
        if strategy == "round_robin":
            return self._select_round_robin(candidates)
        elif strategy == "least_loaded":
            return self._select_least_loaded(candidates)
        else:  # best_score
            return self._select_best_score(candidates)
    
    def _select_best_score(self, candidates: List[AgentIdentity]) -> AgentIdentity:
        """Sélectionne le meilleur score."""
        return max(candidates, key=lambda a: a.overall_score)
    
    def _select_round_robin(self, candidates: List[AgentIdentity]) -> AgentIdentity:
        """Sélection round-robin."""
        if not candidates:
            raise ValueError("No candidates")
        
        self._round_robin_idx = (self._round_robin_idx + 1) % len(candidates)
        return candidates[self._round_robin_idx]
    
    def _select_least_loaded(self, candidates: List[AgentIdentity]) -> AgentIdentity:
        """Sélectionne le moins chargé."""
        return min(candidates, key=lambda a: a.current_load)
    
    # ==========================================
    # HEALTH CHECKING
    # ==========================================
    
    def health_check(self) -> Dict[str, Any]:
        """Effectue un health check de la population."""
        results = {
            "total_agents": len(self._agents),
            "active_agents": len(self._active_agents),
            "healthy_count": 0,
            "degraded_count": 0,
            "unhealthy_count": 0,
            "offline_count": 0,
            "stale_count": 0,
            "avg_trust_score": 0.0,
            "avg_performance_score": 0.0,
            "avg_load": 0.0,
        }
        
        if not self._agents:
            return results
        
        trust_scores = []
        performance_scores = []
        loads = []
        
        for agent in self._agents.values():
            # Check stale
            if agent.check_stale(self.config.heartbeat_timeout_s):
                results["stale_count"] += 1
                if agent.health_status != AgentHealthStatus.OFFLINE:
                    old_status = agent.health_status
                    agent.health_status = AgentHealthStatus.OFFLINE
                    self._on_health_change(agent, old_status)
            
            # Count by status
            if agent.health_status == AgentHealthStatus.HEALTHY:
                results["healthy_count"] += 1
            elif agent.health_status in [AgentHealthStatus.DEGRADED, AgentHealthStatus.STRESSED]:
                results["degraded_count"] += 1
            elif agent.health_status == AgentHealthStatus.UNHEALTHY:
                results["unhealthy_count"] += 1
            elif agent.health_status == AgentHealthStatus.OFFLINE:
                results["offline_count"] += 1
            
            trust_scores.append(agent.trust_score)
            performance_scores.append(agent.performance_score)
            loads.append(agent.current_load)
        
        results["avg_trust_score"] = sum(trust_scores) / len(trust_scores)
        results["avg_performance_score"] = sum(performance_scores) / len(performance_scores)
        results["avg_load"] = sum(loads) / len(loads)
        
        return results
    
    def _on_health_change(
        self,
        agent: AgentIdentity,
        old_status: AgentHealthStatus,
    ) -> None:
        """Gère les changements de santé."""
        for callback in self._on_agent_health_change:
            try:
                callback(agent, old_status)
            except Exception as e:
                logger.error(f"Health change callback error: {e}")
    
    def _cleanup_stale(self) -> int:
        """Nettoie les agents stale."""
        to_remove = []
        
        for agent_id, agent in self._agents.items():
            if agent.check_stale(self.config.stale_agent_removal_s):
                to_remove.append(agent_id)
        
        for agent_id in to_remove:
            self.unregister(agent_id)
        
        return len(to_remove)
    
    # ==========================================
    # LOAD BALANCING
    # ==========================================
    
    def get_population_load(self) -> float:
        """Retourne la charge de la population."""
        if not self._agents:
            return 0.0
        
        return sum(a.current_load for a in self._agents.values()) / len(self._agents)
    
    def get_available_capacity(self) -> int:
        """Retourne la capacité disponible (tâches)."""
        return sum(
            a.max_concurrent_tasks - a.current_tasks
            for a in self._agents.values()
            if a.is_available
        )
    
    def get_available_agents(self) -> List[AgentIdentity]:
        """Retourne les agents disponibles."""
        return [a for a in self._agents.values() if a.is_available]
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du registre."""
        health = self.health_check()
        
        return {
            **health,
            "total_registrations": self._total_registrations,
            "total_selections": self._total_selections,
            "capability_count": len(self._capability_index),
            "specialization_count": len(self._specialization_index),
        }
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retourne le classement des agents."""
        sorted_agents = sorted(
            self._agents.values(),
            key=lambda a: a.overall_score,
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "agent_id": a.agent_id,
                "name": a.name,
                "overall_score": a.overall_score,
                "trust_score": a.trust_score,
                "performance_score": a.performance_score,
                "tasks_completed": a.total_tasks_completed,
            }
            for i, a in enumerate(sorted_agents[:limit])
        ]
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_agent_registered(
        self,
        callback: Callable[[AgentIdentity], None]
    ) -> None:
        """Callback pour enregistrement."""
        self._on_agent_registered.append(callback)
    
    def on_agent_unregistered(
        self,
        callback: Callable[[AgentIdentity], None]
    ) -> None:
        """Callback pour désenregistrement."""
        self._on_agent_unregistered.append(callback)
    
    def on_agent_health_change(
        self,
        callback: Callable[[AgentIdentity, AgentHealthStatus], None]
    ) -> None:
        """Callback pour changement de santé."""
        self._on_agent_health_change.append(callback)


# ==========================================
# FACTORY
# ==========================================

def create_agent_registry(
    config: Optional[AgentRegistryConfig] = None,
) -> AgentRegistry:
    """Factory pour créer un registre."""
    return AgentRegistry(config=config)


def create_agent_identity(
    name: str,
    role: AgentRoleCategory = AgentRoleCategory.WORKER,
    capabilities: Optional[List[AgentCapabilityRecord]] = None,
    specializations: Optional[List[str]] = None,
) -> AgentIdentity:
    """Factory pour créer une identité d'agent."""
    identity = AgentIdentity(
        name=name,
        role=role,
        specializations=specializations or [],
    )
    
    for cap in (capabilities or []):
        identity.add_capability(cap)
    
    return identity
