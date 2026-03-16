"""
Phoenix Agent - Core Module
==========================

Core runtime components for Phoenix Agent.

Components (v0.3):
    - State: Session state management
    - AgentLoop: Think → Act → Observe cycle
    - ContextBuilder: Build prompts with context
    - Orchestrator: Main entry point

Components (v0.4):
    - Task: Task abstraction for multi-agent
    - TaskManager: Task decomposition and orchestration
    - DelegationEngine: Sub-agent delegation (structure)
    - MemoryManager: Context window management (structure)
    - SubAgent: Sub-agent runner (structure)

Components (v0.5):
    - AgentProfile: Agent self-model with cognitive limits
    - CapabilityMonitor: Real-time capability monitoring
    - Capability: Agent capability model
    - DelegationTrigger: Cognitive delegation triggers

Components (v0.6 - Runtime Abstractions):
    - AgentStateMachine: Execution state transitions (IDLE→THINKING→ACTING→...)
    - ExecutionContext: Task execution tracing and delegation chain
    - AgentProtocol: Agent communication protocol (AgentMessage, MessageBus)
    - CognitiveMemoryManager: Active memory strategies (compress, summarize, prune)
    - RecoveryEngine: Failure recovery and fallback strategies

IMPORTANT:
    - Phoenix ne contient AUCUNE logique LLM
    - Phoenix délègue TOUT à la gateway
    - Phoenix est un runtime COGNITIF, pas un simple task runner
"""

# ==========================================
# v0.3 - BASE KERNEL
# ==========================================

from .state import (
    SessionState,
    SessionManager,
)

from .context_builder import (
    ContextBuilder,
    ContextOptions,
)

from .agent_loop import (
    AgentLoop,
    AgentLoopResult,
)

from .orchestrator import (
    PhoenixOrchestrator,
    RunResult,
    create_orchestrator,
)


# ==========================================
# v0.4 - TASK ABSTRACTION
# ==========================================

from .task import (
    # Core
    Task,
    TaskResult,
    TaskPlan,
    
    # Enums
    TaskStatus,
    TaskPriority,
    TaskComplexity,
    TaskType,
)

from .task_manager import (
    TaskManager,
    TaskAnalysis,
    ComplexityAnalyzer,
    TaskTypeClassifier,
    TaskDecomposer,
)


# ==========================================
# v0.4 - DELEGATION (Structure)
# ==========================================

from .delegation import (
    # Core
    DelegationEngine,
    DelegationRequest,
    DelegationResponse,
    
    # Types
    AgentRole,
    AgentCapability,
    SubAgentInfo,
)


# ==========================================
# v0.4 - MEMORY MANAGER (Structure)
# ==========================================

from .memory_manager import (
    MemoryManager,
    MemoryManagerConfig,
    MemoryWindow,
    MemoryStats,
    MemoryAnalysis,
    MemoryStrategy,
)


# ==========================================
# v0.4 - SUB-AGENT (Structure)
# ==========================================

from .subagent import (
    SubAgent,
    SubAgentConfig,
    SubAgentResult,
    SubAgentStatus,
    SubAgentPool,
)


# ==========================================
# v0.5 - AGENT PROFILE (Self-Model)
# ==========================================

from .agent_profile import (
    # Core
    AgentProfile,
    AgentState,
    AgentType,
    
    # Factories
    create_default_profile,
    create_specialist_profile,
)


# ==========================================
# v0.5 - CAPABILITY MODEL
# ==========================================

from .capability import (
    # Core
    AgentCapability,
    CapabilityLimits,
    CapabilityResources,
    CapabilityCost,
    CapabilityAssessment,
    CapabilityRegistry,
    
    # Enums
    Domain,
    ResourceType,
)


# ==========================================
# v0.5 - CAPABILITY MONITOR (Self-Awareness)
# ==========================================

from .capability_monitor import (
    # Core
    CapabilityMonitor,
    MonitoringResult,
    MonitoringDecision,
    MonitoringConfig,
    
    # Triggers
    DelegationTrigger,
)


# ==========================================
# v0.6 - DECISION ENGINE (Cognitive Decisions)
# ==========================================

from .decision_engine import (
    # Core
    DecisionEngine,
    CognitiveDecision,
    DecisionContext,
    DecisionResult,
    DecisionRule,
)


# ==========================================
# v0.6 - DELEGATION POLICY (Trigger → Action)
# ==========================================

from .delegation_policy import (
    # Core
    DelegationPolicy,
    DelegationStrategy,
    DelegationAction,
    TargetAgentType,
    PolicyBuilder,
)


# ==========================================
# v0.6 - AGENT ROLE (Specialization)
# ==========================================

