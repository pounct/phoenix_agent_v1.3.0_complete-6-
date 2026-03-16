# Phoenix Agent v1.3.0

**Model-Agnostic Agent Runtime Engine**

---

## The Core Philosophy

### LLM ≠ Agent

| LLM | Agent |
|-----|-------|
| **Raisonne** (Reasons) | **Agit** (Acts) |
| - | **Planifie** (Plans) |
| - | **Mémorise** (Remembers) |
| - | **Orchestre** (Orchestrates) |

### The Golden Rule

> **Phoenix does NOT depend on an LLM.**
> **Phoenix depends on COGNITIVE CAPABILITIES.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MODEL PROVIDERS                               │
│                                                                      │
│   OpenAI    Ollama    vLLM    Gemini    Claude    Local Models     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  COGNITIVE INTERFACE LAYER                          │
│                                                                      │
│   CognitiveEngine                                                   │
│   ├── reason()      - Logical reasoning                             │
│   ├── plan()        - Strategic planning                            │
│   ├── evaluate()    - Result evaluation                             │
│   ├── summarize()   - Content summarization                         │
│   ├── reflect()     - Self-reflection                               │
│   └── decide()      - Decision making                               │
│                                                                      │
│   Adapters: LLMGateway, OpenAI, Ollama, Mock                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PHOENIX RUNTIME                                │
│                                                                      │
│   Platform Layer                                                    │
│   ├── SafetyEngine         - Guardrails & Safety Controls           │
│   ├── EnvironmentAdapter   - External System Integration            │
│   └── ToolExecutor         - Action Execution Layer                 │
│                                                                      │
│   Cognitive Kernel                                                  │
│   ├── AgentRuntimeController - The Conductor                        │
│   ├── GoalManager            - Persistent Objectives                 │
│   ├── PlannerEngine          - Strategic Planning                    │
│   ├── DecisionEngine         - Reactive Decisions                    │
│   ├── ResourceManager        - Budget Control                        │
│   ├── LearningLoop           - Cognitive Feedback                    │
│   ├── AdaptationEngine       - Self-Evolution                        │
│   ├── AgentRegistry          - Population Management                 │
│   └── TaskGraphExecutor      - Graph Execution                       │
│                                                                      │
│   Task System                                                       │
│   ├── TaskEntity           - Internal work units                     │
│   ├── TaskIdentity         - Full traceability                       │
│   ├── TaskLifecycle        - State management                        │
│   └── RequestParser        - Request→Task conversion                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Five Pillars of Phoenix

1. **Cognitive Abstraction** - Model independence through CognitiveEngine
2. **Task System** - Identity + Lifecycle + Tracking
3. **Execution Runtime** - Pipeline + Orchestration
4. **Agent Coordination** - Delegation + Synthesis
5. **Memory Evolution** - Learning + Adaptation

---

## Request vs Task Separation

```
┌─────────────┐
│   Request   │  ← External, untrusted, variable format
│ (External)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│RequestParser│  ← Parse and validate
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ TaskBuilder │  ← Create Task entities
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  TaskGraph  │  ← Internal task graph
│  (Internal) │
└─────────────┘
```

**Key Insight:**
- **Request** = External input (what comes in)
- **Task** = Internal work unit (what Phoenix manages)

---

## Installation

```bash
# Clone or download
cd phoenix_agent

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### Basic Usage

```python
from phoenix_agent import (
    # Cognitive Layer
    CognitiveEngine, create_cognitive_engine,
    MockCognitiveAdapter,
    
    # Task System
    TaskEntity, create_task_entity,
    RequestParser, TaskBuilder,
    
    # Runtime
    AgentRuntimeController, create_runtime_controller,
)

# 1. Create a cognitive engine with your preferred provider
adapter = MockCognitiveAdapter()  # Use OpenAIAdapter, OllamaAdapter in production
engine = create_cognitive_engine(adapter)

# 2. Parse a request
parser = RequestParser()
analysis = parser.parse("Analyze the scalability of this architecture")

# 3. Build task graph
builder = TaskBuilder()
graph = builder.build_from_analysis(analysis)

# 4. Execute
controller = create_runtime_controller(cognitive_engine=engine)
result = await controller.run(graph)

print(result)
```

### Using Different Providers

```python
from phoenix_agent.cognitive import (
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    create_adapter,
)

# Option 1: LLM Gateway (recommended for production)
adapter = create_adapter("llm_gateway", base_url="http://gateway:8000")

# Option 2: OpenAI directly
adapter = create_adapter("openai", api_key="sk-...", model="gpt-4")

# Option 3: Ollama (local)
adapter = create_adapter("ollama", model="llama3")

# Option 4: Mock (testing)
adapter = create_adapter("mock")

# Create engine with any adapter
engine = create_cognitive_engine(adapter)
```

### With Fallback

```python
# Primary: LLM Gateway, Fallback: Local Ollama
primary = create_adapter("llm_gateway", base_url="http://gateway:8000")
fallback = create_adapter("ollama", model="llama3")

