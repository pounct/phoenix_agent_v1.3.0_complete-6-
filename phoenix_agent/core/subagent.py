"""
Phoenix Agent - Sub-Agent Runner
================================

Exécuteur de sub-agents pour Phoenix.

Responsabilités:
    - Créer et gérer des sub-agents
    - Exécuter des tâches déléguées
    - Isoler le contexte des sub-agents
    - Collecter les résultats

Architecture:
    DelegationEngine → SubAgentRunner → AgentLoop → Result

Version: 0.4.0 (Structure préparée)
Version: 1.0.0 (Implémentation complète prévue)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

from .task import Task, TaskResult, TaskStatus
from .delegation import AgentRole, AgentCapability
from .agent_loop import AgentLoop, AgentLoopResult
from .state import SessionState
from .context_builder import ContextBuilder


logger = logging.getLogger("phoenix.subagent")


# ==========================================
# SUB-AGENT STATUS
# ==========================================

class SubAgentStatus(str, Enum):
    """Statut d'un sub-agent."""
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


# ==========================================
# SUB-AGENT CONFIG
# ==========================================

@dataclass
class SubAgentConfig:
    """Configuration d'un sub-agent."""
    agent_id: str
    role: AgentRole
    system_prompt: str = ""
    
    # Capacités
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # Limites
    max_iterations: int = 5
    max_context_tokens: int = 2000
    
    # Comportement
    auto_register: bool = True
    timeout_ms: float = 60000.0


# ==========================================
# SUB-AGENT RESULT
# ==========================================

@dataclass
class SubAgentResult:
    """Résultat de l'exécution d'un sub-agent."""
    agent_id: str
    task_id: str
    success: bool
    result: str
    error: Optional[str] = None
    
    # Métriques
    execution_time_ms: float = 0.0
    tokens_used: int = 0
    iterations: int = 0
    
    # Contexte généré
    generated_context: str = ""


# ==========================================
# SUB-AGENT
# ==========================================

