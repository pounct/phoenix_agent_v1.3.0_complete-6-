"""
Phoenix Agent - Agent Lifecycle
================================

Agent Lifecycle Definition - THE STATE MACHINE of an Agent Runtime.

This is what separates "modules in folders" from "Agent Runtime Engine".

Without Lifecycle:
    - Components are disconnected
    - No clear execution flow
    - Hard to debug and monitor

With Lifecycle:
    - Clear states and transitions
    - Predictable behavior
    - Observable execution
    - Recoverable errors

Lifecycle States:
    ┌─────────────────────────────────────────────────────────────┐
    │                    AGENT LIFECYCLE                           │
    │                                                              │
    │    ┌──────────┐                                             │
    │    │   IDLE   │ ←──────────────────────────┐               │
    │    └────┬─────┘                            │               │
    │         │ receive_task                     │               │
    │         ▼                                  │               │
    │    ┌──────────┐                            │               │
    │    │RECEIVING │                            │               │
    │    └────┬─────┘                            │               │
    │         │ analyze                          │               │
    │         ▼                                  │               │
    │    ┌──────────┐                            │               │
    │    │ ANALYZING│                            │               │
    │    └────┬─────┘                            │               │
    │         │ plan                             │               │
    │         ▼                                  │               │
    │    ┌──────────┐    needs_resources         │               │
    │    │ PLANNING │───────────────────┐        │               │
    │    └────┬─────┘                   │        │               │
    │         │ execute                 ▼        │               │
    │         │                   ┌──────────┐   │               │
    │         │                   │ WAITING  │   │               │
    │         │                   │(resources)│  │               │
    │         │                   └────┬─────┘   │               │
    │         │                        │ ready   │               │
    │         ▼                        └─────────│───────────┐   │
    │    ┌──────────┐                            │           │   │
    │    │EXECUTING │────────────────────────────┼───────────┤   │
    │    └────┬─────┘                            │           │   │
    │         │ delegate                         │           │   │
    │         ├───────────────────────┐          │           │   │
    │         │                       ▼          │           │   │
    │         │                 ┌──────────┐     │           │   │
    │         │                 │DELEGATING│     │           │   │
    │         │                 └────┬─────┘     │           │   │
    │         │                      │           │           │   │
    │         ▼                      ▼           │           │   │
    │    ┌──────────┐           ┌──────────┐    │           │   │
    │    │SYNTHESIZ │◄──────────│ WAITING  │    │           │   │
    │    │  (ING)   │           │(results) │    │           │   │
    │    └────┬─────┘           └──────────┘    │           │   │
    │         │ learn                           │           │   │
    │         ▼                                  │           │   │
    │    ┌──────────┐                            │           │   │
    │    │ LEARNING │                            │           │   │
    │    └────┬─────┘                            │           │   │
    │         │ complete                         │           │   │
    │         ▼                                  │           │   │
    │    ┌──────────┐                            │           │   │
    │    │COMPLETED │────────────────────────────┼───────────┘   │
    │    └──────────┘                            │               │
    │                                            │               │
    │    ERROR PATH:                             │               │
    │    ┌──────────┐    recover                 │               │
    │    │  ERROR   │────────────────────────────┘               │
    │    └────┬─────┘                                            │
    │         │ abort                                            │
    │         ▼                                                  │
    │    ┌──────────┐                                            │
    │    │ ABORTED  │                                            │
    │    └──────────┘                                            │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

Version: 1.2.0 (Agent Lifecycle)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4
import logging


logger = logging.getLogger("phoenix.lifecycle")


# ============================================================================
# LIFECYCLE STATE
# ============================================================================


class LifecycleState(str, Enum):
    """
    Agent Lifecycle States.
    
    These define the complete life of an agent from idle to completion.
    
    State Categories:
        - IDLE: Not doing anything
        - ACTIVE: Processing (RECEIVING → ANALYZING → PLANNING → EXECUTING)
        - WAITING: Waiting for external resources/results
        - TERMINAL: Done (COMPLETED, ABORTED)
    """
    # Idle
    IDLE = "idle"
    
    # Active - Receiving
    RECEIVING = "receiving"
    
    # Active - Understanding
    ANALYZING = "analyzing"
    
    # Active - Planning
    PLANNING = "planning"
    
    # Active - Executing
    EXECUTING = "executing"
    
    # Active - Delegating
    DELEGATING = "delegating"
    
    # Waiting
    WAITING_RESOURCES = "waiting_resources"
    WAITING_RESULTS = "waiting_results"
    
    # Active - Synthesizing
    SYNTHESIZING = "synthesizing"
    
    # Active - Learning
    LEARNING = "learning"
    
    # Recovery
    RECOVERING = "recovering"
    
    # Terminal
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class LifecycleCategory(str, Enum):
    """Categories of lifecycle states."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING = "waiting"
    RECOVERY = "recovery"
    TERMINAL = "terminal"


