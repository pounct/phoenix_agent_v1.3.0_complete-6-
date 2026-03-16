"""
Phoenix Agent - Task Graph Executor
====================================

Exécution intelligente des graphes de tâches.

Un Agent OS ne "planifie" pas seulement.
Il **exécute** des graphes avec dépendances et parallélisme.

Sans TaskGraphExecutor:
    - PlannerEngine reste théorique
    - Pas de gestion des dépendances réelles
    - Pas de parallélisme intelligent
    - Pas de détection de blocage
    - Pas de réoptimisation en cours d'exécution

Avec TaskGraphExecutor:
    - Exécution de graphes de dépendances
    - Parallélisme automatique des tâches indépendantes
    - Détection et résolution des blocages
    - Réoptimisation dynamique
    - Chemin critique calculé
    - Rollback sur échec

C'est LA couche qui transforme un "plan" en "exécution réelle".

CAPABILITIES:
    - Dependency resolution
    - Parallel execution
    - Critical path detection
    - Blocking detection
    - Dynamic reoptimization
    - Partial execution on failure

Version: 1.0.0 (Graph Execution Layer)
"""

from typing import Optional, List, Dict, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import logging
import uuid


logger = logging.getLogger("phoenix.task_graph_executor")


# ==========================================
# NODE STATUS
# ==========================================

class NodeStatus(str, Enum):
    """Status d'un nœud du graphe."""
    PENDING = "pending"             # En attente
    READY = "ready"                 # Dépendances satisfaites
    RUNNING = "running"             # En cours
    COMPLETED = "completed"         # Terminé avec succès
    FAILED = "failed"               # Échec
    SKIPPED = "skipped"             # Sauté (dépendance échouée)
    BLOCKED = "blocked"             # Bloqué
    CANCELLED = "cancelled"         # Annulé


class GraphStatus(str, Enum):
    """Status du graphe."""
    PENDING = "pending"             # En attente
    RUNNING = "running"             # En cours
    COMPLETED = "completed"         # Terminé
    PARTIAL = "partial"             # Partiellement terminé
    FAILED = "failed"               # Échec
    CANCELLED = "cancelled"         # Annulé
    BLOCKED = "blocked"             # Bloqué


class ExecutionStrategy(str, Enum):
    """Stratégie d'exécution."""
    SEQUENTIAL = "sequential"       # Une tâche à la fois
    PARALLEL = "parallel"           # Parallèle maximal
    ADAPTIVE = "adaptive"           # Adaptatif selon les ressources
    CRITICAL_PATH = "critical_path" # Priorise le chemin critique


# ==========================================
# TASK NODE
# ==========================================

@dataclass
class TaskNode:
    """
    Nœud dans le graphe de tâches.
    
    Chaque nœud représente une tâche avec ses dépendances.
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    
    # Task info
    name: str = ""
    description: str = ""
    task_type: str = "general"
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # node_ids
    dependents: List[str] = field(default_factory=list)    # node_ids
    
    # Execution
    status: NodeStatus = NodeStatus.PENDING
    priority: int = 5  # 1-10
    
    # Estimation
    estimated_duration_ms: float = 1000.0
    estimated_tokens: int = 500
    
    # Actual
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_ms: float = 0.0
    actual_tokens: int = 0
    
    # Result
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Execution metadata
    agent_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_ready(self) -> bool:
        """Le nœud est prêt à exécuter."""
        return self.status == NodeStatus.READY
    
    @property
    def is_completed(self) -> bool:
        """Le nœud est terminé."""
        return self.status == NodeStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Le nœud a échoué."""
        return self.status == NodeStatus.FAILED
    
    @property
    def is_terminal(self) -> bool:
        """Le nœud est dans un état terminal."""
        return self.status in [
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.CANCELLED,
        ]
    
    @property
    def is_blocking(self) -> bool:
        """Le nœud bloque d'autres nœuds."""
        return self.status in [NodeStatus.BLOCKED, NodeStatus.FAILED] and len(self.dependents) > 0
    
    def mark_running(self, agent_id: Optional[str] = None) -> None:
        """Marque comme en cours."""
        self.status = NodeStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.agent_id = agent_id
    
    def mark_completed(self, result: Any, tokens: int = 0) -> None:
        """Marque comme terminé."""
        self.status = NodeStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result
        self.actual_tokens = tokens
        
        if self.started_at:
            self.actual_duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def mark_failed(self, error: str) -> None:
        """Marque comme échoué."""
        self.status = NodeStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        
        if self.started_at:
            self.actual_duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def mark_blocked(self, reason: str = "") -> None:
        """Marque comme bloqué."""
        self.status = NodeStatus.BLOCKED
        self.error = reason
    
    def mark_skipped(self, reason: str = "") -> None:
        """Marque comme sauté."""
        self.status = NodeStatus.SKIPPED
        self.error = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "dependents": len(self.dependents),
            "duration_ms": self.actual_duration_ms or self.estimated_duration_ms,
        }


