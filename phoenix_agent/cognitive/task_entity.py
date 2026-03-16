"""
Phoenix Agent - Task Entity System
===================================

Task Identity, Lifecycle, and Tracking.

THE KEY DISTINCTION:
    Request = External input (what comes in)
    Task = Internal work unit (what Phoenix manages)

This separation is CRITICAL for true agent autonomy:

    ┌─────────────┐
    │   Request   │  ← External, untrusted, variable format
    │ (External)  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ RequestParser│  ← Parse and validate
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ TaskBuilder  │  ← Create Task entities
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  TaskGraph  │  ← Internal task graph
    │  (Internal) │
    └─────────────┘

Task Entity features:
    - Unique identity (task_id, correlation_id, trace_id)
    - Full lifecycle (PENDING → RUNNING → COMPLETED)
    - Cost tracking (tokens, time, delegations)
    - History (state transitions, events)
    - Dependencies (soft and hard)

Version: 1.3.0
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
import logging


logger = logging.getLogger("phoenix.cognitive.task_entity")


# ============================================================================
# TASK LIFECYCLE
# ============================================================================


class TaskLifecycleState(str, Enum):
    """
    Complete task lifecycle states.
    
    This is more detailed than simple PENDING/RUNNING/COMPLETED.
    Real agent runtimes need to track:
        - Why a task is waiting
        - How many times it was retried
        - Whether it was delegated or recovered
    """
    # Initial
    CREATED = "created"              # Just created, not yet validated
    VALIDATED = "validated"          # Validated and ready to queue
    
    # Queue
    QUEUED = "queued"                # In execution queue
    PENDING = "pending"              # Waiting for dependencies
    
    # Active
    ANALYZING = "analyzing"          # Being analyzed for complexity
    PLANNING = "planning"            # Being planned
    EXECUTING = "executing"          # Currently executing
    DELEGATING = "delegating"        # Being delegated to another agent
    
    # Waiting
    WAITING_INPUT = "waiting_input"    # Waiting for external input
    WAITING_RESOURCE = "waiting_resource"  # Waiting for resources
    WAITING_AGENT = "waiting_agent"    # Waiting for agent availability
    WAITING_RESULTS = "waiting_results"  # Waiting for delegation results
    
    # Recovery
    RETRYING = "retrying"            # Retrying after failure
    RECOVERING = "recovering"        # In recovery mode
    
    # Terminal
    COMPLETED = "completed"          # Successfully completed
    FAILED = "failed"                # Failed
    CANCELLED = "cancelled"          # Cancelled
    TIMEOUT = "timeout"              # Timed out
    SKIPPED = "skipped"              # Skipped (dependency failed)


class TaskLifecycleCategory(str, Enum):
    """Categories of task states."""
    INITIAL = "initial"
    QUEUED = "queued"
    ACTIVE = "active"
    WAITING = "waiting"
    RECOVERY = "recovery"
    TERMINAL = "terminal"


# State to category mapping
STATE_CATEGORIES: Dict[TaskLifecycleState, TaskLifecycleCategory] = {
    TaskLifecycleState.CREATED: TaskLifecycleCategory.INITIAL,
    TaskLifecycleState.VALIDATED: TaskLifecycleCategory.INITIAL,
    TaskLifecycleState.QUEUED: TaskLifecycleCategory.QUEUED,
    TaskLifecycleState.PENDING: TaskLifecycleCategory.QUEUED,
    TaskLifecycleState.ANALYZING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.PLANNING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.EXECUTING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.DELEGATING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.WAITING_INPUT: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.WAITING_RESOURCE: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.WAITING_AGENT: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.WAITING_RESULTS: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.RETRYING: TaskLifecycleCategory.RECOVERY,
    TaskLifecycleState.RECOVERING: TaskLifecycleCategory.RECOVERY,
    TaskLifecycleState.COMPLETED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.FAILED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.CANCELLED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.TIMEOUT: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.SKIPPED: TaskLifecycleCategory.TERMINAL,
}

# Valid state transitions
VALID_TRANSITIONS: Dict[TaskLifecycleState, Set[TaskLifecycleState]] = {
    TaskLifecycleState.CREATED: {
        TaskLifecycleState.VALIDATED, TaskLifecycleState.CANCELLED
    },
    TaskLifecycleState.VALIDATED: {
        TaskLifecycleState.QUEUED, TaskLifecycleState.CANCELLED
    },
    TaskLifecycleState.QUEUED: {
        TaskLifecycleState.PENDING, TaskLifecycleState.ANALYZING,
        TaskLifecycleState.CANCELLED
    },
    TaskLifecycleState.PENDING: {
        TaskLifecycleState.ANALYZING, TaskLifecycleState.EXECUTING,
        TaskLifecycleState.WAITING_RESOURCE, TaskLifecycleState.CANCELLED
    },
    TaskLifecycleState.ANALYZING: {
        TaskLifecycleState.PLANNING, TaskLifecycleState.EXECUTING,
        TaskLifecycleState.DELEGATING, TaskLifecycleState.FAILED
    },
    TaskLifecycleState.PLANNING: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.DELEGATING,
        TaskLifecycleState.WAITING_RESOURCE, TaskLifecycleState.FAILED
    },
    TaskLifecycleState.EXECUTING: {
        TaskLifecycleState.COMPLETED, TaskLifecycleState.FAILED,
        TaskLifecycleState.DELEGATING, TaskLifecycleState.WAITING_INPUT,
        TaskLifecycleState.WAITING_RESULTS, TaskLifecycleState.TIMEOUT,
        TaskLifecycleState.RETRYING
    },
    TaskLifecycleState.DELEGATING: {
        TaskLifecycleState.WAITING_RESULTS, TaskLifecycleState.FAILED
    },
    TaskLifecycleState.WAITING_INPUT: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.CANCELLED,
        TaskLifecycleState.TIMEOUT
    },
    TaskLifecycleState.WAITING_RESOURCE: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.CANCELLED,
        TaskLifecycleState.TIMEOUT
    },
    TaskLifecycleState.WAITING_AGENT: {
        TaskLifecycleState.DELEGATING, TaskLifecycleState.EXECUTING,
        TaskLifecycleState.CANCELLED, TaskLifecycleState.TIMEOUT
    },
    TaskLifecycleState.WAITING_RESULTS: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.FAILED,
        TaskLifecycleState.TIMEOUT
    },
    TaskLifecycleState.RETRYING: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.RECOVERING,
        TaskLifecycleState.FAILED
    },
    TaskLifecycleState.RECOVERING: {
        TaskLifecycleState.EXECUTING, TaskLifecycleState.FAILED,
        TaskLifecycleState.SKIPPED
    },
    TaskLifecycleState.COMPLETED: set(),  # Terminal
    TaskLifecycleState.FAILED: {
        TaskLifecycleState.RETRYING, TaskLifecycleState.RECOVERING
    },
    TaskLifecycleState.CANCELLED: set(),  # Terminal
    TaskLifecycleState.TIMEOUT: {
        TaskLifecycleState.RETRYING, TaskLifecycleState.FAILED
    },
    TaskLifecycleState.SKIPPED: set(),  # Terminal
}


# ============================================================================
# TASK IDENTITY
# ============================================================================


@dataclass
class TaskIdentity:
    """
    Unique identity for a task.
    
    This provides complete traceability:
        - task_id: Unique identifier for this task
        - correlation_id: Links related tasks (from same request)
        - trace_id: Distributed tracing across agents
        - parent_task_id: For task decomposition
        - root_task_id: The original request task
        - session_id: User session
        - agent_id: Agent handling this task
    """
    task_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    # Naming
    name: str = ""
    namespace: str = "default"
    
    def __post_init__(self):
        # If root_task_id not set and no parent, this IS the root
        if self.root_task_id is None and self.parent_task_id is None:
            self.root_task_id = self.task_id
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root task."""
        return self.parent_task_id is None
    
    @property
    def is_subtask(self) -> bool:
        """Check if this is a subtask."""
        return self.parent_task_id is not None
    
    @property
    def qualified_name(self) -> str:
        """Get fully qualified name."""
        if self.namespace != "default":
            return f"{self.namespace}:{self.name}"
        return self.name
    
    def create_child_identity(self, name: str = "") -> "TaskIdentity":
        """Create identity for a child task."""
        return TaskIdentity(
            task_id=str(uuid4()),
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            parent_task_id=self.task_id,
            root_task_id=self.root_task_id,
            session_id=self.session_id,
            name=name,
            namespace=self.namespace,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "parent_task_id": self.parent_task_id,
            "root_task_id": self.root_task_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "namespace": self.namespace,
            "is_root": self.is_root,
        }


