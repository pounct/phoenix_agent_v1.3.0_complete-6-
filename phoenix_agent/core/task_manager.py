"""
Phoenix Agent - Task Manager
============================

Gestionnaire de tâches pour l'orchestration multi-tâches.

Responsabilités:
    - Analyser la complexité des tâches
    - Décomposer les tâches complexes
    - Orchestre l'exécution
    - Gérer les dépendances
    - Préparer la délégation

Architecture:
    UserInput → Task → TaskManager.analyze() → Execution Plan

Version: 0.4.0
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .task import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskComplexity,
    TaskType,
    TaskResult,
    TaskPlan,
)


logger = logging.getLogger("phoenix.task_manager")


# ==========================================
# COMPLEXITY ANALYZER
# ==========================================

@dataclass
class ComplexityAnalyzer:
    """
    Analyseur de complexité des tâches.
    
    Utilise des heuristiques pour estimer la complexité.
    v1+: Utilisera un LLM pour l'analyse.
    """
    
    # Seuils de complexité
    simple_max_words: int = 20
    moderate_max_words: int = 100
    
    # Mots-clés indiquant la complexité
    complex_keywords: List[str] = field(default_factory=lambda: [
        "analyze", "compare", "evaluate", "design", "create",
        "implement", "optimize", "refactor", "debug",
        "explain", "describe", "summarize", "synthesize"
    ])
    
    expert_keywords: List[str] = field(default_factory=lambda: [
        "architecture", "system design", "multi-step",
        "coordinate", "orchestrate", "delegate"
    ])
    
    def analyze(self, goal: str) -> TaskComplexity:
        """
        Analyse la complexité d'un goal.
        
        Args:
            goal: Le goal de la tâche
            
        Returns:
            TaskComplexity estimée
        """
        goal_lower = goal.lower()
        word_count = len(goal.split())
        
        # Check expert keywords
        for keyword in self.expert_keywords:
            if keyword in goal_lower:
                return TaskComplexity.EXPERT
        
        # Check complex keywords
        for keyword in self.complex_keywords:
            if keyword in goal_lower:
                return TaskComplexity.COMPLEX
        
        # Check word count
        if word_count <= self.simple_max_words:
            return TaskComplexity.SIMPLE
        elif word_count <= self.moderate_max_words:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.COMPLEX


# ==========================================
# TASK TYPE CLASSIFIER
# ==========================================

@dataclass
class TaskTypeClassifier:
    """
    Classificateur de type de tâche.
    
    v0.4: Heuristiques simples
    v1+: LLM-based classification
    """
    
    type_keywords: Dict[TaskType, List[str]] = field(default_factory=lambda: {
        TaskType.QUERY: ["what", "who", "when", "where", "is", "are", "do", "does"],
        TaskType.REASONING: ["why", "how", "explain", "analyze", "compare", "evaluate"],
        TaskType.RESEARCH: ["find", "search", "lookup", "research", "investigate"],
        TaskType.CODE: ["code", "implement", "write", "function", "class", "debug", "fix"],
        TaskType.ANALYSIS: ["analyze", "evaluate", "assess", "review", "examine"],
        TaskType.DELEGATION: ["delegate", "assign", "subtask"],
    })
    
    def classify(self, goal: str) -> TaskType:
        """Classifie le type de tâche."""
        goal_lower = goal.lower()
        
        for task_type, keywords in self.type_keywords.items():
            for keyword in keywords:
                if goal_lower.startswith(keyword) or f" {keyword} " in f" {goal_lower} ":
                    return task_type
        
        return TaskType.QUERY


# ==========================================
# TASK DECOMPOSER
# ==========================================

class TaskDecomposer:
    """
    Décomposeur de tâches complexes.
    
    v0.4: Structure en place, décomposition simple
    v1+: LLM-powered decomposition
    """
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
    
    def can_decompose(self, task: Task) -> bool:
        """Vérifie si une tâche peut être décomposée."""
        return (
            task.complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]
            and task.depth < self.max_depth
            and not task.has_children
        )
    
    async def decompose(
        self,
        task: Task,
        context: Optional[str] = None
    ) -> TaskPlan:
        """
        Décompose une tâche en sous-tâches.
        
        v0.4: Décomposition heuristique simple
        v1+: LLM-powered intelligent decomposition
        
        Args:
            task: La tâche à décomposer
            context: Contexte additionnel
            
        Returns:
            TaskPlan avec sous-tâches
        """
        plan = TaskPlan(
            root_task_id=task.task_id,
            reasoning=f"Decomposing task: {task.goal[:100]}..."
        )
        
        # v0.4: Décomposition simple basée sur le type
        if task.task_type == TaskType.CODE:
            subtasks = self._decompose_code_task(task)
        elif task.task_type == TaskType.ANALYSIS:
            subtasks = self._decompose_analysis_task(task)
        elif task.task_type == TaskType.RESEARCH:
            subtasks = self._decompose_research_task(task)
        else:
            subtasks = self._decompose_generic_task(task)
        
        plan.subtasks = subtasks
        plan.execution_order = [t.task_id for t in subtasks]
        
        # Simple: tout peut être parallèle
        plan.parallel_groups = [[t.task_id for t in subtasks]]
        
        return plan
    
    def _decompose_code_task(self, task: Task) -> List[Task]:
        """Décompose une tâche de code."""
        return [
            task.create_subtask(
                goal=f"Analyze requirements for: {task.goal}",
                task_type=TaskType.ANALYSIS,
                complexity=TaskComplexity.MODERATE,
            ),
            task.create_subtask(
                goal=f"Design solution for: {task.goal}",
                task_type=TaskType.REASONING,
                complexity=TaskComplexity.COMPLEX,
            ),
            task.create_subtask(
                goal=f"Implement: {task.goal}",
                task_type=TaskType.CODE,
                complexity=TaskComplexity.MODERATE,
            ),
        ]
    
    def _decompose_analysis_task(self, task: Task) -> List[Task]:
        """Décompose une tâche d'analyse."""
        return [
            task.create_subtask(
                goal=f"Gather information for: {task.goal}",
                task_type=TaskType.RESEARCH,
                complexity=TaskComplexity.MODERATE,
            ),
            task.create_subtask(
                goal=f"Analyze findings for: {task.goal}",
                task_type=TaskType.ANALYSIS,
                complexity=TaskComplexity.COMPLEX,
            ),
            task.create_subtask(
                goal=f"Synthesize conclusions for: {task.goal}",
                task_type=TaskType.REASONING,
                complexity=TaskComplexity.MODERATE,
            ),
        ]
    
    def _decompose_research_task(self, task: Task) -> List[Task]:
        """Décompose une tâche de recherche."""
        return [
            task.create_subtask(
                goal=f"Search for information: {task.goal}",
                task_type=TaskType.RESEARCH,
                complexity=TaskComplexity.MODERATE,
            ),
            task.create_subtask(
                goal=f"Summarize findings: {task.goal}",
                task_type=TaskType.QUERY,
                complexity=TaskComplexity.SIMPLE,
            ),
        ]
    
    def _decompose_generic_task(self, task: Task) -> List[Task]:
        """Décomposition générique."""
        return [
            task.create_subtask(
                goal=f"Analyze: {task.goal}",
                task_type=TaskType.ANALYSIS,
                complexity=TaskComplexity.MODERATE,
            ),
            task.create_subtask(
                goal=f"Execute: {task.goal}",
                task_type=TaskType.QUERY,
                complexity=TaskComplexity.MODERATE,
            ),
        ]


