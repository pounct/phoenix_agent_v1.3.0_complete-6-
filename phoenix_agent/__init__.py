"""
Phoenix Agent - Model-Agnostic Agent Runtime
=============================================

Phoenix est un **Model-Agnostic Agent Runtime Engine**.

THE KEY INSIGHT (v1.3):
    Phoenix does NOT depend on an LLM.
    Phoenix depends on COGNITIVE CAPABILITIES.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    MODEL PROVIDERS                          │
    │                                                              │
    │   OpenAI    Ollama    vLLM    Gemini    Claude    Local     │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │               COGNITIVE INTERFACE LAYER (v1.3)              │
    │                                                              │
    │   CognitiveEngine                                           │
    │   ├── reason()      - Logical reasoning                     │
    │   ├── plan()        - Strategic planning                    │
    │   ├── evaluate()    - Result evaluation                     │
    │   ├── summarize()   - Content summarization                 │
    │   ├── reflect()     - Self-reflection                       │
    │   └── decide()      - Decision making                       │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  PHOENIX RUNTIME                            │
    │                                                              │
    │   Platform Layer (v1.1)                                     │
    │   ├── SafetyEngine      ← Guardrails & Safety Controls      │
    │   ├── EnvironmentAdapter ← External System Integration      │
    │   └── ToolExecutor      ← Action Execution Layer            │
    │                                                              │
    │   Cognitive Kernel (v0.3 - v1.0)                            │
    │   ├── AgentRuntimeController ← The Conductor                │
    │   ├── GoalManager         ← Persistent Objectives           │
    │   ├── PlannerEngine       ← Strategic Planning              │
    │   ├── DecisionEngine      ← Reactive Decisions              │
    │   ├── ResourceManager     ← Budget Control                  │
    │   ├── LearningLoop        ← Cognitive Feedback              │
    │   ├── AdaptationEngine    ← Self-Evolution                  │
    │   ├── AgentRegistry       ← Population Management           │
    │   └── TaskGraphExecutor   ← Graph Execution                 │
    │                                                              │
    │   Task System (v1.3)                                        │
    │   ├── TaskEntity        ← Internal work units               │
    │   ├── TaskIdentity      ← Full traceability                 │
    │   ├── TaskLifecycle     ← State management                  │
    │   └── RequestParser     ← Request→Task conversion           │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

RÈGLES:
    - Phoenix does NOT depend on any specific LLM
    - Phoenix uses CognitiveEngine (model-agnostic abstraction)
    - Phoenix operates on Tasks, not Requests
    - Phoenix has full task traceability and cost tracking
    - Phoenix is portable, independent, future-proof

Version: 1.3.0 (Model-Agnostic Architecture)

Example:
    from phoenix_agent import (
        # Platform Layer
        ToolExecutor, EnvironmentAdapter, SafetyEngine,
        
        # Cognitive Kernel
        AgentRuntimeController, GoalManager, PlannerEngine,
        
        # Core
        PhoenixOrchestrator, create_orchestrator,
    )
    
    # Create platform components
    safety = SafetyEngine()
    env = EnvironmentAdapter()
    tools = ToolExecutor()
    
    # Create cognitive kernel
    controller = AgentRuntimeController()
    
    # Run agent
    result = await controller.run(task)
"""

__version__ = "1.3.0"
__author__ = "Phoenix Team"


# ==========================================
# CONFIG
# ==========================================

from .config import (
    PhoenixConfig,
    GatewayConfig,
    AgentConfig,
    get_config,
    set_config,
    reset_config,
    LogLevel,
)


# ==========================================
# CONTRACT
# ==========================================

from .contract.schemas import (
    # Gateway native
    GenerateRequest,
    GenerateResponse,
    ErrorResponse,
    
    # Types
    ProviderName,
    FALLBACK_PROVIDERS,
    POPULAR_MODELS,
    DEFAULT_MODEL,
)

from .contract.events import (
    # Events
    AgentEvent,
    ThinkEvent,
    ActEvent,
    ObserveEvent,
    CompleteEvent,
    ErrorEvent,
    EventType,
    event_to_sse,
)

from .contract.session import (
    # Session
    Message,
    Session,
    SessionStatus,
    SessionResult,
)


# ==========================================
# STATE
# ==========================================

from .core.state import (
    SessionState,
    SessionManager,
)


# ==========================================
# CONTEXT
# ==========================================

from .core.context_builder import (
    ContextBuilder,
    ContextOptions,
)


