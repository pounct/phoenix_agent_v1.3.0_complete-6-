#!/usr/bin/env python3
"""
Phoenix Agent v1.3.0 - Project Builder
======================================

Ce script recrée la structure complète du projet Phoenix Agent.
Exécutez ce script pour générer tous les fichiers nécessaires.

Usage:
    python phoenix_agent_builder.py

Le projet sera créé dans le répertoire courant: ./phoenix_agent/
"""

import os
import json

# ============================================================================
# STRUCTURE DU PROJET
# ============================================================================

PROJECT_STRUCTURE = {
    "phoenix_agent": {
        "__init__.py": '''"""
Phoenix Agent - Model-Agnostic Agent Runtime
=============================================

Phoenix est un **Model-Agnostic Agent Runtime Engine**.

THE KEY INSIGHT (v1.3):
    Phoenix does NOT depend on an LLM.
    Phoenix depends on COGNITIVE CAPABILITIES.

Version: 1.3.0 (Model-Agnostic Architecture)
"""

__version__ = "1.3.0"
__author__ = "Phoenix Team"

from .config import (
    PhoenixConfig,
    GatewayConfig,
    AgentConfig,
    get_config,
    set_config,
    reset_config,
    LogLevel,
)

from .cognitive.engine import (
    CognitiveEngine,
    CognitiveConfig,
    CognitiveCapability,
    create_cognitive_engine,
)

from .cognitive.adapters import (
    CognitiveAdapter,
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    MockCognitiveAdapter,
    create_adapter,
)

from .cognitive.task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycle,
    TaskLifecycleState,
    create_task_entity,
)

from .cognitive.request_parser import (
    RequestParser,
    TaskBuilder,
    create_request_parser,
    create_task_builder,
)

__all__ = [
    "__version__",
    "PhoenixConfig",
    "GatewayConfig", 
    "AgentConfig",
    "get_config",
    "set_config",
    "reset_config",
    "LogLevel",
    "CognitiveEngine",
    "CognitiveConfig",
    "CognitiveCapability",
    "create_cognitive_engine",
    "CognitiveAdapter",
    "LLMGatewayAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "MockCognitiveAdapter",
    "create_adapter",
    "TaskEntity",
    "TaskIdentity",
    "TaskLifecycle",
    "TaskLifecycleState",
    "create_task_entity",
    "RequestParser",
    "TaskBuilder",
    "create_request_parser",
    "create_task_builder",
]
''',
        
        "config.py": '''"""Phoenix Agent - Configuration"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class GatewayConfig:
    """Configuration de connexion à la LLM Gateway."""
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout_seconds: float = 120.0
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> "GatewayConfig":
        return cls(
            base_url=os.getenv("PHOENIX_GATEWAY_URL", "http://localhost:8000"),
            api_key=os.getenv("PHOENIX_GATEWAY_API_KEY"),
            timeout_seconds=float(os.getenv("PHOENIX_GATEWAY_TIMEOUT", "120")),
        )


@dataclass
class AgentConfig:
    """Configuration de l'Agent Loop."""
    max_iterations: int = 10
    enable_thinking: bool = True
    enable_tools: bool = False


@dataclass
class PhoenixConfig:
    """Configuration principale Phoenix."""
    app_name: str = "Phoenix Agent"
    version: str = "1.3.0"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    
    @classmethod
    def from_env(cls) -> "PhoenixConfig":
        config = cls()
        if os.getenv("PHOENIX_DEBUG", "false").lower() == "true":
            config.debug = True
            config.log_level = LogLevel.DEBUG
        config.gateway = GatewayConfig.from_env()
        return config


_config: Optional[PhoenixConfig] = None


def get_config() -> PhoenixConfig:
    global _config
    if _config is None:
        _config = PhoenixConfig.from_env()
    return _config


def set_config(config: PhoenixConfig) -> None:
    global _config
    _config = config


def reset_config() -> None:
    global _config
    _config = None
''',

        "requirements.txt": '''# Phoenix Agent v1.3.0 - Requirements
typing_extensions>=4.0.0
aiohttp>=3.8.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
''',

        "README.md": '''# Phoenix Agent v1.3.0

**Model-Agnostic Agent Runtime Engine**

## The Golden Rule

> **Phoenix does NOT depend on an LLM.**
> **Phoenix depends on COGNITIVE CAPABILITIES.**

## Quick Start

```python
from phoenix_agent import (
    CognitiveEngine, create_cognitive_engine,
    MockCognitiveAdapter, create_adapter,
)

# Create engine with any provider
adapter = create_adapter("mock")  # or "openai", "ollama", "llm_gateway"
engine = create_cognitive_engine(adapter)

# Use cognitive capabilities
result = await engine.reason("Analyze this problem")
print(result.output)
```

## Architecture

```
Model Providers (OpenAI, Ollama, etc.)
        ↓
CognitiveEngine (reason, plan, evaluate, summarize)
        ↓
Phoenix Runtime (Tasks, Goals, Memory, Learning)
```

## The Five Pillars

1. **Cognitive Abstraction** - Model independence
2. **Task System** - Identity + Lifecycle
3. **Execution Runtime** - Pipeline + Orchestration
4. **Agent Coordination** - Delegation + Synthesis
5. **Memory Evolution** - Learning + Adaptation

## License: MIT
'''
    }
}

