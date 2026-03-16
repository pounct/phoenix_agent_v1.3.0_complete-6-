"""
Phoenix Agent - v1.3 Cognitive Abstraction Tests
=================================================

Tests for the model-agnostic cognitive layer.

Key test areas:
    1. CognitiveEngine abstraction
    2. Cognitive adapters (Mock, LLMGateway, etc.)
    3. Task Entity system
    4. Request Parser and Task Builder

Version: 1.3.0
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any

# Import cognitive components
from phoenix_agent.cognitive.engine import (
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

from phoenix_agent.cognitive.adapters import (
    MockCognitiveAdapter,
    LLMGatewayAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    AdapterConfig,
    AdapterStatus,
    create_adapter,
)

from phoenix_agent.cognitive.task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycle,
    TaskLifecycleState,
    TaskLifecycleCategory,
    TaskHistory,
    TaskCost,
    TaskDependency,
    TaskDependencyType,
    STATE_CATEGORIES,
    VALID_TRANSITIONS,
    create_task_entity,
    create_task_identity,
)

from phoenix_agent.cognitive.request_parser import (
    RequestParser,
    TaskBuilder,
    RequestAnalysis,
    RequestType,
    RequestIntent,
    RequestComplexity,
    TaskGraph,
    TaskNode,
    create_request_parser,
    create_task_builder,
)


# ============================================================================
# COGNITIVE ENGINE TESTS
# ============================================================================


class TestCognitiveEngine:
    """Test CognitiveEngine with mock adapter."""
    
    def test_create_cognitive_engine(self):
        """Test creating a cognitive engine."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        assert engine.adapter is adapter
        assert engine.supports(CognitiveCapability.REASON)
        assert engine.supports(CognitiveCapability.PLAN)
    
    def test_cognitive_engine_reason(self):
        """Test reasoning capability."""
        adapter = MockCognitiveAdapter(
            response_content="Test reasoning result",
            confidence=0.9
        )
        engine = CognitiveEngine(adapter=adapter)
        
        # Run async test
        async def run_test():
            result = await engine.reason(
                problem="What is 2+2?",
                constraints=["Must be a number"]
            )
            
            assert result.success
            assert result.output == "Test reasoning result"
            assert result.confidence == 0.9
            assert result.provider == "mock"
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_plan(self):
        """Test planning capability."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        async def run_test():
            result = await engine.plan(
                goal="Create a web application",
                constraints=["Use Python", "FastAPI"]
            )
            
            assert result.success
            assert len(result.steps) > 0
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_evaluate(self):
        """Test evaluation capability."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        async def run_test():
            result = await engine.evaluate(
                result="The code works correctly",
                criteria=["Correctness", "Performance"]
            )
            
            assert result.success
            assert result.score >= 0.0
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_summarize(self):
        """Test summarization capability."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        async def run_test():
            result = await engine.summarize(
                content="This is a long text that needs summarization. " * 10,
                max_length=100
            )
            
            assert result.success
            assert result.summary is not None
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_reflect(self):
        """Test reflection capability."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        async def run_test():
            result = await engine.reflect(
                experience="Completed a complex task",
                outcome="Success with some issues"
            )
            
            assert result.success
            assert len(result.insights) > 0
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_decide(self):
        """Test decision capability."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        async def run_test():
            result = await engine.decide(
                options=[
                    {"name": "Option A", "score": 0.8},
                    {"name": "Option B", "score": 0.6},
                ],
                criteria=["Efficiency", "Cost"]
            )
            
            assert result.success
            assert result.chosen_option is not None
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_cognitive_engine_stats(self):
        """Test engine statistics."""
        adapter = MockCognitiveAdapter()
        engine = CognitiveEngine(adapter=adapter)
        
        stats = engine.get_stats()
        
        assert stats["provider"] == "mock"
        assert stats["request_count"] == 0
        assert "capabilities" in stats


# ============================================================================
# COGNITIVE ADAPTER TESTS
# ============================================================================


class TestCognitiveAdapters:
    """Test cognitive adapter implementations."""
    
    def test_mock_adapter_basic(self):
        """Test mock adapter basic functionality."""
        adapter = MockCognitiveAdapter(
            response_content="Mock response",
            confidence=0.85
        )
        
        assert adapter.provider_name == "mock"
        assert adapter.supports(CognitiveCapability.REASON)
        
        async def run_test():
            result = await adapter.reason(ReasoningRequest(problem="Test"))
            assert result.success
            assert result.confidence == 0.85
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_mock_adapter_health_check(self):
        """Test mock adapter health check."""
        adapter = MockCognitiveAdapter()
        
        async def run_test():
            healthy = await adapter.health_check()
            assert healthy is True
            return healthy
        
        asyncio.run(run_test())
    
    def test_create_adapter_factory(self):
        """Test adapter factory function."""
        # Create mock adapter
        mock = create_adapter("mock")
        assert mock.provider_name == "mock"
        
        # Create with custom config
        mock2 = create_adapter("mock", response_content="Custom response")
        assert mock2.response_content == "Custom response"


# ============================================================================
# TASK ENTITY TESTS
# ============================================================================


class TestTaskIdentity:
    """Test task identity system."""
    
    def test_create_task_identity(self):
        """Test creating task identity."""
        identity = create_task_identity(
            name="Test Task",
            session_id="session-123"
        )
        
        assert identity.name == "Test Task"
        assert identity.session_id == "session-123"
        assert identity.task_id is not None
        assert identity.correlation_id is not None
        assert identity.trace_id is not None
    
    def test_task_identity_is_root(self):
        """Test root task detection."""
        identity = TaskIdentity(name="Root Task")
        
        assert identity.is_root is True
        assert identity.is_subtask is False
    
    def test_task_identity_create_child(self):
        """Test creating child identity."""
        parent = create_task_identity(name="Parent Task")
        child = parent.create_child_identity(name="Child Task")
        
        assert child.parent_task_id == parent.task_id
        assert child.root_task_id == parent.task_id
        assert child.is_subtask is True
        assert child.correlation_id == parent.correlation_id
        assert child.trace_id == parent.trace_id


class TestTaskLifecycle:
    """Test task lifecycle management."""
    
    def test_lifecycle_initial_state(self):
        """Test initial lifecycle state."""
        lifecycle = TaskLifecycle()
        
        assert lifecycle.state == TaskLifecycleState.CREATED
        assert lifecycle.category == TaskLifecycleCategory.INITIAL
        assert not lifecycle.is_terminal
    
    def test_lifecycle_valid_transition(self):
        """Test valid state transition."""
        lifecycle = TaskLifecycle()
        
        # CREATED -> VALIDATED
        assert lifecycle.can_transition_to(TaskLifecycleState.VALIDATED)
        assert lifecycle.transition(TaskLifecycleState.VALIDATED, "Task validated")
        
        assert lifecycle.state == TaskLifecycleState.VALIDATED
    
    def test_lifecycle_invalid_transition(self):
        """Test invalid state transition."""
        lifecycle = TaskLifecycle()
        
        # Cannot go directly from CREATED to EXECUTING
        assert not lifecycle.can_transition_to(TaskLifecycleState.EXECUTING)
        assert not lifecycle.transition(TaskLifecycleState.EXECUTING)
        
        assert lifecycle.state == TaskLifecycleState.CREATED
    
    def test_lifecycle_history(self):
        """Test lifecycle history tracking."""
        lifecycle = TaskLifecycle()
        
        lifecycle.transition(TaskLifecycleState.VALIDATED, "Validated")
        lifecycle.transition(TaskLifecycleState.QUEUED, "Queued")
        
        history = lifecycle.history
        transitions = history.get_state_transitions()
        
        assert len(transitions) == 2
    
    def test_lifecycle_terminal_state(self):
        """Test terminal state detection."""
        lifecycle = TaskLifecycle()
        
        lifecycle.transition(TaskLifecycleState.VALIDATED)
        lifecycle.transition(TaskLifecycleState.QUEUED)
        lifecycle.transition(TaskLifecycleState.EXECUTING)
        lifecycle.transition(TaskLifecycleState.COMPLETED, "Done")
        
        assert lifecycle.is_terminal
        assert lifecycle.state == TaskLifecycleState.COMPLETED


class TestTaskCost:
    """Test task cost tracking."""
    
    def test_task_cost_tracking(self):
        """Test cost tracking."""
        cost = TaskCost()
        
        cost.add_tokens(input_tokens=100, output_tokens=50)
        cost.add_delegation()
        cost.add_retry()
        cost.add_api_call()
        
        assert cost.input_tokens == 100
        assert cost.output_tokens == 50
        assert cost.total_tokens == 150
        assert cost.delegation_count == 1
        assert cost.retry_count == 1
        assert cost.api_calls == 1
    
    def test_task_cost_merge(self):
        """Test cost merging."""
        cost1 = TaskCost(input_tokens=100, output_tokens=50)
        cost2 = TaskCost(input_tokens=200, output_tokens=100)
        
        cost1.merge(cost2)
        
        assert cost1.input_tokens == 300
        assert cost1.output_tokens == 150
        assert cost1.total_tokens == 450


class TestTaskEntity:
    """Test complete task entity."""
    
    def test_create_task_entity(self):
        """Test creating a task entity."""
        task = create_task_entity(
            goal="Test goal",
            description="Test description",
            priority=8
        )
        
        assert task.goal == "Test goal"
        assert task.priority == 8
        assert task.state == TaskLifecycleState.CREATED
        assert task.identity.name == "Test goal"
    
    def test_task_entity_lifecycle(self):
        """Test task entity lifecycle transitions."""
        task = create_task_entity(goal="Test task")
        
        # Start
        assert task.start()
        assert task.state == TaskLifecycleState.EXECUTING
        assert task.started_at is not None
        
        # Complete
        assert task.complete("Test output")
        assert task.state == TaskLifecycleState.COMPLETED
        assert task.output == "Test output"
    
    def test_task_entity_failure(self):
        """Test task entity failure handling."""
        task = create_task_entity(goal="Test task")
        
        task.start()
        assert task.fail("Test error")
        
        assert task.state == TaskLifecycleState.FAILED
        assert task.error == "Test error"
    
    def test_task_entity_create_subtask(self):
        """Test creating subtask."""
        parent = create_task_entity(goal="Parent task")
        child = parent.create_subtask(goal="Child task")
        
        assert child.is_subtask
        assert child.identity.parent_task_id == parent.task_id
        assert child.identity.root_task_id == parent.task_id
    
    def test_task_entity_dependencies(self):
        """Test task dependencies."""
        task = create_task_entity(goal="Test task")
        dep_task_id = "dep-task-123"
        
        task.add_dependency(dep_task_id, TaskDependencyType.HARD)
        
        assert len(task.dependencies) == 1
        assert task.dependencies[0].task_id == dep_task_id
        
        # Check dependency satisfaction
        assert not task.check_dependencies_satisfied(set())
        assert task.check_dependencies_satisfied({dep_task_id})


# ============================================================================
# REQUEST PARSER TESTS
# ============================================================================


class TestRequestParser:
    """Test request parsing."""
    
    def test_parse_simple_request(self):
        """Test parsing a simple request."""
        parser = create_request_parser()
        analysis = parser.parse("What is the weather?")
        
        assert analysis.detected_intent == RequestIntent.QUERY
        assert analysis.complexity == RequestComplexity.SIMPLE
        assert analysis.confidence > 0
    
    def test_parse_complex_request(self):
        """Test parsing a complex request."""
        parser = create_request_parser()
        analysis = parser.parse(
            "Please analyze this codebase, identify performance bottlenecks, "
            "create a detailed report with recommendations, and implement the fixes"
        )
        
        assert analysis.requires_decomposition
        assert analysis.complexity in [RequestComplexity.COMPLEX, RequestComplexity.EXPERT]
    
    def test_parse_with_metadata(self):
        """Test parsing with metadata."""
        parser = create_request_parser()
        analysis = parser.parse(
            "Create a report",
            metadata={"priority": 8, "deadline": "tomorrow"}
        )
        
        assert analysis.priority == 8
    
    def test_intent_detection(self):
        """Test intent detection patterns."""
        parser = create_request_parser()
        
        # Query intent
        query = parser.parse("What is machine learning?")
        assert query.detected_intent == RequestIntent.QUERY
        
        # Command intent
        command = parser.parse("Create a new file")
        assert command.detected_intent == RequestIntent.CREATION
        
        # Analysis intent
        analysis = parser.parse("Analyze the performance data")
        assert analysis.detected_intent == RequestIntent.ANALYSIS


class TestTaskBuilder:
    """Test task building from requests."""
    
    def test_build_single_task(self):
        """Test building a single task."""
        builder = create_task_builder()
        task = builder.build_single_task(
            goal="Test goal",
            description="Test description"
        )
        
        assert task.goal == "Test goal"
        assert task.state == TaskLifecycleState.VALIDATED
    
    def test_build_from_analysis(self):
        """Test building task graph from analysis."""
        parser = create_request_parser()
        builder = create_task_builder()
        
        analysis = parser.parse("Analyze the code and create a report")
        graph = builder.build_from_analysis(analysis)
        
        assert graph.total_tasks >= 1
        assert graph.root_task_id is not None
    
    def test_build_delegation_task(self):
        """Test building a delegation task."""
        builder = create_task_builder()
        task = builder.build_delegation_task(
            goal="Expert analysis",
            target_agent="code-expert"
        )
        
        assert task.assigned_agent == "code-expert"
        assert "delegation" in task.description.lower()


class TestTaskGraph:
    """Test task graph functionality."""
    
    def test_create_task_graph(self):
        """Test creating a task graph."""
        graph = TaskGraph()
        
        task1 = create_task_entity(goal="Task 1")
        task2 = create_task_entity(goal="Task 2")
        
        graph.add_task(task1)
        graph.add_task(task2, dependencies=[task1.task_id])
        
        assert graph.total_tasks == 2
        assert len(graph.nodes[task2.task_id].dependencies) == 1
    
    def test_execution_order(self):
        """Test execution order calculation."""
        graph = TaskGraph()
        
        task1 = create_task_entity(goal="Task 1")
        task2 = create_task_entity(goal="Task 2")
        task3 = create_task_entity(goal="Task 3")
        
        graph.add_task(task1)
        graph.add_task(task2, dependencies=[task1.task_id])
        graph.add_task(task3, dependencies=[task2.task_id])
        
        order = graph.calculate_execution_order()
        
        assert order.index(task1.task_id) < order.index(task2.task_id)
        assert order.index(task2.task_id) < order.index(task3.task_id)
    
    def test_parallel_groups(self):
        """Test parallel group identification."""
        graph = TaskGraph()
        
        # Root task
        root = create_task_entity(goal="Root")
        graph.add_task(root)
        
        # Two independent tasks
        task1 = create_task_entity(goal="Parallel 1")
        task2 = create_task_entity(goal="Parallel 2")
        graph.add_task(task1, dependencies=[root.task_id])
        graph.add_task(task2, dependencies=[root.task_id])
        
        groups = graph.identify_parallel_groups()
        
        # Find tasks at same depth
        assert len(groups) >= 2
    
    def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        graph = TaskGraph()
        
        task1 = create_task_entity(goal="Task 1")
        task2 = create_task_entity(goal="Task 2")
        
        graph.add_task(task1)
        graph.add_task(task2, dependencies=[task1.task_id])
        
        # Initially only task1 is ready
        ready = graph.get_ready_tasks(set())
        assert len(ready) == 1
        assert ready[0].task_id == task1.task_id
        
        # After task1 completes, task2 is ready
        task1.complete("Done")
        ready = graph.get_ready_tasks({task1.task_id})
        assert len(ready) == 1
        assert ready[0].task_id == task2.task_id


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for cognitive layer."""
    
    def test_full_request_to_task_flow(self):
        """Test full flow from request to task graph."""
        parser = create_request_parser()
        builder = create_task_builder()
        
        # Parse request
        analysis = parser.parse(
            "Create a comprehensive analysis of the system architecture "
            "and provide recommendations for improvement"
        )
        
        # Build task graph
        graph = builder.build_from_analysis(analysis)
        
        assert graph.total_tasks > 0
        assert graph.root_task_id is not None
        
        # Verify execution order exists
        order = graph.calculate_execution_order()
        assert len(order) > 0
    
    def test_cognitive_engine_with_mock(self):
        """Test cognitive engine end-to-end with mock."""
        adapter = MockCognitiveAdapter(
            response_content="Detailed analysis result",
            confidence=0.9
        )
        engine = create_cognitive_engine(adapter)
        
        async def run_test():
            # Reason
            reasoning = await engine.reason("Test problem")
            assert reasoning.success
            
            # Plan
            planning = await engine.plan(goal="Test goal")
            assert planning.success
            
            # Stats
            stats = engine.get_stats()
            assert stats["request_count"] == 2
            
            return True
        
        result = asyncio.run(run_test())
        assert result


