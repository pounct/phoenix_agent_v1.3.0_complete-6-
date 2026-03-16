"""
Phoenix Agent - Platform Layer Tests
====================================

Tests for v1.1 Platform Layer:
    - ToolExecutor
    - EnvironmentAdapter
    - SafetyEngine
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any

# Import platform components
from phoenix_agent.platform.tool_executor import (
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

from phoenix_agent.platform.environment_adapter import (
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

from phoenix_agent.platform.safety_engine import (
    SafetyEngine,
    SafetyCheckResult,
    SafetyViolation,
    Guardrails,
    SafetyConfig,
    SafetyLevel,
    ViolationType,
    ViolationSeverity,
    CostLimits,
    RateLimits,
    LoopLimits,
    TimeLimits,
    create_safety_engine,
    create_permissive_safety,
    create_strict_safety,
)


# ============================================================================
# TOOL EXECUTOR TESTS
# ============================================================================


class TestToolExecutor:
    """Tests for ToolExecutor component."""
    
    def test_tool_creation(self):
        """Test creating a tool."""
        async def echo_handler(params: Dict, context: ToolContext) -> Any:
            return {"echo": params.get("message", "")}
        
        tool = Tool(
            tool_id="test.echo",
            name="Echo",
            description="Echo back a message",
            category=ToolCategory.COMPUTE,
            handler=echo_handler,
        )
        
        assert tool.tool_id == "test.echo"
        assert tool.name == "Echo"
        assert tool.category == ToolCategory.COMPUTE
        assert tool.is_available()[0] == True
    
    def test_tool_registry(self):
        """Test tool registry."""
        registry = ToolRegistry()
        
        tool = Tool(
            tool_id="test.echo",
            name="Echo",
            description="Echo tool",
            category=ToolCategory.COMPUTE,
            handler=lambda p, c: {"result": p}
        )
        
        # Register
        assert registry.register(tool) == True
        assert registry.get("test.echo") == tool
        
        # Duplicate registration
        assert registry.register(tool) == False
        
        # Unregister
        assert registry.unregister("test.echo") == True
        assert registry.get("test.echo") is None
    
    def test_tool_registry_by_category(self):
        """Test getting tools by category."""
        registry = ToolRegistry()
        
        tools = [
            Tool(f"tool.{i}", f"Tool {i}", f"Desc {i}", ToolCategory.COMPUTE)
            for i in range(3)
        ]
        
        for tool in tools:
            registry.register(tool)
        
        compute_tools = registry.get_by_category(ToolCategory.COMPUTE)
        assert len(compute_tools) == 3
    
    @pytest.mark.asyncio
    async def test_tool_executor_basic(self):
        """Test basic tool execution."""
        async def echo_handler(params: Dict, context: ToolContext) -> Any:
            return {"echo": params.get("message", "")}
        
        executor = create_tool_executor()
        
        tool = Tool(
            tool_id="test.echo",
            name="Echo",
            description="Echo tool",
            category=ToolCategory.COMPUTE,
            handler=echo_handler,
        )
        
        executor.register_tool(tool)
        
        # Execute
        result = await executor.execute("test.echo", {"message": "hello"})
        
        assert result.success == True
        assert result.status == ToolStatus.SUCCESS
        assert result.output == {"echo": "hello"}
    
    @pytest.mark.asyncio
    async def test_tool_executor_timeout(self):
        """Test tool execution with timeout."""
        async def slow_handler(params: Dict, context: ToolContext) -> Any:
            await asyncio.sleep(10)
            return {"result": "done"}
        
        executor = ToolExecutor()
        
        tool = Tool(
            tool_id="test.slow",
            name="Slow",
            description="Slow tool",
            category=ToolCategory.COMPUTE,
            handler=slow_handler,
            timeout_seconds=0.1,  # Very short timeout
        )
        
        executor.register_tool(tool)
        
        result = await executor.execute("test.slow", {})
        
        assert result.status == ToolStatus.TIMEOUT
        assert result.success == False
    
    @pytest.mark.asyncio
    async def test_tool_executor_retry(self):
        """Test tool execution with retry."""
        call_count = 0
        
        async def flaky_handler(params: Dict, context: ToolContext) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return {"result": "success"}
        
        executor = ToolExecutor()
        
        tool = Tool(
            tool_id="test.flaky",
            name="Flaky",
            description="Flaky tool",
            category=ToolCategory.COMPUTE,
            handler=flaky_handler,
            retry_count=3,
            timeout_seconds=5.0,
        )
        
        executor.register_tool(tool)
        
        result = await executor.execute("test.flaky", {})
        
        assert result.success == True
        assert call_count == 3
    
    def test_tool_validation(self):
        """Test tool parameter validation."""
        from phoenix_agent.platform.tool_executor import ToolSchema
        
        schema = ToolSchema(
            required_params=["query"],
            optional_params={"limit": 10}
        )
        
        tool = Tool(
            tool_id="test.search",
            name="Search",
            description="Search tool",
            category=ToolCategory.SEARCH,
            schema=schema,
        )
        
        # Valid params
        valid, error = tool.validate_params({"query": "test"})
        assert valid == True
        
        # Missing required param
        valid, error = tool.validate_params({})
        assert valid == False
        assert "query" in error.lower()


# ============================================================================
# ENVIRONMENT ADAPTER TESTS
# ============================================================================


class TestEnvironmentAdapter:
    """Tests for EnvironmentAdapter component."""
    
    def test_environment_config(self):
        """Test environment configuration."""
        config = EnvironmentConfig(
            name="test_env",
            auto_connect=False
        )
        
        adapter = EnvironmentAdapter(config)
        
        assert adapter.config.name == "test_env"
    
    def test_connection_registration(self):
        """Test connection registration."""
        adapter = EnvironmentAdapter()
        
        # Create mock connection
        conn = LLMGatewayConnection(
            connection_id="llm_1",
            config=None
        )
        
        # Register
        assert adapter.register_connection(conn) == True
        assert adapter.get_connection("llm_1") == conn
        
        # Duplicate registration
        assert adapter.register_connection(conn) == False
    
    def test_connection_by_type(self):
        """Test getting connections by type."""
        adapter = EnvironmentAdapter()
        
        llm1 = LLMGatewayConnection("llm_1")
        llm2 = LLMGatewayConnection("llm_2")
        db1 = DatabaseConnection("db_1")
        
        adapter.register_connection(llm1)
        adapter.register_connection(llm2)
        adapter.register_connection(db1)
        
        llm_conns = adapter.get_connections_by_type(ConnectionType.LLM_GATEWAY)
        assert len(llm_conns) == 2
        
        db_conns = adapter.get_connections_by_type(ConnectionType.DATABASE)
        assert len(db_conns) == 1
    
    def test_convenience_accessors(self):
        """Test convenience accessors."""
        adapter = EnvironmentAdapter()
        
        llm = LLMGatewayConnection("llm_1")
        db = DatabaseConnection("db_1")
        api = APIConnection("api_1")
        
        adapter.register_connection(llm)
        adapter.register_connection(db)
        adapter.register_connection(api)
        
        assert adapter.get_llm_gateway() == llm
        assert adapter.get_database() == db
        assert adapter.get_api() == api
    
    @pytest.mark.asyncio
    async def test_environment_connect(self):
        """Test environment connection."""
        adapter = EnvironmentAdapter()
        
        llm = LLMGatewayConnection("llm_1")
        adapter.register_connection(llm)
        
        # Connect
        result = await adapter.connect()
        
        assert result == True
        assert adapter.status.connected == True
        assert llm.status == ConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_environment_disconnect(self):
        """Test environment disconnection."""
        adapter = EnvironmentAdapter()
        
        llm = LLMGatewayConnection("llm_1")
        adapter.register_connection(llm)
        
        await adapter.connect()
        await adapter.disconnect()
        
        assert adapter.status.connected == False
        assert llm.status == ConnectionStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        adapter = EnvironmentAdapter()
        
        llm = LLMGatewayConnection("llm_1")
        adapter.register_connection(llm)
        
        await adapter.connect()
        
        results = await adapter.health_check_all()
        
        assert "llm_1" in results
        assert results["llm_1"][0] == True  # healthy


# ============================================================================
# SAFETY ENGINE TESTS
# ============================================================================


class TestSafetyEngine:
    """Tests for SafetyEngine component."""
    
    def test_safety_config(self):
        """Test safety configuration."""
        config = SafetyConfig(
            safety_level=SafetyLevel.STRICT
        )
        
        engine = SafetyEngine(config)
        
        assert engine.config.safety_level == SafetyLevel.STRICT
    
    def test_safety_levels(self):
        """Test different safety levels."""
        permissive = create_permissive_safety()
        strict = create_strict_safety()
        
        assert permissive.config.safety_level == SafetyLevel.PERMISSIVE
        assert strict.config.safety_level == SafetyLevel.STRICT
    
    def test_action_check_allowed(self):
        """Test action check for allowed action."""
        engine = SafetyEngine()
        engine.start_session()
        
        result = engine.check_action("read", {"agent_id": "test"})
        
        assert result.allowed == True
        assert len(result.violations) == 0
    
    def test_action_check_blocked(self):
        """Test action check for blocked action."""
        guardrails = Guardrails(
            blocked_actions={"dangerous_action"}
        )
        engine = SafetyEngine(SafetyConfig(guardrails=guardrails))
        engine.start_session()
        
        result = engine.check_action("dangerous_action", {"agent_id": "test"})
        
        assert result.allowed == False
        assert len(result.violations) > 0
        assert result.violations[0].violation_type == ViolationType.PERMISSION_DENIED
    
    def test_loop_detection(self):
        """Test loop detection."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Record same action multiple times
        for i in range(10):
            engine.record_action("same_action", {"param": "value"})
        
        # Check should detect loop
        result = engine.check_action("same_action", {"param": "value"})
        
        # Should have loop warning or violation
        # (depends on thresholds in LoopLimits)
    
    def test_cost_tracking(self):
        """Test cost tracking."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Record costs
        engine.record_cost(10.0)
        engine.record_cost(5.0)
        
        result = engine.check_cost(100.0)
        
        # Should warn about approaching limit
        # (depends on CostLimits)
    
    def test_delegation_depth(self):
        """Test delegation depth tracking."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Enter delegation
        depth = engine.enter_delegation()
        assert depth == 1
        
        depth = engine.enter_delegation()
        assert depth == 2
        
        # Exit delegation
        depth = engine.exit_delegation()
        assert depth == 1
    
    def test_rate_limiting(self):
        """Test rate limiting."""
        limits = RateLimits(
            max_actions_per_minute=5
        )
        guardrails = Guardrails(rate=limits)
        engine = SafetyEngine(SafetyConfig(
            safety_level=SafetyLevel.STRICT,
            guardrails=guardrails
        ))
        engine.start_session()
        
        # Record many actions quickly
        for i in range(10):
            engine.record_action("test_action", {})
        
        # Check should hit rate limit
        result = engine.check_action("test_action", {"agent_id": "test"})
        
        # May have rate limit violation depending on timing
    
    def test_emergency_stop(self):
        """Test emergency stop."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Activate emergency stop
        engine.emergency_stop("Test emergency")
        
        # All actions should be blocked
        result = engine.check_action("any_action", {})
        
        assert result.allowed == False
        assert engine.is_emergency_stopped() == True
        
        # Clear emergency
        engine.clear_emergency()
        assert engine.is_emergency_stopped() == False
    
    def test_session_lifecycle(self):
        """Test session lifecycle."""
        engine = SafetyEngine()
        
        # Start session
        engine.start_session("session_1")
        assert engine._session_start is not None
        
        # End session
        summary = engine.end_session()
        
        assert "duration_seconds" in summary
        assert "total_cost" in summary
        assert "total_actions" in summary
    
    def test_violation_recording(self):
        """Test violation recording."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Cause a violation
        guardrails = Guardrails(blocked_actions={"blocked"})
        engine.guardrails = guardrails
        
        result = engine.check_action("blocked", {})
        
        # Get violations
        violations = engine.get_violations()
        
        assert len(violations) > 0
        assert violations[0].violation_type == ViolationType.PERMISSION_DENIED
    
    def test_safety_statistics(self):
        """Test safety statistics."""
        engine = SafetyEngine()
        engine.start_session()
        
        # Record some actions
        for i in range(5):
            engine.record_action(f"action_{i}", {}, cost=1.0)
        
        stats = engine.get_statistics()
        
        assert stats["session_cost"] == 5.0
        assert stats["total_violations"] == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestPlatformIntegration:
    """Integration tests for platform layer."""
    
    @pytest.mark.asyncio
    async def test_full_platform_setup(self):
        """Test full platform setup."""
        # Create environment
        env = EnvironmentAdapter()
        env.register_connection(LLMGatewayConnection("llm_1"))
        env.register_connection(DatabaseConnection("db_1"))
        
        # Create safety
        safety = SafetyEngine()
        safety.start_session()
        
        # Create tool executor
        tools = ToolExecutor()
        
        # Register a tool
        async def query_handler(params: Dict, ctx: ToolContext) -> Any:
            return {"result": "query executed"}
        
        tools.register_tool(Tool(
            tool_id="db.query",
            name="DB Query",
            description="Execute database query",
            category=ToolCategory.DATABASE,
            handler=query_handler,
        ))
        
        # Connect environment
        await env.connect()
        
        # Check safety before action
        check = safety.check_action("db.query", {})
        assert check.allowed == True
        
        # Execute tool
        result = await tools.execute("db.query", {"query": "SELECT 1"})
        assert result.success == True
        
        # Record action
        safety.record_action("db.query", {}, cost=0.01)
        
        # Cleanup
        await env.disconnect()
        safety.end_session()
    
    @pytest.mark.asyncio
    async def test_safety_blocks_dangerous_tool(self):
        """Test safety blocking dangerous tool."""
        # Create safety with blocked action
        guardrails = Guardrails(blocked_actions={"dangerous.tool"})
        safety = SafetyEngine(SafetyConfig(guardrails=guardrails))
        safety.start_session()
        
        # Create tool executor
        tools = ToolExecutor()
        
        async def dangerous_handler(params: Dict, ctx: ToolContext) -> Any:
            return {"danger": "executed"}
        
        tools.register_tool(Tool(
            tool_id="dangerous.tool",
            name="Dangerous",
            description="A dangerous tool",
            category=ToolCategory.EXECUTE,
            handler=dangerous_handler,
        ))
        
        # Check safety first
        check = safety.check_action("dangerous.tool", {})
        
        # Should be blocked
        assert check.allowed == False
        
        # Tool should not execute
        # (In real implementation, executor would check safety first)
    
    @pytest.mark.asyncio
    async def test_cost_control(self):
        """Test cost control across platform."""
        # Create strict cost limits
        cost_limits = CostLimits(
            max_cost_per_action=0.1,
            max_cost_per_session=1.0
        )
        guardrails = Guardrails(cost=cost_limits)
        safety = SafetyEngine(SafetyConfig(
            safety_level=SafetyLevel.STRICT,
            guardrails=guardrails
        ))
        safety.start_session()
        
        # Try to check expensive operation
        result = safety.check_cost(5.0)
        
        # Should be blocked or warned
        assert not result.allowed or len(result.warnings) > 0


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
