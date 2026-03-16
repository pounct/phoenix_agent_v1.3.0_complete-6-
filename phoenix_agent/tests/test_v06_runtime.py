"""
Phoenix Agent - v0.6 Runtime Abstractions Tests
================================================

Tests for runtime abstraction components.

Version: 0.6.0
"""

import pytest
import asyncio
from datetime import datetime, timedelta

# Import v0.6 components
from phoenix_agent.core.agent_state_machine import (
    AgentStateMachine,
    AgentExecutionState,
    StateTransition,
    TransitionRule,
    StateCategory,
    get_state_category,
)

from phoenix_agent.core.execution_context import (
    ExecutionContext,
    ExecutionSpan,
    ExecutionTraceEvent,
    ExecutionStatus,
    ExecutionEventType,
    DelegationChain,
    ExecutionContextManager,
    create_execution_context,
)

from phoenix_agent.core.agent_protocol import (
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

from phoenix_agent.core.cognitive_memory import (
    CognitiveMemoryManager,
    MemoryItem,
    MemorySnapshot,
    MemoryStats,
    CompressionResult,
    MemoryManagerConfig,
    MemoryStrategy,
    create_memory_manager,
)

from phoenix_agent.core.recovery_engine import (
    RecoveryEngine,
    ErrorContext,
    RecoveryResult,
    RecoveryRule,
    ErrorType,
    RecoveryStrategy,
    create_recovery_engine,
)


# ==========================================
# AGENT STATE MACHINE TESTS
# ==========================================

class TestAgentStateMachine:
    """Tests for AgentStateMachine."""
    
    def test_initial_state(self):
        """Test initial state is IDLE."""
        sm = AgentStateMachine()
        assert sm.current_state == AgentExecutionState.IDLE
        assert sm.previous_state is None
        assert not sm.is_terminal
        assert sm.state_category == StateCategory.INITIAL
    
    def test_valid_transition(self):
        """Test valid state transition."""
        sm = AgentStateMachine()
        
        # Start the state machine (IDLE → INITIALIZING → THINKING)
        assert sm.start()
        
        assert sm.current_state == AgentExecutionState.THINKING
        assert sm.previous_state == AgentExecutionState.INITIALIZING
        assert sm.transition_count == 2
    
    def test_invalid_transition_returns_false(self):
        """Test invalid transition returns False."""
        sm = AgentStateMachine()
        
        # Try to go from IDLE directly to COMPLETED (invalid)
        result = sm.transition(AgentExecutionState.COMPLETED)
        assert result is False
        assert sm.current_state == AgentExecutionState.IDLE
    
    def test_full_execution_cycle(self):
        """Test complete execution cycle."""
        sm = AgentStateMachine()
        
        # Start (IDLE → INITIALIZING → THINKING)
        sm.start()
        assert sm.current_state == AgentExecutionState.THINKING
        
        # THINKING → ACTING
        sm.act()
        assert sm.current_state == AgentExecutionState.ACTING
        
        # ACTING → OBSERVING
        sm.observe()
        assert sm.current_state == AgentExecutionState.OBSERVING
        
        # OBSERVING → COMPLETED
        sm.complete("Task done")
        assert sm.current_state == AgentExecutionState.COMPLETED
        assert sm.is_terminal
    
    def test_delegation_flow(self):
        """Test delegation state flow."""
        sm = AgentStateMachine()
        
        sm.start()  # → THINKING
        sm.delegate(target_agent="specialist-1")  # THINKING → DELEGATING
        assert sm.current_state == AgentExecutionState.DELEGATING
        
        sm.wait_for_results()
        assert sm.current_state == AgentExecutionState.WAITING_RESULTS
        
        sm.receive_results()
        assert sm.current_state == AgentExecutionState.RECEIVING_RESULTS
        
        sm.synthesize()
        assert sm.current_state == AgentExecutionState.SYNTHESIZING
    
    def test_transition_history(self):
        """Test transition history tracking."""
        sm = AgentStateMachine()
        
        sm.start()  # 2 transitions
        sm.act()    # 1 transition
        sm.observe()  # 1 transition
        sm.complete()  # 1 transition
        
        history = sm.get_history()
        assert len(history) == 5
        
        # Check first transition
        first = history[0]
        assert first.from_state == AgentExecutionState.IDLE
        assert first.to_state == AgentExecutionState.INITIALIZING
    
    def test_state_category_classification(self):
        """Test state category classification."""
        assert get_state_category(AgentExecutionState.IDLE) == StateCategory.INITIAL
        assert get_state_category(AgentExecutionState.THINKING) == StateCategory.ACTIVE
        assert get_state_category(AgentExecutionState.WAITING_RESULTS) == StateCategory.WAITING
        assert get_state_category(AgentExecutionState.COMPLETED) == StateCategory.TERMINAL
    
    def test_custom_transition_rule(self):
        """Test adding custom transition rules."""
        sm = AgentStateMachine()
        
        # Add custom transition: allow direct IDLE → THINKING
        sm.allow_transition(
            AgentExecutionState.IDLE,
            AgentExecutionState.THINKING
        )
        
        # Now we can go directly from IDLE to THINKING
        result = sm.transition(AgentExecutionState.THINKING)
        assert result is True
        assert sm.current_state == AgentExecutionState.THINKING
    
    def test_stats(self):
        """Test state machine statistics."""
        sm = AgentStateMachine()
        
        sm.start()  # IDLE → INITIALIZING → THINKING
        sm.act()    # THINKING → ACTING
        sm.observe()  # ACTING → OBSERVING
        sm.complete()  # OBSERVING → COMPLETED
        
        stats = sm.get_stats()
        assert stats["transition_count"] == 5
        assert stats["current_state"] == AgentExecutionState.COMPLETED.value
        assert stats["is_terminal"] is True


# ==========================================
# EXECUTION CONTEXT TESTS
# ==========================================

class TestExecutionContext:
    """Tests for ExecutionContext."""
    
    def test_context_creation(self):
        """Test creating execution context."""
        ctx = create_execution_context(
            task_id="task-123",
            agent_id="agent-main"
        )
        
        assert ctx.task_id == "task-123"
        assert ctx.agent_id == "agent-main"
        assert ctx.status == ExecutionStatus.PENDING
        assert ctx.delegation_depth == 0
    
    def test_context_lifecycle(self):
        """Test context lifecycle."""
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-1")
        
        # Start
        ctx.start()
        assert ctx.status == ExecutionStatus.RUNNING
        assert ctx.is_running
        
        # Complete
        ctx.complete()
        assert ctx.status == ExecutionStatus.COMPLETED
        assert ctx.is_completed
    
    def test_event_tracing(self):
        """Test adding events to trace."""
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-1")
        ctx.start()
        
        # Add events
        ctx.add_event(ExecutionEventType.THINK, "Analyzing task")
        ctx.add_event(ExecutionEventType.ACT, "Calling LLM")
        ctx.add_event(ExecutionEventType.OBSERVE, "Received response")
        
        assert len(ctx.trace) == 4  # STARTED + 3 events
    
    def test_span_management(self):
        """Test execution span management."""
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-1")
        ctx.start()
        
        # Start child span
        span = ctx.start_span("llm_call")
        assert span.name == "llm_call"
        assert span.status == ExecutionStatus.RUNNING
        
        # End span
        ctx.end_span()
        assert span.is_finished
    
    def test_child_context_creation(self):
        """Test creating child context for delegation."""
        parent = ExecutionContext(
            task_id="task-1",
            agent_id="agent-main",
            max_delegation_depth=3
        )
        parent.start()
        
        # Create child
        child = parent.create_child_context(
            task_id="task-1-sub",
            agent_id="agent-specialist"
        )
        
        assert child.parent_task_id == "task-1"
        assert child.parent_context_id == parent.context_id
        assert child.delegation_depth == 1
        assert child.can_delegate
        
        # Parent tracks spawned agents
        assert "agent-specialist" in parent.spawned_agents
    
    def test_delegation_depth_limit(self):
        """Test delegation depth limit."""
        ctx = ExecutionContext(
            task_id="task-1",
            agent_id="agent-1",
            delegation_depth=4,
            max_delegation_depth=5
        )
        
        assert ctx.can_delegate
        
        ctx.delegation_depth = 5
        assert not ctx.can_delegate
    
    def test_memory_snapshot(self):
        """Test memory snapshot in context."""
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-1")
        
        # Take snapshot
        ctx.take_memory_snapshot({"key": "value", "items": [1, 2, 3]})
        
        assert ctx.memory_snapshot is not None
        
        # Restore
        restored = ctx.restore_memory_snapshot()
        assert restored == {"key": "value", "items": [1, 2, 3]}
    
    def test_context_to_dict(self):
        """Test context serialization to dict."""
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-1")
        ctx.start()
        ctx.add_event(ExecutionEventType.THINK, "Thinking...")
        ctx.complete()
        
        data = ctx.to_dict()
        
        assert data["task_id"] == "task-1"
        assert data["agent_id"] == "agent-1"
        assert data["status"] == ExecutionStatus.COMPLETED.value


class TestExecutionContextManager:
    """Tests for ExecutionContextManager."""
    
    def test_context_manager_creation(self):
        """Test creating contexts via manager."""
        manager = ExecutionContextManager()
        
        ctx = manager.create_context(
            task_id="task-1",
            agent_id="agent-1"
        )
        
        assert ctx.task_id == "task-1"
        assert manager.get_active_context() == ctx
    
    def test_context_lookup(self):
        """Test looking up contexts."""
        manager = ExecutionContextManager()
        
        ctx = manager.create_context(task_id="task-1", agent_id="agent-1")
        
        # Lookup by ID
        found = manager.get_context(ctx.context_id)
        assert found == ctx
        
        # Lookup active
        active = manager.get_active_context()
        assert active == ctx


# ==========================================
# AGENT PROTOCOL TESTS
# ==========================================

class TestAgentMessage:
    """Tests for AgentMessage."""
    
    def test_message_creation(self):
        """Test creating a message."""
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="What is the result?"
        )
        
        assert msg.header.sender == "agent-1"
        assert msg.header.receiver == "agent-2"
        assert msg.header.message_type == MessageType.QUERY
        assert msg.payload.content == "What is the result?"
        assert msg.status == MessageStatus.PENDING
    
    def test_delegation_message(self):
        """Test creating a delegation message."""
        msg = create_delegation_message(
            sender="orchestrator",
            receiver="coder-1",
            task_id="task-123",
            task_goal="Implement authentication",
            context="Use OAuth2"
        )
        
        assert msg.header.message_type == MessageType.DELEGATE_REQUEST
        assert msg.payload.task_id == "task-123"
        assert msg.payload.task_goal == "Implement authentication"
        assert msg.is_request
    
    def test_response_message(self):
        """Test creating a response message."""
        original = create_delegation_message(
            sender="orchestrator",
            receiver="coder-1",
            task_id="task-123",
            task_goal="Implement authentication"
        )
        
        response = create_response_message(
            original=original,
            content="Authentication implemented",
            result="Success: OAuth2 implemented",
            success=True
        )
        
        assert response.header.message_type == MessageType.DELEGATE_RESULT
        assert response.header.sender == "coder-1"
        assert response.header.receiver == "orchestrator"
        assert response.header.in_reply_to == original.header.message_id
        assert response.is_response
    
    def test_message_is_request_response(self):
        """Test message type classification."""
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="Test"
        )
        
        assert msg.is_request
        assert not msg.is_response
    
    def test_message_expiration(self):
        """Test message TTL expiration."""
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="Test"
        )
        
        # No TTL
        assert not msg.is_expired