class SubAgent:
    """
    Sub-agent Phoenix.
    
    Un sub-agent est un agent spécialisé qui peut être
    créé dynamiquement pour exécuter des tâches spécifiques.
    
    v0.4: Structure en place
    v1.0: Implémentation complète avec isolation
    
    Architecture:
        SubAgent
            │
            ├── AgentLoop (Think → Act → Observe)
            ├── SessionState (isolé)
            └── ContextBuilder (spécifique)
    
    Example:
        config = SubAgentConfig(
            agent_id="coder-1",
            role=AgentRole.CODER,
            system_prompt="You are an expert Python developer.",
            capabilities=[AgentCapability(name="python", ...)]
        )
        
        subagent = SubAgent(config, gateway_adapter)
        result = await subagent.execute(task)
    """
    
    def __init__(
        self,
        config: SubAgentConfig,
        gateway_adapter,  # GatewayAdapter
        delegation_engine=None,
    ):
        self.config = config
        self.gateway_adapter = gateway_adapter
        self.delegation_engine = delegation_engine
        
        # Status
        self.status = SubAgentStatus.IDLE
        self.current_task: Optional[Task] = None
        self.tasks_completed = 0
        
        # Components
        self.agent_loop = AgentLoop(
            adapter=gateway_adapter,
            max_iterations=config.max_iterations,
            system_prompt=config.system_prompt or self._default_system_prompt(),
        )
        
        self.context_builder = ContextBuilder()
        self.session: Optional[SessionState] = None
    
    def _default_system_prompt(self) -> str:
        """Génère un prompt système par défaut selon le rôle."""
        role_prompts = {
            AgentRole.GENERAL: "You are a helpful AI assistant.",
            AgentRole.RESEARCHER: "You are a research specialist. Your job is to find and analyze information.",
            AgentRole.CODER: "You are an expert software developer. Write clean, efficient code.",
            AgentRole.ANALYST: "You are a data analyst. Analyze information and provide insights.",
            AgentRole.WRITER: "You are a professional writer. Create clear, engaging content.",
            AgentRole.REVIEWER: "You are a critical reviewer. Evaluate and provide constructive feedback.",
            AgentRole.SPECIALIST: "You are a domain specialist. Apply your expertise to solve problems.",
        }
        return role_prompts.get(self.config.role, "You are a helpful AI assistant.")
    
    # ==========================================
    # EXECUTION
    # ==========================================
    
    async def execute(self, task: Task) -> SubAgentResult:
        """
        Exécute une tâche.
        
        v0.4: Simulation
        v1.0: Vraie exécution avec isolation
        
        Args:
            task: La tâche à exécuter
            
        Returns:
            SubAgentResult
        """
        import time
        start_time = time.time()
        
        self.status = SubAgentStatus.RUNNING
        self.current_task = task
        
        try:
            # Créer une session isolée
            self.session = SessionState(
                session_id=f"subagent-{self.config.agent_id}-{task.task_id}",
                model="llama3.2:latest",
                max_iterations=self.config.max_iterations
            )
            
            # Exécuter via AgentLoop
            result = await self.agent_loop.run(
                user_input=task.goal,
                session=self.session,
                model="llama3.2:latest"
            )
            
            self.status = SubAgentStatus.IDLE
            self.tasks_completed += 1
            
            return SubAgentResult(
                agent_id=self.config.agent_id,
                task_id=task.task_id,
                success=result.is_success,
                result=result.response,
                error=result.error,
                execution_time_ms=(time.time() - start_time) * 1000,
                tokens_used=result.total_tokens,
                iterations=result.iterations,
            )
            
        except Exception as e:
            self.status = SubAgentStatus.ERROR
            logger.error(f"Sub-agent {self.config.agent_id} error: {e}")
            
            return SubAgentResult(
                agent_id=self.config.agent_id,
                task_id=task.task_id,
                success=False,
                result="",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        
        finally:
            self.current_task = None
    
    # ==========================================
    # CAPABILITIES
    # ==========================================
    
    def can_handle(self, task: Task) -> bool:
        """Vérifie si le sub-agent peut gérer la tâche."""
        if self.status == SubAgentStatus.RUNNING:
            return False
        
        # Check capacités
        if self.config.capabilities:
            for cap in self.config.capabilities:
                if task.task_type.value in cap.supported_task_types:
                    return True
            return False
        
        return True  # Pas de restrictions
    
    # ==========================================
    # INFO
    # ==========================================
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les infos du sub-agent."""
        return {
            "agent_id": self.config.agent_id,
            "role": self.config.role.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "capabilities": [c.name for c in self.config.capabilities],
            "current_task_id": self.current_task.task_id if self.current_task else None,
        }


# ==========================================
# SUB-AGENT POOL
# ==========================================

class SubAgentPool:
    """
    Pool de sub-agents disponibles.
    
    Gère la création, le registry et l'attribution des sub-agents.
    
    v0.4: Structure en place
    v1.0: Pool dynamique avec scaling
    
    Example:
        pool = SubAgentPool(gateway_adapter)
        
        # Créer des agents
        pool.create_agent(AgentRole.CODER, system_prompt="...")
        pool.create_agent(AgentRole.RESEARCHER, system_prompt="...")
        
        # Obtenir un agent
        agent = pool.get_agent_for_task(task)
        result = await agent.execute(task)
    """
    
    def __init__(self, gateway_adapter):
        self.gateway_adapter = gateway_adapter
        self._agents: Dict[str, SubAgent] = {}
    
    # ==========================================
    # AGENT MANAGEMENT
    # ==========================================
    
    def create_agent(
        self,
        role: AgentRole,
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        agent_id: Optional[str] = None,
    ) -> SubAgent:
        """Crée un nouveau sub-agent."""
        agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:8]}"
        
        config = SubAgentConfig(
            agent_id=agent_id,
            role=role,
            system_prompt=system_prompt or "",
            capabilities=capabilities or [],
        )
        
        agent = SubAgent(config, self.gateway_adapter)
        self._agents[agent_id] = agent
        
        logger.info(f"Created sub-agent: {agent_id} ({role.value})")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Récupère un agent par ID."""
        return self._agents.get(agent_id)
    
    def get_agent_for_task(self, task: Task) -> Optional[SubAgent]:
        """Trouve le meilleur agent pour une tâche."""
        candidates = [
            a for a in self._agents.values()
            if a.can_handle(task) and a.status == SubAgentStatus.IDLE
        ]
        
        if not candidates:
            return None
        
        # Retourner le moins chargé
        return min(candidates, key=lambda a: a.tasks_completed)
    
    def list_agents(self) -> List[SubAgent]:
        """Liste tous les agents."""
        return list(self._agents.values())
    
    def list_available(self) -> List[SubAgent]:
        """Liste les agents disponibles."""
        return [a for a in self._agents.values() if a.status == SubAgentStatus.IDLE]
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du pool."""
        agents = list(self._agents.values())
        
        return {
            "total_agents": len(agents),
            "idle_agents": sum(1 for a in agents if a.status == SubAgentStatus.IDLE),
            "running_agents": sum(1 for a in agents if a.status == SubAgentStatus.RUNNING),
            "total_tasks_completed": sum(a.tasks_completed for a in agents),
            "agents_by_role": {
                role.value: sum(1 for a in agents if a.config.role == role)
                for role in AgentRole
            },
        }
    
    # ==========================================
    # CLEANUP
    # ==========================================
    
    def remove_agent(self, agent_id: str) -> bool:
        """Supprime un agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    def clear(self) -> None:
        """Vide le pool."""
        self._agents.clear()
