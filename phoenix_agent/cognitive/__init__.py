"""
Phoenix Agent - Cognitive Interface Layer
==========================================

THE MODEL-AGNOSTIC ABSTRACTION LAYER.

This is what makes Phoenix independent of any LLM provider.

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
    │               COGNITIVE INTERFACE LAYER                     │
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
    │   Goals → Tasks → Execution → Memory → Learning             │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

RÈGLE D'OR:
    Phoenix NEVER talks to OpenAI/Ollama/Claude directly.
    Phoenix ONLY talks to CognitiveEngine.

This makes Phoenix:
    - Portable (works with any model)
    - Independent (no vendor lock-in)
    - Future-proof (new models just need an adapter)

Version: 1.3.0 (Model-Agnostic Architecture)
"""

from .engine import (
    # Core Engine
    CognitiveEngine,
    CognitiveConfig,
    CognitiveCapability,
    CognitiveResult,
    
    # Capabilities
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
    
    # Factory
    create_cognitive_engine,
)

from .adapters import (
    # Base adapter
    CognitiveAdapter,
    AdapterConfig,
    AdapterStatus,
    
    # Specific adapters
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    MockCognitiveAdapter,
    
    # Factory
    create_adapter,
    create_adapter_from_config,
)

from .task_entity import (
    # Task Identity System
    TaskEntity,
    TaskIdentity,
    TaskLifecycle,
    TaskLifecycleState,
    TaskHistory,
    TaskCost,
    TaskDependency,
    TaskDependencyType,
    
    # Factories
    create_task_entity,
    create_task_identity,
)

from .request_parser import (
    # Request vs Task separation
    RequestParser,
    TaskBuilder,
    RequestAnalysis,
    TaskGraph,
    TaskNode,
    
    # Factories
    create_request_parser,
    create_task_builder,
)


__all__ = [
    # Core Engine
    "CognitiveEngine",
    "CognitiveConfig",
    "CognitiveCapability",
    "CognitiveResult",
    
    # Capabilities
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
    
    # Factory
    "create_cognitive_engine",
    
    # Adapters
    "CognitiveAdapter",
    "AdapterConfig",
    "AdapterStatus",
    "LLMGatewayAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "MockCognitiveAdapter",
    "create_adapter",
    "create_adapter_from_config",
    
    # Task Entity System
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
    
    # Request Parser
    "RequestParser",
    "TaskBuilder",
    "RequestAnalysis",
    "TaskGraph",
    "TaskNode",
    "create_request_parser",
    "create_task_builder",
]
