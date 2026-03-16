"""
Phoenix Agent - Goal Manager
============================

Couche de gestion des objectifs persistants.

La différence entre Task et Goal:

    Task = ACTION
        - "Execute this function"
        - "Process this data"
        - Finite, specific, executable

    Goal = INTENTION
        - "Become proficient in Python"
        - "Solve the user's problem"
        - Persistent, strategic, directional

Un Agent OS traite des GOALS, pas juste des tasks.

Sans GoalManager:
    - Tasks isolées sans contexte stratégique
    - Pas de priorisation intelligente
    - Pas de dépendances entre objectifs
    - Pas de succès durable

Avec GoalManager:
    - Objectifs persistants avec lifecycle
    - Priorisation automatique
    - Dépendances et contraintes
    - Critères de succès vérifiables
    - Alignement des tasks vers les goals

Architecture:
    Goal → GoalManager → PlannerEngine → Tasks → Execution

LIFECYCLE:
    DRAFT → ACTIVE → IN_PROGRESS → COMPLETED/FAILED/SUSPENDED

Version: 1.0.0 (Cognitive Goal Layer)
"""

from typing import Optional, List, Dict, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid


logger = logging.getLogger("phoenix.goal_manager")


# ==========================================
# GOAL STATUS
# ==========================================

class GoalStatus(str, Enum):
    """Status d'un objectif."""
    DRAFT = "draft"                   # En création
    ACTIVE = "active"                 # Actif, en attente
    IN_PROGRESS = "in_progress"       # En cours de réalisation
    BLOCKED = "blocked"               # Bloqué par dépendances
    SUSPENDED = "suspended"           # Suspendu temporairement
    COMPLETED = "completed"           # Terminé avec succès
    FAILED = "failed"                 # Échec
    CANCELLED = "cancelled"           # Annulé
    MERGED = "merged"                 # Fusionné dans un autre goal


class GoalPriority(str, Enum):
    """Priorité d'un objectif."""
    CRITICAL = "critical"    # Urgent, bloque tout
    HIGH = "high"            # Important
    NORMAL = "normal"        # Standard
    LOW = "low"              # Peut attendre
    BACKGROUND = "background"  # Quand rien d'autre


class GoalType(str, Enum):
    """Type d'objectif."""
    ACHIEVEMENT = "achievement"   # Atteindre un état
    MAINTENANCE = "maintenance"   # Maintenir un état
    OPTIMIZATION = "optimization"  # Optimiser quelque chose
    EXPLORATION = "exploration"   # Explorer des options
    LEARNING = "learning"         # Apprendre quelque chose
    PROBLEM_SOLVING = "problem_solving"  # Résoudre un problème


# ==========================================
# SUCCESS CRITERIA
# ==========================================

@dataclass
class SuccessCriterion:
    """Critère de succès pour un objectif."""
    criterion_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    
    # Type
    metric: str = ""  # accuracy, completion_rate, time, etc.
    target_value: float = 1.0
    operator: str = ">="  # >=, <=, ==, >, <
    
    # Current state
    current_value: Optional[float] = None
    
    # Weight in overall success
    weight: float = 1.0
    
    @property
    def is_satisfied(self) -> bool:
        """Le critère est satisfait."""
        if self.current_value is None:
            return False
        
        ops = {
            ">=": self.current_value >= self.target_value,
            "<=": self.current_value <= self.target_value,
            "==": self.current_value == self.target_value,
            ">": self.current_value > self.target_value,
            "<": self.current_value < self.target_value,
        }
        return ops.get(self.operator, False)
    
    def check(self, value: float) -> bool:
        """Vérifie le critère avec une valeur."""
        self.current_value = value
        return self.is_satisfied
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "description": self.description,
            "metric": self.metric,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "is_satisfied": self.is_satisfied,
            "weight": self.weight,
        }


# ==========================================
# GOAL CONSTRAINT
# ==========================================

