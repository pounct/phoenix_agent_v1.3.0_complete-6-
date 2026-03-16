"""
Phoenix Agent - Planner Engine
==============================

Moteur de planification stratégique pour Phoenix.

La différence entre DecisionEngine et PlannerEngine:

    DecisionEngine = RÉACTIF
        - Répond à: "Que dois-je faire MAINTENANT?"
        - Basé sur l'état cognitif actuel
        - Décisions immédiates

    PlannerEngine = STRATÉGIQUE
        - Répond à: "Comment dois-je accomplir ce goal?"
        - Basé sur l'analyse de la tâche
        - Planification à moyen/long terme

Sans PlannerEngine:
    - Agent purement réactif
    - Pas de vision à long terme
    - Pas de décomposition intelligente
    - Risque de boucles et inefficacité

Avec PlannerEngine:
    - Planification stratégique
    - Décomposition de goals
    - Exécution ordonnée
    - Adaptation du plan

Architecture:
    Task → PlannerEngine → PlanGraph → Execution → Adapt

CAPABILITIES:
    - Goal decomposition (décomposer un goal en étapes)
    - Plan graph construction (graphe de dépendances)
    - Execution ordering (ordonnancement)
    - Plan adaptation (révision en cours d'exécution)
    - Progress tracking (suivi de progression)

Version: 0.8.0 (Strategic Planning Layer)
"""

from typing import Optional, List, Dict, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
import re


logger = logging.getLogger("phoenix.planner")


# ==========================================
# PLAN STATUS
# ==========================================

class PlanStatus(str, Enum):
    """Status d'un plan."""
    DRAFT = "draft"               # En cours de création
    READY = "ready"               # Prêt à exécuter
    EXECUTING = "executing"       # En cours d'exécution
    ADAPTING = "adapting"         # En cours d'adaptation
    COMPLETED = "completed"       # Terminé avec succès
    PARTIAL = "partial"           # Succès partiel
    FAILED = "failed"             # Échec
    ABANDONED = "abandoned"       # Abandonné


class StepStatus(str, Enum):
    """Status d'une étape de plan."""
    PENDING = "pending"           # En attente
    READY = "ready"               # Prêt (dépendances satisfaites)
    RUNNING = "running"           # En cours
    COMPLETED = "completed"       # Terminé
    FAILED = "failed"             # Échec
    SKIPPED = "skipped"           # Sauté
    BLOCKED = "blocked"           # Bloqué par dépendances


# ==========================================
# PLAN STEP
# ==========================================