# ==========================================
# TASK GRAPH
# ==========================================

@dataclass
class TaskGraph:
    """
    Graphe de tâches avec dépendances.
    
    C'est le modèle central pour l'exécution structurée.
    """
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Nodes
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    
    # Entry and exit points
    entry_nodes: List[str] = field(default_factory=list)  # node_ids with no dependencies
    exit_nodes: List[str] = field(default_factory=list)   # node_ids with no dependents
    
    # Execution state
    status: GraphStatus = GraphStatus.PENDING
    
    # Execution info
    execution_strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    max_parallel: int = 5
    
    # Metrics
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    
    # Critical path
    critical_path: List[str] = field(default_factory=list)  # node_ids
    critical_path_duration_ms: float = 0.0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress(self) -> float:
        """Progression (0.0 - 1.0)."""
        if self.total_nodes == 0:
            return 0.0
        return self.completed_nodes / self.total_nodes
    
    @property
    def is_complete(self) -> bool:
        """Le graphe est terminé."""
        return self.status in [
            GraphStatus.COMPLETED,
            GraphStatus.PARTIAL,
            GraphStatus.FAILED,
            GraphStatus.CANCELLED,
        ]
    
    @property
    def success_rate(self) -> float:
        """Taux de succès."""
        if self.total_nodes == 0:
            return 1.0
        
        terminal = sum(
            1 for n in self.nodes.values()
            if n.is_terminal
        )
        
        if terminal == 0:
            return 1.0
        
        return self.completed_nodes / terminal
    
    def add_node(self, node: TaskNode) -> None:
        """Ajoute un nœud."""
        self.nodes[node.node_id] = node
        self.total_nodes = len(self.nodes)
    
    def remove_node(self, node_id: str) -> bool:
        """Supprime un nœud."""
        if node_id not in self.nodes:
            return False
        
        # Remove from dependencies
        node = self.nodes[node_id]
        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.remove(node_id)
        
        for dep_id in node.dependents:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependencies.remove(node_id)
        
        del self.nodes[node_id]
        self.total_nodes = len(self.nodes)
        return True
    
    def add_edge(self, from_node_id: str, to_node_id: str) -> bool:
        """Ajoute une dépendance (edge)."""
        if from_node_id not in self.nodes or to_node_id not in self.nodes:
            return False
        
        from_node = self.nodes[from_node_id]
        to_node = self.nodes[to_node_id]
        
        # Add dependency
        if to_node_id not in from_node.dependents:
            from_node.dependents.append(to_node_id)
        
        if from_node_id not in to_node.dependencies:
            to_node.dependencies.append(from_node_id)
        
        return True
    
    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """Récupère un nœud."""
        return self.nodes.get(node_id)
    
    def get_ready_nodes(self) -> List[TaskNode]:
        """Retourne les nœuds prêts à exécuter."""
        ready = []
        for node in self.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            
            # Check all dependencies completed
            deps_satisfied = all(
                self.nodes.get(dep_id, TaskNode()).status == NodeStatus.COMPLETED
                for dep_id in node.dependencies
            )
            
            if deps_satisfied:
                node.status = NodeStatus.READY
                ready.append(node)
        
        return ready
    
    def get_running_nodes(self) -> List[TaskNode]:
        """Retourne les nœuds en cours."""
        return [n for n in self.nodes.values() if n.status == NodeStatus.RUNNING]
    
    def detect_cycles(self) -> bool:
        """Détecte les cycles dans le graphe."""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            node = self.nodes.get(node_id)
            if node:
                for dep_id in node.dependents:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def calculate_critical_path(self) -> List[str]:
        """Calcule le chemin critique."""
        # Forward pass: earliest start times
        earliest: Dict[str, float] = {}
        
        def get_earliest(node_id: str) -> float:
            if node_id in earliest:
                return earliest[node_id]
            
            node = self.nodes.get(node_id)
            if not node:
                return 0.0
            
            if not node.dependencies:
                earliest[node_id] = 0.0
            else:
                earliest[node_id] = max(
                    get_earliest(dep) + self.nodes.get(dep, TaskNode()).estimated_duration_ms
                    for dep in node.dependencies
                )
            
            return earliest[node_id]
        
        for node_id in self.nodes:
            get_earliest(node_id)
        
        # Backward pass: latest start times
        latest: Dict[str, float] = {}
        max_time = max(
            earliest.get(nid, 0.0) + self.nodes.get(nid, TaskNode()).estimated_duration_ms
            for nid in self.nodes
        ) if self.nodes else 0.0
        
        def get_latest(node_id: str) -> float:
            if node_id in latest:
                return latest[node_id]
            
            node = self.nodes.get(node_id)
            if not node:
                return max_time
            
            if not node.dependents:
                latest[node_id] = max_time - node.estimated_duration_ms
            else:
                latest[node_id] = min(
                    get_latest(dep) - node.estimated_duration_ms
                    for dep in node.dependents
                )
            
            return latest[node_id]
        
        for node_id in self.nodes:
            get_latest(node_id)
        
        # Find critical nodes (earliest == latest)
        critical = []
        for node_id in self.nodes:
            if abs(earliest.get(node_id, 0.0) - latest.get(node_id, 0.0)) < 0.01:
                critical.append(node_id)
        
        self.critical_path = critical
        self.critical_path_duration_ms = max_time
        
        return critical
    
    def detect_blocking(self) -> List[TaskNode]:
        """Détecte les nœuds bloquants."""
        blocked = []
        
        for node in self.nodes.values():
            if node.status == NodeStatus.FAILED:
                # Check if this blocks any pending nodes
                for dep_id in node.dependents:
                    dep = self.nodes.get(dep_id)
                    if dep and dep.status == NodeStatus.PENDING:
                        blocked.append(node)
                        break
        
        return blocked
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "status": self.status.value,
            "progress": f"{self.progress:.1%}",
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "critical_path_length": len(self.critical_path),
            "critical_path_duration_ms": self.critical_path_duration_ms,
        }