# ==========================================
# AGENT LOOP
# ==========================================

from .core.agent_loop import (
    AgentLoop,
    AgentLoopResult,
)


# ==========================================
# ORCHESTRATOR
# ==========================================

from .core.orchestrator import (
    PhoenixOrchestrator,
    RunResult,
    create_orchestrator,
)


# ==========================================
# GATEWAY
# ==========================================

from .gateway.adapter import (
    GatewayAdapter,
    HTTPGatewayAdapter,
    MockGatewayAdapter,
    create_gateway_adapter,
)


# ==========================================
# v0.4 - TASK ABSTRACTION
# ==========================================

from .core.task import (
    Task,
    TaskResult,
    TaskPlan,
    TaskStatus,
    TaskPriority,
    TaskComplexity,
    TaskType,
)

from .core.task_manager import (
    TaskManager,
    TaskAnalysis,
    ComplexityAnalyzer,
    TaskTypeClassifier,
    TaskDecomposer,
)

from .core.delegation import (
    DelegationEngine,
    DelegationRequest,
    DelegationResponse,
    AgentRole,
    AgentCapability,
    SubAgentInfo,
)

from .core.memory_manager import (
    MemoryManager,
    MemoryManagerConfig,
    MemoryWindow,
    MemoryStats,
    MemoryAnalysis,
    MemoryStrategy,
)

from .core.subagent import (
    SubAgent,
    SubAgentConfig,
    SubAgentResult,
    SubAgentStatus,
    SubAgentPool,
)


# ==========================================
# v0.5 - COGNITIVE SELF-AWARENESS
# ==========================================

from .core.agent_profile import (
    AgentProfile,
    AgentState,
    AgentType,
    create_default_profile,
    create_specialist_profile,
)

from .core.capability import (
    AgentCapability,
    CapabilityLimits,
    CapabilityResources,
    CapabilityCost,
    CapabilityAssessment,
    CapabilityRegistry,
    Domain,
    ResourceType,
)

from .core.capability_monitor import (
    CapabilityMonitor,
    MonitoringResult,
    MonitoringDecision,
    MonitoringConfig,
    DelegationTrigger,
)


# ==========================================
# v0.6 - RUNTIME ABSTRACTIONS
# ==========================================

from .core.agent_state_machine import (
    AgentStateMachine,
    AgentExecutionState,
    StateTransition,
    TransitionRule,
    StateCategory,
    InvalidStateTransitionError,
    create_state_machine,
)

from .core.execution_context import (
    ExecutionContext,
    ExecutionSpan,
    ExecutionTraceEvent,
    DelegationChain,
    ExecutionStatus,
    ExecutionEventType,
    ExecutionContextManager,
    create_execution_context,
)

from .core.agent_protocol import (
    AgentMessage,
    MessageHeader,
    MessagePayload,
    MessageAck,
    MessageBus,
    MessageType,
    MessagePriority,
    MessageStatus,
    create_message,
    create_delegation_message,
    create_response_message,
)

from .core.cognitive_memory import (
    CognitiveMemoryManager,
    MemoryItem,
    MemorySnapshot,
    CompressionResult,
    create_memory_manager,
)

from .core.recovery_engine import (
    RecoveryEngine,
    ErrorContext,
    RecoveryResult,
    RecoveryRule,
    ErrorType,
    RecoveryStrategy,
    create_recovery_engine,
)

from .core.decision_engine import (
    DecisionEngine,
    CognitiveDecision,
    DecisionContext,
    DecisionResult,
    DecisionRule,
)

from .core.delegation_policy import (
    DelegationPolicy,
    DelegationStrategy,
    DelegationAction,
    TargetAgentType,
    PolicyBuilder,
)

from .core.agent_role import (
    AgentRole,
    AgentRoleType,
    RoleCategory,
    RoleRegistry,
    get_predefined_roles,
)

from .core.result_synthesizer import (
    ResultSynthesizer,
    SynthesisStrategy,
    AgentResult,
    SynthesisResult,
    synthesize_results,
)


# ==========================================
# v0.8 - RUNTIME INTEGRATION LAYER
# ==========================================

from .core.runtime_controller import (
    AgentRuntimeController,
    RuntimeConfig,
    RuntimeStatus,
    CycleResult,
    ExecutionCycle,
    create_runtime_controller,
)

from .core.planner_engine import (
    PlannerEngine,
    PlanGraph,
    PlanStep,
    PlanStatus,
    StepStatus,
    PlanningContext,
    DecompositionStrategy,
    create_plan,
    plan_goal,
)