# ============================================================================
# STATE TRANSITIONS
# ============================================================================


@dataclass
class StateTransition:
    """A transition between lifecycle states."""
    from_state: LifecycleState
    to_state: LifecycleState
    trigger: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "trigger": self.trigger,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# TRANSITION RULES
# ============================================================================


# Valid state transitions
VALID_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    # From IDLE
    LifecycleState.IDLE: {
        LifecycleState.RECEIVING,
    },
    
    # From RECEIVING
    LifecycleState.RECEIVING: {
        LifecycleState.ANALYZING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From ANALYZING
    LifecycleState.ANALYZING: {
        LifecycleState.PLANNING,
        LifecycleState.EXECUTING,  # Simple tasks skip planning
        LifecycleState.DELEGATING,  # Delegate to specialist
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From PLANNING
    LifecycleState.PLANNING: {
        LifecycleState.EXECUTING,
        LifecycleState.WAITING_RESOURCES,
        LifecycleState.DELEGATING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From EXECUTING
    LifecycleState.EXECUTING: {
        LifecycleState.DELEGATING,
        LifecycleState.WAITING_RESULTS,
        LifecycleState.SYNTHESIZING,
        LifecycleState.RECOVERING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From DELEGATING
    LifecycleState.DELEGATING: {
        LifecycleState.WAITING_RESULTS,
        LifecycleState.EXECUTING,
        LifecycleState.RECOVERING,
        LifecycleState.FAILED,
    },
    
    # From WAITING_RESOURCES
    LifecycleState.WAITING_RESOURCES: {
        LifecycleState.PLANNING,
        LifecycleState.EXECUTING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From WAITING_RESULTS
    LifecycleState.WAITING_RESULTS: {
        LifecycleState.SYNTHESIZING,
        LifecycleState.EXECUTING,
        LifecycleState.RECOVERING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # From SYNTHESIZING
    LifecycleState.SYNTHESIZING: {
        LifecycleState.LEARNING,
        LifecycleState.EXECUTING,  # Need more execution
        LifecycleState.COMPLETED,
        LifecycleState.FAILED,
    },
    
    # From LEARNING
    LifecycleState.LEARNING: {
        LifecycleState.COMPLETED,
        LifecycleState.IDLE,  # For continuous learning
    },
    
    # From RECOVERING
    LifecycleState.RECOVERING: {
        LifecycleState.PLANNING,
        LifecycleState.EXECUTING,
        LifecycleState.DELEGATING,
        LifecycleState.FAILED,
        LifecycleState.ABORTED,
    },
    
    # Terminal states
    LifecycleState.COMPLETED: {
        LifecycleState.IDLE,
    },
    LifecycleState.FAILED: {
        LifecycleState.IDLE,
        LifecycleState.RECOVERING,
    },
    LifecycleState.ABORTED: {
        LifecycleState.IDLE,
    },
}


# State categories
STATE_CATEGORIES: Dict[LifecycleState, LifecycleCategory] = {
    LifecycleState.IDLE: LifecycleCategory.IDLE,
    LifecycleState.RECEIVING: LifecycleCategory.ACTIVE,
    LifecycleState.ANALYZING: LifecycleCategory.ACTIVE,
    LifecycleState.PLANNING: LifecycleCategory.ACTIVE,
    LifecycleState.EXECUTING: LifecycleCategory.ACTIVE,
    LifecycleState.DELEGATING: LifecycleCategory.ACTIVE,
    LifecycleState.SYNTHESIZING: LifecycleCategory.ACTIVE,
    LifecycleState.LEARNING: LifecycleCategory.ACTIVE,
    LifecycleState.WAITING_RESOURCES: LifecycleCategory.WAITING,
    LifecycleState.WAITING_RESULTS: LifecycleCategory.WAITING,
    LifecycleState.RECOVERING: LifecycleCategory.RECOVERY,
    LifecycleState.COMPLETED: LifecycleCategory.TERMINAL,
    LifecycleState.FAILED: LifecycleCategory.TERMINAL,
    LifecycleState.ABORTED: LifecycleCategory.TERMINAL,
}


# ============================================================================
# AGENT LIFECYCLE
# ============================================================================


@dataclass
class AgentLifecycle:
    """
    Agent Lifecycle Controller.
    
    This is THE state machine that governs an agent's behavior.
    
    Responsibilities:
        1. Track current state
        2. Validate transitions
        3. Record history
        4. Enforce rules
        5. Provide observability
    
    Usage:
        lifecycle = AgentLifecycle()
        
        # Start
        lifecycle.receive_task()
        
        # Progress
        lifecycle.analyze()
        lifecycle.plan()
        lifecycle.execute()
        lifecycle.complete()
        
        # Check state
        if lifecycle.is_active:
            print("Agent is working")
    """
    
    # Identity
    agent_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Current state
    current_state: LifecycleState = LifecycleState.IDLE
    previous_state: Optional[LifecycleState] = None
    
    # Transition history
    transition_history: List[StateTransition] = field(default_factory=list)
    
    # State entry times
    state_entered_at: Dict[LifecycleState, datetime] = field(default_factory=dict)
    
    # Callbacks
    _on_transition: List[Callable[[StateTransition], None]] = field(default_factory=list)
    
    # State data
    _state_data: Dict[LifecycleState, Dict[str, Any]] = field(default_factory=dict)
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    
    @property
    def is_idle(self) -> bool:
        """Agent is idle."""
        return self.current_state == LifecycleState.IDLE
    
    @property
    def is_active(self) -> bool:
        """Agent is actively processing."""
        return STATE_CATEGORIES.get(self.current_state) == LifecycleCategory.ACTIVE
    
    @property
    def is_waiting(self) -> bool:
        """Agent is waiting for something."""
        return STATE_CATEGORIES.get(self.current_state) == LifecycleCategory.WAITING
    
    @property
    def is_terminal(self) -> bool:
        """Agent is in terminal state."""
        return STATE_CATEGORIES.get(self.current_state) == LifecycleCategory.TERMINAL
    
    @property
    def can_receive_task(self) -> bool:
        """Agent can receive a new task."""
        return self.current_state in (LifecycleState.IDLE, LifecycleState.COMPLETED)
    
    @property
    def state_category(self) -> LifecycleCategory:
        """Get current state category."""
        return STATE_CATEGORIES.get(self.current_state, LifecycleCategory.IDLE)
    
    # ========================================================================
    # TRANSITION METHODS
    # ========================================================================
    
    def transition(
        self,
        to_state: LifecycleState,
        trigger: str = "",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Transition to a new state.
        
        Args:
            to_state: Target state
            trigger: What triggered the transition
            metadata: Additional data
        
        Returns:
            True if transition succeeded
        """
        # Validate transition
        if not self._is_valid_transition(to_state):
            logger.warning(
                f"Invalid transition: {self.current_state.value} → {to_state.value}"
            )
            return False
        
        # Record transition
        old_state = self.current_state
        self.previous_state = old_state
        self.current_state = to_state
        
        # Record history
        transition = StateTransition(
            from_state=old_state,
            to_state=to_state,
            trigger=trigger,
            metadata=metadata or {},
        )
        self.transition_history.append(transition)
        
        # Record entry time
        self.state_entered_at[to_state] = datetime.utcnow()
        
        # Execute callbacks
        for callback in self._on_transition:
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Transition callback error: {e}")
        
        logger.info(f"Lifecycle transition: {old_state.value} → {to_state.value}")
        
        return True
    
    def _is_valid_transition(self, to_state: LifecycleState) -> bool:
        """Check if transition is valid."""
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        return to_state in allowed
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    def receive_task(self, task_id: str = "") -> bool:
        """Transition to RECEIVING state."""
        return self.transition(
            LifecycleState.RECEIVING,
            trigger="receive_task",
            metadata={"task_id": task_id}
        )
    
    def analyze(self) -> bool:
        """Transition to ANALYZING state."""
        return self.transition(
            LifecycleState.ANALYZING,
            trigger="analyze"
        )
    
    def plan(self) -> bool:
        """Transition to PLANNING state."""
        return self.transition(
            LifecycleState.PLANNING,
            trigger="plan"
        )
    
    def execute(self) -> bool:
        """Transition to EXECUTING state."""
        return self.transition(
            LifecycleState.EXECUTING,
            trigger="execute"
        )
    
    def delegate(self, target: str = "") -> bool:
        """Transition to DELEGATING state."""
        return self.transition(
            LifecycleState.DELEGATING,
            trigger="delegate",
            metadata={"target": target}
        )
    
    def wait_for_resources(self) -> bool:
        """Transition to WAITING_RESOURCES state."""
        return self.transition(
            LifecycleState.WAITING_RESOURCES,
            trigger="wait_resources"
        )
    
    def wait_for_results(self) -> bool:
        """Transition to WAITING_RESULTS state."""
        return self.transition(
            LifecycleState.WAITING_RESULTS,
            trigger="wait_results"
        )
    
    def synthesize(self) -> bool:
        """Transition to SYNTHESIZING state."""
        return self.transition(
            LifecycleState.SYNTHESIZING,
            trigger="synthesize"
        )
    
    def learn(self) -> bool:
        """Transition to LEARNING state."""
        return self.transition(
            LifecycleState.LEARNING,
            trigger="learn"
        )
    
    def recover(self) -> bool:
        """Transition to RECOVERING state."""
        return self.transition(
            LifecycleState.RECOVERING,
            trigger="recover"
        )
    
    def complete(self, result: str = "") -> bool:
        """Transition to COMPLETED state."""
        return self.transition(
            LifecycleState.COMPLETED,
            trigger="complete",
            metadata={"result": result}
        )
    
    def fail(self, error: str = "") -> bool:
        """Transition to FAILED state."""
        self.error_count += 1
        self.last_error = error
        return self.transition(
            LifecycleState.FAILED,
            trigger="fail",
            metadata={"error": error}
        )
    
    def abort(self, reason: str = "") -> bool:
        """Transition to ABORTED state."""
        return self.transition(
            LifecycleState.ABORTED,
            trigger="abort",
            metadata={"reason": reason}
        )
    
    def reset(self) -> bool:
        """Reset to IDLE state."""
        if self.is_terminal:
            return self.transition(
                LifecycleState.IDLE,
                trigger="reset"
            )
        return False
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_transition(self, callback: Callable[[StateTransition], None]) -> None:
        """Register callback for state transitions."""
        self._on_transition.append(callback)
    
    # ========================================================================
    # STATE DATA
    # ========================================================================
    
    def set_state_data(self, key: str, value: Any) -> None:
        """Store data for current state."""
        if self.current_state not in self._state_data:
            self._state_data[self.current_state] = {}
        self._state_data[self.current_state][key] = value
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Get data for current state."""
        state_data = self._state_data.get(self.current_state, {})
        return state_data.get(key, default)
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_time_in_state(self, state: LifecycleState = None) -> float:
        """Get time spent in a state (seconds)."""
        state = state or self.current_state
        if state not in self.state_entered_at:
            return 0.0
        
        entered = self.state_entered_at[state]
        
        # If currently in this state, calculate ongoing time
        if state == self.current_state:
            return (datetime.utcnow() - entered).total_seconds()
        
        # Otherwise find the transition out
        for t in self.transition_history:
            if t.from_state == state:
                return (t.timestamp - entered).total_seconds()
        
        return 0.0
    
    def get_transition_count(self) -> int:
        """Get total number of transitions."""
        return len(self.transition_history)
    
    def get_state_visits(self, state: LifecycleState) -> int:
        """Count how many times a state was entered."""
        return sum(
            1 for t in self.transition_history
            if t.to_state == state
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize lifecycle state."""
        return {
            "agent_id": self.agent_id,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "state_category": self.state_category.value,
            "is_active": self.is_active,
            "is_waiting": self.is_waiting,
            "is_terminal": self.is_terminal,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "transition_count": self.get_transition_count(),
        }
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get transition history."""
        return [t.to_dict() for t in self.transition_history[-limit:]]


# ============================================================================
# LIFECYCLE MANAGER
# ============================================================================


class LifecycleManager:
    """
    Manages lifecycles for multiple agents.
    
    Use this for multi-agent systems.
    """
    
    def __init__(self):
        self._lifecycles: Dict[str, AgentLifecycle] = {}
    
    def create(self, agent_id: str = None) -> AgentLifecycle:
        """Create a new lifecycle."""
        lifecycle = AgentLifecycle(agent_id=agent_id or str(uuid4()))
        self._lifecycles[lifecycle.agent_id] = lifecycle
        return lifecycle
    
    def get(self, agent_id: str) -> Optional[AgentLifecycle]:
        """Get a lifecycle by agent ID."""
        return self._lifecycles.get(agent_id)
    
    def remove(self, agent_id: str) -> bool:
        """Remove a lifecycle."""
        if agent_id in self._lifecycles:
            del self._lifecycles[agent_id]
            return True
        return False
    
    def get_all_active(self) -> List[AgentLifecycle]:
        """Get all active lifecycles."""
        return [lc for lc in self._lifecycles.values() if lc.is_active]
    
    def get_all_waiting(self) -> List[AgentLifecycle]:
        """Get all waiting lifecycles."""
        return [lc for lc in self._lifecycles.values() if lc.is_waiting]
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of all lifecycles."""
        summary = {state.value: 0 for state in LifecycleState}
        for lc in self._lifecycles.values():
            summary[lc.current_state.value] += 1
        return summary


# ============================================================================
# FACTORY
# ============================================================================


def create_lifecycle(agent_id: str = None) -> AgentLifecycle:
    """Create an AgentLifecycle."""
    return AgentLifecycle(agent_id=agent_id)


def get_lifecycle_state_category(state: LifecycleState) -> LifecycleCategory:
    """Get the category of a lifecycle state."""
    return STATE_CATEGORIES.get(state, LifecycleCategory.IDLE)
