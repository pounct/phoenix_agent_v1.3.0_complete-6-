"""
World State Manager - State Authority
======================================

LAW 2: STATE DRIVES DECISIONS, NOT EVENTS.

This is THE foundation of the cognitive agent.

Difference from Event-Driven:
    Event-Driven: task arrives → react
    State-Driven: state changes → reconsider world

The World State Manager is:
    - THE authority on world state
    - Single source of truth
    - Change detector
    - State evolution tracker

Why State-Driven Matters:
    - Proactive instead of reactive
    - Anticipates changes
    - Maintains coherent worldview
    - Enables deliberation

Architecture Position:
    World State Manager is the FOUNDATION.
    Everything else builds on it.

    Reasoning reads state.
    Planning reads state.
    Execution reads state.
    Self Model reads state.

    Nothing bypasses state.

Version: 3.0.0 (Cognitive Kernel)
"""

from typing import Optional, List, Dict, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import copy


logger = logging.getLogger("phoenix.kernel.world_state")


# ==========================================
# STATE DOMAIN
# ==========================================

class StateDomain(str, Enum):
    """Domains of state."""
    COGNITIVE = "cognitive"       # Internal cognitive state
    OPERATIONAL = "operational"   # Task/operation state
    ENVIRONMENT = "environment"   # External environment
    SOCIAL = "social"             # Multi-agent relationships
    RESOURCE = "resource"         # Resource availability
    TEMPORAL = "temporal"         # Time-related state
    GOAL = "goal"                 # Goal landscape
    RISK = "risk"                 # Risk landscape


class StateVariable(str, Enum):
    """Standard state variables."""
    # Cognitive
    COGNITIVE_LOAD = "cognitive_load"
    CONFIDENCE = "confidence"
    ATTENTION_FOCUS = "attention_focus"
    
    # Operational
    ACTIVE_TASKS = "active_tasks"
    PENDING_DECISIONS = "pending_decisions"
    EXECUTION_STATUS = "execution_status"
    
    # Environment
    TOOL_HEALTH = "tool_health"
    AGENT_AVAILABILITY = "agent_availability"
    EXTERNAL_RESOURCES = "external_resources"
    
    # Resource
    TOKEN_BUDGET = "token_budget"
    TIME_BUDGET = "time_budget"
    DELEGATION_BUDGET = "delegation_budget"
    
    # Temporal
    DEADLINE_PRESSURE = "deadline_pressure"
    TIME_ELAPSED = "time_elapsed"
    
    # Goal
    GOAL_PROGRESS = "goal_progress"
    GOAL_CONFLICTS = "goal_conflicts"
    GOAL_PRIORITY = "goal_priority"
    
    # Risk
    RISK_LEVEL = "risk_level"
    UNCERTAINTY = "uncertainty"