# ============================================================================
# TASK COST
# ============================================================================


@dataclass
class TaskCost:
    """
    Cost tracking for a task.
    
    Real agent runtimes MUST track costs:
        - Token usage (input, output, total)
        - Time (wall clock, CPU)
        - Delegations (how many sub-agents involved)
        - External API calls
        - Money (if applicable)
    """
    # Tokens
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Time
    wall_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    queue_time_ms: float = 0.0
    
    # Counts
    delegation_count: int = 0
    retry_count: int = 0
    api_calls: int = 0
    tool_calls: int = 0
    
    # Money (optional)
    estimated_cost_usd: float = 0.0
    
    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add token usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
    
    def add_delegation(self) -> None:
        """Add a delegation."""
        self.delegation_count += 1
    
    def add_retry(self) -> None:
        """Add a retry."""
        self.retry_count += 1
    
    def add_api_call(self) -> None:
        """Add an API call."""
        self.api_calls += 1
    
    def add_tool_call(self) -> None:
        """Add a tool call."""
        self.tool_calls += 1
    
    def set_wall_time(self, start_time: float) -> None:
        """Set wall time from start."""
        self.wall_time_ms = (time.time() - start_time) * 1000
    
    def merge(self, other: "TaskCost") -> None:
        """Merge another cost into this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens
        self.wall_time_ms += other.wall_time_ms
        self.cpu_time_ms += other.cpu_time_ms
        self.delegation_count += other.delegation_count
        self.retry_count += other.retry_count
        self.api_calls += other.api_calls
        self.tool_calls += other.tool_calls
        self.estimated_cost_usd += other.estimated_cost_usd
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "wall_time_ms": self.wall_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "queue_time_ms": self.queue_time_ms,
            "delegation_count": self.delegation_count,
            "retry_count": self.retry_count,
            "api_calls": self.api_calls,
            "tool_calls": self.tool_calls,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


# ============================================================================
# TASK HISTORY
# ============================================================================


@dataclass
class HistoryEvent:
    """A single event in task history."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""
    from_state: Optional[TaskLifecycleState] = None
    to_state: Optional[TaskLifecycleState] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value if self.to_state else None,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class TaskHistory:
    """
    Complete history of a task.
    
    This enables:
        - Debugging (what happened?)
        - Auditing (who did what when?)
        - Learning (what patterns lead to success/failure?)
    """
    events: List[HistoryEvent] = field(default_factory=list)
    
    def record_state_change(
        self,
        from_state: TaskLifecycleState,
        to_state: TaskLifecycleState,
        message: str = "",
        metadata: Dict[str, Any] = None
    ) -> None:
        """Record a state transition."""
        self.events.append(HistoryEvent(
            event_type="state_change",
            from_state=from_state,
            to_state=to_state,
            message=message,
            metadata=metadata or {},
        ))
    
    def record_event(
        self,
        event_type: str,
        message: str = "",
        metadata: Dict[str, Any] = None
    ) -> None:
        """Record a generic event."""
        self.events.append(HistoryEvent(
            event_type=event_type,
            message=message,
            metadata=metadata or {},
        ))
    
    def get_state_transitions(self) -> List[HistoryEvent]:
        """Get all state transitions."""
        return [e for e in self.events if e.event_type == "state_change"]
    
    def get_events_by_type(self, event_type: str) -> List[HistoryEvent]:
        """Get events by type."""
        return [e for e in self.events if e.event_type == event_type]
    
    @property
    def duration_ms(self) -> float:
        """Calculate total duration from history."""
        if len(self.events) < 2:
            return 0.0
        
        first = self.events[0].timestamp
        last = self.events[-1].timestamp
        delta = last - first
        return delta.total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "events": [e.to_dict() for e in self.events],
            "event_count": len(self.events),
            "duration_ms": self.duration_ms,
        }