# Add cognitive module
PROJECT_STRUCTURE["phoenix_agent"]["cognitive"] = {
    "__init__.py": '''"""Phoenix Agent - Cognitive Interface Layer"""

from .engine import (
    CognitiveEngine,
    CognitiveConfig,
    CognitiveCapability,
    create_cognitive_engine,
)

from .adapters import (
    CognitiveAdapter,
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    MockCognitiveAdapter,
    create_adapter,
)

from .task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycle,
    TaskLifecycleState,
    create_task_entity,
)

from .request_parser import (
    RequestParser,
    TaskBuilder,
    create_request_parser,
    create_task_builder,
)

__all__ = [
    "CognitiveEngine",
    "CognitiveConfig",
    "CognitiveCapability",
    "create_cognitive_engine",
    "CognitiveAdapter",
    "LLMGatewayAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "MockCognitiveAdapter",
    "create_adapter",
    "TaskEntity",
    "TaskIdentity",
    "TaskLifecycle",
    "TaskLifecycleState",
    "create_task_entity",
    "RequestParser",
    "TaskBuilder",
    "create_request_parser",
    "create_task_builder",
]
''',

    "engine.py": '''"""Phoenix Agent - Cognitive Engine"""

from __future__ import annotations
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4
import logging

logger = logging.getLogger("phoenix.cognitive")


class CognitiveCapability(str, Enum):
    """Capabilities that a cognitive engine can provide."""
    REASON = "reason"
    PLAN = "plan"
    EVALUATE = "evaluate"
    SUMMARIZE = "summarize"
    REFLECT = "reflect"
    DECIDE = "decide"


@dataclass
class CognitiveRequest:
    """Base class for cognitive requests."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningRequest(CognitiveRequest):
    """Request for logical reasoning."""
    problem: str = ""
    constraints: List[str] = field(default_factory=list)


@dataclass
class PlanningRequest(CognitiveRequest):
    """Request for strategic planning."""
    goal: str = ""
    constraints: List[str] = field(default_factory=list)


@dataclass
class CognitiveResult:
    """Base class for cognitive results."""
    request_id: str = ""
    success: bool = False
    output: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    provider: str = "unknown"
    error: Optional[str] = None


@dataclass
class ReasoningResult(CognitiveResult):
    """Result of reasoning."""
    reasoning_chain: List[str] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class PlanningResult(CognitiveResult):
    """Result of planning."""
    steps: List[Dict[str, Any]] = field(default_factory=list)


class CognitiveAdapter(ABC):
    """Abstract interface for cognitive providers."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def available_capabilities(self) -> List[CognitiveCapability]:
        pass
    
    @abstractmethod
    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        pass
    
    @abstractmethod
    async def plan(self, request: PlanningRequest) -> PlanningResult:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
    
    def supports(self, capability: CognitiveCapability) -> bool:
        return capability in self.available_capabilities


@dataclass
class CognitiveConfig:
    """Configuration for CognitiveEngine."""
    default_timeout: float = 60.0
    max_retries: int = 3
    fallback_enabled: bool = True
    cache_enabled: bool = True


class CognitiveEngine:
    """THE MODEL-AGNOSTIC COGNITIVE ENGINE."""
    
    def __init__(
        self,
        adapter: CognitiveAdapter,
        config: CognitiveConfig = None,
        fallback_adapter: Optional[CognitiveAdapter] = None,
    ):
        self.adapter = adapter
        self.config = config or CognitiveConfig()
        self.fallback_adapter = fallback_adapter
        self._cache: Dict[str, CognitiveResult] = {}
        self._request_count = 0
        logger.info(f"CognitiveEngine initialized with: {adapter.provider_name}")
    
    async def reason(
        self,
        problem: str,
        constraints: List[str] = None,
        **kwargs
    ) -> ReasoningResult:
        """Perform logical reasoning."""
        request = ReasoningRequest(
            problem=problem,
            constraints=constraints or [],
        )
        return await self._execute(
            lambda a: a.reason(request),
            CognitiveCapability.REASON
        )
    
    async def plan(
        self,
        goal: str,
        constraints: List[str] = None,
        **kwargs
    ) -> PlanningResult:
        """Create a strategic plan."""
        request = PlanningRequest(
            goal=goal,
            constraints=constraints or [],
        )
        return await self._execute(
            lambda a: a.plan(request),
            CognitiveCapability.PLAN
        )
    
    async def _execute(
        self,
        executor: Callable[[CognitiveAdapter], Any],
        capability: CognitiveCapability,
    ) -> CognitiveResult:
        """Execute with fallback support."""
        start_time = time.time()
        self._request_count += 1
        
        try:
            if self.adapter.supports(capability):
                result = await executor(self.adapter)
                result.latency_ms = (time.time() - start_time) * 1000
                return result
        except Exception as e:
            logger.warning(f"Primary adapter failed: {e}")
            if self.fallback_adapter and self.fallback_adapter.supports(capability):
                try:
                    result = await executor(self.fallback_adapter)
                    result.latency_ms = (time.time() - start_time) * 1000
                    return result
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
        
        return CognitiveResult(
            success=False,
            error=f"Capability {capability} not available",
            latency_ms=(time.time() - start_time) * 1000,
        )
    
    async def health_check(self) -> bool:
        try:
            return await self.adapter.health_check()
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider": self.adapter.provider_name,
            "request_count": self._request_count,
        }


def create_cognitive_engine(
    adapter: CognitiveAdapter,
    config: CognitiveConfig = None,
    fallback_adapter: Optional[CognitiveAdapter] = None,
) -> CognitiveEngine:
    return CognitiveEngine(adapter, config, fallback_adapter)
''',

    "adapters.py": '''"""Phoenix Agent - Cognitive Adapters"""

from __future__ import annotations
import asyncio
import time
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging

from .engine import (
    CognitiveAdapter,
    CognitiveCapability,
    ReasoningRequest,
    ReasoningResult,
    PlanningRequest,
    PlanningResult,
)

logger = logging.getLogger("phoenix.cognitive.adapters")


@dataclass
class AdapterConfig:
    """Configuration for cognitive adapters."""
    timeout_seconds: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.7
    model: str = "default"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AdapterStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class BaseCognitiveAdapter(CognitiveAdapter):
    """Base implementation with common functionality."""
    
    def __init__(self, config: AdapterConfig = None):
        self.config = config or AdapterConfig()
        self._status = AdapterStatus.UNKNOWN
    
    @property
    def available_capabilities(self) -> List[CognitiveCapability]:
        return list(CognitiveCapability)
    
    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        prompt = f"Problem: {request.problem}\\n\\nPerform logical reasoning."
        response = await self._call_model(prompt, request)
        return ReasoningResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            reasoning_chain=response.get("reasoning_chain", []),
            conclusion=response.get("conclusion", ""),
            error=response.get("error"),
        )
    
    async def plan(self, request: PlanningRequest) -> PlanningResult:
        prompt = f"Goal: {request.goal}\\n\\nCreate a detailed plan."
        response = await self._call_model(prompt, request)
        return PlanningResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            steps=response.get("steps", []),
            error=response.get("error"),
        )
    
    @abstractmethod
    async def _call_model(self, prompt: str, request: Any) -> Dict[str, Any]:
        pass


class LLMGatewayAdapter(BaseCognitiveAdapter):
    """Adapter for the external LLM Gateway."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None, config: AdapterConfig = None):
        super().__init__(config)
        self.base_url = base_url.rstrip(\'/\')
        self.api_key = api_key
        self._session = None
    
    @property
    def provider_name(self) -> str:
        return "llm_gateway"
    
    async def _get_session(self):
        if self._session is None:
            import aiohttp
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def _call_model(self, prompt: str, request: Any) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            payload = {"prompt": prompt, "model": self.config.model}
            async with session.post(f"{self.base_url}/v1/generate", json=payload) as resp:
                if resp.status != 200:
                    return {"success": False, "error": f"HTTP {resp.status}"}
                data = await resp.json()
                return {"success": True, "output": data.get("response", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as resp:
                return resp.status == 200
        except:
            return False


class OpenAIAdapter(BaseCognitiveAdapter):
    """Direct OpenAI API adapter."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4", config: AdapterConfig = None):
        super().__init__(config)
        self.api_key = api_key
        self.config.model = model
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def _call_model(self, prompt: str, request: Any) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
            )
            content = response.choices[0].message.content if response.choices else ""
            return {"success": True, "output": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        return True


class OllamaAdapter(BaseCognitiveAdapter):
    """Ollama local model adapter."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", config: AdapterConfig = None):
        super().__init__(config)
        self.base_url = base_url.rstrip(\'/\')
        self.config.model = model
        self._session = None
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _call_model(self, prompt: str, request: Any) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            payload = {"model": self.config.model, "prompt": prompt, "stream": False}
            async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                if resp.status != 200:
                    return {"success": False, "error": f"HTTP {resp.status}"}
                data = await resp.json()
                return {"success": True, "output": data.get("response", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as resp:
                return resp.status == 200
        except:
            return False


class MockCognitiveAdapter(BaseCognitiveAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, response_content: str = "Mock response", confidence: float = 0.8):
        super().__init__()
        self.response_content = response_content
        self.confidence = confidence
        self.call_count = 0
    
    @property
    def provider_name(self) -> str:
        return "mock"
    
    async def _call_model(self, prompt: str, request: Any) -> Dict[str, Any]:
        self.call_count += 1
        return {
            "success": True,
            "output": self.response_content,
            "confidence": self.confidence,
            "reasoning_chain": ["Step 1", "Step 2", "Conclusion"],
            "conclusion": self.response_content,
        }
    
    async def health_check(self) -> bool:
        return True


def create_adapter(provider: str = "mock", **kwargs) -> CognitiveAdapter:
    """Create a cognitive adapter by provider name."""
    adapters = {
        "llm_gateway": LLMGatewayAdapter,
        "openai": OpenAIAdapter,
        "ollama": OllamaAdapter,
        "mock": MockCognitiveAdapter,
    }
    if provider not in adapters:
        raise ValueError(f"Unknown provider: {provider}")
    return adapters[provider](**kwargs)
''',

    "task_entity.py": '''"""Phoenix Agent - Task Entity System"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
import logging

logger = logging.getLogger("phoenix.cognitive.task_entity")


class TaskLifecycleState(str, Enum):
    """Complete task lifecycle states."""
    CREATED = "created"
    VALIDATED = "validated"
    QUEUED = "queued"
    PENDING = "pending"
    EXECUTING = "executing"
    DELEGATING = "delegating"
    WAITING_INPUT = "waiting_input"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskLifecycleCategory(str, Enum):
    INITIAL = "initial"
    QUEUED = "queued"
    ACTIVE = "active"
    WAITING = "waiting"
    TERMINAL = "terminal"


STATE_CATEGORIES = {
    TaskLifecycleState.CREATED: TaskLifecycleCategory.INITIAL,
    TaskLifecycleState.VALIDATED: TaskLifecycleCategory.INITIAL,
    TaskLifecycleState.QUEUED: TaskLifecycleCategory.QUEUED,
    TaskLifecycleState.PENDING: TaskLifecycleCategory.QUEUED,
    TaskLifecycleState.EXECUTING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.DELEGATING: TaskLifecycleCategory.ACTIVE,
    TaskLifecycleState.WAITING_INPUT: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.RETRYING: TaskLifecycleCategory.WAITING,
    TaskLifecycleState.COMPLETED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.FAILED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.CANCELLED: TaskLifecycleCategory.TERMINAL,
    TaskLifecycleState.TIMEOUT: TaskLifecycleCategory.TERMINAL,
}


@dataclass
class TaskIdentity:
    """Unique identity for a task."""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None
    session_id: Optional[str] = None
    name: str = ""
    
    def __post_init__(self):
        if self.root_task_id is None and self.parent_task_id is None:
            self.root_task_id = self.task_id
    
    @property
    def is_root(self) -> bool:
        return self.parent_task_id is None
    
    @property
    def is_subtask(self) -> bool:
        return self.parent_task_id is not None
    
    def create_child_identity(self, name: str = "") -> "TaskIdentity":
        return TaskIdentity(
            task_id=str(uuid4()),
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            parent_task_id=self.task_id,
            root_task_id=self.root_task_id,
            session_id=self.session_id,
            name=name,
        )


@dataclass
class TaskCost:
    """Cost tracking for a task."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    wall_time_ms: float = 0.0
    delegation_count: int = 0
    retry_count: int = 0
    api_calls: int = 0
    
    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
    
    def add_delegation(self) -> None:
        self.delegation_count += 1
    
    def add_retry(self) -> None:
        self.retry_count += 1


class TaskLifecycle:
    """Manages task lifecycle state transitions."""
    
    def __init__(self, initial_state: TaskLifecycleState = TaskLifecycleState.CREATED):
        self._state = initial_state
        self._history: List[Dict[str, Any]] = []
    
    @property
    def state(self) -> TaskLifecycleState:
        return self._state
    
    @property
    def category(self) -> TaskLifecycleCategory:
        return STATE_CATEGORIES.get(self._state, TaskLifecycleCategory.INITIAL)
    
    @property
    def is_terminal(self) -> bool:
        return self.category == TaskLifecycleCategory.TERMINAL
    
    @property
    def is_active(self) -> bool:
        return self.category == TaskLifecycleCategory.ACTIVE
    
    def transition(self, new_state: TaskLifecycleState, message: str = "") -> bool:
        old_state = self._state
        self._state = new_state
        self._history.append({
            "from": old_state.value,
            "to": new_state.value,
            "message": message,
        })
        logger.debug(f"Task transition: {old_state.value} -> {new_state.value}")
        return True
    
    def force_state(self, new_state: TaskLifecycleState, reason: str = "") -> None:
        old_state = self._state
        self._state = new_state
        self._history.append({
            "from": old_state.value,
            "to": new_state.value,
            "message": f"Forced: {reason}",
            "forced": True,
        })


class TaskDependencyType(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    TRIGGER = "trigger"


@dataclass
class TaskDependency:
    """A dependency on another task."""
    task_id: str
    dependency_type: TaskDependencyType = TaskDependencyType.HARD


@dataclass
class TaskEntity:
    """Complete Task Entity with Identity, Lifecycle, Cost, and History."""
    identity: TaskIdentity = field(default_factory=TaskIdentity)
    goal: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    lifecycle: TaskLifecycle = field(default_factory=TaskLifecycle)
    cost: TaskCost = field(default_factory=TaskCost)
    dependencies: List[TaskDependency] = field(default_factory=list)
    priority: int = 5
    complexity: str = "moderate"
    tags: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    max_retries: int = 3
    timeout_seconds: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    _start_time: float = field(default=0.0, repr=False)
    
    def __post_init__(self):
        if not self.identity.name:
            self.identity.name = self.goal[:50] if self.goal else "unnamed"
    
    @property
    def task_id(self) -> str:
        return self.identity.task_id
    
    @property
    def is_root(self) -> bool:
        return self.identity.is_root
    
    @property
    def state(self) -> TaskLifecycleState:
        return self.lifecycle.state
    
    @property
    def is_terminal(self) -> bool:
        return self.lifecycle.is_terminal
    
    def start(self) -> bool:
        if self._start_time == 0:
            self._start_time = time.time()
            self.started_at = datetime.utcnow()
        return self.lifecycle.transition(TaskLifecycleState.EXECUTING, "Started")
    
    def complete(self, output: str) -> bool:
        self.output = output
        self.completed_at = datetime.utcnow()
        if self._start_time > 0:
            self.cost.wall_time_ms = (time.time() - self._start_time) * 1000
        return self.lifecycle.transition(TaskLifecycleState.COMPLETED, f"Output: {len(output)} chars")
    
    def fail(self, error: str) -> bool:
        self.error = error
        self.completed_at = datetime.utcnow()
        return self.lifecycle.transition(TaskLifecycleState.FAILED, error[:100])
    
    def cancel(self, reason: str = "") -> bool:
        self.completed_at = datetime.utcnow()
        return self.lifecycle.transition(TaskLifecycleState.CANCELLED, reason)
    
    def retry(self) -> bool:
        if self.cost.retry_count >= self.max_retries:
            return False
        self.cost.add_retry()
        return self.lifecycle.transition(TaskLifecycleState.RETRYING, f"Attempt {self.cost.retry_count}")
    
    def delegate(self, agent_id: str) -> bool:
        self.assigned_agent = agent_id
        self.cost.add_delegation()
        return self.lifecycle.transition(TaskLifecycleState.DELEGATING, f"To: {agent_id}")
    
    def create_subtask(self, goal: str, description: str = "", **kwargs) -> "TaskEntity":
        child_identity = self.identity.create_child_identity(name=goal[:50])
        subtask = TaskEntity(
            identity=child_identity,
            goal=goal,
            description=description,
            priority=self.priority,
            **kwargs
        )
        subtask.dependencies.append(TaskDependency(task_id=self.task_id))
        return subtask


def create_task_identity(name: str = "", correlation_id: str = None, trace_id: str = None) -> TaskIdentity:
    return TaskIdentity(
        name=name,
        correlation_id=correlation_id or str(uuid4()),
        trace_id=trace_id or str(uuid4()),
    )


def create_task_entity(goal: str, description: str = "", priority: int = 5, identity: TaskIdentity = None, **kwargs) -> TaskEntity:
    return TaskEntity(
        identity=identity or create_task_identity(name=goal[:50]),
        goal=goal,
        description=description,
        priority=priority,
        **kwargs
    )
''',

    "request_parser.py": '''"""Phoenix Agent - Request Parser & Task Builder"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

from .task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycleState,
    create_task_entity,
    create_task_identity,
)

logger = logging.getLogger("phoenix.cognitive.request_parser")


class RequestType(str, Enum):
    USER_MESSAGE = "user_message"
    API_CALL = "api_call"
    EVENT = "event"
    SCHEDULED = "scheduled"
    DELEGATION = "delegation"


class RequestIntent(str, Enum):
    QUERY = "query"
    COMMAND = "command"
    ANALYSIS = "analysis"
    CREATION = "creation"
    MODIFICATION = "modification"
    DELEGATION = "delegation"
    UNKNOWN = "unknown"


class RequestComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class RequestAnalysis:
    """Analysis result of an external request."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    request_type: RequestType = RequestType.USER_MESSAGE
    detected_intent: RequestIntent = RequestIntent.UNKNOWN
    complexity: RequestComplexity = RequestComplexity.MODERATE
    confidence: float = 0.0
    original_input: str = ""
    normalized_input: str = ""
    key_topics: List[str] = field(default_factory=list)
    suggested_tasks: List[Dict[str, Any]] = field(default_factory=list)
    requires_decomposition: bool = False
    constraints: List[str] = field(default_factory=list)
    priority: int = 5
    session_id: Optional[str] = None
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    analysis_time_ms: float = 0.0


class RequestParser:
    """Parse external requests into structured analysis."""
    
    def __init__(self):
        self.intent_patterns = {
            RequestIntent.QUERY.value: ["what", "how", "why", "when", "explain", "describe"],
            RequestIntent.COMMAND.value: ["do", "run", "execute", "create", "delete", "update"],
            RequestIntent.ANALYSIS.value: ["analyze", "examine", "review", "evaluate", "assess"],
            RequestIntent.CREATION.value: ["create", "build", "make", "generate", "design"],
        }
    
    def parse(self, input_data: Any, request_type: RequestType = RequestType.USER_MESSAGE, metadata: Dict[str, Any] = None) -> RequestAnalysis:
        start_time = time.time()
        
        if isinstance(input_data, str):
            original = input_data
        elif isinstance(input_data, dict):
            original = input_data.get("content", str(input_data))
        else:
            original = str(input_data)
        
        normalized = original.lower()
        
        analysis = RequestAnalysis(
            request_type=request_type,
            original_input=original,
            normalized_input=normalized,
            metadata=metadata or {},
        )
        
        analysis.detected_intent = self._detect_intent(normalized)
        analysis.complexity = self._assess_complexity(normalized)
        analysis.key_topics = self._extract_topics(normalized)
        analysis.requires_decomposition = analysis.complexity in [RequestComplexity.COMPLEX, RequestComplexity.EXPERT]
        analysis.priority = self._extract_priority(normalized)
        
        analysis.analysis_time_ms = (time.time() - start_time) * 1000
        analysis.confidence = 0.7 if analysis.detected_intent != RequestIntent.UNKNOWN else 0.3
        
        return analysis
    
    def _detect_intent(self, text: str) -> RequestIntent:
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return RequestIntent(intent)
        if "?" in text:
            return RequestIntent.QUERY
        return RequestIntent.UNKNOWN
    
    def _assess_complexity(self, text: str) -> RequestComplexity:
        word_count = len(text.split())
        complex_indicators = ["multiple", "comprehensive", "detailed", "step by step", "integrate"]
        if any(ind in text for ind in complex_indicators):
            return RequestComplexity.COMPLEX
        if word_count > 50:
            return RequestComplexity.COMPLEX
        elif word_count > 10:
            return RequestComplexity.MODERATE
        return RequestComplexity.SIMPLE
    
    def _extract_topics(self, text: str) -> List[str]:
        stop_words = {"the", "a", "an", "is", "are", "was", "to", "of", "in", "for", "on", "with", "and", "or"}
        words = [w for w in text.split() if w not in stop_words and len(w) > 3]
        return list(set(words))[:5]
    
    def _extract_priority(self, text: str) -> int:
        high_words = ["urgent", "critical", "important", "asap", "emergency"]
        low_words = ["whenever", "eventually", "someday", "no rush"]
        if any(w in text for w in high_words):
            return 8
        if any(w in text for w in low_words):
            return 3
        return 5


class TaskBuilder:
    """Build Task Entities from Request Analysis."""
    
    def __init__(self, default_priority: int = 5, auto_decompose: bool = True):
        self.default_priority = default_priority
        self.auto_decompose = auto_decompose
    
    def build_from_analysis(self, analysis: RequestAnalysis) -> TaskEntity:
        identity = create_task_identity(
            name=analysis.normalized_input[:50],
            correlation_id=analysis.trace_id,
            session_id=analysis.session_id,
        )
        
        task = TaskEntity(
            identity=identity,
            goal=analysis.original_input,
            description=f"Task from request {analysis.request_id}",
            priority=analysis.priority,
            complexity=analysis.complexity.value,
            tags=analysis.key_topics,
        )
        
        task.lifecycle.transition(TaskLifecycleState.VALIDATED, "Created from request")
        return task
    
    def build_single_task(self, goal: str, description: str = "", priority: int = None, metadata: Dict[str, Any] = None) -> TaskEntity:
        task = create_task_entity(
            goal=goal,
            description=description,
            priority=priority or self.default_priority,
            metadata=metadata or {},
        )
        task.lifecycle.transition(TaskLifecycleState.VALIDATED, "Single task created")
        return task


def create_request_parser() -> RequestParser:
    return RequestParser()


def create_task_builder(default_priority: int = 5, auto_decompose: bool = True) -> TaskBuilder:
    return TaskBuilder(default_priority=default_priority, auto_decompose=auto_decompose)
'''
}