# ==========================================
# TASK MANAGER
# ==========================================

class TaskManager:
    """
    Gestionnaire de tâches Phoenix.
    
    Responsabilités:
        - Analyser les tâches entrantes
        - Classifier la complexité
        - Décider de la stratégie d'exécution
        - Orchestre la décomposition si nécessaire
        - Préparer la délégation
    
    Example:
        manager = TaskManager()
        
        task = Task.from_user_input("Explain quantum computing")
        analysis = manager.analyze(task)
        
        if analysis.should_delegate:
            # Déléguer à un sub-agent
            ...
        elif analysis.should_decompose:
            # Décomposer en sous-tâches
            plan = await manager.decompose(task)
        else:
            # Exécuter directement
            result = await manager.execute(task)
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        complexity_threshold: TaskComplexity = TaskComplexity.COMPLEX,
    ):
        self.max_depth = max_depth
        self.complexity_threshold = complexity_threshold
        
        # Components
        self.complexity_analyzer = ComplexityAnalyzer()
        self.type_classifier = TaskTypeClassifier()
        self.decomposer = TaskDecomposer(max_depth=max_depth)
        
        # Task registry
        self._tasks: Dict[str, Task] = {}
        self._results: Dict[str, TaskResult] = {}
    
    # ==========================================
    # ANALYSIS
    # ==========================================
    
    def analyze(self, task: Task) -> "TaskAnalysis":
        """
        Analyse une tâche pour déterminer la stratégie.
        
        Args:
            task: La tâche à analyser
            
        Returns:
            TaskAnalysis avec recommandations
        """
        # Analyser la complexité si pas déjà fait
        if task.complexity == TaskComplexity.SIMPLE and task.is_root:
            task.complexity = self.complexity_analyzer.analyze(task.goal)
        
        # Classifier le type si pas déjà fait
        if task.task_type == TaskType.QUERY and task.is_root:
            task.task_type = self.type_classifier.classify(task.goal)
        
        # Enregistrer la tâche
        self._tasks[task.task_id] = task
        
        # Déterminer la stratégie
        should_decompose = (
            task.complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]
            and task.depth < self.max_depth
        )
        
        should_delegate = (
            task.complexity == TaskComplexity.EXPERT
            and task.depth > 0  # Pas déléguer la racine directement
        )
        
        return TaskAnalysis(
            task_id=task.task_id,
            complexity=task.complexity,
            task_type=task.task_type,
            should_decompose=should_decompose,
            should_delegate=should_delegate,
            recommended_strategy="decompose" if should_decompose else ("delegate" if should_delegate else "execute"),
        )
    
    # ==========================================
    # DECOMPOSITION
    # ==========================================
    
    async def decompose(self, task: Task) -> TaskPlan:
        """
        Décompose une tâche complexe.
        
        Args:
            task: La tâche à décomposer
            
        Returns:
            TaskPlan avec sous-tâches
        """
        logger.info(f"Decomposing task {task.task_id}: {task.goal[:50]}...")
        
        plan = await self.decomposer.decompose(task)
        
        # Enregistrer les sous-tâches
        for subtask in plan.subtasks:
            self._tasks[subtask.task_id] = subtask
        
        logger.info(f"Created {len(plan.subtasks)} subtasks")
        
        return plan
    
    # ==========================================
    # EXECUTION ORCHESTRATION
    # ==========================================
    
    async def execute_task(
        self,
        task: Task,
        executor: Callable[[Task], Any],
    ) -> TaskResult:
        """
        Exécute une tâche avec l'exécuteur fourni.
        
        Args:
            task: La tâche à exécuter
            executor: Fonction d'exécution async
            
        Returns:
            TaskResult
        """
        task.start()
        
        try:
            result = await executor(task)
            
            if isinstance(result, str):
                task.complete(result)
            elif isinstance(result, TaskResult):
                task.complete(result.result or "")
            
            return TaskResult.from_task(task)
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.fail(str(e))
            return TaskResult.from_task(task)
    
    async def execute_plan(
        self,
        plan: TaskPlan,
        executor: Callable[[Task], Any],
    ) -> TaskResult:
        """
        Exécute un plan de tâches.
        
        v0.4: Exécution séquentielle
        v1+: Exécution parallèle par groupes
        
        Args:
            plan: Le plan à exécuter
            executor: Fonction d'exécution
            
        Returns:
            TaskResult agrégé
        """
        results = []
        
        # v0.4: Exécution séquentielle
        for task in plan.get_execution_order():
            result = await self.execute_task(task, executor)
            results.append(result)
        
        # Agréger les résultats
        root_task = self._tasks.get(plan.root_task_id)
        
        return TaskResult(
            task_id=plan.root_task_id,
            status=TaskStatus.COMPLETED,
            result="\n\n".join(r.result or "" for r in results if r.result),
            subtask_results=results,
        )
    
    # ==========================================
    # TASK REGISTRY
    # ==========================================
    
    def register(self, task: Task) -> None:
        """Enregistre une tâche."""
        self._tasks[task.task_id] = task
    
    def get(self, task_id: str) -> Optional[Task]:
        """Récupère une tâche par ID."""
        return self._tasks.get(task_id)
    
    def get_children(self, task_id: str) -> List[Task]:
        """Récupère les sous-tâches d'une tâche."""
        task = self.get(task_id)
        if not task:
            return []
        return [self._tasks[cid] for cid in task.child_task_ids if cid in self._tasks]
    
    def list_all(self) -> List[Task]:
        """Liste toutes les tâches."""
        return list(self._tasks.values())
    
    def list_by_status(self, status: TaskStatus) -> List[Task]:
        """Liste les tâches par statut."""
        return [t for t in self._tasks.values() if t.status == status]
    
    def clear_completed(self) -> int:
        """Supprime les tâches terminées."""
        to_remove = [
            tid for tid, t in self._tasks.items()
            if t.is_terminal
        ]
        for tid in to_remove:
            del self._tasks[tid]
        return len(to_remove)


# ==========================================
# TASK ANALYSIS RESULT
# ==========================================

@dataclass
class TaskAnalysis:
    """Résultat de l'analyse d'une tâche."""
    task_id: str
    complexity: TaskComplexity
    task_type: TaskType
    should_decompose: bool
    should_delegate: bool
    recommended_strategy: str  # "execute", "decompose", "delegate"
    
    # Pour délégation future
    required_agent_role: Optional[str] = None
    estimated_tokens: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "complexity": self.complexity.value,
            "task_type": self.task_type.value,
            "should_decompose": self.should_decompose,
            "should_delegate": self.should_delegate,
            "recommended_strategy": self.recommended_strategy,
        }