from .core.telemetry import (
    AgentTelemetry,
    TelemetryConfig,
    TelemetryEvent,
    Metric,
    TraceSpan,
    HealthCheck,
    MetricsCollector,
    EventLogger,
    TraceCollector,
    HealthMonitor,
    MetricType,
    EventType,
    create_telemetry,
)


# ==========================================
# v1.0 - COGNITIVE DEEP LAYERS
# ==========================================

from .core.goal_manager import (
    GoalManager,
    Goal,
    SuccessCriterion,
    GoalConstraint,
    GoalManagerConfig,
    GoalStatus,
    GoalPriority,
    GoalType,
    create_goal_manager,
)

from .core.resource_manager import (
    ResourceManager,
    ResourceBudget,
    ResourceAllocation,
    ResourceRequest,
    ResourceManagerConfig,
    EnforcementStrategy,
    AllocationStatus,
    create_resource_manager,
)

from .core.learning_loop import (
    LearningLoop,
    CognitiveFeedback,
    PatternRecord,
    StrategyRecord,
    LearningConfig,
    OutcomeType,
    LearningCategory,
    create_learning_loop,
)


# ==========================================
# v1.0 FINAL - SELF-ORGANIZATION LAYER
# ==========================================

from .core.agent_registry import (
    AgentRegistry,
    AgentIdentity,
    AgentCapabilityRecord,
    AgentRegistryConfig,
    AgentHealthStatus,
    AgentRoleCategory,
    create_agent_registry,
    create_agent_identity,
)

from .core.task_graph_executor import (
    TaskGraphExecutor,
    TaskGraph,
    TaskNode,
    ExecutorConfig,
    NodeStatus,
    GraphStatus,
    ExecutionStrategy,
    create_task_graph_executor,
    create_task_graph,
)

from .core.adaptation_engine import (
    AdaptationEngine,
    AdaptationRecord,
    AdaptationRule,
    AdaptationConfig,
    AdaptationType,
    AdaptationTrigger,
    AdaptationStatus,
    create_adaptation_engine,
)


# ==========================================
# v1.1 - PLATFORM LAYER (System Interface)
# ==========================================

from .platform.tool_executor import (
    ToolExecutor,
    Tool,
    ToolResult,
    ToolContext,
    ToolRegistry,
    ToolExecutorConfig,
    ToolStatus,
    ToolCategory,
    ExecutionMode,
    create_tool_executor,
    register_tool,
)

from .platform.environment_adapter import (
    EnvironmentAdapter,
    EnvironmentConfig,
    EnvironmentStatus,
    LLMGatewayConnection,
    DatabaseConnection,
    APIConnection,
    FileSystemConnection,
    QueueConnection,
    ConnectionType,
    ConnectionStatus,
    create_environment_adapter,
)

from .platform.safety_engine import (
    SafetyEngine,
    SafetyCheckResult,
    SafetyViolation,
    Guardrails,
    SafetyConfig,
    SafetyLevel,
    ViolationType,
    ViolationSeverity,
    create_safety_engine,
)


# ==========================================
# v1.3 - MODEL-AGNOSTIC COGNITIVE LAYER
# ==========================================

from .cognitive.engine import (
    CognitiveEngine,
    CognitiveConfig,
    CognitiveCapability,
    CognitiveResult,
    ReasoningRequest,
    ReasoningResult,
    PlanningRequest,
    PlanningResult,
    EvaluationRequest,
    EvaluationResult,
    SummarizationRequest,
    SummarizationResult,
    ReflectionRequest,
    ReflectionResult,
    DecisionRequest,
    DecisionResult,
    create_cognitive_engine,
)

from .cognitive.adapters import (
    CognitiveAdapter,
    AdapterConfig,
    AdapterStatus,
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    MockCognitiveAdapter,
    create_adapter,
    create_adapter_from_config,
)

from .cognitive.task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycle,
    TaskLifecycleState,
    TaskHistory,
    TaskCost,
    TaskDependency,
    TaskDependencyType,
    create_task_entity,
    create_task_identity,
)

from .cognitive.request_parser import (
    RequestParser,
    TaskBuilder,
    RequestAnalysis,
    RequestType,
    RequestIntent,
    RequestComplexity,
    create_request_parser,
    create_task_builder,
)


# ==========================================
# v1.2 - RUNTIME INTEGRATION (Execution Cohesion)
# ==========================================

