"""
Agent Kernel - The Living Cognitive Loop
========================================

THE COGNITIVE ORGANISM.

This is NOT a module. This is THE LIVING AGENT.

The Agent Kernel implements the complete cognitive cycle:
    while alive:
        perceive(world_state)
        update_self_model()
        
        reason(world_state, self_model)
        plan(intention)
        
        decide(plan)
        execute(decision)
        
        monitor(results)
        learn(outcomes)

The 3 Laws Implementation:

    Law 1: Cognition must never execute.
    → Reasoning Loop produces Intentions
    → Execution Engine transforms to Actions
    → Separation enforced

    Law 2: State drives decisions.
    → World State Manager is authority
    → All decisions read state
    → State changes trigger reconsideration

    Law 3: Agent must continuously model itself.
    → Self Model tracks performance
    → Self Regulation adapts behavior
    → Continuous calibration

Architecture:
    
    ┌─────────────────────────────────────────────────────────┐
    │                     AGENT KERNEL                        │
    │                  (The Living Loop)                      │
    │                                                          │
    │   ┌─────────────┐                              ┌──────┐ │
    │   │World State  │◀────────────────────────────│Self  │ │
    │   │  Manager    │                              │Model │ │
    │   └──────┬──────┘                              └──────┘ │
    │          │                                        │     │
    │          ▼                                        │     │
    │   ┌─────────────┐    Law 1: Cognition Sandbox   │     │
    │   │ Reasoning   │    ─────────────────────────  │     │
    │   │    Loop     │──────────────┐                │     │
    │   └─────────────┘              │                │     │
    │          │                     ▼                │     │
    │          │              ┌─────────────┐         │     │
    │          │              │ Execution   │         │     │
    │          │              │   Engine    │         │     │
    │          │              └─────────────┘         │     │
    │          │                     │                │     │
    │          ▼                     ▼                ▼     │
    │   ┌─────────────────────────────────────────────────┐ │
    │   │              MONITORING & LEARNING               │ │
    │   └─────────────────────────────────────────────────┘ │
    │                                                          │
    └─────────────────────────────────────────────────────────┘

This transforms:
    "collection of modules" → "living cognitive organism"

Version: 3.0.0 (Cognitive Kernel)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging

from .world_state import (
    WorldStateManager,
    WorldState,
    StateVariable,
    StateDiff,
)
from .self_model import (
    SelfModel,
    SelfState,
    FatigueLevel,
)
from .reasoning_loop import (
    ReasoningLoop,
    Intention,
    IntentionType,
    ReasoningPhase,
)
from .execution_engine import (
    ExecutionEngine,
    Action,
    ExecutionResult,
    ExecutionStatus,
)


logger = logging.getLogger("phoenix.kernel")


# ==========================================
# KERNEL STATE
# ==========================================

class KernelState(str, Enum):
    """States of the agent kernel."""
    DORMANT = "dormant"             # Not started
    INITIALIZING = "initializing"   # Starting up
    IDLE = "idle"                   # Waiting for work
    PERCEIVING = "perceiving"       # Gathering state
    REASONING = "reasoning"         # Thinking
    PLANNING = "planning"           # Creating plan
    EXECUTING = "executing"         # Acting
    MONITORING = "monitoring"       # Observing results
    LEARNING = "learning"           # Updating models
    RECOVERING = "recovering"       # Recovering from error
    SHUTTING_DOWN = "shutting_down" # Stopping


# ==========================================
# KERNEL CONFIG
# ==========================================

@dataclass
class KernelConfig:
    """Configuration for the agent kernel."""
    # Identity
    agent_id: str = "phoenix-main"
    agent_name: str = "Phoenix Agent"
    role: str = "general"
    
    # Cognitive settings
    tick_interval_ms: float = 100.0
    max_iterations: int = 100
    idle_timeout_seconds: float = 60.0
    
    # Reasoning settings
    reasoning_time_budget_ms: float = 5000.0
    max_reasoning_cycles: int = 3
    
    # Execution settings
    execution_timeout_ms: float = 30000.0
    max_concurrent_executions: int = 3
    
    # State settings
    state_history_size: int = 100
    
    # Learning settings
    learning_enabled: bool = True
    reflection_interval: int = 10  # Reflect every N cycles
    
    # Safety
    safe_mode: bool = False
    emergency_stop_enabled: bool = True


# ==========================================
# KERNEL CYCLE RESULT
# ==========================================

@dataclass
class CycleResult:
    """Result of a single cognitive cycle."""
    cycle_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Phases
    perception_duration_ms: float = 0.0
    reasoning_duration_ms: float = 0.0
    execution_duration_ms: float = 0.0
    learning_duration_ms: float = 0.0
    
    # Outcomes
    state_changed: bool = False
    intentions_produced: int = 0
    actions_executed: int = 0
    actions_succeeded: int = 0
    
    # Final state
    kernel_state: KernelState = KernelState.IDLE
    
    @property
    def total_duration_ms(self) -> float:
        """Get total duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0


