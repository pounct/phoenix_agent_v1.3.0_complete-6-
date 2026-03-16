"""
Phoenix Agent - Tool Executor
=============================

Tool Execution Layer - The "hands" of Phoenix.

Without this layer, Phoenix can only reason.
With this layer, Phoenix can ACT in the real world.

Architecture Decision:
    - Tools are NOT part of cognition
    - Tools are the ACTION layer
    - Cognitive kernel decides WHAT to do
    - ToolExecutor executes HOW to do it

Key Responsibilities:
    1. Execute tools with timeout control
    2. Validate outputs against schemas
    3. Retry with backoff on transient failures
    4. Fallback to alternative tools on failure
    5. Track tool costs and performance
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union
from uuid import uuid4

# ============================================================================
# ENUMERATIONS
# ============================================================================


class ToolStatus(Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ToolCategory(Enum):
    """Categories of tools."""
    # Information
    SEARCH = "search"
    RETRIEVE = "retrieve"
    QUERY = "query"
    
    # Action
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    
    # Communication
    SEND = "send"
    RECEIVE = "receive"
    NOTIFY = "notify"
    
    # Computation
    COMPUTE = "compute"
    ANALYZE = "analyze"
    TRANSFORM = "transform"
    
    # System
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    API = "api"
    LLM = "llm"


class ExecutionMode(Enum):
    """How to execute the tool."""
    SYNC = "sync"              # Block until complete
    ASYNC = "async"            # Return immediately, poll for result
    FIRE_AND_FORGET = "fire"   # Execute without waiting


# ============================================================================
# TOOL DEFINITION
# ============================================================================


@dataclass
class ToolSchema:
    """Schema for tool input/output validation."""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    optional_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate_input(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate input parameters against schema."""
        # Check required parameters
        for param in self.required_params:
            if param not in params:
                return False, f"Missing required parameter: {param}"
        
        # Could add more sophisticated validation here
        return True, None
    
    def validate_output(self, result: Any) -> tuple[bool, Optional[str]]:
        """Validate output against schema."""
        # Basic validation - could be extended
        if self.output_schema:
            # Check type constraints
            expected_type = self.output_schema.get("type")
            if expected_type and not isinstance(result, eval(expected_type)):
                return False, f"Expected type {expected_type}, got {type(result)}"
        return True, None


@dataclass
class ToolCost:
    """Cost model for a tool."""
    base_cost: float = 0.0              # Base cost per execution
    per_token_cost: float = 0.0         # Cost per token (for LLM tools)
    per_byte_cost: float = 0.0          # Cost per byte (for data tools)
    time_cost_factor: float = 0.0       # Cost multiplier per second
    
    def estimate_cost(
        self,
        tokens: int = 0,
        bytes_count: int = 0,
        duration_seconds: float = 0.0
    ) -> float:
        """Estimate total cost for an execution."""
        return (
            self.base_cost +
            (self.per_token_cost * tokens) +
            (self.per_byte_cost * bytes_count) +
            (self.time_cost_factor * duration_seconds)
        )


@dataclass
class ToolReliability:
    """Reliability metrics for a tool."""
    success_rate: float = 1.0           # Historical success rate (0-1)
    avg_latency_ms: float = 0.0         # Average latency
    p99_latency_ms: float = 0.0         # P99 latency
    timeout_rate: float = 0.0           # Timeout rate (0-1)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    
    def is_reliable(self, threshold: float = 0.8) -> bool:
        """Check if tool meets reliability threshold."""
        return (
            self.success_rate >= threshold and
            self.consecutive_failures < 3
        )
    
    def update_success(self, latency_ms: float) -> None:
        """Update metrics after successful execution."""
        self.last_success = datetime.utcnow()
        self.consecutive_failures = 0
        # Simple moving average for latency
        self.avg_latency_ms = (self.avg_latency_ms * 0.9) + (latency_ms * 0.1)
    
    def update_failure(self) -> None:
        """Update metrics after failed execution."""
        self.last_failure = datetime.utcnow()
        self.consecutive_failures += 1
        # Decay success rate
        self.success_rate = max(0.0, self.success_rate - 0.05)


