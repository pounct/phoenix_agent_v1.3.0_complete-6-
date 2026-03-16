"""
Phoenix Agent - Task Abstraction
================================

Abstraction Task pour la décomposition et délégation.

Une Task représente une unité de travail qui peut être:
    - Exécutée par l'agent principal
    - Déléguée à un sub-agent
    - Décomposée en sous-tâches

Cette abstraction est LA FONDATION du multi-agent.

Architecture:
    UserRequest → Task(s) → AgentLoop | Delegation → Result

Version: 0.4.0 (Task Abstraction)
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


# ==========================================
# TASK STATUS
# ==========================================

class TaskStatus(str, Enum):
    """Statut d'une tâche."""
    PENDING = "pending"           # En attente
    QUEUED = "queued"             # Dans la file
    RUNNING = "running"           # En cours
    DELEGATED = "delegated"       # Déléguée à un sub-agent
    COMPLETED = "completed"       # Terminée
    FAILED = "failed"             # Échouée
    CANCELLED = "cancelled"       # Annulée


# ==========================================
# TASK PRIORITY
# ==========================================

class TaskPriority(int, Enum):
    """Priorité d'une tâche."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


# ==========================================
# TASK COMPLEXITY
# ==========================================

class TaskComplexity(str, Enum):
    """Complexité estimée d'une tâche."""
    SIMPLE = "simple"           # Réponse directe
    MODERATE = "moderate"       # Nécessite raisonnement
    COMPLEX = "complex"         # Nécessite décomposition
    EXPERT = "expert"           # Nécessite sub-agent spécialisé


# ==========================================
# TASK TYPE
# ==========================================

class TaskType(str, Enum):
    """Type de tâche."""
    QUERY = "query"                   # Question simple
    REASONING = "reasoning"           # Raisonnement
    RESEARCH = "research"             # Recherche
    CODE = "code"                     # Génération code
    ANALYSIS = "analysis"             # Analyse
    DELEGATION = "delegation"         # Délégation à sub-agent
    COMPOSITION = "composition"       # Composition de résultats
    TOOL_EXECUTION = "tool_execution" # Exécution d'outil


# ==========================================
# TASK
# ==========================================