class StateTrend(str, Enum):
    """Trends in state values."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


# ==========================================
# STATE DIFF
# ==========================================

@dataclass
class StateDiff:
    """
    Represents a change in state.
    
    Critical for state-driven behavior:
        detect what changed → decide what to reconsider
    """
    variable: StateVariable
    domain: StateDomain
    old_value: Any
    new_value: Any
    delta: Optional[float] = None
    significance: float = 0.0              # How important this change is
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def changed(self) -> bool:
        """Check if value actually changed."""
        return self.old_value != self.new_value
    
    def calculate_significance(self, threshold: float = 0.1) -> float:
        """Calculate significance of change."""
        if self.delta is not None:
            self.significance = min(1.0, abs(self.delta) / threshold)
        elif isinstance(self.old_value, (int, float)) and isinstance(self.new_value, (int, float)):
            if self.old_value != 0:
                self.significance = abs(self.new_value - self.old_value) / abs(self.old_value)
            else:
                self.significance = abs(self.new_value)
        else:
            self.significance = 1.0 if self.changed else 0.0
        return self.significance


# ==========================================
# WORLD STATE
# ==========================================

@dataclass
class WorldState:
    """
    THE SINGLE SOURCE OF TRUTH.
    
    This represents the complete state of the agent's world.
    All decisions should be based on this state, not events.
    
    Structure:
        - Primary state (key metrics)
        - Domain state (organized by domain)
        - Meta state (timestamps, trends)
    """
    # Identity
    state_id: str
    agent_id: str
    
    # Primary state (most accessed)
    cognitive_load: float = 0.0
    confidence: float = 0.5
    risk_level: float = 0.0
    goal_progress: float = 0.0
    resource_pressure: float = 0.0
    time_pressure: float = 0.0
    
    # Operational state
    active_tasks: List[str] = field(default_factory=list)
    pending_decisions: List[str] = field(default_factory=list)
    execution_status: str = "idle"
    
    # Environment state
    tool_health: Dict[str, float] = field(default_factory=dict)
    agent_availability: Dict[str, bool] = field(default_factory=dict)
    
    # Resource state
    token_budget_remaining: float = 100000.0
    time_budget_remaining: float = 300.0
    delegation_budget_remaining: int = 10
    
    # Goal state
    active_goals: List[str] = field(default_factory=list)
    goal_conflicts: List[Tuple[str, str]] = field(default_factory=list)
    goal_priorities: Dict[str, float] = field(default_factory=dict)
    
    # Temporal state
    deadline_pressure: float = 0.0
    session_duration: float = 0.0
    
    # Domain-specific state (extensible)
    domain_state: Dict[StateDomain, Dict[str, Any]] = field(default_factory=dict)
    
    # Trends (computed)
    trends: Dict[StateVariable, StateTrend] = field(default_factory=dict)
    
    # Meta
    timestamp: datetime = field(default_factory=datetime.utcnow)
    previous_state_id: Optional[str] = None
    version: int = 1
    
    def get(self, variable: StateVariable, default: Any = None) -> Any:
        """Get a state variable value."""
        var_map = {
            StateVariable.COGNITIVE_LOAD: self.cognitive_load,
            StateVariable.CONFIDENCE: self.confidence,
            StateVariable.RISK_LEVEL: self.risk_level,
            StateVariable.GOAL_PROGRESS: self.goal_progress,
            StateVariable.ACTIVE_TASKS: self.active_tasks,
            StateVariable.PENDING_DECISIONS: self.pending_decisions,
            StateVariable.EXECUTION_STATUS: self.execution_status,
            StateVariable.TOOL_HEALTH: self.tool_health,
            StateVariable.AGENT_AVAILABILITY: self.agent_availability,
            StateVariable.TOKEN_BUDGET: self.token_budget_remaining,
            StateVariable.TIME_BUDGET: self.time_budget_remaining,
            StateVariable.DELEGATION_BUDGET: self.delegation_budget_remaining,
            StateVariable.DEADLINE_PRESSURE: self.deadline_pressure,
            StateVariable.TIME_ELAPSED: self.session_duration,
            StateVariable.GOAL_CONFLICTS: self.goal_conflicts,
            StateVariable.GOAL_PRIORITY: self.goal_priorities,
            StateVariable.UNCERTAINTY: 1.0 - self.confidence,
            StateVariable.RISK_LEVEL: self.risk_level,
        }
        return var_map.get(variable, default)
    
    def set(self, variable: StateVariable, value: Any) -> None:
        """Set a state variable value."""
        if variable == StateVariable.COGNITIVE_LOAD:
            self.cognitive_load = value
        elif variable == StateVariable.CONFIDENCE:
            self.confidence = value
        elif variable == StateVariable.RISK_LEVEL:
            self.risk_level = value
        elif variable == StateVariable.GOAL_PROGRESS:
            self.goal_progress = value
        elif variable == StateVariable.ACTIVE_TASKS:
            self.active_tasks = value
        elif variable == StateVariable.PENDING_DECISIONS:
            self.pending_decisions = value
        elif variable == StateVariable.EXECUTION_STATUS:
            self.execution_status = value
        elif variable == StateVariable.TOKEN_BUDGET:
            self.token_budget_remaining = value
        elif variable == StateVariable.TIME_BUDGET:
            self.time_budget_remaining = value
        elif variable == StateVariable.DELEGATION_BUDGET:
            self.delegation_budget_remaining = value
        elif variable == StateVariable.DEADLINE_PRESSURE:
            self.deadline_pressure = value
    
    def domain(self, domain: StateDomain) -> Dict[str, Any]:
        """Get all state for a domain."""
        return self.domain_state.get(domain, {})
    
    def set_domain(self, domain: StateDomain, state: Dict[str, Any]) -> None:
        """Set state for a domain."""
        self.domain_state[domain] = state
    
    def get_trend(self, variable: StateVariable) -> StateTrend:
        """Get trend for a variable."""
        return self.trends.get(variable, StateTrend.UNKNOWN)
    
    def overall_pressure(self) -> float:
        """Calculate overall pressure score."""
        return (
            self.cognitive_load * 0.2 +
            self.risk_level * 0.2 +
            self.resource_pressure * 0.2 +
            self.time_pressure * 0.2 +
            self.deadline_pressure * 0.2
        )
    
    def is_healthy(self) -> bool:
        """Check if agent state is healthy."""
        return (
            self.cognitive_load < 0.8 and
            self.confidence > 0.3 and
            self.risk_level < 0.7 and
            self.overall_pressure() < 0.7
        )
    
    def needs_attention(self) -> List[StateVariable]:
        """Get variables that need attention."""
        needs = []
        
        if self.cognitive_load > 0.7:
            needs.append(StateVariable.COGNITIVE_LOAD)
        if self.confidence < 0.5:
            needs.append(StateVariable.CONFIDENCE)
        if self.risk_level > 0.6:
            needs.append(StateVariable.RISK_LEVEL)
        if self.resource_pressure > 0.7:
            needs.append(StateVariable.TOKEN_BUDGET)
        if self.time_pressure > 0.7:
            needs.append(StateVariable.TIME_BUDGET)
        if len(self.goal_conflicts) > 0:
            needs.append(StateVariable.GOAL_CONFLICTS)
        
        return needs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state_id": self.state_id,
            "agent_id": self.agent_id,
            "primary": {
                "cognitive_load": self.cognitive_load,
                "confidence": self.confidence,
                "risk_level": self.risk_level,
                "goal_progress": self.goal_progress,
                "resource_pressure": self.resource_pressure,
                "time_pressure": self.time_pressure,
            },
            "operational": {
                "active_tasks": self.active_tasks,
                "pending_decisions": self.pending_decisions,
                "execution_status": self.execution_status,
            },
            "resource": {
                "token_budget_remaining": self.token_budget_remaining,
                "time_budget_remaining": self.time_budget_remaining,
                "delegation_budget_remaining": self.delegation_budget_remaining,
            },
            "goal": {
                "active_goals": self.active_goals,
                "goal_conflicts": self.goal_conflicts,
                "goal_priorities": self.goal_priorities,
            },
            "health": {
                "is_healthy": self.is_healthy(),
                "overall_pressure": self.overall_pressure(),
                "needs_attention": [v.value for v in self.needs_attention()],
            },
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }


# ==========================================
# WORLD STATE MANAGER
# ==========================================

class WorldStateManager:
    """
    THE STATE AUTHORITY.
    
    This implements LAW 2: State drives decisions, not events.
    
    The WorldStateManager:
        - Maintains THE authoritative world state
        - Detects state changes (diffs)
        - Tracks state evolution (trends)
        - Notifies state subscribers
        - Provides state history
    
    Critical Design:
        - All state changes go through this manager
        - Nothing bypasses state
        - State is THE source of truth
    
    Usage:
        world = WorldStateManager(agent_id="phoenix-main")
        
        # Get current state
        state = world.get_state()
        
        # Update state
        world.update({
            StateVariable.COGNITIVE_LOAD: 0.8,
            StateVariable.CONFIDENCE: 0.6,
        })
        
        # Detect changes
        diffs = world.get_recent_diffs()
        
        # Subscribe to state changes
        world.subscribe(on_state_change)
        
        # Check if reconsideration needed
        if world.significant_change_detected():
            agent.reconsider()
    """
    
    def __init__(
        self,
        agent_id: str,
        history_size: int = 100,
        diff_threshold: float = 0.05,
    ):
        self.agent_id = agent_id
        self.history_size = history_size
        self.diff_threshold = diff_threshold
        
        # Current state
        self._current_state: Optional[WorldState] = None
        self._previous_state: Optional[WorldState] = None
        
        # State history
        self._state_history: List[WorldState] = []
        
        # Diffs
        self._diff_history: List[StateDiff] = []
        self._max_diff_history = 500
        
        # Trend tracking
        self._value_history: Dict[StateVariable, List[Tuple[datetime, Any]]] = {}
        self._trend_window = 10
        
        # Subscribers
        self._subscribers: List[Callable[[WorldState, List[StateDiff]], None]] = []
        
        # Significant change tracking
        self._significant_diffs: List[StateDiff] = []
        
        # Initialize state
        self._initialize_state()
        
        logger.info(f"WorldStateManager initialized for {agent_id}")
    
    def _initialize_state(self) -> None:
        """Initialize the world state."""
        import uuid
        
        state_id = f"state-{uuid.uuid4().hex[:8]}"
        
        self._current_state = WorldState(
            state_id=state_id,
            agent_id=self.agent_id,
        )
    
    # ==========================================
    # STATE ACCESS (THE AUTHORITY)
    # ==========================================
    
    def get_state(self) -> WorldState:
        """
        Get THE current world state.
        
        This is the ONLY way to get authoritative state.
        """
        if self._current_state is None:
            self._initialize_state()
        return self._current_state
    
    def get_previous_state(self) -> Optional[WorldState]:
        """Get the previous state (for comparison)."""
        return self._previous_state
    
    def get_state_history(self, limit: int = 10) -> List[WorldState]:
        """Get recent state history."""
        return self._state_history[-limit:]
    
    # ==========================================
    # STATE UPDATE (THE SINGLE ENTRY POINT)
    # ==========================================
    
    def update(
        self,
        updates: Dict[StateVariable, Any],
        domain_updates: Optional[Dict[StateDomain, Dict[str, Any]]] = None,
        reason: str = "",
    ) -> List[StateDiff]:
        """
        Update world state.
        
        This is THE way to change state.
        All state changes go through this method.
        
        Returns:
            List of state diffs (what changed)
        """
        if self._current_state is None:
            self._initialize_state()
        
        # Store previous state
        self._previous_state = copy.deepcopy(self._current_state)
        
        # Track diffs
        diffs = []
        
        # Apply updates
        for variable, new_value in updates.items():
            old_value = self._current_state.get(variable)
            
            if old_value != new_value:
                diff = StateDiff(
                    variable=variable,
                    domain=self._get_domain_for_variable(variable),
                    old_value=old_value,
                    new_value=new_value,
                )
                diff.calculate_significance(self.diff_threshold)
                diffs.append(diff)
                
                # Update state
                self._current_state.set(variable, new_value)
                
                # Track value history for trends
                self._track_value(variable, new_value)
        
        # Apply domain updates
        if domain_updates:
            for domain, state in domain_updates.items():
                self._current_state.set_domain(domain, state)
        
        # Update meta
        self._current_state.version += 1
        self._current_state.timestamp = datetime.utcnow()
        if self._previous_state:
            self._current_state.previous_state_id = self._previous_state.state_id
        
        # Record history
        self._state_history.append(copy.deepcopy(self._current_state))
        if len(self._state_history) > self.history_size:
            self._state_history = self._state_history[-self.history_size:]
        
        # Record diffs
        self._diff_history.extend(diffs)
        if len(self._diff_history) > self._max_diff_history:
            self._diff_history = self._diff_history[-self._max_diff_history:]
        
        # Track significant diffs
        significant = [d for d in diffs if d.significance > 0.5]
        self._significant_diffs.extend(significant)
        if len(self._significant_diffs) > 50:
            self._significant_diffs = self._significant_diffs[-50:]
        
        # Update trends
        self._update_trends()
        
        # Notify subscribers
        if diffs:
            self._notify_subscribers(diffs)
        
        if diffs:
            logger.debug(f"State updated: {len(diffs)} changes, {len(significant)} significant")
        
        return diffs
    
    def _get_domain_for_variable(self, variable: StateVariable) -> StateDomain:
        """Get the domain for a state variable."""
        domain_map = {
            StateVariable.COGNITIVE_LOAD: StateDomain.COGNITIVE,
            StateVariable.CONFIDENCE: StateDomain.COGNITIVE,
            StateVariable.ATTENTION_FOCUS: StateDomain.COGNITIVE,
            StateVariable.ACTIVE_TASKS: StateDomain.OPERATIONAL,
            StateVariable.PENDING_DECISIONS: StateDomain.OPERATIONAL,
            StateVariable.EXECUTION_STATUS: StateDomain.OPERATIONAL,
            StateVariable.TOOL_HEALTH: StateDomain.ENVIRONMENT,
            StateVariable.AGENT_AVAILABILITY: StateDomain.SOCIAL,
            StateVariable.TOKEN_BUDGET: StateDomain.RESOURCE,
            StateVariable.TIME_BUDGET: StateDomain.RESOURCE,
            StateVariable.DELEGATION_BUDGET: StateDomain.RESOURCE,
            StateVariable.DEADLINE_PRESSURE: StateDomain.TEMPORAL,
            StateVariable.TIME_ELAPSED: StateDomain.TEMPORAL,
            StateVariable.GOAL_PROGRESS: StateDomain.GOAL,
            StateVariable.GOAL_CONFLICTS: StateDomain.GOAL,
            StateVariable.GOAL_PRIORITY: StateDomain.GOAL,
            StateVariable.RISK_LEVEL: StateDomain.RISK,
            StateVariable.UNCERTAINTY: StateDomain.RISK,
        }
        return domain_map.get(variable, StateDomain.OPERATIONAL)
    
    def _track_value(self, variable: StateVariable, value: Any) -> None:
        """Track value history for trend detection."""
        if variable not in self._value_history:
            self._value_history[variable] = []
        
        self._value_history[variable].append((datetime.utcnow(), value))
        
        # Trim to window
        if len(self._value_history[variable]) > self._trend_window:
            self._value_history[variable] = self._value_history[variable][-self._trend_window:]
    
    def _update_trends(self) -> None:
        """Update trend indicators for all tracked variables."""
        for variable, history in self._value_history.items():
            if len(history) < 3:
                self._current_state.trends[variable] = StateTrend.UNKNOWN
                continue
            
            # Get numeric values
            numeric_values = []
            for _, val in history:
                if isinstance(val, (int, float)):
                    numeric_values.append(val)
            
            if len(numeric_values) < 3:
                self._current_state.trends[variable] = StateTrend.UNKNOWN
                continue
            
            # Calculate trend
            first_half = numeric_values[:len(numeric_values)//2]
            second_half = numeric_values[len(numeric_values)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            diff = second_avg - first_avg
            
            if abs(diff) < 0.05 * first_avg:
                trend = StateTrend.STABLE
            elif diff > 0:
                trend = StateTrend.INCREASING
            else:
                trend = StateTrend.DECREASING
            
            # Check volatility
            variance = sum((v - sum(numeric_values)/len(numeric_values))**2 for v in numeric_values) / len(numeric_values)
            if variance > 0.1:
                trend = StateTrend.VOLATILE
            
            self._current_state.trends[variable] = trend
    
    # ==========================================
    # DIFF DETECTION (STATE-DRIVEN BEHAVIOR)
    # ==========================================
    
    def get_recent_diffs(self, limit: int = 10) -> List[StateDiff]:
        """Get recent state diffs."""
        return self._diff_history[-limit:]
    
    def get_significant_diffs(self) -> List[StateDiff]:
        """Get significant state changes (for reconsideration)."""
        return self._significant_diffs.copy()
    
    def clear_significant_diffs(self) -> None:
        """Clear significant diffs (after handling)."""
        self._significant_diffs = []
    
    def significant_change_detected(self) -> bool:
        """
        Check if significant state change occurred.
        
        This is KEY for state-driven behavior:
            if significant change → agent should reconsider
        """
        return len(self._significant_diffs) > 0
    
    def get_diffs_by_domain(self, domain: StateDomain) -> List[StateDiff]:
        """Get diffs for a specific domain."""
        return [d for d in self._diff_history if d.domain == domain]
    
    def get_diffs_by_variable(self, variable: StateVariable) -> List[StateDiff]:
        """Get diffs for a specific variable."""
        return [d for d in self._diff_history if d.variable == variable]
    
    # ==========================================
    # STATE QUERIES (FOR DELIBERATION)
    # ==========================================
    
    def get_trend(self, variable: StateVariable) -> StateTrend:
        """Get trend for a state variable."""
        if self._current_state:
            return self._current_state.get_trend(variable)
        return StateTrend.UNKNOWN
    
    def is_improving(self, variable: StateVariable) -> bool:
        """Check if a metric is improving."""
        trend = self.get_trend(variable)
        return trend == StateTrend.DECREASING if variable in [
            StateVariable.RISK_LEVEL,
            StateVariable.COGNITIVE_LOAD,
        ] else trend == StateTrend.INCREASING
    
    def needs_reconsideration(self) -> bool:
        """
        Check if agent needs to reconsider its situation.
        
        State-driven agents call this regularly.
        """
        state = self.get_state()
        
        # Significant change
        if self.significant_change_detected():
            return True
        
        # State pressure
        if state.overall_pressure() > 0.6:
            return True
        
        # Needs attention
        if len(state.needs_attention()) > 2:
            return True
        
        # Not healthy
        if not state.is_healthy():
            return True
        
        return False
    
    # ==========================================
    # SUBSCRIPTION (FOR REACTIVE COMPONENTS)
    # ==========================================
    
    def subscribe(
        self,
        callback: Callable[[WorldState, List[StateDiff]], None],
    ) -> None:
        """Subscribe to state changes."""
        self._subscribers.append(callback)
    
    def unsubscribe(
        self,
        callback: Callable[[WorldState, List[StateDiff]], None],
    ) -> None:
        """Unsubscribe from state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify_subscribers(self, diffs: List[StateDiff]) -> None:
        """Notify subscribers of state changes."""
        state = self.get_state()
        
        for callback in self._subscribers:
            try:
                callback(state, diffs)
            except Exception as e:
                logger.error(f"State subscriber error: {e}")
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        state = self.get_state()
        
        return {
            "agent_id": self.agent_id,
            "state_version": state.version,
            "state_history_size": len(self._state_history),
            "diff_history_size": len(self._diff_history),
            "significant_diffs_pending": len(self._significant_diffs),
            "tracked_variables": len(self._value_history),
            "subscriber_count": len(self._subscribers),
            "current_state": state.to_dict(),
        }
