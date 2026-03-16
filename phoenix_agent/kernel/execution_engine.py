"""
Execution Engine - The Action Layer
===================================

LAW 1: EXECUTION MUST NEVER REASON.

This is THE ACTION LAYER.

The Execution Engine:
    - Receives Intentions (from Reasoning)
    - Transforms Intentions into Actions
    - Executes Actions (calls tools, APIs)
    - Monitors execution
    - Reports results

Critical Design:
    Execution Engine NEVER reasons.
    Execution Engine NEVER deliberates.
    Execution Engine NEVER decides.

    It ONLY executes.

The Difference:
    Intention: "I want to delegate this task"
    Action: "POST /api/delegate with task_id=X"

    Reasoning produces Intentions.
    Execution transforms to Actions.
    Execution executes Actions.

Why This Separation:
    - Execution can fail safely (cognition isolated)
    - Execution can be sandboxed
    - Execution can be rolled back
    - Cognition stays clean (no execution side effects)

Architecture Position:
    ┌─────────────────┐
    │ Reasoning Loop  │ (thinks, produces intentions)
    └────────┬────────┘
             │
             ▼ Intention
    ┌─────────────────┐
    │Execution Engine │ (acts, executes actions)
    └────────┬────────┘
             │
             ▼ Result
    ┌─────────────────┐
    │   World State   │ (reports results)
    └─────────────────┘

Version: 3.0.0 (Cognitive Kernel)
"""

from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging
import uuid


logger = logging.getLogger("phoenix.kernel.execution")


# ==========================================
# EXECUTION STATUS
# ==========================================

class ExecutionStatus(str, Enum):
    """Status of execution."""
    PENDING = "pending"                 # Not yet started
    PREPARING = "preparing"             # Preparing to execute
    RUNNING = "running"                 # Currently executing
    COMPLETED = "completed"             # Successfully completed
    FAILED = "failed"                   # Execution failed
    TIMEOUT = "timeout"                 # Execution timed out
    CANCELLED = "cancelled"             # Execution cancelled
    ROLLED_BACK = "rolled_back"         # Execution rolled back


class ActionType(str, Enum):
    """Types of actions."""
    TOOL_CALL = "tool_call"             # Call a tool
    API_CALL = "api_call"               # Call external API
    DELEGATION = "delegation"           # Delegate to sub-agent
    INTERNAL = "internal"               # Internal operation
    RECOVERY = "recovery"               # Recovery action
    ROLLBACK = "rollback"               # Rollback action


class ExecutionPriority(str, Enum):
    """Priority of execution."""
    CRITICAL = "critical"               # Must execute immediately
    HIGH = "high"                       # Execute soon
    NORMAL = "normal"                   # Normal execution
    LOW = "low"                         # Can wait
    BACKGROUND = "background"           # Execute when possible


# ==========================================
# ACTION (THE EXECUTION UNIT)
# ==========================================