# ==========================================
# AGENT KERNEL
# ==========================================

class AgentKernel:
    """
    THE LIVING COGNITIVE ORGANISM.
    
    This is THE core of Phoenix.
    
    The Agent Kernel:
        - Implements the 3 Laws
        - Runs the cognitive cycle
        - Coordinates all components
        - Maintains agent life
    
    The Cognitive Cycle:
        while alive:
            perceive()
            update_self()
            
            if needs_reasoning():
                reason()
            
            if has_intention():
                plan()
                execute()
            
            monitor()
            learn()
    
    The 3 Laws:
        Law 1: Cognition never executes
        → Reasoning Loop is sandboxed
        
        Law 2: State drives decisions
        → World State Manager is authority
        
        Law 3: Continuous self-modeling
        → Self Model updates continuously
    
    Usage:
        config = KernelConfig(agent_id="phoenix-main")
        kernel = AgentKernel(config)
        
        # Start the kernel
        await kernel.start()
        
        # Run cognitive cycles
        while running:
            result = await kernel.tick()
        
        # Stop gracefully
        await kernel.stop()
    
    Architecture Position:
        This is THE orchestrator.
        All components flow through this kernel.
        It is the "heart" of the agent.
    """
    
    def __init__(
        self,
        config: KernelConfig,
    ):
        self.config = config
        
        # Kernel state
        self._state = KernelState.DORMANT
        self._running = False
        self._iteration = 0
        self._started_at: Optional[datetime] = None
        
        # Core components
        self._world_state = WorldStateManager(
            agent_id=config.agent_id,
            history_size=config.state_history_size,
        )
        
        self._self_model = SelfModel(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            role=config.role,
        )
        
        self._reasoning = ReasoningLoop(
            max_deliberation_cycles=config.max_reasoning_cycles,
            default_time_budget_ms=config.reasoning_time_budget_ms,
        )
        
        self._execution = ExecutionEngine(
            default_timeout_ms=config.execution_timeout_ms,
            max_concurrent=config.max_concurrent_executions,
        )
        
        # Connect state providers
        self._reasoning.set_world_state_provider(
            lambda: self._world_state.get_state()
        )
        self._reasoning.set_self_state_provider(
            lambda: self._self_model.get_state()
        )
        
        # Callbacks
        self._on_cycle_complete: Optional[Callable[[CycleResult], None]] = None
        self._on_state_change: Optional[Callable[[KernelState, KernelState], None]] = None
        
        # Pending intentions (from reasoning, to execution)
        self._pending_intentions: List[Intention] = []
        
        # Cycle results
        self._cycle_history: List[CycleResult] = []
        self._max_cycle_history = 100
        
        logger.info(f"AgentKernel created: {config.agent_id}")
    
    # ==========================================
    # LIFECYCLE
    # ==========================================
    
    async def start(self) -> None:
        """Start the agent kernel."""
        if self._running:
            return
        
        self._set_state(KernelState.INITIALIZING)
        
        self._running = True
        self._started_at = datetime.utcnow()
        self._iteration = 0
        
        # Initialize state
        self._world_state.update({
            StateVariable.EXECUTION_STATUS: "idle",
        })
        
        self._set_state(KernelState.IDLE)
        
        logger.info(f"AgentKernel started: {self.config.agent_id}")
    
    async def stop(self) -> None:
        """Stop the agent kernel gracefully."""
        if not self._running:
            return
        
        self._set_state(KernelState.SHUTTING_DOWN)
        
        self._running = False
        
        # Wait for active executions
        active = self._execution.get_active_executions()
        if active:
            logger.info(f"Waiting for {len(active)} active executions...")
            await asyncio.sleep(0.5)
        
        self._set_state(KernelState.DORMANT)
        
        logger.info(f"AgentKernel stopped: {self.config.agent_id}")
    
    # ==========================================
    # THE COGNITIVE CYCLE (THE TICK)
    # ==========================================
    
    async def tick(self) -> CycleResult:
        """
        Run ONE cognitive cycle.
        
        This is THE heartbeat of the agent.
        
        The Cycle:
            1. PERCEIVE: Update world state
            2. SELF: Update self model
            3. REASON: Think about situation
            4. PLAN: Create execution plan
            5. EXECUTE: Run actions
            6. MONITOR: Observe results
            7. LEARN: Update models
        """
        import uuid
        
        self._iteration += 1
        cycle_id = f"cycle-{uuid.uuid4().hex[:8]}"
        
        result = CycleResult(
            cycle_id=cycle_id,
            started_at=datetime.utcnow(),
        )
        
        # 1. PERCEIVE
        perceive_start = datetime.utcnow()
        await self._phase_perceive()
        result.perception_duration_ms = (
            datetime.utcnow() - perceive_start
        ).total_seconds() * 1000
        
        # 2. SELF UPDATE
        await self._phase_update_self()
        
        # 3. REASON (if needed)
        if self._needs_reasoning():
            self._set_state(KernelState.REASONING)
            reason_start = datetime.utcnow()
            
            intentions = await self._phase_reason()
            
            result.reasoning_duration_ms = (
                datetime.utcnow() - reason_start
            ).total_seconds() * 1000
            result.intentions_produced = len(intentions)
            
            self._pending_intentions.extend(intentions)
        
        # 4 & 5. PLAN AND EXECUTE (if intentions pending)
        if self._pending_intentions:
            self._set_state(KernelState.EXECUTING)
            exec_start = datetime.utcnow()
            
            exec_results = await self._phase_execute()
            
            result.execution_duration_ms = (
                datetime.utcnow() - exec_start
            ).total_seconds() * 1000
            result.actions_executed = len(exec_results)
            result.actions_succeeded = sum(1 for r in exec_results if r.success)
        
        # 6. MONITOR
        await self._phase_monitor()
        
        # 7. LEARN
        if self.config.learning_enabled:
            self._set_state(KernelState.LEARNING)
            learn_start = datetime.utcnow()
            
            await self._phase_learn()
            
            result.learning_duration_ms = (
                datetime.utcnow() - learn_start
            ).total_seconds() * 1000
        
        # Complete cycle
        result.completed_at = datetime.utcnow()
        result.kernel_state = self._state
        result.state_changed = self._world_state.significant_change_detected()
        
        # Record history
        self._cycle_history.append(result)
        if len(self._cycle_history) > self._max_cycle_history:
            self._cycle_history = self._cycle_history[-self._max_cycle_history:]
        
        # Callback
        if self._on_cycle_complete:
            try:
                self._on_cycle_complete(result)
            except Exception as e:
                logger.error(f"Cycle complete callback error: {e}")
        
        # Return to idle
        self._set_state(KernelState.IDLE)
        
        # Small delay for tick interval
        if self.config.tick_interval_ms > 0:
            await asyncio.sleep(self.config.tick_interval_ms / 1000.0)
        
        return result
    
    # ==========================================
    # CYCLE PHASES
    # ==========================================
    
    async def _phase_perceive(self) -> None:
        """
        Phase 1: Perceive world state.
        
        Gather state from environment.
        """
        self._set_state(KernelState.PERCEIVING)
        
        # Update time-based state
        if self._started_at:
            elapsed = (datetime.utcnow() - self._started_at).total_seconds()
            self._world_state.update({
                StateVariable.TIME_ELAPSED: elapsed,
            })
        
        # Clear significant diffs after processing
        self._world_state.clear_significant_diffs()
    
    async def _phase_update_self(self) -> None:
        """
        Phase 2: Update self model.
        
        Track cognitive state and fatigue.
        """
        state = self._world_state.get_state()
        
        # Update cognitive load in self model
        self._self_model.record_cognitive_load(state.cognitive_load)
    
    async def _phase_reason(self) -> List[Intention]:
        """
        Phase 3: Reason about situation.
        
        LAW 1: This is sandboxed - no execution.
        """
        intentions = await self._reasoning.deliberate()
        
        return intentions
    
    async def _phase_execute(self) -> List[ExecutionResult]:
        """
        Phase 5: Execute intentions.
        
        LAW 1: Execution is separate from reasoning.
        """
        results = []
        
        while self._pending_intentions:
            intention = self._pending_intentions.pop(0)
            
            # Transform intention to actions
            actions = self._execution.transform(intention)
            
            # Execute
            exec_results = await self._execution.execute(actions)
            results.extend(exec_results)
            
            # Record outcomes in self model
            for r in exec_results:
                self._self_model.record_outcome(
                    capability=f"execute_{intention.intention_type}",
                    success=r.success,
                    time_ms=r.duration_ms,
                    cost=r.cost,
                )
        
        return results
    
    async def _phase_monitor(self) -> None:
        """
        Phase 6: Monitor execution results.
        
        Observe outcomes without reasoning.
        """
        # Check for failures
        recent = self._execution.get_execution_history(limit=5)
        failures = [r for r in recent if not r.success]
        
        # Update state based on failures
        if failures:
            failure_rate = len(failures) / len(recent) if recent else 0
            
            self._world_state.update({
                StateVariable.RISK_LEVEL: min(1.0, failure_rate * 2),
            })
    
    async def _phase_learn(self) -> None:
        """
        Phase 7: Learn from experience.
        
        Update models based on outcomes.
        """
        # Calibrate self model
        self._self_model.calibrate_from_performance()
        
        # Periodic reflection
        if self._iteration % self.config.reflection_interval == 0:
            # Log statistics
            stats = self.get_stats()
            logger.info(
                f"Cycle {self._iteration}: "
                f"success_rate={stats['self_model']['performance']['overall_success_rate']:.2f}, "
                f"fatigue={stats['self_model']['cognitive']['fatigue']}"
            )
    
    # ==========================================
    # DECISION HELPERS
    # ==========================================
    
    def _needs_reasoning(self) -> bool:
        """
        Determine if reasoning is needed.
        
        LAW 2: Based on state, not events.
        """
        state = self._world_state.get_state()
        
        # State-driven triggers
        if state.needs_reconsideration():
            return True
        
        if self._world_state.significant_change_detected():
            return True
        
        # Self model triggers
        self_state = self._self_model.get_state()
        
        if self_state.fatigue_level == FatigueLevel.CRITICAL:
            return True  # Need to reason about recovery
        
        # No pending intentions
        if not self._pending_intentions:
            # Check if there's work to do
            if state.active_tasks or state.pending_decisions:
                return True
        
        return False
    
    # ==========================================
    # EXTERNAL INTERFACE
    # ==========================================
    
    async def submit_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a goal for the agent.
        
        This is the main external interface.
        """
        import uuid
        
        goal_id = f"goal-{uuid.uuid4().hex[:8]}"
        
        # Update state with new goal
        self._world_state.update({
            StateVariable.ACTIVE_TASKS: [goal_id],
        })
        
        # Add to domain state
        goal_state = self._world_state.get_state().domain_state.copy()
        goal_state["goals"] = goal_state.get("goals", {})
        goal_state["goals"][goal_id] = {
            "description": goal,
            "context": context or {},
            "submitted_at": datetime.utcnow().isoformat(),
        }
        
        self._world_state.update({}, domain_updates={"goal": goal_state["goals"]})
        
        logger.info(f"Goal submitted: {goal_id}")
        
        return goal_id
    
    async def emergency_stop(self) -> None:
        """Emergency stop - halt all execution."""
        logger.warning("EMERGENCY STOP triggered")
        
        self._pending_intentions.clear()
        
        # Cancel active executions
        for action in self._execution.get_active_executions():
            await self._execution.cancel(action.action_id)
        
        self._set_state(KernelState.RECOVERING)
    
    # ==========================================
    # STATE MANAGEMENT
    # ==========================================
    
    def _set_state(self, state: KernelState) -> None:
        """Set kernel state."""
        old_state = self._state
        self._state = state
        
        if old_state != state and self._on_state_change:
            try:
                self._on_state_change(old_state, state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")
    
    @property
    def state(self) -> KernelState:
        """Get current kernel state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if kernel is running."""
        return self._running
    
    # ==========================================
    # COMPONENT ACCESS
    # ==========================================
    
    @property
    def world_state(self) -> WorldStateManager:
        """Get world state manager."""
        return self._world_state
    
    @property
    def self_model(self) -> SelfModel:
        """Get self model."""
        return self._self_model
    
    @property
    def reasoning(self) -> ReasoningLoop:
        """Get reasoning loop."""
        return self._reasoning
    
    @property
    def execution(self) -> ExecutionEngine:
        """Get execution engine."""
        return self._execution
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_cycle_complete(self, callback: Callable[[CycleResult], None]) -> None:
        """Set callback for cycle completion."""
        self._on_cycle_complete = callback
    
    def on_state_change(self, callback: Callable[[KernelState, KernelState], None]) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive kernel statistics."""
        return {
            "kernel": {
                "state": self._state.value,
                "running": self._running,
                "iteration": self._iteration,
                "pending_intentions": len(self._pending_intentions),
            },
            "world_state": self._world_state.get_stats(),
            "self_model": self._self_model.get_stats(),
            "reasoning": self._reasoning.get_stats(),
            "execution": self._execution.get_stats(),
        }
    
    def get_cycle_history(self, limit: int = 10) -> List[CycleResult]:
        """Get recent cycle history."""
        return self._cycle_history[-limit:]


# ==========================================
# FACTORY
# ==========================================

def create_kernel(
    agent_id: str = "phoenix-main",
    agent_name: str = "Phoenix Agent",
    role: str = "general",
    safe_mode: bool = False,
) -> AgentKernel:
    """Factory for creating an agent kernel."""
    config = KernelConfig(
        agent_id=agent_id,
        agent_name=agent_name,
        role=role,
        safe_mode=safe_mode,
    )
    
    return AgentKernel(config)