@dataclass
class GoalConstraint:
    """Contrainte sur un objectif."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Type
    constraint_type: str = "resource"  # resource, time, dependency, quality
    
    # Value
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    
    # Is it a hard constraint?
    hard: bool = True  # Hard = must respect, Soft = should respect
    
    # Current status
    is_violated: bool = False
    
    def check(self, current_value: float) -> bool:
        """Vérifie si la contrainte est respectée."""
        self.is_violated = False
        
        if self.max_value is not None and current_value > self.max_value:
            self.is_violated = True
        
        if self.min_value is not None and current_value < self.min_value:
            self.is_violated = True
        
        return not self.is_violated
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "type": self.constraint_type,
            "hard": self.hard,
            "is_violated": self.is_violated,
        }


# ==========================================
# GOAL
# ==========================================

@dataclass
class Goal:
    """
    Un objectif persistant avec lifecycle complet.
    
    La différence clé avec Task:
        - Task = "faire"
        - Goal = "atteindre"
    
    Un Goal peut générer plusieurs Tasks.
    Un Goal persiste au-delà des tasks individuelles.
    """
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Type and Priority
    goal_type: GoalType = GoalType.ACHIEVEMENT
    priority: GoalPriority = GoalPriority.NORMAL
    
    # Status
    status: GoalStatus = GoalStatus.DRAFT
    
    # Hierarchy
    parent_goal_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)  # goal_ids
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # goal_ids that must complete first
    blocks: List[str] = field(default_factory=list)      # goal_ids that wait for this one
    
    # Success criteria
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    
    # Constraints
    constraints: List[GoalConstraint] = field(default_factory=list)
    
    # Origin
    origin: str = "user"  # user, system, agent, derived
    created_by: str = ""
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Metrics
    progress: float = 0.0  # 0.0 - 1.0
    effort_spent: float = 0.0  # Cumulative effort
    tasks_generated: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Results
    outcome: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Le goal est actif."""
        return self.status in [GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS]
    
    @property
    def is_completed(self) -> bool:
        """Le goal est terminé."""
        return self.status in [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED, GoalStatus.MERGED]
    
    @property
    def is_blocked(self) -> bool:
        """Le goal est bloqué."""
        return self.status == GoalStatus.BLOCKED
    
    @property
    def is_overdue(self) -> bool:
        """Le goal est en retard."""
        if self.deadline is None:
            return False
        return datetime.utcnow() > self.deadline and not self.is_completed
    
    @property
    def success_rate(self) -> float:
        """Taux de succès des critères."""
        if not self.success_criteria:
            return self.progress
        
        satisfied = sum(1 for c in self.success_criteria if c.is_satisfied)
        return satisfied / len(self.success_criteria)
    
    @property
    def has_hard_constraint_violation(self) -> bool:
        """Violence de contrainte dure."""
        return any(c.is_violated and c.hard for c in self.constraints)
    
    def check_success(self) -> bool:
        """Vérifie si le goal est réussi."""
        if not self.success_criteria:
            return self.progress >= 1.0
        
        return all(c.is_satisfied for c in self.success_criteria)
    
    def check_constraints(self) -> bool:
        """Vérifie les contraintes."""
        return not self.has_hard_constraint_violation
    
    def update_progress(self, progress: float) -> None:
        """Met à jour la progression."""
        self.progress = max(0.0, min(1.0, progress))
        
        # Auto-complete if 100%
        if self.progress >= 1.0 and self.check_success():
            self.status = GoalStatus.COMPLETED
            self.completed_at = datetime.utcnow()
    
    def add_criterion(self, criterion: SuccessCriterion) -> None:
        """Ajoute un critère de succès."""
        self.success_criteria.append(criterion)
    
    def add_constraint(self, constraint: GoalConstraint) -> None:
        """Ajoute une contrainte."""
        self.constraints.append(constraint)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "type": self.goal_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "progress": self.progress,
            "success_rate": self.success_rate,
            "is_active": self.is_active,
            "is_blocked": self.is_blocked,
            "is_overdue": self.is_overdue,
            "depends_on": self.depends_on,
            "blocks": self.blocks,
            "criteria_count": len(self.success_criteria),
            "constraints_count": len(self.constraints),
        }


# ==========================================
# GOAL MANAGER CONFIG
# ==========================================

@dataclass
class GoalManagerConfig:
    """Configuration du GoalManager."""
    max_active_goals: int = 10
    max_total_goals: int = 100
    
    # Priority settings
    auto_prioritize: bool = True
    priority_boost_on_overdue: bool = True
    
    # Dependency handling
    auto_block_on_dependency: bool = True
    auto_unblock_on_completion: bool = True
    
    # Cleanup
    auto_cleanup_completed: bool = True
    completed_retention_days: int = 7
    
    # Goal merging
    allow_goal_merging: bool = True
    merge_similarity_threshold: float = 0.8


# ==========================================
# GOAL MANAGER
# ==========================================