class Task(BaseModel):
    """
    Task - Unité de travail Phoenix.
    
    Une Task représente une unité de travail qui peut être:
        - Exécutée directement par l'agent
        - Déléguée à un sub-agent
        - Décomposée en sous-tâches
    
    Architecture:
        UserRequest
            ↓
        Task (root)
            ↓
        TaskManager.analyze()
            ↓
        ┌─────────────────────────────┐
        │ Simple? → AgentLoop.run()   │
        │ Complex? → Decompose        │
        │ Expert? → Delegate          │
        └─────────────────────────────┘
    
    Example:
        task = Task.create(
            goal="Explain quantum computing",
            task_type=TaskType.QUERY,
            complexity=TaskComplexity.MODERATE
        )
    """
    
    # ==========================================
    # IDENTITY
    # ==========================================
    
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier"
    )
    
    goal: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="What the task should accomplish"
    )
    
    # ==========================================
    # CLASSIFICATION
    # ==========================================
    
    task_type: TaskType = Field(
        default=TaskType.QUERY,
        description="Type of task"
    )
    
    complexity: TaskComplexity = Field(
        default=TaskComplexity.SIMPLE,
        description="Estimated complexity"
    )
    
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Task priority"
    )
    
    # ==========================================
    # STATE
    # ==========================================
    
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current status"
    )
    
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Completion progress (0.0 to 1.0)"
    )
    
    # ==========================================
    # CONTEXT
    # ==========================================
    
    context: str = Field(
        default="",
        description="Additional context for the task"
    )
    
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for the task"
    )
    
    constraints: List[str] = Field(
        default_factory=list,
        description="Constraints to respect"
    )
    
    # ==========================================
    # HIERARCHY (for decomposition)
    # ==========================================
    
    parent_task_id: Optional[str] = Field(
        default=None,
        description="Parent task ID (if this is a subtask)"
    )
    
    child_task_ids: List[str] = Field(
        default_factory=list,
        description="Child task IDs (if decomposed)"
    )
    
    depth: int = Field(
        default=0,
        ge=0,
        description="Depth in task tree (0 = root)"
    )
    
    # ==========================================
    # ASSIGNMENT
    # ==========================================
    
    assigned_agent: Optional[str] = Field(
        default=None,
        description="Agent assigned to this task"
    )
    
    agent_role: Optional[str] = Field(
        default=None,
        description="Required agent role (for delegation)"
    )
    
    # ==========================================
    # RESULT
    # ==========================================
    
    result: Optional[str] = Field(
        default=None,
        description="Task result (when completed)"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)"
    )
    
    # ==========================================
    # METADATA
    # ==========================================
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="Start timestamp"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Completion timestamp"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # ==========================================
    # FACTORY METHODS
    # ==========================================
    
    @classmethod
    def create(
        cls,
        goal: str,
        task_type: TaskType = TaskType.QUERY,
        complexity: TaskComplexity = TaskComplexity.SIMPLE,
        priority: TaskPriority = TaskPriority.NORMAL,
        context: str = "",
        parent_task_id: Optional[str] = None,
        depth: int = 0,
    ) -> "Task":
        """Factory method to create a task."""
        return cls(
            goal=goal,
            task_type=task_type,
            complexity=complexity,
            priority=priority,
            context=context,
            parent_task_id=parent_task_id,
            depth=depth,
        )
    
    @classmethod
    def from_user_input(
        cls,
        user_input: str,
        context: str = ""
    ) -> "Task":
        """Create a root task from user input."""
        return cls(
            goal=user_input,
            task_type=TaskType.QUERY,
            complexity=TaskComplexity.SIMPLE,  # Will be analyzed
            context=context,
            depth=0,
        )
    
    # ==========================================
    # SUBTASK CREATION
    # ==========================================
    
    def create_subtask(
        self,
        goal: str,
        task_type: TaskType = TaskType.QUERY,
        complexity: TaskComplexity = TaskComplexity.SIMPLE,
    ) -> "Task":
        """Create a subtask of this task."""
        subtask = Task(
            goal=goal,
            task_type=task_type,
            complexity=complexity,
            parent_task_id=self.task_id,
            depth=self.depth + 1,
            context=self.context,
        )
        self.child_task_ids.append(subtask.task_id)
        return subtask
    
    # ==========================================
    # STATE TRANSITIONS
    # ==========================================
    
    def start(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def delegate(self, agent_role: str) -> None:
        """Mark task as delegated."""
        self.status = TaskStatus.DELEGATED
        self.agent_role = agent_role
        self.metadata["delegated_at"] = datetime.utcnow().isoformat()
    
    def complete(self, result: str) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
    
    def cancel(self) -> None:
        """Cancel the task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    # ==========================================
    # PROGRESS
    # ==========================================
    
    def update_progress(self, progress: float) -> None:
        """Update task progress."""
        self.progress = max(0.0, min(1.0, progress))
    
    def calculate_progress_from_children(
        self,
        child_tasks: List["Task"]
    ) -> float:
        """Calculate progress from child tasks."""
        if not child_tasks:
            return self.progress
        
        completed = sum(1 for t in child_tasks if t.status == TaskStatus.COMPLETED)
        self.progress = completed / len(child_tasks)
        return self.progress
    
    # ==========================================
    # QUERIES
    # ==========================================
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root task."""
        return self.parent_task_id is None
    
    @property
    def is_subtask(self) -> bool:
        """Check if this is a subtask."""
        return self.parent_task_id is not None
    
    @property
    def has_children(self) -> bool:
        """Check if task has children."""
        return len(self.child_task_ids) > 0
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        ]
    
    @property
    def is_active(self) -> bool:
        """Check if task is active."""
        return self.status in [
            TaskStatus.PENDING,
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.DELEGATED
        ]
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate task duration in milliseconds."""
        if self.started_at is None:
            return None
        
        end = self.completed_at or datetime.utcnow()
        delta = end - self.started_at
        return delta.total_seconds() * 1000
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_prompt_context(self) -> str:
        """Convert task to context string for prompts."""
        parts = [
            f"Task: {self.goal}",
            f"Type: {self.task_type.value}",
            f"Status: {self.status.value}",
        ]
        
        if self.context:
            parts.append(f"Context: {self.context}")
        
        if self.constraints:
            parts.append(f"Constraints: {', '.join(self.constraints)}")
        
        return "\n".join(parts)


# ==========================================
# TASK RESULT
# ==========================================

class TaskResult(BaseModel):
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    
    # For decomposed tasks
    subtask_results: List["TaskResult"] = Field(default_factory=list)
    
    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED
    
    @classmethod
    def from_task(cls, task: Task) -> "TaskResult":
        return cls(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            duration_ms=task.duration_ms,
        )


# ==========================================
# TASK PLAN (for decomposition)
# ==========================================

class TaskPlan(BaseModel):
    """
    Plan for task decomposition.
    
    Generated by the agent when analyzing a complex task.
    """
    root_task_id: str
    subtasks: List[Task] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)
    parallel_groups: List[List[str]] = Field(default_factory=list)
    
    reasoning: str = ""
    
    @property
    def total_subtasks(self) -> int:
        return len(self.subtasks)
    
    def get_execution_order(self) -> List[Task]:
        """Get tasks in execution order."""
        task_map = {t.task_id: t for t in self.subtasks}
        return [task_map[tid] for tid in self.execution_order if tid in task_map]