from .agent_role import (
    # Core
    AgentRole,
    AgentRoleType,
    RoleCategory,
    RoleRegistry,
    
    # Helpers
    get_predefined_roles,
)


# ==========================================
# v0.6 - RESULT SYNTHESIZER (Multi-Agent Fusion)
# ==========================================

from .result_synthesizer import (
    # Core
    ResultSynthesizer,
    SynthesisStrategy,
    AgentResult,
    SynthesisResult,
    
    # Helpers
    synthesize_results,
)


# ==========================================
# v0.6 - AGENT STATE MACHINE (Execution Control)
# ==========================================

from .agent_state_machine import (
    # Core
    AgentStateMachine,
    AgentExecutionState,
    StateTransition,
    TransitionRule,
    
    # Enums
    StateCategory,
    
    # Exceptions
    InvalidStateTransitionError,
    
    # Factory
    create_state_machine,
)


# ==========================================
# v0.6 - EXECUTION CONTEXT (Task Tracing)
# ==========================================

from .execution_context import (
    # Core
    ExecutionContext,
    ExecutionSpan,
    ExecutionTraceEvent,
    DelegationChain,
    
    # Enums
    ExecutionStatus,
    ExecutionEventType,
    
    # Manager
    ExecutionContextManager,
    
    # Factory
    create_execution_context,
)


# ==========================================
# v0.6 - AGENT PROTOCOL (Communication)
# ==========================================

from .agent_protocol import (
    # Core
    AgentMessage,
    MessageHeader,
    MessagePayload,
    MessageAck,
    MessageBus,
    
    # Enums
    MessageType,
    MessagePriority,
    MessageStatus,
    
    # Factories
    create_message,
    create_delegation_message,
    create_response_message,
)


# ==========================================
# v0.6 - COGNITIVE MEMORY MANAGER (Active Memory)
# ==========================================

from .cognitive_memory import (
    # Core
    CognitiveMemoryManager,
    MemoryItem,
    MemorySnapshot,
    MemoryStats,
    CompressionResult,
    
    # Config
    MemoryManagerConfig,
    
    # Enums
    # MemoryStrategy already imported from v0.4
    
    # Factory
    create_memory_manager,
)


# ==========================================
# v0.6 - RECOVERY ENGINE (Failure Handling)
# ==========================================

from .recovery_engine import (
    # Core
    RecoveryEngine,
    ErrorContext,
    RecoveryResult,
    RecoveryRule,
    
    # Enums
    ErrorType,
    RecoveryStrategy,
    
    # Factory
    create_recovery_engine,
)


# ==========================================
# v0.8 - RUNTIME CONTROLLER (Integration Layer)
# ==========================================

from .runtime_controller import (
    # Core
    AgentRuntimeController,
    RuntimeConfig,
    RuntimeStatus,
    CycleResult,
    ExecutionCycle,
    
    # Factory
    create_runtime_controller,
)


# ==========================================
# v0.8 - PLANNER ENGINE (Strategic Planning)
# ==========================================

from .planner_engine import (
    # Core
    PlannerEngine,
    PlanGraph,
    PlanStep,
    PlanStatus,
    StepStatus,
    
    # Context
    PlanningContext,
    
    # Enums
    DecompositionStrategy,
    
    # Helpers
    create_plan,
    plan_goal,
)


# ==========================================
# v0.8 - TELEMETRY (Observability)
# ==========================================

from .telemetry import (
    # Core
    AgentTelemetry,
    TelemetryConfig,
    TelemetryEvent,
    Metric,
    TraceSpan,
    HealthCheck,
    
    # Collectors
    MetricsCollector,
    EventLogger,
    TraceCollector,
    HealthMonitor,
    
    # Enums
    MetricType,
    EventType,
    
    # Factory
    create_telemetry,
)


# ==========================================
# v1.0 - GOAL MANAGER (Persistent Objectives)
# ==========================================

from .goal_manager import (
    # Core
    GoalManager,
    Goal,
    SuccessCriterion,
    GoalConstraint,
    GoalManagerConfig,
    
    # Enums
    GoalStatus,
    GoalPriority,
    GoalType,
    
    # Factory
    create_goal_manager,
)


# ==========================================
# v1.0 - RESOURCE MANAGER (Runtime Control)
# ==========================================

from .resource_manager import (
    # Core
    ResourceManager,
    ResourceBudget,
    ResourceAllocation,
    ResourceRequest,
    ResourceManagerConfig,
    
    # Enums
    ResourceType,
    EnforcementStrategy,
    AllocationStatus,
    
    # Factory
    create_resource_manager,
)