# ==========================================
# EXECUTOR CONFIG
# ==========================================

@dataclass
class ExecutorConfig:
    """Configuration de l'exécuteur."""
    # Execution
    default_strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    max_parallel_tasks: int = 5
    
    # Timeouts
    node_timeout_ms: float = 60000.0
    graph_timeout_ms: float = 300000.0
    
    # Retries
    auto_retry: bool = True
    max_node_retries: int = 2
    
    # Blocking
    auto_skip_blocked: bool = True
    block_threshold_s: float = 30.0
    
    # Resources
    check_resources: bool = True


# ==========================================
# TASK GRAPH EXECUTOR
# ==========================================

class TaskGraphExecutor:
    """
    Exécuteur de graphes de tâches.
    
    C'est LE composant qui transforme un plan en exécution réelle.
    
    Responsabilités:
        1. Exécuter les nœuds selon les dépendances
        2. Gérer le parallélisme
        3. Détecter et résoudre les blocages
        4. Réessayer sur échec
        5. Optimiser l'ordonnancement
    
    Architecture:
        TaskGraph
            │
            └── TaskGraphExecutor
                    │
                    ├── resolve_dependencies()
                    ├── schedule_parallel()
                    ├── execute_node()
                    ├── detect_blocking()
                    └── reoptimize()
    
    Example:
        executor = TaskGraphExecutor()
        
        # Create graph
        graph = TaskGraph(name="Build Pipeline")
        
        # Add nodes
        node1 = TaskNode(name="Setup", task_id="task-1")
        node2 = TaskNode(name="Build", task_id="task-2")
        node2.dependencies.append(node1.node_id)
        
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(node1.node_id, node2.node_id)
        
        # Execute
        result = await executor.execute(graph)
        
        print(f"Progress: {result.progress:.1%}")
    """
    
    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        resource_manager: Optional[Any] = None,
        agent_registry: Optional[Any] = None,
    ):
        self.config = config or ExecutorConfig()
        self.resource_manager = resource_manager
        self.agent_registry = agent_registry
        
        # Active executions
        self._active_graphs: Dict[str, TaskGraph] = {}
        
        # Execution history
        self._execution_history: List[TaskGraph] = []
        
        # Callbacks
        self._on_node_start: List[Callable[[TaskNode, TaskGraph], None]] = []
        self._on_node_complete: List[Callable[[TaskNode, TaskGraph], None]] = []
        self._on_graph_complete: List[Callable[[TaskGraph], None]] = []
        
        # Task executor (injected or default)
        self._task_executor: Optional[Callable] = None
        
        # Stats
        self._total_executions = 0
        self._successful_executions = 0
        
        logger.info("TaskGraphExecutor initialized")
    
    def set_task_executor(self, executor: Callable) -> None:
        """Définit l'exécuteur de tâches."""
        self._task_executor = executor
    
    # ==========================================
    # MAIN EXECUTION
    # ==========================================
    
    async def execute(
        self,
        graph: TaskGraph,
        strategy: Optional[ExecutionStrategy] = None,
    ) -> TaskGraph:
        """
        Exécute un graphe de tâches.
        
        C'est LA méthode centrale du TaskGraphExecutor.
        
        Args:
            graph: Le graphe à exécuter
            strategy: Stratégie d'exécution
            
        Returns:
            Le graphe avec les résultats
        """
        strategy = strategy or graph.execution_strategy or self.config.default_strategy
        
        # Validate
        if graph.detect_cycles():
            logger.error(f"Graph {graph.graph_id} has cycles")
            graph.status = GraphStatus.FAILED
            return graph
        
        # Calculate critical path
        graph.calculate_critical_path()
        
        # Initialize
        graph.status = GraphStatus.RUNNING
        graph.started_at = datetime.utcnow()
        self._active_graphs[graph.graph_id] = graph
        self._total_executions += 1
        
        logger.info(
            f"Starting graph execution: {graph.name} "
            f"({graph.total_nodes} nodes, strategy: {strategy.value})"
        )
        
        try:
            # Execute based on strategy
            if strategy == ExecutionStrategy.SEQUENTIAL:
                await self._execute_sequential(graph)
            elif strategy == ExecutionStrategy.PARALLEL:
                await self._execute_parallel(graph)
            elif strategy == ExecutionStrategy.CRITICAL_PATH:
                await self._execute_critical_path(graph)
            else:
                await self._execute_adaptive(graph)
            
            # Finalize
            self._finalize_graph(graph)
            
        except asyncio.TimeoutError:
            logger.error(f"Graph {graph.graph_id} timed out")
            graph.status = GraphStatus.FAILED
            
        except Exception as e:
            logger.error(f"Graph {graph.graph_id} failed: {e}")
            graph.status = GraphStatus.FAILED
        
        finally:
            self._active_graphs.pop(graph.graph_id, None)
            self._execution_history.append(graph)
        
        return graph
    
    async def _execute_sequential(self, graph: TaskGraph) -> None:
        """Exécution séquentielle."""
        # Topological sort
        order = self._topological_sort(graph)
        
        for node_id in order:
            node = graph.nodes.get(node_id)
            if not node:
                continue
            
            if node.is_terminal:
                continue
            
            await self._execute_node(node, graph)
            
            if node.status == NodeStatus.FAILED:
                # Check if should continue
                if not self._should_continue_after_failure(graph, node):
                    break
    
    async def _execute_parallel(self, graph: TaskGraph) -> None:
        """Exécution parallèle maximale."""
        while not graph.is_complete:
            # Get ready nodes
            ready = graph.get_ready_nodes()
            
            if not ready:
                # Check if blocked
                running = graph.get_running_nodes()
                if not running:
                    break
                
                # Wait for any to complete
                await asyncio.sleep(0.1)
                continue
            
            # Execute all ready in parallel
            tasks = [
                self._execute_node(node, graph)
                for node in ready[:self.config.max_parallel_tasks]
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_critical_path(self, graph: TaskGraph) -> None:
        """Exécution priorisant le chemin critique."""
        # Prioritize critical path nodes
        while not graph.is_complete:
            ready = graph.get_ready_nodes()
            
            if not ready:
                running = graph.get_running_nodes()
                if not running:
                    break
                await asyncio.sleep(0.1)
                continue
            
            # Sort by critical path priority
            ready.sort(
                key=lambda n: (
                    0 if n.node_id in graph.critical_path else 1,
                    -n.priority
                )
            )
            
            # Execute critical first
            to_execute = ready[:self.config.max_parallel_tasks]
            
            tasks = [
                self._execute_node(node, graph)
                for node in to_execute
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_adaptive(self, graph: TaskGraph) -> None:
        """Exécution adaptative selon les ressources."""
        while not graph.is_complete:
            ready = graph.get_ready_nodes()
            
            if not ready:
                running = graph.get_running_nodes()
                if not running:
                    break
                await asyncio.sleep(0.1)
                continue
            
            # Check resources
            available_slots = self._get_available_slots()
            
            if available_slots <= 0:
                await asyncio.sleep(0.1)
                continue
            
            # Select nodes to execute
            to_execute = ready[:min(available_slots, self.config.max_parallel_tasks)]
            
            # Sort by priority and critical path
            to_execute.sort(
                key=lambda n: (
                    0 if n.node_id in graph.critical_path else 1,
                    -n.priority
                )
            )
            
            tasks = [
                self._execute_node(node, graph)
                for node in to_execute
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_node(self, node: TaskNode, graph: TaskGraph) -> None:
        """Exécute un seul nœud."""
        # Callback
        for callback in self._on_node_start:
            try:
                callback(node, graph)
            except Exception as e:
                logger.error(f"Node start callback error: {e}")
        
        node.mark_running()
        
        try:
            # Execute task
            result = await self._execute_task(node)
            
            node.mark_completed(result=result.get("result"), tokens=result.get("tokens", 0))
            graph.completed_nodes += 1
            
            logger.debug(f"Node {node.node_id} completed")
            
        except asyncio.TimeoutError:
            node.mark_failed("Timeout")
            graph.failed_nodes += 1
            logger.warning(f"Node {node.node_id} timed out")
            
        except Exception as e:
            node.mark_failed(str(e))
            graph.failed_nodes += 1
            logger.warning(f"Node {node.node_id} failed: {e}")
            
            # Retry if configured
            if self.config.auto_retry and node.retry_count < node.max_retries:
                node.retry_count += 1
                node.status = NodeStatus.PENDING
                logger.info(f"Retrying node {node.node_id} (attempt {node.retry_count})")
        
        # Callback
        for callback in self._on_node_complete:
            try:
                callback(node, graph)
            except Exception as e:
                logger.error(f"Node complete callback error: {e}")
    
    async def _execute_task(self, node: TaskNode) -> Dict[str, Any]:
        """Exécute la tâche associée à un nœud."""
        if self._task_executor:
            return await self._task_executor(node)
        
        # Default: simulate execution
        await asyncio.sleep(node.estimated_duration_ms / 1000.0)
        
        return {
            "result": f"Completed: {node.name}",
            "tokens": node.estimated_tokens,
        }
    
    def _get_available_slots(self) -> int:
        """Récupère les slots disponibles."""
        if self.resource_manager:
            # Check with resource manager
            return getattr(self.resource_manager, 'get_available_capacity', lambda: self.config.max_parallel_tasks)()
        
        # Default: based on running tasks
        running = sum(
            len(g.get_running_nodes())
            for g in self._active_graphs.values()
        )
        return max(0, self.config.max_parallel_tasks - running)
    
    def _should_continue_after_failure(self, graph: TaskGraph, failed_node: TaskNode) -> bool:
        """Détermine si on continue après un échec."""
        if not self.config.auto_skip_blocked:
            return False
        
        # Skip dependent nodes
        for dep_id in failed_node.dependents:
            dep = graph.nodes.get(dep_id)
            if dep:
                dep.mark_skipped(f"Dependency {failed_node.node_id} failed")
        
        return True
    
    def _finalize_graph(self, graph: TaskGraph) -> None:
        """Finalise le graphe."""
        graph.completed_at = datetime.utcnow()
        
        # Determine final status
        if graph.completed_nodes == graph.total_nodes:
            graph.status = GraphStatus.COMPLETED
            self._successful_executions += 1
        elif graph.completed_nodes > 0:
            graph.status = GraphStatus.PARTIAL
        else:
            graph.status = GraphStatus.FAILED
        
        # Callback
        for callback in self._on_graph_complete:
            try:
                callback(graph)
            except Exception as e:
                logger.error(f"Graph complete callback error: {e}")
        
        logger.info(
            f"Graph {graph.graph_id} finalized: {graph.status.value} "
            f"({graph.completed_nodes}/{graph.total_nodes} nodes)"
        )
    
    # ==========================================
    # TOPOLOGICAL SORT
    # ==========================================
    
    def _topological_sort(self, graph: TaskGraph) -> List[str]:
        """Tri topologique du graphe."""
        in_degree: Dict[str, int] = {}
        
        for node_id, node in graph.nodes.items():
            in_degree[node_id] = len(node.dependencies)
        
        # Queue for nodes with no dependencies
        queue = [
            nid for nid, deg in in_degree.items()
            if deg == 0
        ]
        
        result = []
        
        while queue:
            # Sort by priority
            queue.sort(key=lambda nid: -graph.nodes.get(nid, TaskNode()).priority)
            
            node_id = queue.pop(0)
            result.append(node_id)
            
            node = graph.nodes.get(node_id)
            if node:
                for dep_id in node.dependents:
                    in_degree[dep_id] -= 1
                    if in_degree[dep_id] == 0:
                        queue.append(dep_id)
        
        return result
    
    # ==========================================
    # REOPTIMIZATION
    # ==========================================
    
    def reoptimize(self, graph: TaskGraph) -> None:
        """Réoptimise le graphe en cours d'exécution."""
        # Recalculate critical path
        graph.calculate_critical_path()
        
        # Detect and handle blocking
        blocked = graph.detect_blocking()
        
        for node in blocked:
            if self.config.auto_skip_blocked:
                self._skip_dependents(graph, node)
    
    def _skip_dependents(self, graph: TaskGraph, failed_node: TaskNode) -> None:
        """Skip les dépendants d'un nœud échoué."""
        for dep_id in failed_node.dependents:
            dep = graph.nodes.get(dep_id)
            if dep and dep.status == NodeStatus.PENDING:
                dep.mark_skipped(f"Dependency {failed_node.node_id} failed")
    
    # ==========================================
    # CONTROL
    # ==========================================
    
    def cancel(self, graph_id: str) -> bool:
        """Annule un graphe en cours."""
        graph = self._active_graphs.get(graph_id)
        if not graph:
            return False
        
        graph.status = GraphStatus.CANCELLED
        
        for node in graph.nodes.values():
            if node.status == NodeStatus.RUNNING:
                node.status = NodeStatus.CANCELLED
            elif node.status == NodeStatus.PENDING:
                node.status = NodeStatus.CANCELLED
        
        logger.info(f"Graph {graph_id} cancelled")
        return True
    
    def get_active_executions(self) -> List[TaskGraph]:
        """Retourne les exécutions actives."""
        return list(self._active_graphs.values())
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return {
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "success_rate": self._successful_executions / self._total_executions if self._total_executions > 0 else 0,
            "active_executions": len(self._active_graphs),
            "history_size": len(self._execution_history),
        }
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_node_start(
        self,
        callback: Callable[[TaskNode, TaskGraph], None]
    ) -> None:
        """Callback pour début de nœud."""
        self._on_node_start.append(callback)
    
    def on_node_complete(
        self,
        callback: Callable[[TaskNode, TaskGraph], None]
    ) -> None:
        """Callback pour fin de nœud."""
        self._on_node_complete.append(callback)
    
    def on_graph_complete(
        self,
        callback: Callable[[TaskGraph], None]
    ) -> None:
        """Callback pour fin de graphe."""
        self._on_graph_complete.append(callback)


# ==========================================
# FACTORY
# ==========================================

def create_task_graph_executor(
    config: Optional[ExecutorConfig] = None,
) -> TaskGraphExecutor:
    """Factory pour créer un exécuteur."""
    return TaskGraphExecutor(config=config)


def create_task_graph(
    name: str,
    nodes: Optional[List[TaskNode]] = None,
) -> TaskGraph:
    """Factory pour créer un graphe."""
    graph = TaskGraph(name=name)
    
    for node in (nodes or []):
        graph.add_node(node)
    
    return graph