@dataclass
class ToolPermissions:
    """Permissions for tool execution."""
    allowed: bool = True
    requires_approval: bool = False      # Requires human approval
    approval_timeout_seconds: float = 300.0
    allowed_callers: List[str] = field(default_factory=list)  # Agent IDs
    rate_limit_per_minute: int = 60
    max_concurrent: int = 10
    restricted_params: List[str] = field(default_factory=list)
    
    def can_execute(self, caller_id: str) -> tuple[bool, Optional[str]]:
        """Check if caller has permission to execute."""
        if not self.allowed:
            return False, "Tool is not allowed"
        
        if self.allowed_callers and caller_id not in self.allowed_callers:
            return False, f"Caller {caller_id} not in allowed list"
        
        if self.requires_approval:
            return False, "Tool requires approval"
        
        return True, None


@dataclass
class Tool:
    """
    A tool that Phoenix can execute.
    
    Tools are the ACTION layer - they transform decisions into effects.
    
    Attributes:
        tool_id: Unique identifier
        name: Human-readable name
        description: What the tool does
        category: Tool category for routing
        schema: Input/output schemas
        cost: Cost model
        reliability: Reliability metrics
        permissions: Execution permissions
        handler: The actual execution function
        fallback_tools: Alternative tools on failure
        timeout_seconds: Default timeout
        retry_count: Number of retries on failure
        retry_delay_seconds: Delay between retries
    """
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    schema: ToolSchema = field(default_factory=ToolSchema)
    cost: ToolCost = field(default_factory=ToolCost)
    reliability: ToolReliability = field(default_factory=ToolReliability)
    permissions: ToolPermissions = field(default_factory=ToolPermissions)
    handler: Optional[Callable] = None
    fallback_tools: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_delay_seconds: float = 1.0
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate input parameters."""
        return self.schema.validate_input(params)
    
    def estimate_cost(self, **kwargs) -> float:
        """Estimate execution cost."""
        return self.cost.estimate_cost(**kwargs)
    
    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if tool is available for execution."""
        if not self.handler:
            return False, "No handler registered"
        
        if not self.permissions.allowed:
            return False, "Tool not allowed"
        
        if self.reliability.consecutive_failures >= 5:
            return False, "Tool is degraded (too many failures)"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tool metadata."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "reliability": {
                "success_rate": self.reliability.success_rate,
                "avg_latency_ms": self.reliability.avg_latency_ms,
            },
            "permissions": {
                "allowed": self.permissions.allowed,
                "requires_approval": self.permissions.requires_approval,
            },
        }


# ============================================================================
# TOOL CONTEXT
# ============================================================================