# ==========================================
# v1.0 - LEARNING LOOP (Cognitive Feedback)
# ==========================================

from .learning_loop import (
    # Core
    LearningLoop,
    CognitiveFeedback,
    PatternRecord,
    StrategyRecord,
    LearningConfig,
    
    # Enums
    OutcomeType,
    LearningCategory,
    
    # Factory
    create_learning_loop,
)


# ==========================================
# v1.0 - AGENT REGISTRY (Population Management)
# ==========================================

from .agent_registry import (
    # Core
    AgentRegistry,
    AgentIdentity,
    AgentCapabilityRecord,
    AgentRegistryConfig,
    
    # Enums
    AgentHealthStatus,
    AgentRoleCategory,
    
    # Factory
    create_agent_registry,
    create_agent_identity,
)


# ==========================================
# v1.0 - TASK GRAPH EXECUTOR (Execution Intelligence)
# ==========================================

from .task_graph_executor import (
    # Core
    TaskGraphExecutor,
    TaskGraph,
    TaskNode,
    ExecutorConfig,
    
    # Enums
    NodeStatus,
    GraphStatus,
    ExecutionStrategy,
    
    # Factory
    create_task_graph_executor,
    create_task_graph,
)


# ==========================================
# v1.0 - ADAPTATION ENGINE (Self Evolution)
# ==========================================

from .adaptation_engine import (
    # Core
    AdaptationEngine,
    AdaptationRecord,
    AdaptationRule,
    AdaptationConfig,
    
    # Enums
    AdaptationType,
    AdaptationTrigger,
    AdaptationStatus,
    
    # Factory
    create_adaptation_engine,
)


# ==========================================
# v1.2 - EXECUTION PIPELINE (Runtime Integration)
# ==========================================

from .execution_pipeline import (
    # Core
    ExecutionPipeline,
    PipelineContext,
    PipelineStage,
    PipelineStatus,
    StageResult,
    PipelineConfig,
    
    # Factory
    create_execution_pipeline,
)


# ==========================================
# v1.2 - AGENT LIFECYCLE (State Machine)
# ==========================================

from .agent_lifecycle import (
    # Core
    AgentLifecycle,
    LifecycleState,
    LifecycleCategory,
    StateTransition,
    LifecycleManager,
    
    # Constants
    VALID_TRANSITIONS,
    STATE_CATEGORIES,
    
    # Factory
    create_lifecycle,
    get_lifecycle_state_category,
)


