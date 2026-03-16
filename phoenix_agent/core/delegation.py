"""
Phoenix Agent - Delegation Engine
=================================

Moteur de délégation pour le multi-agent.

Permet à l'agent principal de déléguer des tâches à des sub-agents.

Architecture:
    Task → DelegationEngine → SubAgent → Result

Version: 0.4.0 (Structure préparée)
Version: 1.0.0 (Implémentation complète prévue)

STRATÉGIES DE DÉLÉGATION:
    1. Role-based: Déléguer selon le rôle requis
    2. Capability-based: Déléguer selon les capacités
    3. Load-based: Déléguer selon la charge
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .task import Task, TaskStatus, TaskComplexity, TaskResult


logger = logging.getLogger("phoenix.delegation")


# ==========================================
# AGENT ROLE
# ==========================================

class AgentRole(str, Enum):
    """Rôles disponibles pour les sub-agents."""
    GENERAL = "general"               # Agent généraliste
    RESEARCHER = "researcher"         # Recherche d'information
    CODER = "coder"                   # Génération de code
    ANALYST = "analyst"               # Analyse de données
    WRITER = "writer"                 # Rédaction
    REVIEWER = "reviewer"             # Révision/critique
    SPECIALIST = "specialist"         # Expert domaine spécifique


# ==========================================
# AGENT CAPABILITY
# ==========================================

@dataclass
class AgentCapability:
    """Capacité d'un agent."""
    name: str
    description: str
    proficiency: float = 1.0  # 0.0 to 1.0
    
    # Types de tâches supportées
    supported_task_types: List[str] = field(default_factory=list)
    
    # Complexité max gérable
    max_complexity: TaskComplexity = TaskComplexity.COMPLEX


# ==========================================
# SUB-AGENT INFO
# ==========================================

@dataclass
class SubAgentInfo:
    """Information sur un sub-agent disponible."""
    agent_id: str
    role: AgentRole
    capabilities: List[AgentCapability]
    
    # État
    is_available: bool = True
    current_load: float = 0.0  # 0.0 to 1.0
    tasks_completed: int = 0
    
    # Performance
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    
    def can_handle(self, task: Task) -> bool:
        """Vérifie si l'agent peut gérer la tâche."""
        if not self.is_available:
            return False
        
        if self.current_load >= 1.0:
            return False
        
        # Check complexity
        complexity_order = [
            TaskComplexity.SIMPLE,
            TaskComplexity.MODERATE,
            TaskComplexity.COMPLEX,
            TaskComplexity.EXPERT
        ]
        task_complexity_idx = complexity_order.index(task.complexity)
        max_complexity_idx = complexity_order.index(
            max(c.max_complexity for c in self.capabilities)
        )
        
        return task_complexity_idx <= max_complexity_idx


# ==========================================
# DELEGATION REQUEST
# ==========================================

@dataclass
class DelegationRequest:
    """Requête de délégation."""
    task: Task
    required_role: Optional[AgentRole] = None
    required_capabilities: List[str] = field(default_factory=list)
    priority: int = 5
    timeout_ms: float = 60000.0
    
    # Contexte à transmettre
    context_to_share: str = ""
    parent_session_id: Optional[str] = None


# ==========================================
# DELEGATION RESPONSE
# ==========================================

@dataclass
class DelegationResponse:
    """Réponse à une délégation."""
    success: bool
    assigned_agent_id: Optional[str] = None
    task_result: Optional[TaskResult] = None
    error: Optional[str] = None
    
    # Métriques
    delegation_latency_ms: float = 0.0
    execution_latency_ms: float = 0.0


# ==========================================
# DELEGATION ENGINE
# ==========================================