@dataclass
class ToolContext:
    """
    Context for a tool execution.
    
    Provides execution context including caller info, session, and metadata.
    """
    context_id: str = field(default_factory=lambda: str(uuid4()))
    caller_id: str = ""
    session_id: str = ""
    task_id: str = ""
    goal_id: str = ""
    execution_id: str = ""
    
    # Parent context reference
    parent_context: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Resource limits for this execution
    max_tokens: Optional[int] = None
    max_time_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context."""
        return {
            "context_id": self.context_id,
            "caller_id": self.caller_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "execution_id": self.execution_id,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# TOOL RESULT
# ============================================================================


@dataclass
class ToolResult:
    """
    Result of a tool execution.
    
    Captures the outcome, timing, and metadata of an execution.
    """
    result_id: str = field(default_factory=lambda: str(uuid4()))
    tool_id: str = ""
    context_id: str = ""
    
    # Status
    status: ToolStatus = ToolStatus.PENDING
    
    # Output
    output: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Validation
    output_valid: bool = True
    validation_error: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    
    # Cost
    tokens_used: int = 0
    bytes_processed: int = 0
    cost: float = 0.0
    
    # Retry info
    attempt: int = 1
    max_attempts: int = 1
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolStatus.SUCCESS and self.output_valid
    
    @property
    def should_retry(self) -> bool:
        """Check if execution should be retried."""
        return (
            self.status in (ToolStatus.FAILED, ToolStatus.TIMEOUT) and
            self.attempt < self.max_attempts
        )
    
    def mark_started(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.utcnow()
        self.status = ToolStatus.RUNNING
    
    def mark_completed(
        self,
        output: Any,
        tokens: int = 0,
        bytes_count: int = 0
    ) -> None:
        """Mark execution as completed successfully."""
        self.output = output
        self.completed_at = datetime.utcnow()
        self.status = ToolStatus.SUCCESS
        self.tokens_used = tokens
        self.bytes_processed = bytes_count
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def mark_failed(self, error: str, error_type: str = None) -> None:
        """Mark execution as failed."""
        self.error = error
        self.error_type = error_type or "ExecutionError"
        self.completed_at = datetime.utcnow()
        self.status = ToolStatus.FAILED
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def mark_timeout(self) -> None:
        """Mark execution as timed out."""
        self.error = "Execution timed out"
        self.error_type = "TimeoutError"
        self.completed_at = datetime.utcnow()
        self.status = ToolStatus.TIMEOUT
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def record_retry(self, reason: str) -> None:
        """Record a retry attempt."""
        self.retry_history.append({
            "attempt": self.attempt,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.attempt += 1
        self.status = ToolStatus.RETRYING
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize result."""
        return {
            "result_id": self.result_id,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "cost": self.cost,
            "attempt": f"{self.attempt}/{self.max_attempts}",
        }


# ============================================================================
# TOOL REGISTRY
# ============================================================================


