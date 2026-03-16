"""
Phoenix Agent - Cognitive Kernel
=================================

THE LIVING CORE.

This is not a collection of modules.
This is a COGNITIVE ORGANISM.

The kernel implements the 3 Laws of Agent Architecture:

Law 1: Cognition must never execute. Execution must never reason.
Law 2: State drives decisions, not events.
Law 3: Agent must continuously model itself.

Architecture:
    AgentKernel (The Living Loop)
        │
        ├── WorldStateManager (Law 2: State Authority)
        ├── SelfModel (Law 3: Continuous Self Representation)
        ├── ReasoningLoop (Law 1: Cognitive Sandbox)
        ├── ExecutionEngine (Law 1: Separate from Cognition)
        └── PlanningEngine (Strategic Intelligence)

The Kernel Loop:
    while alive:
        perceive(world_state)
        update_self_model()
        
        reason(world_state, self_model)
        plan(intention)
        
        execute(decision)
        monitor(results)
        learn(outcomes)

This transforms:
    "collection of engines" → "living cognitive organism"

Version: 3.0.0 (Cognitive Kernel)
"""

from .world_state import (
    WorldStateManager,
    WorldState,
    StateDomain,
    StateVariable,
    StateDiff,
    StateTrend,
)
from .self_model import (
    SelfModel,
    SelfState,
    PerformanceTrend,
    CapabilityState,
    FatigueLevel,
    AdaptiveParameter,
    CapabilityMetrics,
)
from .reasoning_loop import (
    ReasoningLoop,
    Intention,
    IntentionType,
    DeliberationContext,
    DeliberationStatus,
    ReasoningPhase,
    SimulationResult,
)
from .execution_engine import (
    ExecutionEngine,
    Action,
    ActionType,
    ExecutionResult,
    ExecutionStatus,
    ExecutionPriority,
    ExecutionPlan,
)
from .agent_kernel import (
    AgentKernel,
    KernelConfig,
    KernelState,
    CycleResult,
    create_kernel,
)

__all__ = [
    # World State (Law 2)
    "WorldStateManager",
    "WorldState",
    "StateDomain",
    "StateVariable",
    "StateDiff",
    "StateTrend",
    # Self Model (Law 3)
    "SelfModel",
    "SelfState",
    "PerformanceTrend",
    "CapabilityState",
    "FatigueLevel",
    "AdaptiveParameter",
    "CapabilityMetrics",
    # Reasoning (Law 1: Sandbox)
    "ReasoningLoop",
    "Intention",
    "IntentionType",
    "DeliberationContext",
    "DeliberationStatus",
    "ReasoningPhase",
    "SimulationResult",
    # Execution (Law 1: Separate)
    "ExecutionEngine",
    "Action",
    "ActionType",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionPriority",
    "ExecutionPlan",
    # Kernel
    "AgentKernel",
    "KernelConfig",
    "KernelState",
    "CycleResult",
    "create_kernel",
]
