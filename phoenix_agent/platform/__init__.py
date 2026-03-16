"""
Phoenix Agent - Platform Layer
==============================

System Interface Layer for Phoenix Agent Platform.

This layer transforms Phoenix from a Cognitive Kernel into a usable Agent Platform.

Components (v1.1 - Platform Layer):
    - ToolExecutor: Tool execution runtime (action layer)
    - EnvironmentAdapter: External system integration (integration layer)
    - SafetyEngine: Guardrails and safety controls (safety layer)

IMPORTANT:
    - Platform Layer provides the "hands and eyes" for the cognitive kernel
    - Without this layer, Phoenix can only reason, not act
    - This is the final layer needed for production readiness

Architecture:

    ┌─────────────────────────────────────────────────────┐
    │                 PHOENIX PLATFORM                     │
    ├─────────────────────────────────────────────────────┤
    │                                                      │
    │   ┌─────────────┐    ┌─────────────────────────┐   │
    │   │   Safety    │───▶│    Environment          │   │
    │   │   Engine    │    │    Adapter              │   │
    │   └─────────────┘    └─────────────────────────┘   │
    │          │                      │                   │
    │          │                      │                   │
    │          ▼                      ▼                   │
    │   ┌─────────────────────────────────────────────┐   │
    │   │              Tool Executor                  │   │
    │   │         (execute, retry, fallback)          │   │
    │   └─────────────────────────────────────────────┘   │
    │                          │                           │
    └──────────────────────────┼───────────────────────────┘
                               │
                               ▼
                    External World (APIs, Files, DBs)
"""

from .tool_executor import (
    # Core
    ToolExecutor,
    Tool,
    ToolResult,
    ToolContext,
    ToolRegistry,
    
    # Config
    ToolExecutorConfig,
    
    # Enums
    ToolStatus,
    ToolCategory,
    ExecutionMode,
    
    # Factory
    create_tool_executor,
    register_tool,
)

from .environment_adapter import (
    # Core
    EnvironmentAdapter,
    EnvironmentConfig,
    EnvironmentStatus,
    
    # Connections
    LLMGatewayConnection,
    DatabaseConnection,
    APIConnection,
    FileSystemConnection,
    QueueConnection,
    
    # Enums
    ConnectionType,
    ConnectionStatus,
    
    # Factory
    create_environment_adapter,
)

from .safety_engine import (
    # Core
    SafetyEngine,
    SafetyCheckResult,
    SafetyViolation,
    Guardrails,
    
    # Config
    SafetyConfig,
    
    # Enums
    SafetyLevel,
    ViolationType,
    ViolationSeverity,
    
    # Factory
    create_safety_engine,
)


__all__ = [
    # Tool Executor
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
    
    # Environment Adapter
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
    
    # Safety Engine
    "SafetyEngine",
    "SafetyCheckResult",
    "SafetyViolation",
    "Guardrails",
    "SafetyConfig",
    "SafetyLevel",
    "ViolationType",
    "ViolationSeverity",
    "create_safety_engine",
]