class TestMessageBus:
    """Tests for MessageBus."""
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message."""
        bus = MessageBus()
        
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="Test message"
        )
        
        ack = await bus.send(msg)
        
        assert ack.received
        assert ack.message_id == msg.header.message_id
    
    @pytest.mark.asyncio
    async def test_handler_registration(self):
        """Test registering message handlers."""
        bus = MessageBus()
        received = []
        
        async def handler(msg):
            received.append(msg)
        
        bus.register_handler(MessageType.QUERY, handler)
        
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="Test"
        )
        
        await bus.send(msg)
        
        assert len(received) == 1
        assert received[0].payload.content == "Test"
    
    @pytest.mark.asyncio
    async def test_message_history(self):
        """Test message history tracking."""
        bus = MessageBus()
        
        for i in range(3):
            msg = create_message(
                sender=f"agent-{i}",
                receiver="agent-target",
                message_type=MessageType.QUERY,
                content=f"Message {i}"
            )
            await bus.send(msg)
        
        history = bus.get_history()
        assert len(history) == 3
    
    @pytest.mark.asyncio
    async def test_bus_stats(self):
        """Test bus statistics."""
        bus = MessageBus()
        
        msg = create_message(
            sender="agent-1",
            receiver="agent-2",
            message_type=MessageType.QUERY,
            content="Test"
        )
        
        await bus.send(msg)
        
        stats = bus.get_stats()
        assert stats["total_messages"] == 1


# ==========================================
# COGNITIVE MEMORY MANAGER TESTS
# ==========================================

class TestCognitiveMemoryManager:
    """Tests for CognitiveMemoryManager."""
    
    def test_memory_manager_creation(self):
        """Test creating memory manager."""
        manager = create_memory_manager(max_tokens=4000)
        
        assert manager.config.max_tokens == 4000
    
    def test_memory_analysis(self):
        """Test memory analysis."""
        manager = create_memory_manager(max_tokens=1000)
        
        # Create mock session
        class MockSession:
            messages = [
                type('Message', (), {'content': 'A' * 400, 'role': 'user'})(),
                type('Message', (), {'content': 'B' * 400, 'role': 'assistant'})(),
            ]
        
        session = MockSession()
        stats = manager.analyze(session)
        
        assert stats.total_tokens > 0
        assert stats.utilization > 0
    
    def test_sliding_window_compression(self):
        """Test sliding window compression."""
        manager = create_memory_manager(max_tokens=1000)
        manager.config.window_size = 3
        
        # Create session
        class MockSession:
            messages = [
                type('Message', (), {'content': f'Message {i}', 'role': 'user' if i % 2 == 0 else 'assistant'})()
                for i in range(10)
            ]
        
        session = MockSession()
        
        result, messages = manager.compress(session, strategy=MemoryStrategy.SLIDING_WINDOW)
        
        assert result.success
        assert len(messages) <= 3
        assert result.items_removed > 0
    
    def test_memory_snapshot(self):
        """Test memory snapshot."""
        manager = create_memory_manager()
        
        # Create session with proper message structure
        from datetime import datetime
        
        class MockMessage:
            content = 'Test message content'
            role = 'user'
            timestamp = datetime.utcnow()
        
        class MockSession:
            session_id = "session-1"
            messages = [MockMessage()]
        
        session = MockSession()
        
        # Take snapshot
        snapshot = manager.snapshot(session, reason="Before delegation")
        
        assert snapshot.total_items == 1
        assert snapshot.reason == "Before delegation"


# ==========================================
# RECOVERY ENGINE TESTS
# ==========================================

class TestRecoveryEngine:
    """Tests for RecoveryEngine."""
    
    def test_engine_creation(self):
        """Test creating recovery engine."""
        engine = create_recovery_engine(max_retry_attempts=5)
        
        assert engine.max_retry_attempts == 5
    
    def test_error_context_creation(self):
        """Test creating error context."""
        engine = create_recovery_engine()
        
        error = TimeoutError("LLM call timed out")
        ctx = engine.create_error_context(
            error=error,
            error_type=ErrorType.LLM_TIMEOUT,
            agent_id="agent-1",
            task_id="task-1",
            iteration=3,
            tokens_used=2000
        )
        
        assert ctx.error_type == ErrorType.LLM_TIMEOUT
        assert ctx.agent_id == "agent-1"
        assert ctx.task_id == "task-1"
        assert ctx.iteration == 3
        assert ctx.recoverable
    
    @pytest.mark.asyncio
    async def test_retry_strategy(self):
        """Test retry recovery strategy."""
        engine = create_recovery_engine()
        
        error = engine.create_error_context(
            error=TimeoutError("Timeout"),
            error_type=ErrorType.LLM_TIMEOUT,
            agent_id="agent-1"
        )
        
        result = await engine.recover(error)
        
        assert result.success
        assert result.action == "retry"
    
    @pytest.mark.asyncio
    async def test_fallback_agent_strategy(self):
        """Test fallback agent strategy."""
        engine = create_recovery_engine()
        
        error = engine.create_error_context(
            error=Exception("Low confidence"),
            error_type=ErrorType.AGENT_LOW_CONFIDENCE,
            agent_id="agent-1"
        )
        
        result = await engine.recover(error, context={"fallback_agent": "specialist-1"})
        
        assert result.success
        assert result.fallback_agent_id == "specialist-1"
    
    @pytest.mark.asyncio
    async def test_max_retry_limit(self):
        """Test max retry limit."""
        engine = create_recovery_engine(max_retry_attempts=2)
        
        error = engine.create_error_context(
            error=TimeoutError("Timeout"),
            error_type=ErrorType.LLM_TIMEOUT,
            agent_id="agent-1"
        )
        error.retry_count = 2  # Already at limit
        
        result = await engine.recover(error)
        
        assert not result.success or result.action == "degrade"
    
    @pytest.mark.asyncio
    async def test_non_recoverable_error(self):
        """Test non-recoverable error."""
        engine = create_recovery_engine()
        
        error = engine.create_error_context(
            error=ValueError("Invalid task"),
            error_type=ErrorType.TASK_INVALID,
            agent_id="agent-1"
        )
        
        result = await engine.recover(error)
        
        assert not result.success
        assert result.action == "abort"
    
    @pytest.mark.asyncio
    async def test_custom_recovery_rule(self):
        """Test adding custom recovery rule."""
        engine = create_recovery_engine()
        
        # Add custom rule
        rule = RecoveryRule(
            name="custom_timeout",
            error_types=[ErrorType.LLM_TIMEOUT],
            strategy=RecoveryStrategy.RETRY_IMMEDIATE,
            priority=200  # Higher priority
        )
        engine.add_rule(rule)
        
        error = engine.create_error_context(
            error=TimeoutError("Timeout"),
            error_type=ErrorType.LLM_TIMEOUT,
            agent_id="agent-1"
        )
        
        result = await engine.recover(error)
        
        # Should use our custom rule
        assert result.strategy == RecoveryStrategy.RETRY_IMMEDIATE
    
    @pytest.mark.asyncio
    async def test_recovery_stats(self):
        """Test recovery statistics."""
        engine = create_recovery_engine()
        
        # Trigger some recoveries
        for i in range(3):
            error = engine.create_error_context(
                error=TimeoutError(f"Timeout {i}"),
                error_type=ErrorType.LLM_TIMEOUT,
                agent_id="agent-1"
            )
            await engine.recover(error)
        
        stats = engine.get_stats()
        
        assert stats["total_errors"] == 3
        assert stats["successful_recoveries"] == 3
        assert stats["recovery_rate"] == 1.0


# ==========================================
# INTEGRATION TESTS
# ==========================================

class TestRuntimeIntegration:
    """Integration tests for runtime components."""
    
    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execution flow with all components."""
        # Create state machine
        sm = AgentStateMachine()
        
        # Create execution context
        ctx = ExecutionContext(task_id="task-1", agent_id="agent-main")
        
        # Create memory manager
        memory = create_memory_manager(max_tokens=4000)
        
        # Create recovery engine
        recovery = create_recovery_engine()
        
        # Start execution
        sm.start()
        ctx.start()
        
        # Simulate thinking
        sm.think()
        ctx.add_event(ExecutionEventType.THINK, "Analyzing task")
        
        # Simulate acting
        sm.act()
        ctx.add_event(ExecutionEventType.ACT, "Calling LLM")
        
        # Simulate observing
        sm.observe()
        ctx.add_event(ExecutionEventType.OBSERVE, "Received response")
        
        # Complete
        sm.complete()
        ctx.complete()
        
        # Verify state
        assert sm.is_terminal
        assert ctx.is_completed
        assert len(ctx.trace) == 5  # STARTED + THINK + ACT + OBSERVE + COMPLETED
    
    @pytest.mark.asyncio
    async def test_delegation_flow_with_context(self):
        """Test delegation with execution context tracking."""
        # Parent context
        parent_ctx = ExecutionContext(
            task_id="task-1",
            agent_id="orchestrator",
            max_delegation_depth=3
        )
        parent_ctx.start()
        
        # State machine
        sm = AgentStateMachine()
        sm.start()
        
        # Delegation
        sm.delegate(target_agent="specialist-1")
        parent_ctx.add_event(
            ExecutionEventType.DELEGATE_START,
            "Delegating to specialist"
        )
        
        # Create child context
        child_ctx = parent_ctx.create_child_context(
            task_id="task-1-sub",
            agent_id="specialist-1"
        )
        child_ctx.start()
        
        # Child executes
        child_ctx.add_event(ExecutionEventType.THINK, "Working on subtask")
        child_ctx.complete()
        
        # Parent receives result
        sm.receive_results()
        parent_ctx.record_delegation_result(child_ctx, success=True)
        
        # Parent synthesizes
        sm.synthesize()
        parent_ctx.add_event(ExecutionEventType.DELEGATE_END, "Delegation completed")
        
        # Complete
        sm.complete()
        parent_ctx.complete()
        
        # Verify delegation chain
        assert parent_ctx.delegation_chain is not None
        assert parent_ctx.delegation_chain.total_delegations == 1
        assert len(parent_ctx.spawned_agents) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