class ToolRegistry:
    """
    Registry for available tools.
    
    Manages tool registration, lookup, and discovery.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._by_category: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }
        self._by_tag: Dict[str, List[str]] = {}
    
    def register(self, tool: Tool) -> bool:
        """Register a tool."""
        if tool.tool_id in self._tools:
            return False
        
        self._tools[tool.tool_id] = tool
        self._by_category[tool.category].append(tool.tool_id)
        
        for tag in tool.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(tool.tool_id)
        
        return True
    
    def unregister(self, tool_id: str) -> bool:
        """Unregister a tool."""
        if tool_id not in self._tools:
            return False
        
        tool = self._tools.pop(tool_id)
        self._by_category[tool.category].remove(tool_id)
        
        for tag in tool.tags:
            if tag in self._by_tag and tool_id in self._by_tag[tag]:
                self._by_tag[tag].remove(tool_id)
        
        return True
    
    def get(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)
    
    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get all tools in a category."""
        return [self._tools[tid] for tid in self._by_category[category]]
    
    def get_by_tag(self, tag: str) -> List[Tool]:
        """Get all tools with a tag."""
        if tag not in self._by_tag:
            return []
        return [self._tools[tid] for tid in self._by_tag[tag]]
    
    def find_by_capability(self, capability: str) -> List[Tool]:
        """Find tools that provide a capability."""
        results = []
        for tool in self._tools.values():
            if capability.lower() in tool.name.lower() or \
               capability.lower() in tool.description.lower():
                results.append(tool)
            if capability.lower() in [t.lower() for t in tool.tags]:
                results.append(tool)
        return results
    
    def list_all(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_available(self) -> List[Tool]:
        """List all available tools."""
        return [t for t in self._tools.values() if t.is_available()[0]]


# ============================================================================
# TOOL EXECUTOR CONFIG
# ============================================================================


@dataclass
class ToolExecutorConfig:
    """Configuration for ToolExecutor."""
    default_timeout_seconds: float = 30.0
    default_retry_count: int = 2
    default_retry_delay_seconds: float = 1.0
    max_retry_count: int = 5
    
    # Execution limits
    max_concurrent_executions: int = 100
    max_queue_size: int = 1000
    
    # Cost control
    max_cost_per_execution: float = 10.0
    max_total_cost_per_session: float = 100.0
    
    # Timeout backoff
    timeout_backoff_factor: float = 1.5
    
    # Fallback
    enable_fallback: bool = True
    fallback_timeout_multiplier: float = 1.5


# ============================================================================
# TOOL EXECUTOR
# ============================================================================


class ToolExecutor:
    """
    Tool Execution Engine - The "hands" of Phoenix.
    
    This is the ACTION layer. Without it, Phoenix can only reason.
    With it, Phoenix can ACT in the real world.
    
    Responsibilities:
        1. Execute tools with timeout control
        2. Validate outputs
        3. Retry with backoff on transient failures
        4. Fallback to alternatives on failure
        5. Track costs and performance
        6. Enforce permissions and rate limits
    
    Architecture Decision:
        - Tools are NOT part of cognition
        - Cognitive kernel decides WHAT to do
        - ToolExecutor executes HOW to do it
    
    Usage:
        executor = ToolExecutor()
        executor.register_tool(search_tool)
        result = await executor.execute("search", {"query": "hello"})
    """
    
    def __init__(
        self,
        config: ToolExecutorConfig = None,
        registry: ToolRegistry = None
    ):
        self.config = config or ToolExecutorConfig()
        self.registry = registry or ToolRegistry()
        
        # Execution tracking
        self._active_executions: Dict[str, ToolResult] = {}
        self._execution_history: List[ToolResult] = []
        self._max_history = 1000
        
        # Cost tracking
        self._total_cost: float = 0.0
        self._session_costs: Dict[str, float] = {}
        
        # Rate limiting
        self._rate_limits: Dict[str, List[float]] = {}
    
    # ========================================================================
    # Registration
    # ========================================================================
    
    def register_tool(self, tool: Tool) -> bool:
        """Register a tool."""
        return self.registry.register(tool)
    
    def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool."""
        return self.registry.unregister(tool_id)
    
    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.registry.get(tool_id)
    
    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return self.registry.list_all()
    
    def list_available_tools(self) -> List[Tool]:
        """List all available tools."""
        return self.registry.list_available()
    
    # ========================================================================
    # Execution
    # ========================================================================
    
    async def execute(
        self,
        tool_id: str,
        params: Dict[str, Any],
        context: ToolContext = None,
        timeout: float = None,
        retry: bool = True
    ) -> ToolResult:
        """
        Execute a tool.
        
        This is the main entry point for tool execution.
        
        Args:
            tool_id: ID of tool to execute
            params: Parameters for the tool
            context: Execution context
            timeout: Override timeout (None = use tool default)
            retry: Whether to retry on failure
        
        Returns:
            ToolResult with execution outcome
        """
        # Get tool
        tool = self.registry.get(tool_id)
        if not tool:
            result = ToolResult(tool_id=tool_id)
            result.mark_failed(f"Tool not found: {tool_id}", "ToolNotFoundError")
            return result
        
        # Create context if not provided
        if context is None:
            context = ToolContext()
        
        # Check availability
        available, reason = tool.is_available()
        if not available:
            result = ToolResult(
                tool_id=tool_id,
                context_id=context.context_id
            )
            result.mark_failed(reason, "ToolUnavailableError")
            return result
        
        # Check permissions
        can_exec, reason = tool.permissions.can_execute(context.caller_id)
        if not can_exec:
            result = ToolResult(
                tool_id=tool_id,
                context_id=context.context_id
            )
            result.mark_failed(reason, "PermissionError")
            return result
        
        # Validate parameters
        valid, error = tool.validate_params(params)
        if not valid:
            result = ToolResult(
                tool_id=tool_id,
                context_id=context.context_id
            )
            result.mark_failed(error, "ValidationError")
            return result
        
        # Check rate limit
        if not self._check_rate_limit(tool_id, tool.permissions.rate_limit_per_minute):
            result = ToolResult(
                tool_id=tool_id,
                context_id=context.context_id
            )
            result.mark_failed("Rate limit exceeded", "RateLimitError")
            return result
        
        # Create result
        result = ToolResult(
            tool_id=tool_id,
            context_id=context.context_id,
            max_attempts=tool.retry_count + 1 if retry else 1
        )
        
        # Execute with retries
        while True:
            try:
                # Execute with timeout
                exec_timeout = timeout or tool.timeout_seconds
                exec_result = await self._execute_with_timeout(
                    tool, params, context, exec_timeout, result
                )
                
                if exec_result.success or not exec_result.should_retry:
                    break
                
                # Record retry
                exec_result.record_retry(exec_result.error)
                
                # Wait before retry
                delay = tool.retry_delay_seconds * (2 ** (exec_result.attempt - 1))
                await asyncio.sleep(delay)
                
            except asyncio.CancelledError:
                result.status = ToolStatus.CANCELLED
                break
        
        # Update tool reliability
        if result.success:
            tool.reliability.update_success(result.duration_ms)
        else:
            tool.reliability.update_failure()
        
        # Try fallback if failed and fallback enabled
        if not result.success and self.config.enable_fallback and tool.fallback_tools:
            fallback_result = await self._try_fallback(
                tool, params, context, result
            )
            if fallback_result:
                result = fallback_result
        
        # Track cost
        result.cost = tool.cost.estimate_cost(
            tokens=result.tokens_used,
            bytes_count=result.bytes_processed,
            duration_seconds=result.duration_ms / 1000
        )
        self._track_cost(result, context.session_id)
        
        # Record history
        self._record_execution(result)
        
        return result
    
    async def _execute_with_timeout(
        self,
        tool: Tool,
        params: Dict[str, Any],
        context: ToolContext,
        timeout: float,
        result: ToolResult
    ) -> ToolResult:
        """Execute tool with timeout control."""
        result.mark_started()
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(tool.handler):
                output = await asyncio.wait_for(
                    tool.handler(params, context),
                    timeout=timeout
                )
            else:
                # Run sync handler in executor
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: tool.handler(params, context)
                    ),
                    timeout=timeout
                )
            
            # Validate output
            valid, error = tool.schema.validate_output(output)
            result.output_valid = valid
            result.validation_error = error
            
            result.mark_completed(output)
            
        except asyncio.TimeoutError:
            result.mark_timeout()
            
        except Exception as e:
            result.mark_failed(str(e), type(e).__name__)
        
        return result
    
    async def _try_fallback(
        self,
        failed_tool: Tool,
        params: Dict[str, Any],
        context: ToolContext,
        failed_result: ToolResult
    ) -> Optional[ToolResult]:
        """Try fallback tools."""
        for fallback_id in failed_tool.fallback_tools:
            fallback_tool = self.registry.get(fallback_id)
            if not fallback_tool:
                continue
            
            # Try fallback with increased timeout
            fallback_timeout = (
                failed_tool.timeout_seconds * 
                self.config.fallback_timeout_multiplier
            )
            
            fallback_result = await self.execute(
                fallback_id,
                params,
                context,
                timeout=fallback_timeout,
                retry=False
            )
            
            if fallback_result.success:
                # Record that we used fallback
                fallback_result.metadata["fallback_from"] = failed_tool.tool_id
                fallback_result.metadata["fallback_reason"] = failed_result.error
                return fallback_result
        
        return None
    
    # ========================================================================
    # Synchronous Execution
    # ========================================================================
    
    def execute_sync(
        self,
        tool_id: str,
        params: Dict[str, Any],
        context: ToolContext = None,
        timeout: float = None
    ) -> ToolResult:
        """Execute a tool synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.execute(tool_id, params, context, timeout)
        )
    
    # ========================================================================
    # Batch Execution
    # ========================================================================
    
    async def execute_batch(
        self,
        executions: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[ToolResult]:
        """
        Execute multiple tools.
        
        Args:
            executions: List of {tool_id, params, context} dicts
            parallel: Execute in parallel or sequentially
        
        Returns:
            List of ToolResults in same order
        """
        if parallel:
            tasks = [
                self.execute(
                    e["tool_id"],
                    e.get("params", {}),
                    e.get("context")
                )
                for e in executions
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for e in executions:
                result = await self.execute(
                    e["tool_id"],
                    e.get("params", {}),
                    e.get("context")
                )
                results.append(result)
            return results
    
    # ========================================================================
    # Rate Limiting
    # ========================================================================
    
    def _check_rate_limit(self, tool_id: str, limit: int) -> bool:
        """Check if tool is within rate limit."""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Initialize rate limit tracking
        if tool_id not in self._rate_limits:
            self._rate_limits[tool_id] = []
        
        # Clean old entries
        self._rate_limits[tool_id] = [
            t for t in self._rate_limits[tool_id] if t > window_start
        ]
        
        # Check limit
        if len(self._rate_limits[tool_id]) >= limit:
            return False
        
        # Record this execution
        self._rate_limits[tool_id].append(now)
        return True
    
    # ========================================================================
    # Cost Tracking
    # ========================================================================
    
    def _track_cost(self, result: ToolResult, session_id: str) -> None:
        """Track execution cost."""
        self._total_cost += result.cost
        
        if session_id:
            if session_id not in self._session_costs:
                self._session_costs[session_id] = 0.0
            self._session_costs[session_id] += result.cost
    
    def get_total_cost(self) -> float:
        """Get total cost across all executions."""
        return self._total_cost
    
    def get_session_cost(self, session_id: str) -> float:
        """Get cost for a session."""
        return self._session_costs.get(session_id, 0.0)
    
    # ========================================================================
    # History
    # ========================================================================
    
    def _record_execution(self, result: ToolResult) -> None:
        """Record execution in history."""
        self._execution_history.append(result)
        
        # Trim history if needed
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
    
    def get_history(self, limit: int = 100) -> List[ToolResult]:
        """Get execution history."""
        return self._execution_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._execution_history)
        if total == 0:
            return {"total_executions": 0}
        
        successes = sum(1 for r in self._execution_history if r.success)
        failures = total - successes
        avg_duration = sum(r.duration_ms for r in self._execution_history) / total
        total_cost = sum(r.cost for r in self._execution_history)
        
        return {
            "total_executions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total,
            "avg_duration_ms": avg_duration,
            "total_cost": total_cost,
            "registered_tools": len(self.registry.list_all()),
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_tool_executor(
    config: ToolExecutorConfig = None,
    tools: List[Tool] = None
) -> ToolExecutor:
    """Create a configured ToolExecutor."""
    executor = ToolExecutor(config=config)
    
    if tools:
        for tool in tools:
            executor.register_tool(tool)
    
    return executor


def register_tool(
    executor: ToolExecutor,
    tool_id: str,
    name: str,
    handler: Callable,
    category: ToolCategory = ToolCategory.EXECUTE,
    **kwargs
) -> Tool:
    """Create and register a tool with an executor."""
    tool = Tool(
        tool_id=tool_id,
        name=name,
        description=kwargs.get("description", name),
        category=category,
        handler=handler,
        timeout_seconds=kwargs.get("timeout_seconds", 30.0),
        retry_count=kwargs.get("retry_count", 2),
    )
    
    executor.register_tool(tool)
    return tool


# ============================================================================
# BUILT-IN TOOLS
# ============================================================================


def create_builtin_tools() -> List[Tool]:
    """Create built-in tools for Phoenix."""
    tools = []
    
    # Echo tool (for testing)
    async def echo_handler(params: Dict, context: ToolContext) -> Any:
        return {"echo": params.get("message", "")}
    
    tools.append(Tool(
        tool_id="builtin.echo",
        name="Echo",
        description="Echo back a message (testing tool)",
        category=ToolCategory.COMPUTE,
        handler=echo_handler,
        timeout_seconds=5.0,
    ))
    
    # Delay tool (for testing)
    async def delay_handler(params: Dict, context: ToolContext) -> Any:
        delay = params.get("seconds", 1.0)
        await asyncio.sleep(delay)
        return {"slept": delay}
    
    tools.append(Tool(
        tool_id="builtin.delay",
        name="Delay",
        description="Wait for specified seconds",
        category=ToolCategory.COMPUTE,
        handler=delay_handler,
        timeout_seconds=60.0,
    ))
    
    return tools