class DelegationEngine:
    """
    Moteur de délégation pour Phoenix.
    
    v0.4: Structure en place, simulation
    v1.0: Implémentation complète avec vrais sub-agents
    
    Responsabilités:
        - Maintenir le registre des sub-agents
        - Matcher les tâches avec les agents
        - Orchestrer la délégation
        - Collecter les résultats
    
    Example:
        engine = DelegationEngine()
        
        # Enregistrer un sub-agent
        engine.register_agent(SubAgentInfo(
            agent_id="coder-1",
            role=AgentRole.CODER,
            capabilities=[AgentCapability(
                name="python",
                description="Python coding",
                supported_task_types=["code"]
            )]
        ))
        
        # Déléguer une tâche
        response = await engine.delegate(DelegationRequest(
            task=coding_task,
            required_role=AgentRole.CODER
        ))
    """
    
    def __init__(self):
        self._agents: Dict[str, SubAgentInfo] = {}
        self._delegation_history: List[DelegationResponse] = []
    
    # ==========================================
    # AGENT REGISTRY
    # ==========================================
    
    def register_agent(self, agent: SubAgentInfo) -> None:
        """Enregistre un sub-agent."""
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered sub-agent: {agent.agent_id} ({agent.role.value})")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Désenregistre un sub-agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[SubAgentInfo]:
        """Récupère un agent par ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[SubAgentInfo]:
        """Liste tous les agents."""
        return list(self._agents.values())
    
    # ==========================================
    # AGENT SELECTION
    # ==========================================
    
    def find_best_agent(
        self,
        request: DelegationRequest
    ) -> Optional[SubAgentInfo]:
        """
        Trouve le meilleur agent pour une requête.
        
        Critères:
            1. Role match
            2. Capabilities match
            3. Availability
            4. Load balancing
        """
        candidates = []
        
        for agent in self._agents.values():
            if not agent.can_handle(request.task):
                continue
            
            # Role match
            if request.required_role and agent.role != request.required_role:
                continue
            
            # Capabilities match
            if request.required_capabilities:
                agent_caps = {c.name for c in agent.capabilities}
                if not all(c in agent_caps for c in request.required_capabilities):
                    continue
            
            candidates.append(agent)
        
        if not candidates:
            return None
        
        # Sélectionner le moins chargé
        return min(candidates, key=lambda a: a.current_load)
    
    # ==========================================
    # DELEGATION
    # ==========================================
    
    async def delegate(
        self,
        request: DelegationRequest
    ) -> DelegationResponse:
        """
        Délègue une tâche à un sub-agent.
        
        v0.4: Simulation
        v1.0: Vraie exécution via SubAgentRunner
        
        Args:
            request: La requête de délégation
            
        Returns:
            DelegationResponse
        """
        import time
        start_time = time.time()
        
        # Trouver le meilleur agent
        agent = self.find_best_agent(request)
        
        if not agent:
            return DelegationResponse(
                success=False,
                error="No suitable agent available"
            )
        
        logger.info(f"Delegating task {request.task.task_id} to {agent.agent_id}")
        
        # v0.4: Simuler la délégation
        # v1.0: Appeler SubAgentRunner.run()
        
        request.task.delegate(agent.agent_id)
        
        # Simuler l'exécution
        await self._simulate_execution(request.task)
        
        delegation_latency = (time.time() - start_time) * 1000
        
        response = DelegationResponse(
            success=True,
            assigned_agent_id=agent.agent_id,
            task_result=TaskResult(
                task_id=request.task.task_id,
                status=TaskStatus.COMPLETED,
                result=f"[Delegated to {agent.role.value}] Task completed"
            ),
            delegation_latency_ms=delegation_latency
        )
        
        # Enregistrer
        self._delegation_history.append(response)
        agent.tasks_completed += 1
        
        return response
    
    async def _simulate_execution(self, task: Task) -> None:
        """Simule l'exécution d'une tâche (v0.4)."""
        import asyncio
        await asyncio.sleep(0.01)  # Simuler latence
        task.complete(f"Completed: {task.goal[:50]}...")
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de délégation."""
        if not self._delegation_history:
            return {
                "total_delegations": 0,
                "success_rate": 0.0,
                "agents_count": len(self._agents),
            }
        
        successes = sum(1 for r in self._delegation_history if r.success)
        
        return {
            "total_delegations": len(self._delegation_history),
            "successful_delegations": successes,
            "success_rate": successes / len(self._delegation_history),
            "agents_count": len(self._agents),
            "avg_delegation_latency_ms": sum(
                r.delegation_latency_ms for r in self._delegation_history
            ) / len(self._delegation_history),
        }