engine = create_cognitive_engine(
    adapter=primary,
    fallback_adapter=fallback
)
```

---

## Project Structure

```
phoenix_agent/
├── __init__.py              # Main exports
├── config.py                # Configuration
├── README.md                # This file
├── requirements.txt         # Dependencies
│
├── cognitive/               # Model-Agnostic Cognitive Layer (v1.3)
│   ├── __init__.py
│   ├── engine.py            # CognitiveEngine abstraction
│   ├── adapters.py          # LLMGateway, OpenAI, Ollama, Mock adapters
│   ├── task_entity.py       # Task Identity, Lifecycle, Cost, History
│   └── request_parser.py    # Request→Task conversion
│
├── platform/                # Platform Layer (v1.1)
│   ├── __init__.py
│   ├── safety_engine.py     # Guardrails & Safety
│   ├── tool_executor.py     # Tool Execution
│   └── environment_adapter.py # External Integration
│
├── core/                    # Cognitive Kernel (v0.3 - v1.0)
│   ├── __init__.py
│   ├── orchestrator.py      # Main orchestrator
│   ├── runtime_controller.py # Agent runtime
│   ├── goal_manager.py      # Goal management
│   ├── planner_engine.py    # Planning
│   ├── decision_engine.py   # Decision making
│   ├── resource_manager.py  # Resource control
│   ├── learning_loop.py     # Learning
│   ├── adaptation_engine.py # Self-evolution
│   ├── agent_registry.py    # Agent population
│   ├── task_graph_executor.py # Graph execution
│   └── ...                  # Other core modules
│
├── contract/                # API Contract
│   ├── __init__.py
│   ├── schemas.py           # Request/Response schemas
│   ├── events.py            # Event types
│   └── session.py           # Session management
│
├── gateway/                 # Gateway Integration
│   ├── __init__.py
│   └── adapter.py           # Gateway adapters
│
├── tools/                   # Tool System
│   ├── __init__.py
│   ├── base.py              # Tool base classes
│   └── registry.py          # Tool registry
│
└── tests/                   # Test Suite
    ├── test_kernel.py
    ├── test_v04_task.py
    ├── test_v05_cognitive.py
    ├── test_v06_runtime.py
    ├── test_v08_integration.py
    ├── test_v11_platform.py
    └── test_v13_cognitive.py
```

---

## Key Components

### CognitiveEngine

The core abstraction that makes Phoenix model-agnostic:

```python
class CognitiveEngine:
    async def reason(problem, constraints) -> ReasoningResult
    async def plan(goal, constraints) -> PlanningResult
    async def evaluate(result, criteria) -> EvaluationResult
    async def summarize(content) -> SummarizationResult
    async def reflect(experience) -> ReflectionResult
    async def decide(options, criteria) -> DecisionResult
```

### TaskEntity

Complete task representation with full traceability:

```python
@dataclass
class TaskEntity:
    identity: TaskIdentity      # task_id, correlation_id, trace_id
    goal: str                   # What to accomplish
    lifecycle: TaskLifecycle    # State machine
    cost: TaskCost              # Token, time, delegation tracking
    dependencies: List[TaskDependency]
    
    def start() -> bool
    def complete(output) -> bool
    def fail(error) -> bool
    def delegate(agent_id) -> bool
```

### AgentRuntimeController

The conductor that orchestrates execution:

```python
controller = create_runtime_controller(
    cognitive_engine=engine,
    goal_manager=goal_manager,
    resource_manager=resource_manager,
)

result = await controller.run(task_graph)
```

---

## Configuration

### Environment Variables

```bash
# Gateway Configuration
PHOENIX_GATEWAY_URL=http://localhost:8000
PHOENIX_GATEWAY_API_KEY=your-key
PHOENIX_GATEWAY_TIMEOUT=120

# Agent Configuration
PHOENIX_MAX_ITERATIONS=10
PHOENIX_ENABLE_THINKING=true
PHOENIX_DEBUG=false
```

### Programmatic Configuration

```python
from phoenix_agent import PhoenixConfig, GatewayConfig, set_config

config = PhoenixConfig(
    debug=True,
    gateway=GatewayConfig(
        base_url="http://your-gateway:8000",
        api_key="your-key",
    ),
)
set_config(config)
```

---

## Testing

```bash
# Run all tests
pytest phoenix_agent/tests/

# Run specific test
pytest phoenix_agent/tests/test_v13_cognitive.py -v

# With coverage
pytest phoenix_agent/tests/ --cov=phoenix_agent
```

---

## Design Principles

1. **Less Features, More Structure** - Focus on stable interfaces, not feature count
2. **Model Independence** - Phoenix never knows the model, only capabilities
3. **Task-Driven** - Phoenix operates on Tasks, not Requests
4. **Full Traceability** - Every task has identity, history, and cost tracking
5. **Graceful Degradation** - Fallback adapters, retry logic, recovery engines

---

## Version History

| Version | Focus |
|---------|-------|
| v0.3 | Core Kernel - Orchestrator, Session, Agent Loop |
| v0.4 | Task Abstraction - TaskManager, Delegation, Memory |
| v0.5 | Self-Awareness - Profile, Capability, Monitoring |
| v0.6 | Runtime - State Machine, Context, Protocol |
| v0.8 | Integration Layer - Controller, Planner, Telemetry |
| v1.0 | Cognitive Deep - Goals, Resources, Learning, Registry |
| v1.1 | Platform Layer - Safety, Tools, Environment |
| v1.2 | Execution Pipeline - Stages, Lifecycle |
| **v1.3** | **Model-Agnostic** - CognitiveEngine, TaskEntity, RequestParser |

---

## License

MIT License

---

## Authors

Phoenix Team