def create_project(base_dir: str = ".") -> None:
    """Create the complete Phoenix Agent project."""
    
    def write_file(path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created: {path}")
    
    def process_structure(structure: dict, current_path: str) -> None:
        for name, content in structure.items():
            path = os.path.join(current_path, name)
            if isinstance(content, dict):
                process_structure(content, path)
            else:
                write_file(path, content)
    
    project_path = os.path.join(base_dir, "phoenix_agent")
    process_structure(PROJECT_STRUCTURE, base_dir)
    
    print("\\n" + "="*50)
    print("Phoenix Agent v1.3.0 - Project Created!")
    print("="*50)
    print(f"\\nLocation: {os.path.abspath(project_path)}")
    print("\\nTo use:")
    print("  cd phoenix_agent")
    print("  pip install -r requirements.txt")
    print("\\nQuick test:")
    print("  python -c 'from phoenix_agent import CognitiveEngine, MockCognitiveAdapter; print(\"OK!\")'")


if __name__ == "__main__":
    create_project()
''',
}


def main():
    """Main function to create the project."""
    print("="*60)
    print("Phoenix Agent v1.3.0 - Project Builder")
    print("="*60)
    print()
    print("Ce script va créer la structure complète du projet.")
    print()
    
    # Get the script content
    script_content = PROJECT_STRUCTURE["phoenix_agent_builder.py"]
    
    # Write the builder script
    output_path = "phoenix_agent_builder.py"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print(f"✅ Script créé: {output_path}")
    print()
    print("Pour créer le projet complet, exécutez:")
    print(f"    python {output_path}")
    print()
    print("Ou utilisez directement le contenu du script.")
    print()
    print("="*60)


if __name__ == "__main__":
    main()