if __name__ == "__main__":
    # Run tests manually
    print("Running v1.3 Cognitive Abstraction Tests...")
    
    # Engine tests
    print("\nTesting CognitiveEngine...")
    test_engine = TestCognitiveEngine()
    test_engine.test_create_cognitive_engine()
    test_engine.test_cognitive_engine_reason()
    test_engine.test_cognitive_engine_plan()
    print("  ✓ CognitiveEngine tests passed")
    
    # Adapter tests
    print("\nTesting CognitiveAdapters...")
    test_adapters = TestCognitiveAdapters()
    test_adapters.test_mock_adapter_basic()
    test_adapters.test_mock_adapter_health_check()
    test_adapters.test_create_adapter_factory()
    print("  ✓ CognitiveAdapter tests passed")
    
    # Task entity tests
    print("\nTesting TaskEntity...")
    test_identity = TestTaskIdentity()
    test_identity.test_create_task_identity()
    test_identity.test_task_identity_is_root()
    test_identity.test_task_identity_create_child()
    
    test_lifecycle = TestTaskLifecycle()
    test_lifecycle.test_lifecycle_initial_state()
    test_lifecycle.test_lifecycle_valid_transition()
    test_lifecycle.test_lifecycle_invalid_transition()
    
    test_entity = TestTaskEntity()
    test_entity.test_create_task_entity()
    test_entity.test_task_entity_lifecycle()
    test_entity.test_task_entity_create_subtask()
    print("  ✓ TaskEntity tests passed")
    
    # Request parser tests
    print("\nTesting RequestParser...")
    test_parser = TestRequestParser()
    test_parser.test_parse_simple_request()
    test_parser.test_parse_complex_request()
    test_parser.test_intent_detection()
    
    test_builder = TestTaskBuilder()
    test_builder.test_build_single_task()
    test_builder.test_build_from_analysis()
    
    test_graph = TestTaskGraph()
    test_graph.test_create_task_graph()
    test_graph.test_execution_order()
    print("  ✓ RequestParser tests passed")
    
    # Integration tests
    print("\nTesting Integration...")
    test_integration = TestIntegration()
    test_integration.test_full_request_to_task_flow()
    test_integration.test_cognitive_engine_with_mock()
    print("  ✓ Integration tests passed")
    
    print("\n✅ All v1.3 tests passed!")