__all__ = [
    # v0.3 - Base Kernel
    "SessionState",
    "SessionManager",
    "ContextBuilder",
    "ContextOptions",
    "AgentLoop",
    "AgentLoopResult",
    "PhoenixOrchestrator",
    "RunResult",
    "create_orchestrator",
    
    # v0.4 - Task Abstraction
    "Task",
    "TaskResult",
    "TaskPlan",
    "TaskStatus",
    "TaskPriority",
    "TaskComplexity",
    "TaskType",
    
    # v0.4 - Task Manager
    "TaskManager",
    "TaskAnalysis",
    "ComplexityAnalyzer",
    "TaskTypeClassifier",
    "TaskDecomposer",
    
    # v0.4 - Delegation
    "DelegationEngine",
    "DelegationRequest",
    "DelegationResponse",
    "AgentRole",
    "AgentCapability",
    "SubAgentInfo",
    
    # v0.4 - Memory Manager
    "MemoryManager",
    "MemoryManagerConfig",
    "MemoryWindow",
    "MemoryStats",
    "MemoryAnalysis",
    "MemoryStrategy",
    
    # v0.4 - Sub-Agent
    "SubAgent",
    "SubAgentConfig",
    "SubAgentResult",
    "SubAgentStatus",
    "SubAgentPool",
    
    # v0.5 - Agent Profile
    "AgentProfile",
    "AgentState",
    "AgentType",
    "create_default_profile",
    "create_specialist_profile",
    
    # v0.5 - Capability Model
    "CapabilityLimits",
    "CapabilityResources",
    "CapabilityCost",
    "CapabilityAssessment",
    "CapabilityRegistry",
    "Domain",
    "ResourceType",
    
    # v0.5 - Capability Monitor
    "CapabilityMonitor",
    "MonitoringResult",
    "MonitoringDecision",
    "MonitoringConfig",
    "DelegationTrigger",
    
    # v0.6 - Decision Engine
    "DecisionEngine",
    "CognitiveDecision",
    "DecisionContext",
    "DecisionResult",
    
    # v0.6 - Delegation Policy
    "DelegationPolicy",
    "DelegationStrategy",
    "DelegationAction",
    "TargetAgentType",
    
    # v0.6 - Agent Role
    "AgentRole",
    "AgentRoleType",
    "RoleCategory",
    "RoleRegistry",
    
    # v0.6 - Result Synthesizer
    "ResultSynthesizer",
    "SynthesisStrategy",
    "AgentResult",
    "SynthesisResult",
    
    # v0.6 - Agent State Machine
    "AgentStateMachine",
    "AgentExecutionState",
    "StateTransition",
    "TransitionRule",
    "StateCategory",
    "InvalidStateTransitionError",
    "create_state_machine",
    
    # v0.6 - Execution Context
    "ExecutionContext",
    "ExecutionSpan",
    "ExecutionTraceEvent",
    "DelegationChain",
    "ExecutionStatus",
    "ExecutionEventType",
    "ExecutionContextManager",
    "create_execution_context",
    
    # v0.6 - Agent Protocol
    "AgentMessage",
    "MessageHeader",
    "MessagePayload",
    "MessageAck",
    "MessageBus",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "create_message",
    "create_delegation_message",
    "create_response_message",
    
    # v0.6 - Cognitive Memory
    "CognitiveMemoryManager",
    "MemoryItem",
    "MemorySnapshot",
    "CompressionResult",
    "create_memory_manager",
    
    # v0.6 - Recovery Engine
    "RecoveryEngine",
    "ErrorContext",
    "RecoveryResult",
    "RecoveryRule",
    "ErrorType",
    "RecoveryStrategy",
    "create_recovery_engine",
    
    # v0.8 - Runtime Controller
    "AgentRuntimeController",
    "RuntimeConfig",
    "RuntimeStatus",
    "CycleResult",
    "ExecutionCycle",
    "create_runtime_controller",
    
    # v0.8 - Planner Engine
    "PlannerEngine",
    "PlanGraph",
    "PlanStep",
    "PlanStatus",
    "StepStatus",
    "PlanningContext",
    "DecompositionStrategy",
    "create_plan",
    "plan_goal",
    
    # v0.8 - Telemetry
    "AgentTelemetry",
    "TelemetryConfig",
    "TelemetryEvent",
    "Metric",
    "TraceSpan",
    "HealthCheck",
    "MetricsCollector",
    "EventLogger",
    "TraceCollector",
    "HealthMonitor",
    "MetricType",
    "EventType",
    "create_telemetry",
    
    # v1.0 - Goal Manager
    "GoalManager",
    "Goal",
    "GoalStatus",
    "GoalPriority",
    "GoalType",
    "SuccessCriterion",
    "GoalConstraint",
    "GoalManagerConfig",
    "create_goal_manager",
    
    # v1.0 - Resource Manager
    "ResourceManager",
    "ResourceBudget",
    "ResourceAllocation",
    "ResourceRequest",
    "ResourceManagerConfig",
    "ResourceType",
    "EnforcementStrategy",
    "AllocationStatus",
    "create_resource_manager",
    
    # v1.0 - Learning Loop
    "LearningLoop",
    "CognitiveFeedback",
    "PatternRecord",
    "StrategyRecord",
    "LearningConfig",
    "OutcomeType",
    "LearningCategory",
    "create_learning_loop",
    
    # v1.0 - Agent Registry
    "AgentRegistry",
    "AgentIdentity",
    "AgentCapabilityRecord",
    "AgentRegistryConfig",
    "AgentHealthStatus",
    "AgentRoleCategory",
    "create_agent_registry",
    "create_agent_identity",
    
    # v1.0 - Task Graph Executor
    "TaskGraphExecutor",
    "TaskGraph",
    "TaskNode",
    "ExecutorConfig",
    "NodeStatus",
    "GraphStatus",
    "ExecutionStrategy",
    "create_task_graph_executor",
    "create_task_graph",
    
    # v1.0 - Adaptation Engine
    "AdaptationEngine",
    "AdaptationRecord",
    "AdaptationRule",
    "AdaptationConfig",
    "AdaptationType",
    "AdaptationTrigger",
    "AdaptationStatus",
    "create_adaptation_engine",
    
    # v1.2 - Execution Pipeline
    "ExecutionPipeline",
    "PipelineContext",
    "PipelineStage",
    "PipelineStatus",
    "StageResult",
    "PipelineConfig",
    "create_execution_pipeline",
    
    # v1.2 - Agent Lifecycle
    "AgentLifecycle",
    "LifecycleState",
    "LifecycleCategory",
    "StateTransition",
    "LifecycleManager",
    "VALID_TRANSITIONS",
    "STATE_CATEGORIES",
    "create_lifecycle",
    "get_lifecycle_state_category",
]