@dataclass
class PlanStep:
    """
    Une étape dans un plan.
    
    Représente une action atomique dans le plan.
    """
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Action
    action_type: str = "execute"  # execute, delegate, parallel, sequential, condition
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # step_ids
    dependents: List[str] = field(default_factory=list)    # step_ids (populated)
    
    # Status
    status: StepStatus = StepStatus.PENDING
    
    # Estimation
    estimated_tokens: int = 500
    estimated_time_ms: float = 1000.0
    priority: int = 5  # 1-10, higher = more important
    
    # Results
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_id: Optional[str] = None  # If delegated
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_ready(self) -> bool:
        """L'étape est prête à être exécutée."""
        return self.status == StepStatus.READY
    
    @property
    def is_completed(self) -> bool:
        """L'étape est terminée."""
        return self.status == StepStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """L'étape a échoué."""
        return self.status == StepStatus.FAILED
    
    @property
    def is_blocked(self) -> bool:
        """L'étape est bloquée."""
        return self.status == StepStatus.BLOCKED
    
    @property
    def duration_ms(self) -> float:
        """Durée d'exécution."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "result": self.result[:100] if self.result else None,
        }


# ==========================================
# PLAN GRAPH
# ==========================================

@dataclass
class PlanGraph:
    """
    Graphe de plan avec dépendances.
    
    Représente un plan complet avec ses étapes et dépendances.
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Steps
    steps: Dict[str, PlanStep] = field(default_factory=dict)
    step_order: List[str] = field(default_factory=list)  # Execution order
    
    # Status
    status: PlanStatus = PlanStatus.DRAFT
    
    # Goal
    goal: str = ""
    success_criteria: List[str] = field(default_factory=list)
    
    # Metrics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    
    # Estimation
    estimated_total_tokens: int = 0
    estimated_total_time_ms: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Adaptation
    adaptation_count: int = 0
    original_plan_id: Optional[str] = None
    
    @property
    def progress(self) -> float:
        """Progression du plan (0.0 - 1.0)."""
        if self.total_steps == 0:
            return 0.0
        return self.completed_steps / self.total_steps
    
    @property
    def is_complete(self) -> bool:
        """Le plan est terminé."""
        return self.status in [PlanStatus.COMPLETED, PlanStatus.PARTIAL, PlanStatus.FAILED]
    
    @property
    def ready_steps(self) -> List[PlanStep]:
        """Étapes prêtes à exécuter."""
        return [s for s in self.steps.values() if s.is_ready]
    
    @property
    def running_steps(self) -> List[PlanStep]:
        """Étapes en cours."""
        return [s for s in self.steps.values() if s.status == StepStatus.RUNNING]
    
    def add_step(self, step: PlanStep) -> None:
        """Ajoute une étape."""
        self.steps[step.step_id] = step
        self.step_order.append(step.step_id)
        self.total_steps = len(self.steps)
        self._update_estimates()
    
    def remove_step(self, step_id: str) -> bool:
        """Supprime une étape."""
        if step_id in self.steps:
            del self.steps[step_id]
            if step_id in self.step_order:
                self.step_order.remove(step_id)
            self.total_steps = len(self.steps)
            self._update_estimates()
            return True
        return False
    
    def _update_estimates(self) -> None:
        """Met à jour les estimations."""
        self.estimated_total_tokens = sum(s.estimated_tokens for s in self.steps.values())
        self.estimated_total_time_ms = sum(s.estimated_time_ms for s in self.steps.values())
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Récupère une étape par ID."""
        return self.steps.get(step_id)
    
    def get_next_steps(self) -> List[PlanStep]:
        """Retourne les prochaines étapes à exécuter."""
        ready = []
        for step_id in self.step_order:
            step = self.steps.get(step_id)
            if step and step.status == StepStatus.PENDING:
                # Check dependencies
                deps_satisfied = all(
                    self.steps.get(dep_id, PlanStep()).status == StepStatus.COMPLETED
                    for dep_id in step.dependencies
                )
                if deps_satisfied:
                    step.status = StepStatus.READY
                    ready.append(step)
        return ready
    
    def mark_step_running(self, step_id: str) -> bool:
        """Marque une étape comme en cours."""
        step = self.steps.get(step_id)
        if step and step.status in [StepStatus.PENDING, StepStatus.READY]:
            step.status = StepStatus.RUNNING
            step.started_at = datetime.utcnow()
            return True
        return False
    
    def mark_step_completed(self, step_id: str, result: str) -> bool:
        """Marque une étape comme terminée."""
        step = self.steps.get(step_id)
        if step:
            step.status = StepStatus.COMPLETED
            step.result = result
            step.completed_at = datetime.utcnow()
            self.completed_steps = sum(1 for s in self.steps.values() if s.is_completed)
            return True
        return False
    
    def mark_step_failed(self, step_id: str, error: str) -> bool:
        """Marque une étape comme échouée."""
        step = self.steps.get(step_id)
        if step:
            step.status = StepStatus.FAILED
            step.error = error
            step.completed_at = datetime.utcnow()
            self.failed_steps = sum(1 for s in self.steps.values() if s.is_failed)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "estimated_tokens": self.estimated_total_tokens,
            "steps": [s.to_dict() for s in self.steps.values()],
        }


# ==========================================
# DECOMPOSITION STRATEGY
# ==========================================

class DecompositionStrategy(str, Enum):
    """Stratégies de décomposition."""
    SEQUENTIAL = "sequential"       # Étapes séquentielles
    PARALLEL = "parallel"           # Étapes parallèles
    HIERARCHICAL = "hierarchical"   # Décomposition hiérarchique
    CONDITIONAL = "conditional"     # Avec conditions
    ITERATIVE = "iterative"         # Itérative (boucles)


# ==========================================
# PLANNING CONTEXT
# ==========================================

@dataclass
class PlanningContext:
    """Contexte pour la planification."""
    goal: str
    
    # Constraints
    max_steps: int = 10
    max_depth: int = 3
    max_tokens_budget: int = 10000
    max_time_budget_ms: float = 60000.0
    
    # Preferences
    prefer_parallel: bool = True
    prefer_delegation: bool = False
    
    # Available resources
    available_agents: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    
    # Current state
    current_tokens_used: int = 0
    current_iterations: int = 0
    
    # History
    previous_plans: List[str] = field(default_factory=list)
    failed_approaches: List[str] = field(default_factory=list)


# ==========================================
# PLANNER ENGINE
# ==========================================

class PlannerEngine:
    """
    Moteur de planification stratégique.
    
    C'est le composant qui transforme un goal en plan exécutable.
    
    Responsabilités:
        1. Analyser le goal
        2. Décomposer en étapes
        3. Construire le graphe de dépendances
        4. Estimer les ressources
        5. Adapter le plan pendant l'exécution
    
    Architecture:
        Goal
          │
          ▼
        ┌─────────────────┐
        │ analyze_goal()  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ decompose()     │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ build_graph()   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ estimate()      │
        └────────┬────────┘
                 │
                 ▼
        PlanGraph
    
    Example:
        planner = PlannerEngine()
        
        # Create a plan
        plan = await planner.plan(
            goal="Build a REST API for user management",
            context=PlanningContext(max_steps=5)
        )
        
        # Execute step by step
        for step in plan.get_next_steps():
            result = await execute_step(step)
            plan.mark_step_completed(step.step_id, result)
        
        # Adapt if needed
        if needs_adaptation:
            new_plan = await planner.adapt(plan, reason="...")
    """
    
    def __init__(
        self,
        default_strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL,
    ):
        self.default_strategy = default_strategy
        
        # Plan history
        self._plans: Dict[str, PlanGraph] = {}
        self._active_plan: Optional[PlanGraph] = None
        
        # Decomposition rules
        self._decomposition_rules: List[Callable] = []
        self._setup_default_rules()
        
        # Stats
        self._total_plans = 0
        self._successful_plans = 0
    
    def _setup_default_rules(self) -> None:
        """Configure les règles de décomposition par défaut."""
        # Rules are applied during decomposition
        pass
    
    # ==========================================
    # MAIN PLANNING
    # ==========================================
    
    async def plan(
        self,
        goal: str,
        context: Optional[PlanningContext] = None,
        strategy: Optional[DecompositionStrategy] = None,
    ) -> PlanGraph:
        """
        Crée un plan pour un goal.
        
        C'est LA méthode centrale du PlannerEngine.
        
        Args:
            goal: Le goal à planifier
            context: Contexte de planification
            strategy: Stratégie de décomposition
            
        Returns:
            PlanGraph
        """
        logger.info(f"Planning: {goal[:50]}...")
        
        context = context or PlanningContext(goal=goal)
        strategy = strategy or self.default_strategy
        
        self._total_plans += 1
        
        # Analyze goal
        analysis = self._analyze_goal(goal, context)
        
        # Create plan
        plan = PlanGraph(
            name=analysis.get("name", "Plan"),
            description=goal,
            goal=goal,
            success_criteria=analysis.get("success_criteria", []),
        )
        
        # Decompose
        steps = await self._decompose(goal, analysis, context, strategy)
        
        # Add steps
        for step in steps:
            plan.add_step(step)
        
        # Build dependencies
        self._build_dependencies(plan)
        
        # Optimize
        self._optimize_plan(plan, context)
        
        # Mark ready
        plan.status = PlanStatus.READY
        
        # Store
        self._plans[plan.plan_id] = plan
        self._active_plan = plan
        
        logger.info(f"Plan created: {plan.plan_id} with {plan.total_steps} steps")
        
        return plan
    
    def _analyze_goal(self, goal: str, context: PlanningContext) -> Dict[str, Any]:
        """Analyse un goal."""
        analysis = {
            "name": self._extract_name(goal),
            "type": self._detect_goal_type(goal),
            "complexity": self._estimate_complexity(goal),
            "success_criteria": self._extract_success_criteria(goal),
            "keywords": self._extract_keywords(goal),
            "suggested_strategy": self._suggest_strategy(goal),
        }
        
        logger.debug(f"Goal analysis: {analysis}")
        
        return analysis
    
    def _extract_name(self, goal: str) -> str:
        """Extrait un nom depuis le goal."""
        # Take first few words
        words = goal.split()[:5]
        return " ".join(words)
    
    def _detect_goal_type(self, goal: str) -> str:
        """Détecte le type de goal."""
        goal_lower = goal.lower()
        
        if any(w in goal_lower for w in ["create", "build", "develop", "implement"]):
            return "creation"
        elif any(w in goal_lower for w in ["analyze", "examine", "investigate"]):
            return "analysis"
        elif any(w in goal_lower for w in ["fix", "debug", "resolve", "solve"]):
            return "problem_solving"
        elif any(w in goal_lower for w in ["optimize", "improve", "enhance"]):
            return "optimization"
        elif any(w in goal_lower for w in ["research", "find", "search"]):
            return "research"
        else:
            return "general"
    
    def _estimate_complexity(self, goal: str) -> str:
        """Estime la complexité du goal."""
        # Simple heuristic
        word_count = len(goal.split())
        has_multiple_parts = any(w in goal.lower() for w in ["and", "then", "also", "additionally"])
        
        if word_count > 50 or has_multiple_parts:
            return "complex"
        elif word_count > 20:
            return "moderate"
        else:
            return "simple"
    
    def _extract_success_criteria(self, goal: str) -> List[str]:
        """Extrait les critères de succès."""
        criteria = []
        
        # Look for "so that", "in order to", etc.
        patterns = [
            r"so that (.+)",
            r"in order to (.+)",
            r"to (.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal, re.IGNORECASE)
            if match:
                criteria.append(match.group(1))
        
        if not criteria:
            criteria = [f"Complete: {goal[:50]}"]
        
        return criteria
    
    def _extract_keywords(self, goal: str) -> List[str]:
        """Extrait les mots-clés."""
        # Simple extraction
        stop_words = {"the", "a", "an", "and", "or", "to", "for", "in", "on", "at", "is", "are"}
        words = [w.lower() for w in goal.split() if w.lower() not in stop_words and len(w) > 3]
        return list(set(words))[:10]
    
    def _suggest_strategy(self, goal: str) -> DecompositionStrategy:
        """Suggère une stratégie."""
        goal_lower = goal.lower()
        
        if any(w in goal_lower for w in ["then", "after", "followed by"]):
            return DecompositionStrategy.SEQUENTIAL
        elif any(w in goal_lower for w in ["simultaneously", "in parallel", "concurrently"]):
            return DecompositionStrategy.PARALLEL
        elif any(w in goal_lower for w in ["if", "when", "depending on"]):
            return DecompositionStrategy.CONDITIONAL
        else:
            return DecompositionStrategy.SEQUENTIAL
    
    # ==========================================
    # DECOMPOSITION
    # ==========================================
    
    async def _decompose(
        self,
        goal: str,
        analysis: Dict[str, Any],
        context: PlanningContext,
        strategy: DecompositionStrategy,
    ) -> List[PlanStep]:
        """Décompose un goal en étapes."""
        
        if strategy == DecompositionStrategy.SEQUENTIAL:
            return self._decompose_sequential(goal, analysis, context)
        elif strategy == DecompositionStrategy.PARALLEL:
            return self._decompose_parallel(goal, analysis, context)
        elif strategy == DecompositionStrategy.HIERARCHICAL:
            return self._decompose_hierarchical(goal, analysis, context)
        elif strategy == DecompositionStrategy.CONDITIONAL:
            return self._decompose_conditional(goal, analysis, context)
        else:
            return self._decompose_sequential(goal, analysis, context)
    
    def _decompose_sequential(
        self,
        goal: str,
        analysis: Dict[str, Any],
        context: PlanningContext,
    ) -> List[PlanStep]:
        """Décomposition séquentielle."""
        steps = []
        
        # Generic sequential decomposition
        goal_type = analysis.get("type", "general")
        
        if goal_type == "creation":
            steps = [
                PlanStep(
                    name="Analyze requirements",
                    description=f"Understand what needs to be created for: {goal[:50]}",
                    action_type="analyze",
                    priority=8,
                ),
                PlanStep(
                    name="Design approach",
                    description="Plan the implementation approach",
                    action_type="plan",
                    priority=7,
                ),
                PlanStep(
                    name="Implement",
                    description="Create the solution",
                    action_type="execute",
                    estimated_tokens=2000,
                    priority=9,
                ),
                PlanStep(
                    name="Validate",
                    description="Verify the solution meets requirements",
                    action_type="validate",
                    priority=6,
                ),
            ]
        
        elif goal_type == "analysis":
            steps = [
                PlanStep(
                    name="Gather information",
                    description=f"Collect relevant data for: {goal[:50]}",
                    action_type="research",
                    priority=8,
                ),
                PlanStep(
                    name="Analyze data",
                    description="Process and analyze the information",
                    action_type="analyze",
                    estimated_tokens=1500,
                    priority=7,
                ),
                PlanStep(
                    name="Synthesize findings",
                    description="Create summary and insights",
                    action_type="synthesize",
                    priority=6,
                ),
            ]
        
        elif goal_type == "problem_solving":
            steps = [
                PlanStep(
                    name="Identify problem",
                    description=f"Understand the problem: {goal[:50]}",
                    action_type="analyze",
                    priority=9,
                ),
                PlanStep(
                    name="Investigate causes",
                    description="Find root causes",
                    action_type="investigate",
                    priority=8,
                ),
                PlanStep(
                    name="Propose solution",
                    description="Develop solution approach",
                    action_type="plan",
                    priority=7,
                ),
                PlanStep(
                    name="Implement fix",
                    description="Apply the solution",
                    action_type="execute",
                    estimated_tokens=1500,
                    priority=9,
                ),
                PlanStep(
                    name="Verify fix",
                    description="Confirm problem is resolved",
                    action_type="validate",
                    priority=6,
                ),
            ]
        
        else:
            # Generic
            steps = [
                PlanStep(
                    name="Understand goal",
                    description=f"Analyze: {goal[:50]}",
                    action_type="analyze",
                    priority=8,
                ),
                PlanStep(
                    name="Plan approach",
                    description="Determine how to proceed",
                    action_type="plan",
                    priority=7,
                ),
                PlanStep(
                    name="Execute",
                    description="Perform the main work",
                    action_type="execute",
                    estimated_tokens=2000,
                    priority=9,
                ),
                PlanStep(
                    name="Finalize",
                    description="Complete and summarize",
                    action_type="finalize",
                    priority=5,
                ),
            ]
        
        # Set dependencies (sequential)
        for i in range(1, len(steps)):
            steps[i].dependencies.append(steps[i-1].step_id)
        
        # Limit steps
        return steps[:context.max_steps]
    
    def _decompose_parallel(
        self,
        goal: str,
        analysis: Dict[str, Any],
        context: PlanningContext,
    ) -> List[PlanStep]:
        """Décomposition parallèle."""
        # Start with sequential
        steps = self._decompose_sequential(goal, analysis, context)
        
        # Find steps that can be parallelized
        # For simplicity, just remove some dependencies
        for step in steps[2:]:  # Keep first two sequential
            step.dependencies = [steps[0].step_id]  # Only depend on first step
        
        return steps
    
    def _decompose_hierarchical(
        self,
        goal: str,
        analysis: Dict[str, Any],
        context: PlanningContext,
    ) -> List[PlanStep]:
        """Décomposition hiérarchique."""
        # Main step
        main = PlanStep(
            name="Main goal",
            description=goal,
            action_type="hierarchical",
            priority=10,
        )
        
        # Sub-steps
        sub_steps = self._decompose_sequential(goal, analysis, context)
        
        # Make all depend on main
        for step in sub_steps:
            step.dependencies = [main.step_id]
        
        return [main] + sub_steps
    
    def _decompose_conditional(
        self,
        goal: str,
        analysis: Dict[str, Any],
        context: PlanningContext,
    ) -> List[PlanStep]:
        """Décomposition conditionnelle."""
        # Base sequential with condition step
        steps = self._decompose_sequential(goal, analysis, context)
        
        # Add condition check step
        condition = PlanStep(
            name="Check conditions",
            description="Evaluate conditions before proceeding",
            action_type="condition",
            priority=10,
        )
        
        # Insert at beginning
        steps.insert(0, condition)
        
        # Update dependencies
        for step in steps[1:]:
            step.dependencies = [condition.step_id]
        
        return steps
    
    # ==========================================
    # DEPENDENCY BUILDING
    # ==========================================
    
    def _build_dependencies(self, plan: PlanGraph) -> None:
        """Construit les dépendances inverses."""
        # Clear existing
        for step in plan.steps.values():
            step.dependents = []
        
        # Build reverse dependencies
        for step in plan.steps.values():
            for dep_id in step.dependencies:
                dep_step = plan.steps.get(dep_id)
                if dep_step and step.step_id not in dep_step.dependents:
                    dep_step.dependents.append(step.step_id)
    
    def _optimize_plan(self, plan: PlanGraph, context: PlanningContext) -> None:
        """Optimise le plan."""
        # Check token budget
        if plan.estimated_total_tokens > context.max_tokens_budget:
            # Reduce complexity
            self._reduce_plan(plan, context.max_tokens_budget)
        
        # Check step count
        if plan.total_steps > context.max_steps:
            self._consolidate_steps(plan, context.max_steps)
    
    def _reduce_plan(self, plan: PlanGraph, max_tokens: int) -> None:
        """Réduit le plan pour respecter le budget."""
        while plan.estimated_total_tokens > max_tokens and len(plan.steps) > 1:
            # Remove lowest priority step
            lowest = min(
                plan.steps.values(),
                key=lambda s: s.priority
            )
            plan.remove_step(lowest.step_id)
    
    def _consolidate_steps(self, plan: PlanGraph, max_steps: int) -> None:
        """Consolide les étapes."""
        while len(plan.steps) > max_steps:
            # Find adjacent low-priority steps to merge
            merged = False
            step_list = list(plan.steps.values())
            
            for i in range(len(step_list) - 1):
                s1, s2 = step_list[i], step_list[i + 1]
                if s1.priority <= 5 and s2.priority <= 5:
                    # Merge
                    s1.description = f"{s1.description} + {s2.description}"
                    s1.estimated_tokens += s2.estimated_tokens
                    # Remove s2
                    plan.remove_step(s2.step_id)
                    merged = True
                    break
            
            if not merged:
                # Just remove lowest priority
                lowest = min(step_list, key=lambda s: s.priority)
                plan.remove_step(lowest.step_id)
    
    # ==========================================
    # PLAN ADAPTATION
    # ==========================================
    
    async def adapt(
        self,
        plan: PlanGraph,
        reason: str,
        context: Optional[PlanningContext] = None,
    ) -> PlanGraph:
        """
        Adapte un plan existant.
        
        Args:
            plan: Le plan à adapter
            reason: Raison de l'adaptation
            context: Nouveau contexte
            
        Returns:
            PlanGraph adapté
        """
        logger.info(f"Adapting plan {plan.plan_id}: {reason}")
        
        plan.status = PlanStatus.ADAPTING
        plan.adaptation_count += 1
        
        # Create adapted plan
        new_plan = PlanGraph(
            name=f"{plan.name} (adapted)",
            description=plan.description,
            goal=plan.goal,
            success_criteria=plan.success_criteria,
            original_plan_id=plan.plan_id,
        )
        
        # Copy non-completed steps
        for step_id in plan.step_order:
            step = plan.steps.get(step_id)
            if step and step.status not in [StepStatus.COMPLETED, StepStatus.SKIPPED]:
                new_step = PlanStep(
                    name=step.name,
                    description=step.description,
                    action_type=step.action_type,
                    action_params=step.action_params.copy(),
                    priority=step.priority,
                    estimated_tokens=step.estimated_tokens,
                )
                new_plan.add_step(new_step)
        
        # Add recovery step if failure
        if "failed" in reason.lower():
            recovery_step = PlanStep(
                name="Recovery",
                description="Address the failure and retry",
                action_type="recover",
                priority=10,
            )
            new_plan.add_step(recovery_step)
        
        # Rebuild dependencies
        self._build_dependencies(new_plan)
        
        # Optimize
        if context:
            self._optimize_plan(new_plan, context)
        
        new_plan.status = PlanStatus.READY
        
        # Store
        self._plans[new_plan.plan_id] = new_plan
        self._active_plan = new_plan
        
        logger.info(f"Plan adapted: {new_plan.plan_id} with {new_plan.total_steps} steps")
        
        return new_plan
    
    # ==========================================
    # QUICK PLANNING
    # ==========================================
    
    def quick_plan(self, goal: str, max_steps: int = 5) -> PlanGraph:
        """Planification rapide (synchrone)."""
        context = PlanningContext(goal=goal, max_steps=max_steps)
        
        # Simple plan without async decomposition
        plan = PlanGraph(
            name=goal[:30],
            description=goal,
            goal=goal,
        )
        
        # Add generic steps
        generic_steps = [
            ("Analyze", "Understand the goal", "analyze"),
            ("Plan", "Determine approach", "plan"),
            ("Execute", "Perform main work", "execute"),
            ("Verify", "Check results", "validate"),
        ]
        
        prev_id = None
        for name, desc, action in generic_steps[:max_steps]:
            step = PlanStep(name=name, description=desc, action_type=action)
            if prev_id:
                step.dependencies.append(prev_id)
            plan.add_step(step)
            prev_id = step.step_id
        
        plan.status = PlanStatus.READY
        self._plans[plan.plan_id] = plan
        
        return plan
    
    # ==========================================
    # PLAN MANAGEMENT
    # ==========================================
    
    def get_plan(self, plan_id: str) -> Optional[PlanGraph]:
        """Récupère un plan par ID."""
        return self._plans.get(plan_id)
    
    def get_active_plan(self) -> Optional[PlanGraph]:
        """Retourne le plan actif."""
        return self._active_plan
    
    def set_active_plan(self, plan_id: str) -> bool:
        """Définit le plan actif."""
        plan = self._plans.get(plan_id)
        if plan:
            self._active_plan = plan
            return True
        return False
    
    def list_plans(self) -> List[PlanGraph]:
        """Liste tous les plans."""
        return list(self._plans.values())
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        completed = sum(1 for p in self._plans.values() if p.status == PlanStatus.COMPLETED)
        
        return {
            "total_plans": self._total_plans,
            "completed_plans": completed,
            "success_rate": completed / self._total_plans if self._total_plans > 0 else 0,
            "active_plan_id": self._active_plan.plan_id if self._active_plan else None,
            "plans_count": len(self._plans),
        }


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_plan(
    goal: str,
    max_steps: int = 5,
    strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL,
) -> PlanGraph:
    """Fonction utilitaire pour créer un plan rapidement."""
    planner = PlannerEngine(default_strategy=strategy)
    return planner.quick_plan(goal, max_steps)


async def plan_goal(
    goal: str,
    context: Optional[PlanningContext] = None,
) -> PlanGraph:
    """Fonction utilitaire pour planifier un goal."""
    planner = PlannerEngine()
    return await planner.plan(goal, context)