class GoalManager:
    """
    Gestionnaire des objectifs persistants.
    
    C'est LE composant qui répond à: "Pourquoi je fais cette tâche?"
    
    Responsabilités:
        1. Gérer le lifecycle des goals
        2. Prioriser automatiquement
        3. Gérer les dépendances
        4. Vérifier les critères de succès
        5. Aligner les tasks avec les goals
    
    Architecture:
        User Request → GoalManager.add_goal()
                            │
                            ├── Prioritize
                            ├── Check dependencies
                            └── Create tasks
                                    │
                                    ▼
                            PlannerEngine.plan(goal)
    
    Example:
        manager = GoalManager()
        
        # Add a goal
        goal = manager.add_goal(Goal(
            name="Learn Python",
            goal_type=GoalType.LEARNING,
            priority=GoalPriority.HIGH,
            success_criteria=[
                SuccessCriterion(
                    description="Complete 10 exercises",
                    metric="exercises_completed",
                    target_value=10,
                )
            ]
        ))
        
        # Get next goal to work on
        next_goal = manager.get_next_goal()
        
        # Check alignment
        if manager.is_task_aligned(task, goal):
            execute_task(task)
    """
    
    def __init__(self, config: Optional[GoalManagerConfig] = None):
        self.config = config or GoalManagerConfig()
        
        # Goal storage
        self._goals: Dict[str, Goal] = {}
        self._active_goals: Set[str] = set()
        
        # Goal history
        self._completed_goals: List[str] = []
        self._failed_goals: List[str] = []
        
        # Goal-task mapping
        self._goal_tasks: Dict[str, List[str]] = {}  # goal_id -> task_ids
        self._task_goal: Dict[str, str] = {}  # task_id -> goal_id
        
        # Callbacks
        self._on_goal_completed: List[Callable[[Goal], None]] = []
        self._on_goal_blocked: List[Callable[[Goal], None]] = []
        self._on_goal_priority_change: List[Callable[[Goal, GoalPriority], None]] = []
        
        logger.info("GoalManager initialized")
    
    # ==========================================
    # GOAL LIFECYCLE
    # ==========================================
    
    def add_goal(self, goal: Goal) -> Goal:
        """
        Ajoute un nouvel objectif.
        
        C'est LE point d'entrée pour créer des goals.
        
        Args:
            goal: L'objectif à ajouter
            
        Returns:
            Le goal ajouté (avec status mis à jour)
        """
        # Validate
        if len(self._goals) >= self.config.max_total_goals:
            logger.warning(f"Max goals reached ({self.config.max_total_goals})")
            # Try cleanup
            self._cleanup_completed()
        
        # Check dependencies
        unmet_deps = self._check_unmet_dependencies(goal)
        if unmet_deps:
            goal.status = GoalStatus.BLOCKED
            logger.info(f"Goal {goal.goal_id} blocked by: {unmet_deps}")
        else:
            goal.status = GoalStatus.ACTIVE
            goal.activated_at = datetime.utcnow()
        
        # Store
        self._goals[goal.goal_id] = goal
        self._active_goals.add(goal.goal_id)
        
        # Initialize task mapping
        self._goal_tasks[goal.goal_id] = []
        
        # Update dependency graph
        self._update_dependency_graph(goal)
        
        logger.info(f"Added goal: {goal.name} ({goal.goal_id})")
        
        return goal
    
    def create_goal(
        self,
        name: str,
        description: str = "",
        goal_type: GoalType = GoalType.ACHIEVEMENT,
        priority: GoalPriority = GoalPriority.NORMAL,
        success_criteria: Optional[List[SuccessCriterion]] = None,
        constraints: Optional[List[GoalConstraint]] = None,
        depends_on: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
    ) -> Goal:
        """Factory pour créer et ajouter un goal."""
        goal = Goal(
            name=name,
            description=description,
            goal_type=goal_type,
            priority=priority,
            success_criteria=success_criteria or [],
            constraints=constraints or [],
            depends_on=depends_on or [],
            deadline=deadline,
        )
        return self.add_goal(goal)
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Récupère un goal par ID."""
        return self._goals.get(goal_id)
    
    def get_goals_by_status(self, status: GoalStatus) -> List[Goal]:
        """Récupère les goals par status."""
        return [g for g in self._goals.values() if g.status == status]
    
    def get_active_goals(self) -> List[Goal]:
        """Récupère tous les goals actifs."""
        return [self._goals[gid] for gid in self._active_goals if gid in self._goals]
    
    # ==========================================
    # PRIORITIZATION
    # ==========================================
    
    def prioritize(self) -> List[Goal]:
        """
        Priorise automatiquement les goals.
        
        Returns:
            Liste des goals actifs triés par priorité
        """
        active = self.get_active_goals()
        
        # Sort by priority
        priority_order = {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.NORMAL: 2,
            GoalPriority.LOW: 3,
            GoalPriority.BACKGROUND: 4,
        }
        
        # Sort factors
        def priority_score(goal: Goal) -> tuple:
            # Base priority
            base = priority_order.get(goal.priority, 2)
            
            # Boost overdue
            overdue_boost = 0 if not goal.is_overdue else -1
            
            # Progress (less progress = higher priority)
            progress_score = 1 - goal.progress
            
            # Deadline urgency
            deadline_score = 0
            if goal.deadline:
                time_left = (goal.deadline - datetime.utcnow()).total_seconds()
                if time_left < 3600:  # < 1 hour
                    deadline_score = -2
                elif time_left < 86400:  # < 1 day
                    deadline_score = -1
            
            return (base + overdue_boost + deadline_score, progress_score)
        
        sorted_goals = sorted(active, key=priority_score)
        
        # Limit active goals
        if len(sorted_goals) > self.config.max_active_goals:
            # Deactivate lowest priority
            for goal in sorted_goals[self.config.max_active_goals:]:
                goal.status = GoalStatus.SUSPENDED
                self._active_goals.discard(goal.goal_id)
        
        return sorted_goals
    
    def get_next_goal(self) -> Optional[Goal]:
        """Retourne le prochain goal à traiter."""
        prioritized = self.prioritize()
        return prioritized[0] if prioritized else None
    
    def set_priority(self, goal_id: str, priority: GoalPriority) -> bool:
        """Change la priorité d'un goal."""
        goal = self._goals.get(goal_id)
        if goal:
            old_priority = goal.priority
            goal.priority = priority
            logger.info(f"Goal {goal_id} priority: {old_priority.value} → {priority.value}")
            return True
        return False
    
    # ==========================================
    # DEPENDENCY MANAGEMENT
    # ==========================================
    
    def _check_unmet_dependencies(self, goal: Goal) -> List[str]:
        """Vérifie les dépendances non satisfaites."""
        unmet = []
        for dep_id in goal.depends_on:
            dep = self._goals.get(dep_id)
            if not dep or dep.status != GoalStatus.COMPLETED:
                unmet.append(dep_id)
        return unmet
    
    def _update_dependency_graph(self, goal: Goal) -> None:
        """Met à jour le graphe de dépendances."""
        for dep_id in goal.depends_on:
            dep = self._goals.get(dep_id)
            if dep and goal.goal_id not in dep.blocks:
                dep.blocks.append(goal.goal_id)
    
    def _unblock_dependent_goals(self, completed_goal_id: str) -> None:
        """Débloque les goals qui dépendaient du goal complété."""
        goal = self._goals.get(completed_goal_id)
        if not goal:
            return
        
        for blocked_id in goal.blocks:
            blocked = self._goals.get(blocked_id)
            if blocked and blocked.status == GoalStatus.BLOCKED:
                unmet = self._check_unmet_dependencies(blocked)
                if not unmet:
                    blocked.status = GoalStatus.ACTIVE
                    blocked.activated_at = datetime.utcnow()
                    self._active_goals.add(blocked_id)
                    logger.info(f"Goal {blocked_id} unblocked")
    
    # ==========================================
    # GOAL OPERATIONS
    # ==========================================
    
    def start_goal(self, goal_id: str) -> bool:
        """Démarre un goal."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status not in [GoalStatus.ACTIVE, GoalStatus.SUSPENDED]:
            return False
        
        # Check dependencies
        unmet = self._check_unmet_dependencies(goal)
        if unmet:
            goal.status = GoalStatus.BLOCKED
            return False
        
        goal.status = GoalStatus.IN_PROGRESS
        goal.started_at = datetime.utcnow()
        
        logger.info(f"Goal {goal_id} started")
        return True
    
    def suspend_goal(self, goal_id: str, reason: str = "") -> bool:
        """Suspend un goal."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status not in [GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS]:
            return False
        
        goal.status = GoalStatus.SUSPENDED
        self._active_goals.discard(goal_id)
        
        logger.info(f"Goal {goal_id} suspended: {reason}")
        return True
    
    def resume_goal(self, goal_id: str) -> bool:
        """Reprend un goal suspendu."""
        goal = self._goals.get(goal_id)
        if not goal or goal.status != GoalStatus.SUSPENDED:
            return False
        
        # Check if can activate
        unmet = self._check_unmet_dependencies(goal)
        if unmet:
            goal.status = GoalStatus.BLOCKED
            return False
        
        goal.status = GoalStatus.ACTIVE
        self._active_goals.add(goal_id)
        
        logger.info(f"Goal {goal_id} resumed")
        return True
    
    def cancel_goal(self, goal_id: str, reason: str = "") -> bool:
        """Annule un goal."""
        goal = self._goals.get(goal_id)
        if not goal or goal.is_completed:
            return False
        
        goal.status = GoalStatus.CANCELLED
        goal.completed_at = datetime.utcnow()
        goal.outcome = f"Cancelled: {reason}"
        
        self._active_goals.discard(goal_id)
        self._failed_goals.append(goal_id)
        
        logger.info(f"Goal {goal_id} cancelled: {reason}")
        return True
    
    def complete_goal(self, goal_id: str, outcome: str = "") -> bool:
        """Marque un goal comme complété."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = datetime.utcnow()
        goal.outcome = outcome
        goal.progress = 1.0
        
        self._active_goals.discard(goal_id)
        self._completed_goals.append(goal_id)
        
        # Unblock dependent goals
        if self.config.auto_unblock_on_completion:
            self._unblock_dependent_goals(goal_id)
        
        # Callbacks
        for callback in self._on_goal_completed:
            try:
                callback(goal)
            except Exception as e:
                logger.error(f"Goal completion callback error: {e}")
        
        logger.info(f"Goal {goal_id} completed: {outcome}")
        return True
    
    def fail_goal(self, goal_id: str, reason: str = "") -> bool:
        """Marque un goal comme échoué."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        
        goal.status = GoalStatus.FAILED
        goal.completed_at = datetime.utcnow()
        goal.outcome = f"Failed: {reason}"
        
        self._active_goals.discard(goal_id)
        self._failed_goals.append(goal_id)
        
        logger.warning(f"Goal {goal_id} failed: {reason}")
        return True
    
    # ==========================================
    # GOAL MERGING
    # ==========================================
    
    def merge_goals(
        self,
        goal_ids: List[str],
        merged_name: str = "",
        merged_description: str = "",
    ) -> Optional[Goal]:
        """Fusionne plusieurs goals en un seul."""
        if not self.config.allow_goal_merging or len(goal_ids) < 2:
            return None
        
        goals = [self._goals.get(gid) for gid in goal_ids if gid in self._goals]
        if len(goals) < 2:
            return None
        
        # Create merged goal
        merged = Goal(
            name=merged_name or f"Merged: {goals[0].name}",
            description=merged_description or "Merged from multiple goals",
            goal_type=goals[0].goal_type,
            priority=max(goals, key=lambda g: self._priority_value(g.priority)).priority,
            success_criteria=[c for g in goals for c in g.success_criteria],
            constraints=[c for g in goals for c in g.constraints],
        )
        
        # Mark original goals as merged
        for goal in goals:
            goal.status = GoalStatus.MERGED
            goal.completed_at = datetime.utcnow()
            self._active_goals.discard(goal.goal_id)
        
        # Add merged goal
        return self.add_goal(merged)
    
    def _priority_value(self, priority: GoalPriority) -> int:
        """Convertit priorité en valeur numérique."""
        order = {
            GoalPriority.CRITICAL: 5,
            GoalPriority.HIGH: 4,
            GoalPriority.NORMAL: 3,
            GoalPriority.LOW: 2,
            GoalPriority.BACKGROUND: 1,
        }
        return order.get(priority, 3)
    
    # ==========================================
    # TASK ALIGNMENT
    # ==========================================
    
    def align_task(self, task_id: str, goal_id: str) -> bool:
        """Aligne une task avec un goal."""
        if goal_id not in self._goals:
            return False
        
        # Remove from previous goal if any
        old_goal_id = self._task_goal.get(task_id)
        if old_goal_id and old_goal_id in self._goal_tasks:
            if task_id in self._goal_tasks[old_goal_id]:
                self._goal_tasks[old_goal_id].remove(task_id)
        
        # Add to new goal
        self._task_goal[task_id] = goal_id
        if goal_id not in self._goal_tasks:
            self._goal_tasks[goal_id] = []
        self._goal_tasks[goal_id].append(task_id)
        
        # Update goal
        goal = self._goals[goal_id]
        goal.tasks_generated += 1
        
        return True
    
    def is_task_aligned(self, task_id: str, goal_id: str) -> bool:
        """Vérifie si une task est alignée avec un goal."""
        return self._task_goal.get(task_id) == goal_id
    
    def get_goal_for_task(self, task_id: str) -> Optional[Goal]:
        """Récupère le goal associé à une task."""
        goal_id = self._task_goal.get(task_id)
        if goal_id:
            return self._goals.get(goal_id)
        return None
    
    def get_tasks_for_goal(self, goal_id: str) -> List[str]:
        """Récupère les tasks associées à un goal."""
        return self._goal_tasks.get(goal_id, [])
    
    # ==========================================
    # PROGRESS UPDATE
    # ==========================================
    
    def update_progress(self, goal_id: str, progress: float) -> bool:
        """Met à jour la progression d'un goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        
        goal.update_progress(progress)
        
        # Check for completion
        if goal.check_success() and goal.progress >= 1.0:
            self.complete_goal(goal_id, "Success criteria met")
        
        return True
    
    def update_criterion(
        self,
        goal_id: str,
        metric: str,
        value: float,
    ) -> bool:
        """Met à jour un critère de succès."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        
        for criterion in goal.success_criteria:
            if criterion.metric == metric:
                criterion.check(value)
        
        # Check completion
        if goal.check_success():
            self.complete_goal(goal_id, "All criteria satisfied")
        
        return True
    
    # ==========================================
    # QUERY
    # ==========================================
    
    def get_status_summary(self) -> Dict[str, int]:
        """Retourne un résumé par status."""
        summary = {status.value: 0 for status in GoalStatus}
        for goal in self._goals.values():
            summary[goal.status.value] += 1
        return summary
    
    def get_blocked_goals(self) -> List[Goal]:
        """Retourne les goals bloqués."""
        return self.get_goals_by_status(GoalStatus.BLOCKED)
    
    def get_overdue_goals(self) -> List[Goal]:
        """Retourne les goals en retard."""
        return [g for g in self._goals.values() if g.is_overdue]
    
    def get_goal_chain(self, goal_id: str) -> List[Goal]:
        """Retourne la chaîne de goals (parent → goal → sub-goals)."""
        chain = []
        goal = self._goals.get(goal_id)
        if not goal:
            return chain
        
        # Add parent
        if goal.parent_goal_id:
            parent = self._goals.get(goal.parent_goal_id)
            if parent:
                chain.extend(self.get_goal_chain(parent.goal_id))
        
        # Add self
        chain.append(goal)
        
        # Add sub-goals
        for sub_id in goal.sub_goals:
            sub = self._goals.get(sub_id)
            if sub:
                chain.extend(self.get_goal_chain(sub_id))
        
        return chain
    
    # ==========================================
    # CLEANUP
    # ==========================================
    
    def _cleanup_completed(self) -> int:
        """Nettoie les goals complétés anciens."""
        if not self.config.auto_cleanup_completed:
            return 0
        
        cutoff = datetime.utcnow() - timedelta(days=self.config.completed_retention_days)
        
        removed = 0
        to_remove = []
        
        for goal_id, goal in self._goals.items():
            if goal.is_completed and goal.completed_at and goal.completed_at < cutoff:
                to_remove.append(goal_id)
        
        for goal_id in to_remove:
            del self._goals[goal_id]
            self._completed_goals = [gid for gid in self._completed_goals if gid != goal_id]
            removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} completed goals")
        
        return removed
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_goal_completed(self, callback: Callable[[Goal], None]) -> None:
        """Enregistre un callback pour la complétion."""
        self._on_goal_completed.append(callback)
    
    def on_goal_blocked(self, callback: Callable[[Goal], None]) -> None:
        """Enregistre un callback pour le blocage."""
        self._on_goal_blocked.append(callback)
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "total_goals": len(self._goals),
            "active_goals": len(self._active_goals),
            "completed_goals": len(self._completed_goals),
            "failed_goals": len(self._failed_goals),
            "status_summary": self.get_status_summary(),
            "goals": [g.to_dict() for g in self._goals.values()],
        }


# ==========================================
# FACTORY
# ==========================================

def create_goal_manager(config: Optional[GoalManagerConfig] = None) -> GoalManager:
    """Factory pour créer un GoalManager."""
    return GoalManager(config=config)
