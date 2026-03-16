"""
Phoenix Agent - v0.8 Integration Tests
======================================

Tests for the Runtime Integration Layer:
    - AgentRuntimeController
    - PlannerEngine
    - AgentTelemetry

These tests validate that the integration layer correctly
orchestrates all Phoenix components into a cohesive system.

Version: 0.8.0 (Runtime Integration Layer)
"""

import asyncio
import pytest
from datetime import datetime

# Core components
from phoenix_agent.core.runtime_controller import (
    AgentRuntimeController,
    RuntimeConfig,
    RuntimeStatus,
    CycleResult,
    ExecutionCycle,
    create_runtime_controller,
)

from phoenix_agent.core.planner_engine import (
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

from phoenix_agent.core.telemetry import (
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

from phoenix_agent.core.agent_state_machine import (
    AgentStateMachine,
    AgentExecutionState,
)

from phoenix_agent.core.agent_profile import (
    AgentProfile,
    create_default_profile,
)

from phoenix_agent.core.task import Task, TaskComplexity, TaskType


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def agent_profile():
    """Create a test agent profile."""
    return create_default_profile()


@pytest.fixture
def runtime_config():
    """Create a test runtime config."""
    return RuntimeConfig(
        max_cycles=10,
        cycle_delay_ms=0,
        auto_recovery=True,
        enable_telemetry=True,
    )


@pytest.fixture
def telemetry_config():
    """Create a test telemetry config."""
    return TelemetryConfig(
        enabled=True,
        max_events=100,
        max_metrics=100,
        max_traces=50,
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        task_id="test-task-001",
        goal="Build a simple REST API for user management",
        description="Create endpoints for CRUD operations on users",
        complexity=TaskComplexity.MODERATE,
        task_type=TaskType.DEVELOPMENT,
    )


# ==========================================
# TELEMETRY TESTS
# ==========================================

class TestAgentTelemetry:
    """Tests for AgentTelemetry component."""
    
    def test_telemetry_creation(self, telemetry_config):
        """Test telemetry creation."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        assert telemetry.agent_id == "test-agent"
        assert telemetry.config.enabled == True
        assert telemetry.metrics is not None
        assert telemetry.events is not None
        assert telemetry.traces is not None
        assert telemetry.health is not None
    
    def test_cycle_tracking(self, telemetry_config):
        """Test cycle tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        # Start cycle
        telemetry.start_cycle("cycle-001")
        
        # Check metrics
        assert telemetry.metrics.get_counter("cycles_total") == 1
        
        # End cycle
        telemetry.end_cycle(success=True)
        
        assert telemetry.metrics.get_counter("cycles_success") == 1
    
    def test_decision_tracking(self, telemetry_config):
        """Test decision tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        telemetry.record_decision(
            decision="delegate_specialist",
            confidence=0.85,
            triggers=["low_confidence"],
        )
        
        assert telemetry.metrics.get_counter("decisions_total") == 1
        assert telemetry.metrics.get_counter("decisions_delegate_specialist") == 1
    
    def test_delegation_tracking(self, telemetry_config):
        """Test delegation tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        telemetry.record_delegation(
            target_agent="specialist-001",
            task_id="task-001",
            success=True,
        )
        
        assert telemetry.metrics.get_counter("delegations_total") == 1
        assert telemetry.metrics.get_counter("delegations_success") == 1
    
    def test_memory_tracking(self, telemetry_config):
        """Test memory tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        # Record memory utilization
        telemetry.record_memory_utilization(0.75)
        assert telemetry.metrics.get_gauge("memory_utilization") == 0.75
        
        # Record memory operation
        telemetry.record_memory_operation(
            operation="compress",
            tokens_before=1000,
            tokens_after=400,
        )
        
        assert telemetry.metrics.get_counter("memory_operations_compress") == 1
    
    def test_cognitive_tracking(self, telemetry_config):
        """Test cognitive state tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        telemetry.record_cognitive_state(
            confidence=0.8,
            fatigue=0.3,
            load=0.5,
        )
        
        assert telemetry.metrics.get_gauge("cognitive_confidence") == 0.8
        assert telemetry.metrics.get_gauge("cognitive_fatigue") == 0.3
        assert telemetry.metrics.get_gauge("cognitive_load") == 0.5
    
    def test_latency_tracking(self, telemetry_config):
        """Test latency tracking."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        telemetry.record_latency("llm_call", 150.5)
        telemetry.record_latency("llm_call", 200.3)
        telemetry.record_latency("llm_call", 180.7)
        
        stats = telemetry.get_latency_stats("llm_call")
        assert stats["count"] == 3
        assert stats["min"] == 150.5
        assert stats["max"] == 200.3
    
    def test_stats_summary(self, telemetry_config):
        """Test stats summary."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        # Record some activity
        telemetry.start_cycle("cycle-001")
        telemetry.end_cycle(success=True)
        telemetry.record_decision("continue", confidence=0.9)
        
        stats = telemetry.get_stats()
        
        assert "cycles_total" in stats
        assert "decisions_total" in stats
        assert "health_score" in stats
        assert stats["cycles_total"] == 1
    
    def test_health_check(self, telemetry_config):
        """Test health check execution."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        # Run health check
        results = telemetry.run_health_check()
        
        assert "memory" in results
        assert "decisions" in results
        assert "delegations" in results
    
    def test_event_retrieval(self, telemetry_config):
        """Test event retrieval."""
        telemetry = AgentTelemetry(
            agent_id="test-agent",
            config=telemetry_config,
        )
        
        # Log some events
        telemetry.record_state_change("idle", "thinking", "Starting work")
        telemetry.record_state_change("thinking", "acting", "Executing")
        
        # Get events
        events = telemetry.get_events(event_type=EventType.STATE_CHANGE)
        
        assert len(events) >= 2


# ==========================================
# PLANNER ENGINE TESTS
# ==========================================

class TestPlannerEngine:
    """Tests for PlannerEngine component."""
    
    def test_planner_creation(self):
        """Test planner creation."""
        planner = PlannerEngine()
        
        assert planner.default_strategy == DecompositionStrategy.SEQUENTIAL
        assert planner._total_plans == 0
    
    def test_goal_analysis(self):
        """Test goal analysis."""
        planner = PlannerEngine()
        
        analysis = planner._analyze_goal(
            "Build a REST API for user management",
            PlanningContext(goal="Build a REST API for user management"),
        )
        
        assert analysis["type"] == "creation"
        assert len(analysis["keywords"]) > 0
    
    def test_quick_plan(self):
        """Test quick plan creation."""
        plan = create_plan(
            goal="Implement user authentication",
            max_steps=3,
        )
        
        assert plan.total_steps == 3
        assert plan.status == PlanStatus.READY
        assert len(plan.steps) == 3
    
    @pytest.mark.asyncio
    async def test_full_plan(self):
        """Test full plan creation."""
        planner = PlannerEngine()
        
        plan = await planner.plan(
            goal="Create a web scraper for news articles",
            context=PlanningContext(
                goal="Create a web scraper for news articles",
                max_steps=5,
            ),
        )
        
        assert plan is not None
        assert plan.total_steps > 0
        assert plan.status == PlanStatus.READY
        assert len(plan.steps) > 0
    
    def test_plan_step_management(self):
        """Test plan step management."""
        plan = PlanGraph(
            name="Test Plan",
            description="A test plan",
            goal="Test goal",
        )
        
        # Add steps
        step1 = PlanStep(name="Step 1", description="First step")
        step2 = PlanStep(name="Step 2", description="Second step")
        step2.dependencies.append(step1.step_id)
        
        plan.add_step(step1)
        plan.add_step(step2)
        
        assert plan.total_steps == 2
        assert plan.get_step(step1.step_id) is not None
        
        # Mark step running
        plan.mark_step_running(step1.step_id)
        assert plan.get_step(step1.step_id).status == StepStatus.RUNNING
        
        # Complete step
        plan.mark_step_completed(step1.step_id, "Result 1")
        assert plan.get_step(step1.step_id).status == StepStatus.COMPLETED
        assert plan.completed_steps == 1
    
    def test_plan_progress(self):
        """Test plan progress tracking."""
        plan = PlanGraph(
            name="Test Plan",
            goal="Test",
        )
        
        step1 = PlanStep(name="Step 1")
        step2 = PlanStep(name="Step 2")
        
        plan.add_step(step1)
        plan.add_step(step2)
        
        assert plan.progress == 0.0
        
        plan.mark_step_running(step1.step_id)
        plan.mark_step_completed(step1.step_id, "Done")
        
        assert plan.progress == 0.5
    
    def test_plan_get_next_steps(self):
        """Test getting next executable steps."""
        plan = PlanGraph(
            name="Test Plan",
            goal="Test",
        )
        
        step1 = PlanStep(name="Step 1")
        step2 = PlanStep(name="Step 2")
        step2.dependencies.append(step1.step_id)
        
        plan.add_step(step1)
        plan.add_step(step2)
        
        # Initially only step1 should be ready
        next_steps = plan.get_next_steps()
        assert len(next_steps) == 1
        assert next_steps[0].step_id == step1.step_id
        
        # Complete step1
        plan.mark_step_running(step1.step_id)
        plan.mark_step_completed(step1.step_id, "Done")
        
        # Now step2 should be ready
        next_steps = plan.get_next_steps()
        assert len(next_steps) == 1
        assert next_steps[0].step_id == step2.step_id
    
    @pytest.mark.asyncio
    async def test_plan_adaptation(self):
        """Test plan adaptation."""
        planner = PlannerEngine()
        
        # Create initial plan
        plan = await planner.plan(
            goal="Debug a failing test",
            context=PlanningContext(goal="Debug a failing test", max_steps=3),
        )
        
        # Mark a step as failed
        for step in plan.steps.values():
            plan.mark_step_running(step.step_id)
            plan.mark_step_failed(step.step_id, "Something went wrong")
            break
        
        # Adapt the plan
        adapted = await planner.adapt(
            plan,
            reason="Step failed, need alternative approach",
        )
        
        assert adapted.adaptation_count == 1
        assert adapted.original_plan_id == plan.plan_id
    
    def test_decomposition_strategies(self):
        """Test different decomposition strategies."""
        planner = PlannerEngine()
        
        context = PlanningContext(
            goal="Build a feature",
            max_steps=10,
        )
        
        analysis = {"type": "creation"}
        
        # Sequential
        seq_steps = planner._decompose_sequential("Build feature", analysis, context)
        assert len(seq_steps) > 0
        
        # Check dependencies
        for i in range(1, len(seq_steps)):
            assert len(seq_steps[i].dependencies) > 0


# ==========================================
# RUNTIME CONTROLLER TESTS
# ==========================================

class TestAgentRuntimeController:
    """Tests for AgentRuntimeController component."""
    
    def test_controller_creation(self, agent_profile, runtime_config):
        """Test controller creation."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        assert controller.controller_id is not None
        assert controller.config.max_cycles == 10
        assert controller.state_machine is not None
        assert controller.monitor is not None
        assert controller.decision_engine is not None
    
    def test_controller_status(self, agent_profile, runtime_config):
        """Test controller status."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        status = controller.status
        
        assert status.controller_id == controller.controller_id
        assert status.is_running == False
        assert status.current_state == AgentExecutionState.IDLE
    
    @pytest.mark.asyncio
    async def test_tick_cycle(self, agent_profile, runtime_config, sample_task):
        """Test single tick cycle."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        # Start the task
        controller._start(sample_task)
        
        # Execute one tick
        result = await controller.tick()
        
        assert result is not None
        assert result.duration_ms > 0
        assert result.state_before != result.state_after or result.state_before == AgentExecutionState.THINKING
    
    @pytest.mark.asyncio
    async def test_full_run(self, agent_profile, sample_task):
        """Test full task run."""
        config = RuntimeConfig(max_cycles=5)
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=config,
        )
        
        result = await controller.run(sample_task)
        
        assert result is not None
        assert result.task_id == sample_task.task_id
        assert controller._cycle_count <= 5
    
    def test_pause_resume(self, agent_profile, runtime_config, sample_task):
        """Test pause and resume."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        # Start
        controller._start(sample_task)
        assert controller.is_running == True
        
        # Pause
        controller.pause()
        assert controller.is_paused == True
        
        # Resume
        controller.resume()
        assert controller.is_paused == False
    
    def test_abort(self, agent_profile, runtime_config, sample_task):
        """Test abort."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        controller._start(sample_task)
        controller.abort("Test abort")
        
        assert controller.current_state == AgentExecutionState.ABORTED
        assert controller.is_running == False
    
    def test_callbacks(self, agent_profile, runtime_config, sample_task):
        """Test callback registration."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        events = []
        
        def on_state_change(old, new):
            events.append(("state", old.value, new.value))
        
        controller.on_state_change(on_state_change)
        
        # Trigger state change
        controller._start(sample_task)
        
        # Check callback was called
        assert len(events) > 0
    
    def test_get_stats(self, agent_profile, runtime_config):
        """Test getting statistics."""
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=runtime_config,
        )
        
        stats = controller.get_stats()
        
        assert "controller_id" in stats
        assert "status" in stats
        assert "state_machine" in stats
        assert "decision_engine" in stats


# ==========================================
# INTEGRATION TESTS
# ==========================================

class TestIntegration:
    """Integration tests for all v0.8 components together."""
    
    def test_full_stack_integration(self, agent_profile, telemetry_config):
        """Test all components working together."""
        # Create telemetry
        telemetry = AgentTelemetry(
            agent_id="integration-test",
            config=telemetry_config,
        )
        
        # Create planner
        planner = PlannerEngine()
        
        # Create runtime controller with telemetry
        config = RuntimeConfig(max_cycles=3)
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=config,
        )
        
        # Verify all components are connected
        assert controller.state_machine is not None
        assert controller.monitor is not None
        assert controller.decision_engine is not None
        assert controller.delegation_engine is not None
        assert controller.recovery_engine is not None
        
        # Test telemetry tracking
        telemetry.start_cycle("integration-cycle")
        telemetry.record_decision("continue", confidence=0.9)
        telemetry.end_cycle(success=True)
        
        stats = telemetry.get_stats()
        assert stats["cycles_total"] == 1
        assert stats["decisions_total"] == 1
    
    @pytest.mark.asyncio
    async def test_plan_and_execute(self, agent_profile):
        """Test planning and execution flow."""
        planner = PlannerEngine()
        
        # Create plan
        plan = await planner.plan(
            goal="Write a Python function to calculate fibonacci",
            context=PlanningContext(
                goal="Write a Python function to calculate fibonacci",
                max_steps=4,
            ),
        )
        
        assert plan.total_steps > 0
        
        # Simulate execution
        for step_id in plan.step_order[:2]:
            step = plan.get_step(step_id)
            plan.mark_step_running(step_id)
            plan.mark_step_completed(step_id, f"Completed: {step.name}")
        
        assert plan.progress > 0
    
    def test_state_machine_with_telemetry(self, telemetry_config):
        """Test state machine events with telemetry."""
        telemetry = AgentTelemetry(
            agent_id="state-test",
            config=telemetry_config,
        )
        
        state_machine = AgentStateMachine()
        
        # Track state changes
        def track_state(old, new):
            telemetry.record_state_change(old.value, new.value)
        
        state_machine.on_state_change(track_state)
        
        # Execute transitions
        state_machine.start()
        state_machine.act()
        state_machine.observe()
        
        # Check events
        events = telemetry.get_events(event_type=EventType.STATE_CHANGE)
        assert len(events) >= 2
    
    def test_health_monitoring_integration(self, telemetry_config):
        """Test health monitoring with telemetry."""
        telemetry = AgentTelemetry(
            agent_id="health-test",
            config=telemetry_config,
        )
        
        # Simulate some load
        telemetry.record_memory_utilization(0.5)
        telemetry.record_cognitive_state(confidence=0.8, fatigue=0.3, load=0.6)
        telemetry.record_decision("continue", confidence=0.9)
        
        # Run health check
        health = telemetry.run_health_check()
        
        assert telemetry.health.get_overall_health() > 0.5


# ==========================================
# RUN TESTS
# ==========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