from .core.execution_pipeline import (
    ExecutionPipeline,
    PipelineContext,
    PipelineStage,
    PipelineStatus,
    StageResult,
    PipelineConfig,
    create_execution_pipeline,
)

from .core.agent_lifecycle import (
    AgentLifecycle,
    LifecycleState,
    LifecycleCategory,
    StateTransition,
    LifecycleManager,
    VALID_TRANSITIONS,
    STATE_CATEGORIES,
    create_lifecycle,
    get_lifecycle_state_category,
)


__all__ = [
    # Version
    "__version__",
    
    # Config
    "PhoenixConfig",
    "GatewayConfig",
    "AgentConfig",
    "get_config",
    "set_config",
    "reset_config",
    "LogLevel",
    
    # Contract - Schemas
    "GenerateRequest",
    "GenerateResponse",
    "ErrorResponse",
    "ProviderName",
    "FALLBACK_PROVIDERS",
    "POPULAR_MODELS",
    "DEFAULT_MODEL",
    
    # Contract - Events
    "AgentEvent",
    "ThinkEvent",
    "ActEvent",
    "ObserveEvent",
    "CompleteEvent",
    "ErrorEvent",
    "EventType",
    "event_to_sse",
    
    # Contract - Session
    "Message",
    "Session",
    "SessionStatus",
    "SessionResult",
    
    # Core
    "SessionState",
    "SessionManager",
    "ContextBuilder",
    "ContextOptions",
    "AgentLoop",
    "AgentLoopResult",
    "PhoenixOrchestrator",
    "RunResult",
    "create_orchestrator",
    
    # Gateway
    "GatewayAdapter",
    "HTTPGatewayAdapter",
    "MockGatewayAdapter",
    "create_gateway_adapter",
    
    # v0.4 - Task
    "Task",
    "TaskResult",
    "TaskPlan",
    "TaskStatus",
    "TaskPriority",
    "TaskComplexity",
    "TaskType",
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
    
    # v0.4 - Memory
    "MemoryManager",
    "MemoryManagerConfig",
    "MemoryWindow",
    "MemoryStats",
    "MemoryAnalysis",
    "MemoryStrategy",
    
    # v0.4 - SubAgent
    "SubAgent",
    "SubAgentConfig",
    "SubAgentResult",
    "SubAgentStatus",
    "SubAgentPool",
    
    # v0.5 - Cognitive
    "AgentProfile",
    "AgentState",
    "AgentType",
    "create_default_profile",
    "create_specialist_profile",
    "CapabilityLimits",
    "CapabilityResources",
    "CapabilityCost",
    "CapabilityAssessment",
    "CapabilityRegistry",
    "Domain",
    "ResourceType",
    "CapabilityMonitor",
    "MonitoringResult",
    "MonitoringDecision",
    "MonitoringConfig",
    "DelegationTrigger",
    
    # v0.6 - Runtime Abstractions
    "AgentStateMachine",
    "AgentExecutionState",
    "StateTransition",
    "TransitionRule",
    "StateCategory",
    "InvalidStateTransitionError",
    "create_state_machine",
    "ExecutionContext",
    "ExecutionSpan",
    "ExecutionTraceEvent",
    "DelegationChain",
    "ExecutionStatus",
    "ExecutionEventType",
    "ExecutionContextManager",
    "create_execution_context",
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
    "CognitiveMemoryManager",
    "MemoryItem",
    "MemorySnapshot",
    "CompressionResult",
    "create_memory_manager",
    "RecoveryEngine",
    "ErrorContext",
    "RecoveryResult",
    "RecoveryRule",
    "ErrorType",
    "RecoveryStrategy",
    "create_recovery_engine",
    "DecisionEngine",
    "CognitiveDecision",
    "DecisionContext",
    "DecisionResult",
    "DecisionRule",
    "DelegationPolicy",
    "DelegationStrategy",
    "DelegationAction",
    "TargetAgentType",
    "PolicyBuilder",
    "AgentRole",
    "AgentRoleType",
    "RoleCategory",
    "RoleRegistry",
    "get_predefined_roles",
    "ResultSynthesizer",
    "SynthesisStrategy",
    "AgentResult",
    "SynthesisResult",
    "synthesize_results",
    
    # v0.8 - Integration Layer
    "AgentRuntimeController",
    "RuntimeConfig",
    "RuntimeStatus",
    "CycleResult",
    "ExecutionCycle",
    "create_runtime_controller",
    "PlannerEngine",
    "PlanGraph",
    "PlanStep",
    "PlanStatus",
    "StepStatus",
    "PlanningContext",
    "DecompositionStrategy",
    "create_plan",
    "plan_goal",
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
    
    # v1.0 - Cognitive Deep Layers
    "GoalManager",
    "Goal",
    "SuccessCriterion",
    "GoalConstraint",
    "GoalManagerConfig",
    "GoalStatus",
    "GoalPriority",
    "GoalType",
    "create_goal_manager",
    "ResourceManager",
    "ResourceBudget",
    "ResourceAllocation",
    "ResourceRequest",
    "ResourceManagerConfig",
    "EnforcementStrategy",
    "AllocationStatus",
    "create_resource_manager",
    "LearningLoop",
    "CognitiveFeedback",
    "PatternRecord",
    "StrategyRecord",
    "LearningConfig",
    "OutcomeType",
    "LearningCategory",
    "create_learning_loop",
    
    # v1.0 Final - Self-Organization
    "AgentRegistry",
    "AgentIdentity",
    "AgentCapabilityRecord",
    "AgentRegistryConfig",
    "AgentHealthStatus",
    "AgentRoleCategory",
    "create_agent_registry",
    "create_agent_identity",
    "TaskGraphExecutor",
    "TaskGraph",
    "TaskNode",
    "ExecutorConfig",
    "NodeStatus",
    "GraphStatus",
    "ExecutionStrategy",
    "create_task_graph_executor",
    "create_task_graph",
    "AdaptationEngine",
    "AdaptationRecord",
    "AdaptationRule",
    "AdaptationConfig",
    "AdaptationType",
    "AdaptationTrigger",
    "AdaptationStatus",
    "create_adaptation_engine",
    
    # v1.1 - Platform Layer
    "ToolExecutor",
    "Tool",
    "ToolResult",
    "ToolContext",
    "ToolRegistry",
    "ToolExecutorConfig",
    "ToolStatus",
    "ToolCategory",
    "ExecutionMode",
    "create_tool_executor",
    "register_tool",
    "EnvironmentAdapter",
    "EnvironmentConfig",
    "EnvironmentStatus",
    "LLMGatewayConnection",
    "DatabaseConnection",
    "APIConnection",
    "FileSystemConnection",
    "QueueConnection",
    "ConnectionType",
    "ConnectionStatus",
    "create_environment_adapter",
    "SafetyEngine",
    "SafetyCheckResult",
    "SafetyViolation",
    "Guardrails",
    "SafetyConfig",
    "SafetyLevel",
    "ViolationType",
    "ViolationSeverity",
    "create_safety_engine",
    
    # v1.2 - Runtime Integration
    "ExecutionPipeline",
    "PipelineContext",
    "PipelineStage",
    "PipelineStatus",
    "StageResult",
    "PipelineConfig",
    "create_execution_pipeline",
    "AgentLifecycle",
    "LifecycleState",
    "LifecycleCategory",
    "StateTransition",
    "LifecycleManager",
    "VALID_TRANSITIONS",
    "STATE_CATEGORIES",
    "create_lifecycle",
    "get_lifecycle_state_category",
    
    # v1.3 - Model-Agnostic Cognitive Layer
    "CognitiveEngine",
    "CognitiveConfig",
    "CognitiveCapability",
    "CognitiveResult",
    "ReasoningRequest",
    "ReasoningResult",
    "PlanningRequest",
    "PlanningResult",
    "EvaluationRequest",
    "EvaluationResult",
    "SummarizationRequest",
    "SummarizationResult",
    "ReflectionRequest",
    "ReflectionResult",
    "DecisionRequest",
    "DecisionResult",
    "create_cognitive_engine",
    "CognitiveAdapter",
    "AdapterConfig",
    "AdapterStatus",
    "LLMGatewayAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "MockCognitiveAdapter",
    "create_adapter",
    "create_adapter_from_config",
    "TaskEntity",
    "TaskIdentity",
    "TaskLifecycle",
    "TaskLifecycleState",
    "TaskHistory",
    "TaskCost",
    "TaskDependency",
    "TaskDependencyType",
    "create_task_entity",
    "create_task_identity",
    "RequestParser",
    "TaskBuilder",
    "RequestAnalysis",
    "RequestType",
    "RequestIntent",
    "RequestComplexity",
    "create_request_parser",
    "create_task_builder",
]