# ============================================================================
# TASK DEPENDENCY
# ============================================================================


class TaskDependencyType(str, Enum):
    """Types of task dependencies."""
    HARD = "hard"      # Must complete before this task can start
    SOFT = "soft"      # Should complete, but task can proceed
    TRIGGER = "trigger"  # Triggers this task when complete


@dataclass
class TaskDependency:
    """A dependency on another task."""
    task_id: str
    dependency_type: TaskDependencyType = TaskDependencyType.HARD
    condition: Optional[str] = None  # Optional condition for soft deps
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "dependency_type": self.dependency_type.value,
            "condition": self.condition,
        }


# ============================================================================
# TASK LIFECYCLE MANAGER
# ============================================================================


class TaskLifecycle:
    """
    Manages task lifecycle state transitions.
    
    Enforces valid state transitions and records history.
    """
    
    def __init__(
        self,
        initial_state: TaskLifecycleState = TaskLifecycleState.CREATED
    ):
        self._state = initial_state
        self._history = TaskHistory()
        self._history.record_event(
            "created",
            f"Task created in state {initial_state.value}"
        )
    
    @property
    def state(self) -> TaskLifecycleState:
        """Current state."""
        return self._state
    
    @property
    def category(self) -> TaskLifecycleCategory:
        """Current state category."""
        return STATE_CATEGORIES.get(self._state, TaskLifecycleCategory.INITIAL)
    
    @property
    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self.category == TaskLifecycleCategory.TERMINAL
    
    @property
    def is_active(self) -> bool:
        """Check if in active state."""
        return self.category == TaskLifecycleCategory.ACTIVE
    
    @property
    def is_waiting(self) -> bool:
        """Check if in waiting state."""
        return self.category == TaskLifecycleCategory.WAITING
    
    def can_transition_to(self, new_state: TaskLifecycleState) -> bool:
        """Check if transition is valid."""
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_targets
    
    def transition(
        self,
        new_state: TaskLifecycleState,
        message: str = "",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Attempt to transition to a new state.
        
        Returns:
            True if transition succeeded, False if invalid
        """
        if not self.can_transition_to(new_state):
            logger.warning(
                f"Invalid transition: {self._state.value} -> {new_state.value}"
            )
            return False
        
        old_state = self._state
        self._state = new_state
        
        self._history.record_state_change(
            from_state=old_state,
            to_state=new_state,
            message=message,
            metadata=metadata,
        )
        
        logger.debug(f"Task transition: {old_state.value} -> {new_state.value}")
        return True
    
    def force_state(
        self,
        new_state: TaskLifecycleState,
        reason: str = ""
    ) -> None:
        """Force a state transition (for recovery scenarios)."""
        old_state = self._state
        self._state = new_state
        
        self._history.record_state_change(
            from_state=old_state,
            to_state=new_state,
            message=f"Forced transition: {reason}",
            metadata={"forced": True, "reason": reason},
        )
    
    @property
    def history(self) -> TaskHistory:
        """Get the history."""
        return self._history
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "state": self._state.value,
            "category": self.category.value,
            "is_terminal": self.is_terminal,
            "history": self._history.to_dict(),
        }


# ============================================================================
# TASK ENTITY
# ============================================================================


@dataclass
class TaskEntity:
    """
    Complete Task Entity with Identity, Lifecycle, Cost, and History.
    
    This is the INTERNAL representation of work in Phoenix.
    
    Key differences from simple Request:
        - Request: External input (untrusted, variable)
        - TaskEntity: Internal work unit (controlled, tracked)
    
    Features:
        - Identity: Full traceability
        - Lifecycle: State machine with validation
        - Cost: Complete cost tracking
        - History: Audit trail
        - Dependencies: Hard and soft dependencies
    """
    # Identity
    identity: TaskIdentity = field(default_factory=TaskIdentity)
    
    # Content
    goal: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    
    # Lifecycle
    lifecycle: TaskLifecycle = field(default_factory=TaskLifecycle)
    
    # Cost
    cost: TaskCost = field(default_factory=TaskCost)
    
    # Dependencies
    dependencies: List[TaskDependency] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # Tasks that depend on this
    
    # Classification
    priority: int = 5  # 1-10, higher = more important
    complexity: str = "moderate"  # simple, moderate, complex, expert
    tags: List[str] = field(default_factory=list)
    
    # Assignment
    assigned_agent: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    
    # Result
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Retry config
    max_retries: int = 3
    timeout_seconds: float = 300.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal
    _start_time: float = field(default=0.0, repr=False)
    
    def __post_init__(self):
        if not self.identity.name:
            self.identity.name = self.goal[:50] if self.goal else "unnamed"
    
    # ========================================================================
    # IDENTITY HELPERS
    # ========================================================================
    
    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self.identity.task_id
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root task."""
        return self.identity.is_root
    
    @property
    def is_subtask(self) -> bool:
        """Check if this is a subtask."""
        return self.identity.is_subtask
    
    def create_subtask(
        self,
        goal: str,
        description: str = "",
        **kwargs
    ) -> "TaskEntity":
        """Create a subtask of this task."""
        child_identity = self.identity.create_child_identity(name=goal[:50])
        
        subtask = TaskEntity(
            identity=child_identity,
            goal=goal,
            description=description,
            priority=self.priority,
            **kwargs
        )
        
        # Add dependency on parent
        subtask.dependencies.append(TaskDependency(
            task_id=self.task_id,
            dependency_type=TaskDependencyType.HARD
        ))
        
        return subtask
    
    # ========================================================================
    # LIFECYCLE HELPERS
    # ========================================================================
    
    @property
    def state(self) -> TaskLifecycleState:
        """Get current state."""
        return self.lifecycle.state
    
    @property
    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self.lifecycle.is_terminal
    
    @property
    def is_active(self) -> bool:
        """Check if in active state."""
        return self.lifecycle.is_active
    
    def start(self) -> bool:
        """Start execution."""
        if self._start_time == 0:
            self._start_time = time.time()
            self.started_at = datetime.utcnow()
        
        return self.lifecycle.transition(
            TaskLifecycleState.EXECUTING,
            "Task execution started"
        )
    
    def complete(self, output: str) -> bool:
        """Mark as completed."""
        self.output = output
        self.completed_at = datetime.utcnow()
        
        if self._start_time > 0:
            self.cost.set_wall_time(self._start_time)
        
        return self.lifecycle.transition(
            TaskLifecycleState.COMPLETED,
            f"Task completed with output length {len(output)}"
        )
    
    def fail(self, error: str) -> bool:
        """Mark as failed."""
        self.error = error
        self.completed_at = datetime.utcnow()
        
        if self._start_time > 0:
            self.cost.set_wall_time(self._start_time)
        
        return self.lifecycle.transition(
            TaskLifecycleState.FAILED,
            f"Task failed: {error[:100]}"
        )
    
    def cancel(self, reason: str = "") -> bool:
        """Cancel the task."""
        self.completed_at = datetime.utcnow()
        
        return self.lifecycle.transition(
            TaskLifecycleState.CANCELLED,
            f"Task cancelled: {reason}"
        )
    
    def retry(self) -> bool:
        """Attempt to retry."""
        if self.cost.retry_count >= self.max_retries:
            return False
        
        self.cost.add_retry()
        return self.lifecycle.transition(
            TaskLifecycleState.RETRYING,
            f"Retry attempt {self.cost.retry_count}"
        )
    
    def delegate(self, agent_id: str) -> bool:
        """Delegate to another agent."""
        self.assigned_agent = agent_id
        self.cost.add_delegation()
        
        return self.lifecycle.transition(
            TaskLifecycleState.DELEGATING,
            f"Delegating to agent {agent_id}"
        )
    
    # ========================================================================
    # DEPENDENCY HELPERS
    # ========================================================================
    
    def add_dependency(
        self,
        task_id: str,
        dependency_type: TaskDependencyType = TaskDependencyType.HARD
    ) -> None:
        """Add a dependency."""
        self.dependencies.append(TaskDependency(
            task_id=task_id,
            dependency_type=dependency_type
        ))
    
    def check_dependencies_satisfied(
        self,
        completed_tasks: Set[str]
    ) -> bool:
        """Check if all hard dependencies are satisfied."""
        for dep in self.dependencies:
            if dep.dependency_type == TaskDependencyType.HARD:
                if dep.task_id not in completed_tasks:
                    return False
        return True
    
    def get_blocking_dependencies(self, completed_tasks: Set[str]) -> List[str]:
        """Get dependencies that are blocking this task."""
        return [
            dep.task_id
            for dep in self.dependencies
            if dep.dependency_type == TaskDependencyType.HARD
            and dep.task_id not in completed_tasks
        ]
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "identity": self.identity.to_dict(),
            "goal": self.goal,
            "description": self.description,
            "lifecycle": self.lifecycle.to_dict(),
            "cost": self.cost.to_dict(),
            "dependencies": [d.to_dict() for d in self.dependencies],
            "dependents": self.dependents,
            "priority": self.priority,
            "complexity": self.complexity,
            "tags": self.tags,
            "assigned_agent": self.assigned_agent,
            "output": self.output[:500] if self.output else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ============================================================================
# FACTORIES
# ============================================================================


def create_task_identity(
    name: str = "",
    correlation_id: str = None,
    trace_id: str = None,
    session_id: str = None,
) -> TaskIdentity:
    """Create a task identity."""
    return TaskIdentity(
        name=name,
        correlation_id=correlation_id or str(uuid4()),
        trace_id=trace_id or str(uuid4()),
        session_id=session_id,
    )


def create_task_entity(
    goal: str,
    description: str = "",
    priority: int = 5,
    identity: TaskIdentity = None,
    **kwargs
) -> TaskEntity:
    """Create a task entity."""
    return TaskEntity(
        identity=identity or create_task_identity(name=goal[:50]),
        goal=goal,
        description=description,
        priority=priority,
        **kwargs
    )