@dataclass
class Action:
    """
    An ACTION, not an intention.
    
    This is what execution operates on.
    Actions are DERIVED from Intentions.
    
    Difference:
        Intention: "I want to delegate" (internal, cognitive)
        Action: "Call delegation API" (external, execution)
    
    Actions are:
        - External (they affect the world)
        - Concrete (specific implementation)
        - Risky (they can fail)
        - Observable (results can be measured)
    """
    # Identity
    action_id: str
    action_type: ActionType
    
    # Source intention
    intention_id: str
    intention_type: str
    
    # Execution details
    operation: str                      # What operation to perform
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Target
    target: Optional[str] = None
    target_type: Optional[str] = None
    
    # Execution config
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    timeout_ms: float = 30000.0
    max_retries: int = 3
    retry_delay_ms: float = 1000.0
    
    # Rollback
    rollback_action: Optional["Action"] = None
    checkpoint: Optional[Dict[str, Any]] = None
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    attempts: int = 0
    
    # Result
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> float:
        """Get execution duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.ROLLED_BACK,
        ]
    
    @property
    def is_success(self) -> bool:
        """Check if execution succeeded."""
        return self.status == ExecutionStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "intention_id": self.intention_id,
            "operation": self.operation,
            "parameters": self.parameters,
            "target": self.target,
            "priority": self.priority.value,
            "status": self.status.value,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


# ==========================================
# EXECUTION RESULT
# ==========================================

@dataclass
class ExecutionResult:
    """
    Result of executing an action.
    
    This is what execution reports back.
    NO reasoning included - just facts.
    """
    action_id: str
    intention_id: str
    
    # Outcome
    status: ExecutionStatus
    success: bool
    
    # Result data
    output: Optional[Any] = None
    error: Optional[str] = None
    
    # Metrics
    duration_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    
    # Side effects
    state_changes: Dict[str, Any] = field(default_factory=dict)
    artifacts_created: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Retry info
    attempts: int = 1
    final_attempt: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "intention_id": self.intention_id,
            "status": self.status.value,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "error": self.error,
        }


# ==========================================
# EXECUTION PLAN
# ==========================================

@dataclass
class ExecutionPlan:
    """
    A plan of actions to execute.
    
    Created from Intentions, not by reasoning.
    """
    plan_id: str
    actions: List[Action]
    
    # Plan status
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Execution tracking
    current_action_idx: int = 0
    completed_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    
    # Checkpoints for rollback
    checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def progress(self) -> float:
        """Get execution progress."""
        if not self.actions:
            return 0.0
        return len(self.completed_actions) / len(self.actions)
    
    @property
    def current_action(self) -> Optional[Action]:
        """Get current action."""
        if self.current_action_idx < len(self.actions):
            return self.actions[self.current_action_idx]
        return None
    
    def next_action(self) -> Optional[Action]:
        """Get next action."""
        self.current_action_idx += 1
        return self.current_action


# ==========================================
# EXECUTION ENGINE
# ==========================================

class ExecutionEngine:
    """
    THE ACTION LAYER.
    
    This implements LAW 1: Execution must never reason.
    
    The Execution Engine:
        - Receives Intentions (from Reasoning Loop)
        - Transforms Intentions into Actions
        - Executes Actions (safely)
        - Monitors execution
        - Reports results (to World State)
    
    CRITICAL: This NEVER reasons.
    It ONLY executes.
    
    The separation protects:
        - Cognition from execution failures
        - State from cognitive errors
        - Agent from uncontrolled side effects
    
    Architecture Position:
        Reasoning produces Intentions → Execution transforms to Actions
        → Execution runs Actions → Results to World State
    
    Usage:
        engine = ExecutionEngine()
        
        # Register executors
        engine.register_executor(ActionType.TOOL_CALL, tool_executor)
        engine.register_executor(ActionType.DELEGATION, delegation_executor)
        
        # Transform intention to actions
        actions = engine.transform(intention)
        
        # Execute
        results = await engine.execute(actions)
        
        # Results are reported to World State
        # (engine doesn't reason about them)
    
    Executors:
        Executors are external components that implement actual execution.
        They receive Actions and return Results.
        They do NOT reason - they just execute.
    """
    
    def __init__(
        self,
        default_timeout_ms: float = 30000.0,
        max_concurrent: int = 3,
    ):
        self.default_timeout_ms = default_timeout_ms
        self.max_concurrent = max_concurrent
        
        # Registered executors (external)
        self._executors: Dict[ActionType, Callable[[Action], Awaitable[ExecutionResult]]] = {}
        
        # Active executions
        self._active_executions: Dict[str, Action] = {}
        self._execution_queue: asyncio.Queue = asyncio.Queue()
        
        # Execution history
        self._execution_history: List[ExecutionResult] = []
        self._max_history = 500
        
        # Callbacks
        self._on_result: Optional[Callable[[ExecutionResult], None]] = None
        self._on_failure: Optional[Callable[[Action, str], None]] = None
        
        # Statistics
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        
        logger.info("ExecutionEngine initialized (Action Layer)")
    
    # ==========================================
    # EXECUTOR REGISTRATION
    # ==========================================
    
    def register_executor(
        self,
        action_type: ActionType,
        executor: Callable[[Action], Awaitable[ExecutionResult]],
    ) -> None:
        """
        Register an executor for an action type.
        
        Executors are external components that do actual execution.
        They must NOT reason - only execute.
        """
        self._executors[action_type] = executor
        logger.info(f"Registered executor for {action_type.value}")
    
    def unregister_executor(self, action_type: ActionType) -> None:
        """Unregister an executor."""
        if action_type in self._executors:
            del self._executors[action_type]
    
    # ==========================================
    # INTENTION TRANSFORMATION
    # ==========================================
    
    def transform(
        self,
        intention: Any,  # Intention type from reasoning_loop
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Action]:
        """
        Transform an Intention into Actions.
        
        This is the transformation layer between cognition and execution.
        
        IMPORTANT: This does NOT reason about the intention.
        It just transforms structure.
        """
        actions = []
        
        # Get intention attributes
        intention_id = getattr(intention, 'intention_id', 'unknown')
        intention_type = getattr(intention, 'intention_type', 'execute')
        description = getattr(intention, 'description', '')
        target = getattr(intention, 'target', None)
        params = getattr(intention, 'parameters', {})
        priority = getattr(intention, 'priority', 5)
        
        # Map intention type to action type
        action_type_map = {
            'execute': ActionType.TOOL_CALL,
            'delegate': ActionType.DELEGATION,
            'plan': ActionType.INTERNAL,
            'query': ActionType.TOOL_CALL,
            'recover': ActionType.RECOVERY,
            'abort': ActionType.INTERNAL,
            'reflect': ActionType.INTERNAL,
        }
        
        action_type = action_type_map.get(str(intention_type), ActionType.TOOL_CALL)
        
        # Create action
        action = Action(
            action_id=f"act-{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            intention_id=intention_id,
            intention_type=str(intention_type),
            operation=description,
            parameters=params,
            target=target,
            priority=self._map_priority(priority),
        )
        
        # Add rollback if risky
        risk = getattr(intention, 'estimated_risk', 0)
        if risk > 0.5:
            action.checkpoint = context or {}
            action.rollback_action = self._create_rollback_action(action)
        
        actions.append(action)
        
        logger.debug(f"Transformed intention {intention_id} to {len(actions)} actions")
        
        return actions
    
    def _map_priority(self, intention_priority: int) -> ExecutionPriority:
        """Map intention priority to execution priority."""
        if intention_priority >= 9:
            return ExecutionPriority.CRITICAL
        elif intention_priority >= 7:
            return ExecutionPriority.HIGH
        elif intention_priority >= 4:
            return ExecutionPriority.NORMAL
        elif intention_priority >= 2:
            return ExecutionPriority.LOW
        else:
            return ExecutionPriority.BACKGROUND
    
    def _create_rollback_action(self, action: Action) -> Action:
        """Create a rollback action for an action."""
        return Action(
            action_id=f"rb-{uuid.uuid4().hex[:8]}",
            action_type=ActionType.ROLLBACK,
            intention_id=action.intention_id,
            intention_type="rollback",
            operation=f"Rollback: {action.operation}",
            parameters={"original_action_id": action.action_id},
            priority=ExecutionPriority.CRITICAL,
        )
    
    # ==========================================
    # EXECUTION
    # ==========================================
    
    async def execute(
        self,
        actions: List[Action],
    ) -> List[ExecutionResult]:
        """
        Execute a list of actions.
        
        This is THE main execution method.
        
        CRITICAL: This does NOT reason about actions.
        It ONLY executes them using registered executors.
        """
        results = []
        
        for action in actions:
            result = await self._execute_action(action)
            results.append(result)
            
            # Stop on failure unless continuation allowed
            if not result.success and action.priority in [
                ExecutionPriority.CRITICAL,
                ExecutionPriority.HIGH,
            ]:
                break
        
        return results
    
    async def _execute_action(self, action: Action) -> ExecutionResult:
        """Execute a single action."""
        self._total_executions += 1
        self._active_executions[action.action_id] = action
        
        action.status = ExecutionStatus.RUNNING
        action.started_at = datetime.utcnow()
        action.attempts += 1
        
        logger.info(f"Executing action {action.action_id}: {action.operation}")
        
        try:
            # Get executor
            executor = self._executors.get(action.action_type)
            
            if executor is None:
                # No executor registered - simulate
                result = await self._simulate_execution(action)
            else:
                # Execute with timeout
                result = await asyncio.wait_for(
                    executor(action),
                    timeout=action.timeout_ms / 1000.0,
                )
            
            # Update action status
            if result.success:
                action.status = ExecutionStatus.COMPLETED
                action.result = result.output
                self._successful_executions += 1
            else:
                action.status = ExecutionStatus.FAILED
                action.error = result.error
                self._failed_executions += 1
                
                # Retry logic
                if action.attempts < action.max_retries:
                    await asyncio.sleep(action.retry_delay_ms / 1000.0)
                    return await self._execute_action(action)
            
            # Timing
            action.completed_at = datetime.utcnow()
            result.duration_ms = action.duration_ms
            
            # Record history
            self._execution_history.append(result)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]
            
            # Callbacks
            if self._on_result:
                try:
                    self._on_result(result)
                except Exception as e:
                    logger.error(f"Result callback error: {e}")
            
            if not result.success and self._on_failure:
                try:
                    self._on_failure(action, result.error or "Unknown error")
                except Exception as e:
                    logger.error(f"Failure callback error: {e}")
            
            logger.info(
                f"Action {action.action_id} {'SUCCESS' if result.success else 'FAILED'} "
                f"({result.duration_ms:.0f}ms)"
            )
            
            return result
            
        except asyncio.TimeoutError:
            action.status = ExecutionStatus.TIMEOUT
            action.completed_at = datetime.utcnow()
            
            result = ExecutionResult(
                action_id=action.action_id,
                intention_id=action.intention_id,
                status=ExecutionStatus.TIMEOUT,
                success=False,
                error="Execution timed out",
                duration_ms=action.timeout_ms,
                attempts=action.attempts,
            )
            
            self._failed_executions += 1
            self._execution_history.append(result)
            
            return result
            
        except Exception as e:
            action.status = ExecutionStatus.FAILED
            action.completed_at = datetime.utcnow()
            action.error = str(e)
            
            result = ExecutionResult(
                action_id=action.action_id,
                intention_id=action.intention_id,
                status=ExecutionStatus.FAILED,
                success=False,
                error=str(e),
                attempts=action.attempts,
            )
            
            self._failed_executions += 1
            self._execution_history.append(result)
            
            logger.error(f"Action {action.action_id} exception: {e}")
            
            return result
            
        finally:
            if action.action_id in self._active_executions:
                del self._active_executions[action.action_id]
    
    async def _simulate_execution(self, action: Action) -> ExecutionResult:
        """Simulate execution when no executor registered."""
        # Simple simulation for testing
        await asyncio.sleep(0.01)  # Small delay
        
        return ExecutionResult(
            action_id=action.action_id,
            intention_id=action.intention_id,
            status=ExecutionStatus.COMPLETED,
            success=True,
            output={"simulated": True, "operation": action.operation},
            duration_ms=10.0,
        )
    
    # ==========================================
    # EXECUTION CONTROL
    # ==========================================
    
    async def cancel(self, action_id: str) -> bool:
        """Cancel an active execution."""
        if action_id in self._active_executions:
            action = self._active_executions[action_id]
            action.status = ExecutionStatus.CANCELLED
            action.completed_at = datetime.utcnow()
            return True
        return False
    
    async def rollback(self, action_id: str) -> Optional[ExecutionResult]:
        """Rollback a completed action."""
        # Find action in history
        action = None
        for result in reversed(self._execution_history):
            if result.action_id == action_id:
                # Find original action
                if action_id in self._active_executions:
                    action = self._active_executions[action_id]
                break
        
        if action is None or action.rollback_action is None:
            return None
        
        # Execute rollback
        rollback_result = await self._execute_action(action.rollback_action)
        
        # Mark original as rolled back
        action.status = ExecutionStatus.ROLLED_BACK
        
        return rollback_result
    
    # ==========================================
    # STATUS & MONITORING
    # ==========================================
    
    def get_active_executions(self) -> List[Action]:
        """Get currently active executions."""
        return list(self._active_executions.values())
    
    def get_execution_history(self, limit: int = 10) -> List[ExecutionResult]:
        """Get recent execution history."""
        return self._execution_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = self._total_executions
        success_rate = self._successful_executions / total if total > 0 else 0
        
        return {
            "total_executions": total,
            "successful": self._successful_executions,
            "failed": self._failed_executions,
            "success_rate": success_rate,
            "active_executions": len(self._active_executions),
            "registered_executors": list(self._executors.keys()),
        }
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_result(self, callback: Callable[[ExecutionResult], None]) -> None:
        """Set callback for execution results."""
        self._on_result = callback
    
    def on_failure(self, callback: Callable[[Action, str], None]) -> None:
        """Set callback for execution failures."""
        self._on_failure = callback
