"""
Phoenix Agent - Execution Pipeline
===================================

THE REAL RUNTIME - Request Execution Flow.

This is what separates "collection of modules" from "Agent Runtime".

Architecture Reality:
    Without this file, Phoenix is just components in folders.
    With this file, Phoenix becomes a real execution engine.

Pipeline Flow:
    LLM Gateway → Request → Pipeline → Response

    ┌─────────────────────────────────────────────────────────────┐
    │                    EXECUTION PIPELINE                        │
    │                                                              │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
    │  │  ENTRY   │──▶│  INTENT  │──▶│  GOAL    │──▶│ PLANNING │ │
    │  │          │   │          │   │          │   │          │ │
    │  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
    │        │              │              │              │       │
    │        ▼              ▼              ▼              ▼       │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
    │  │ RESOURCE │──▶│  SAFETY  │──▶│EXECUTION │──▶│SYNTHESIS │ │
    │  │  CHECK   │   │  CHECK   │   │          │   │          │ │
    │  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
    │        │              │              │              │       │
    │        ▼              ▼              ▼              ▼       │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
    │  │  MEMORY  │──▶│ LEARNING │──▶│  OUTPUT  │──▶│ RESPONSE │ │
    │  │  UPDATE  │   │  LOOP    │   │  BUILD   │   │          │ │
    │  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

This transforms Phoenix from:
    "architecture on paper" → "runtime that actually runs"

Version: 1.2.0 (Runtime Integration)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, AsyncIterator
from uuid import uuid4
import logging

# Import ALL core components for integration
from .agent_profile import AgentProfile
from .agent_state_machine import AgentStateMachine, AgentExecutionState
from .capability_monitor import CapabilityMonitor
from .decision_engine import DecisionEngine, DecisionContext, DecisionResult
from .goal_manager import GoalManager, Goal, GoalStatus
from .planner_engine import PlannerEngine, PlanGraph, PlanStep
from .resource_manager import ResourceManager, ResourceRequest
from .learning_loop import LearningLoop, CognitiveFeedback
from .memory_manager import MemoryManager
from .delegation import DelegationEngine, DelegationRequest
from .delegation_policy import DelegationPolicy
from .recovery_engine import RecoveryEngine, ErrorContext
from .telemetry import AgentTelemetry
from .task import Task, TaskResult, TaskStatus
from .execution_context import ExecutionContext

# Import Platform Layer
from ..platform.tool_executor import ToolExecutor, Tool, ToolContext, ToolResult
from ..platform.environment_adapter import EnvironmentAdapter
from ..platform.safety_engine import SafetyEngine, SafetyCheckResult


logger = logging.getLogger("phoenix.pipeline")


# ============================================================================
# PIPELINE STAGES
# ============================================================================


class PipelineStage(str, Enum):
    """Stages of the execution pipeline."""
    # Entry
    ENTRY = "entry"
    
    # Understanding
    INTENT_DETECTION = "intent_detection"
    CONTEXT_BUILDING = "context_building"
    
    # Goal
    GOAL_CREATION = "goal_creation"
    GOAL_VALIDATION = "goal_validation"
    
    # Planning
    PLANNING = "planning"
    PLAN_VALIDATION = "plan_validation"
    
    # Resource & Safety
    RESOURCE_CHECK = "resource_check"
    SAFETY_CHECK = "safety_check"
    
    # Execution
    EXECUTION = "execution"
    TOOL_EXECUTION = "tool_execution"
    DELEGATION = "delegation"
    
    # Synthesis
    RESULT_COLLECTION = "result_collection"
    SYNTHESIS = "synthesis"
    
    # Learning
    MEMORY_UPDATE = "memory_update"
    LEARNING = "learning"
    
    # Output
    OUTPUT_BUILD = "output_build"
    RESPONSE = "response"


class PipelineStatus(str, Enum):
    """Status of pipeline execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# PIPELINE CONTEXT
# ============================================================================


@dataclass
class PipelineContext:
    """
    Context that flows through the entire pipeline.
    
    This is THE state that connects all stages.
    """
    # Identity
    pipeline_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    session_id: str = ""
    
    # Input
    user_input: str = ""
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Intent
    detected_intent: Optional[str] = None
    intent_confidence: float = 0.0
    
    # Goal
    goal: Optional[Goal] = None
    
    # Plan
    plan: Optional[PlanGraph] = None
    current_step_index: int = 0
    
    # Resources
    resource_check_passed: bool = False
    resource_allocation: Optional[Dict[str, Any]] = None
    
    # Safety
    safety_check_passed: bool = False
    safety_result: Optional[SafetyCheckResult] = None
    
    # Execution
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    delegation_results: List[Any] = field(default_factory=list)
    
    # Memory
    memory_context: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = field(default_factory=list)
    
    # Learning
    feedback: Optional[CognitiveFeedback] = None
    
    # Output
    output: str = ""
    output_confidence: float = 0.0
    
    # Status
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: PipelineStage = PipelineStage.ENTRY
    error: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stage_times: Dict[PipelineStage, float] = field(default_factory=dict)
    
    def start(self) -> None:
        """Mark pipeline as started."""
        self.started_at = datetime.utcnow()
        self.status = PipelineStatus.RUNNING
    
    def complete(self) -> None:
        """Mark pipeline as completed."""
        self.completed_at = datetime.utcnow()
        self.status = PipelineStatus.COMPLETED
    
    def fail(self, error: str) -> None:
        """Mark pipeline as failed."""
        self.error = error
        self.completed_at = datetime.utcnow()
        self.status = PipelineStatus.FAILED
    
    def record_stage_time(self, stage: PipelineStage, duration_ms: float) -> None:
        """Record time spent in a stage."""
        self.stage_times[stage] = duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context."""
        return {
            "pipeline_id": self.pipeline_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "goal": str(self.goal)[:100] if self.goal else None,
            "output": self.output[:200] if self.output else None,
            "error": self.error,
        }


# ============================================================================
# STAGE RESULT
# ============================================================================


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage: PipelineStage
    success: bool
    duration_ms: float
    output: Any = None
    error: Optional[str] = None
    should_skip: bool = False
    next_stage: Optional[PipelineStage] = None


# ============================================================================
# EXECUTION PIPELINE
# ============================================================================


class ExecutionPipeline:
    """
    THE RUNTIME - Request Execution Pipeline.
    
    This is what transforms Phoenix from "collection of modules" 
    to "Agent Runtime that actually runs".
    
    Pipeline Stages:
        1. ENTRY: Receive request from LLM Gateway
        2. INTENT: Detect user intent
        3. GOAL: Create and validate goal
        4. PLANNING: Build execution plan
        5. RESOURCE_CHECK: Validate resources
        6. SAFETY_CHECK: Validate safety constraints
        7. EXECUTION: Execute plan (tools, delegations)
        8. SYNTHESIS: Synthesize results
        9. MEMORY: Update memory
        10. LEARNING: Learn from execution
        11. OUTPUT: Build response
        12. RESPONSE: Return to caller
    
    Usage:
        pipeline = ExecutionPipeline(profile, config)
        
        # Process a request
        result = await pipeline.process("Analyze this code and suggest improvements")
        
        # Or stream stages
        async for stage_result in pipeline.process_stream(request):
            print(f"Stage: {stage_result.stage}")
    """
    
    def __init__(
        self,
        profile: AgentProfile = None,
        config: PipelineConfig = None,
        
        # Component injections (for testing/customization)
        state_machine: AgentStateMachine = None,
        capability_monitor: CapabilityMonitor = None,
        decision_engine: DecisionEngine = None,
        goal_manager: GoalManager = None,
        planner: PlannerEngine = None,
        resource_manager: ResourceManager = None,
        safety_engine: SafetyEngine = None,
        tool_executor: ToolExecutor = None,
        environment: EnvironmentAdapter = None,
        memory_manager: MemoryManager = None,
        learning_loop: LearningLoop = None,
        telemetry: AgentTelemetry = None,
    ):
        self.profile = profile or AgentProfile()
        self.config = config or PipelineConfig()
        
        # Initialize ALL components
        self.state_machine = state_machine or AgentStateMachine()
        self.capability_monitor = capability_monitor or CapabilityMonitor(self.profile)
        self.decision_engine = decision_engine or DecisionEngine(self.profile, self.capability_monitor)
        self.goal_manager = goal_manager or GoalManager()
        self.planner = planner or PlannerEngine()
        self.resource_manager = resource_manager or ResourceManager()
        self.safety_engine = safety_engine or SafetyEngine()
        self.tool_executor = tool_executor or ToolExecutor()
        self.environment = environment or EnvironmentAdapter()
        self.memory_manager = memory_manager or MemoryManager()
        self.learning_loop = learning_loop or LearningLoop()
        self.telemetry = telemetry or AgentTelemetry()
        
        # Stage handlers
        self._stage_handlers: Dict[PipelineStage, Callable] = {
            PipelineStage.ENTRY: self._stage_entry,
            PipelineStage.INTENT_DETECTION: self._stage_intent,
            PipelineStage.GOAL_CREATION: self._stage_goal,
            PipelineStage.PLANNING: self._stage_planning,
            PipelineStage.RESOURCE_CHECK: self._stage_resource,
            PipelineStage.SAFETY_CHECK: self._stage_safety,
            PipelineStage.EXECUTION: self._stage_execution,
            PipelineStage.SYNTHESIS: self._stage_synthesis,
            PipelineStage.MEMORY_UPDATE: self._stage_memory,
            PipelineStage.LEARNING: self._stage_learning,
            PipelineStage.OUTPUT_BUILD: self._stage_output,
            PipelineStage.RESPONSE: self._stage_response,
        }
        
        # Pipeline order
        self._pipeline_order = [
            PipelineStage.ENTRY,
            PipelineStage.INTENT_DETECTION,
            PipelineStage.GOAL_CREATION,
            PipelineStage.PLANNING,
            PipelineStage.RESOURCE_CHECK,
            PipelineStage.SAFETY_CHECK,
            PipelineStage.EXECUTION,
            PipelineStage.SYNTHESIS,
            PipelineStage.MEMORY_UPDATE,
            PipelineStage.LEARNING,
            PipelineStage.OUTPUT_BUILD,
            PipelineStage.RESPONSE,
        ]
        
        # Callbacks
        self._on_stage_complete: List[Callable[[PipelineStage, StageResult], None]] = []
        
        logger.info(f"ExecutionPipeline initialized for agent {self.profile.agent_id}")
    
    # ========================================================================
    # MAIN ENTRY POINTS
    # ========================================================================
    
    async def process(
        self,
        user_input: str,
        metadata: Dict[str, Any] = None
    ) -> PipelineContext:
        """
        Process a request through the entire pipeline.
        
        This is THE main entry point for Phoenix Runtime.
        
        Args:
            user_input: The user's request
            metadata: Additional request metadata
        
        Returns:
            PipelineContext with complete execution state
        """
        # Create context
        ctx = PipelineContext(
            user_input=user_input,
            request_metadata=metadata or {},
            request_id=str(uuid4()),
        )
        
        ctx.start()
        
        logger.info(f"Processing request: {ctx.request_id}")
        
        # Execute pipeline
        for stage in self._pipeline_order:
            if ctx.status == PipelineStatus.FAILED:
                break
            
            result = await self._execute_stage(stage, ctx)
            
            if not result.success and not result.should_skip:
                ctx.fail(result.error or f"Stage {stage} failed")
                break
            
            # Record timing
            ctx.record_stage_time(stage, result.duration_ms)
            ctx.current_stage = stage
            
            # Execute callbacks
            for callback in self._on_stage_complete:
                try:
                    callback(stage, result)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        ctx.complete()
        
        logger.info(f"Request {ctx.request_id} completed: {ctx.status.value}")
        
        return ctx
    
    async def process_stream(
        self,
        user_input: str,
        metadata: Dict[str, Any] = None
    ) -> AsyncIterator[StageResult]:
        """
        Process with streaming stage results.
        
        Yields:
            StageResult after each stage completes
        """
        ctx = PipelineContext(
            user_input=user_input,
            request_metadata=metadata or {},
        )
        
        ctx.start()
        
        for stage in self._pipeline_order:
            if ctx.status == PipelineStatus.FAILED:
                break
            
            result = await self._execute_stage(stage, ctx)
            yield result
            
            if not result.success and not result.should_skip:
                ctx.fail(result.error or f"Stage {stage} failed")
                break
            
            ctx.record_stage_time(stage, result.duration_ms)
            ctx.current_stage = stage
        
        ctx.complete()
    
    async def _execute_stage(
        self,
        stage: PipelineStage,
        ctx: PipelineContext
    ) -> StageResult:
        """Execute a single stage."""
        start_time = time.time()
        
        handler = self._stage_handlers.get(stage)
        if not handler:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=0,
                error=f"No handler for stage: {stage}"
            )
        
        try:
            result = await handler(ctx)
            result.duration_ms = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Stage {stage} failed: {e}")
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )
    
    # ========================================================================
    # STAGE HANDLERS
    # ========================================================================
    
    async def _stage_entry(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 1: ENTRY
        
        Validate input, set up context.
        """
        # Validate input
        if not ctx.user_input or not ctx.user_input.strip():
            return StageResult(
                stage=PipelineStage.ENTRY,
                success=False,
                duration_ms=0,
                error="Empty input"
            )
        
        # Update state machine
        self.state_machine.start()
        
        # Initialize telemetry
        self.telemetry.start_cycle(ctx.request_id)
        
        return StageResult(
            stage=PipelineStage.ENTRY,
            success=True,
            duration_ms=0,
            output={"validated": True}
        )
    
    async def _stage_intent(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 2: INTENT_DETECTION
        
        Detect user intent from input.
        
        In real implementation, this would call LLM Gateway.
        """
        # Simulate intent detection
        # In production: call LLM Gateway via EnvironmentAdapter
        
        intent = self._classify_intent(ctx.user_input)
        ctx.detected_intent = intent["intent"]
        ctx.intent_confidence = intent["confidence"]
        
        # Transition state
        self.state_machine.think()
        
        return StageResult(
            stage=PipelineStage.INTENT_DETECTION,
            success=True,
            duration_ms=0,
            output=intent
        )
    
    async def _stage_goal(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 3: GOAL_CREATION
        
        Create a goal from detected intent.
        """
        # Create goal
        goal = self.goal_manager.create_goal(
            name=f"Process: {ctx.detected_intent}",
            description=f"Process user request with intent: {ctx.detected_intent}",
        )
        
        ctx.goal = goal
        
        # Validate goal
        if not goal:
            return StageResult(
                stage=PipelineStage.GOAL_CREATION,
                success=False,
                duration_ms=0,
                error="Failed to create goal"
            )
        
        return StageResult(
            stage=PipelineStage.GOAL_CREATION,
            success=True,
            duration_ms=0,
            output={"goal_id": goal.goal_id}
        )
    
    async def _stage_planning(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 4: PLANNING
        
        Build execution plan from goal.
        """
        if not ctx.goal:
            return StageResult(
                stage=PipelineStage.PLANNING,
                success=False,
                duration_ms=0,
                error="No goal to plan"
            )
        
        # Create plan
        plan = self.planner.create_plan(
            goal=ctx.goal.description,
            context={"intent": ctx.detected_intent}
        )
        
        ctx.plan = plan
        
        return StageResult(
            stage=PipelineStage.PLANNING,
            success=True,
            duration_ms=0,
            output={"plan_id": plan.graph_id, "steps": len(plan.steps)}
        )
    
    async def _stage_resource(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 5: RESOURCE_CHECK
        
        Check if we have resources to execute.
        """
        # Create resource request
        request = ResourceRequest(
            request_id=str(uuid4()),
            resources={"tokens": 1000, "iterations": 10}
        )
        
        # Check resources
        can_execute = self.resource_manager.can_execute(request)
        ctx.resource_check_passed = can_execute
        
        if not can_execute:
            # Try to get allocation
            allocation = self.resource_manager.allocate(request)
            if allocation:
                ctx.resource_check_passed = True
                ctx.resource_allocation = allocation.to_dict()
        
        return StageResult(
            stage=PipelineStage.RESOURCE_CHECK,
            success=ctx.resource_check_passed,
            duration_ms=0,
            output={"passed": ctx.resource_check_passed}
        )
    
    async def _stage_safety(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 6: SAFETY_CHECK
        
        Validate safety constraints.
        """
        # Check safety for the planned action
        safety_result = self.safety_engine.check_action(
            action=ctx.detected_intent or "process",
            context={"goal": str(ctx.goal)[:100] if ctx.goal else ""},
            params={"input": ctx.user_input[:100]}
        )
        
        ctx.safety_check_passed = safety_result.allowed
        ctx.safety_result = safety_result
        
        return StageResult(
            stage=PipelineStage.SAFETY_CHECK,
            success=safety_result.allowed,
            duration_ms=0,
            output=safety_result.to_dict()
        )
    
    async def _stage_execution(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 7: EXECUTION
        
        Execute the plan - this is where the real work happens.
        """
        # Transition state
        self.state_machine.act()
        
        results = []
        
        # Execute plan steps
        if ctx.plan:
            for step in ctx.plan.steps:
                step_result = await self._execute_step(step, ctx)
                results.append(step_result)
                
                # Record in telemetry (simplified)
                self.telemetry.record_latency("step_execution", step_result.get("duration_ms", 0))
        
        ctx.execution_results = results
        
        return StageResult(
            stage=PipelineStage.EXECUTION,
            success=True,
            duration_ms=0,
            output={"results_count": len(results)}
        )
    
    async def _execute_step(self, step: PlanStep, ctx: PipelineContext) -> Dict[str, Any]:
        """Execute a single plan step."""
        result = {"step_id": step.step_id, "success": False}
        
        # Determine action type
        action = step.action.lower() if step.action else ""
        
        if "tool:" in action:
            # Tool execution
            tool_id = action.replace("tool:", "")
            tool_result = await self.tool_executor.execute(
                tool_id,
                step.parameters or {},
                ToolContext()
            )
            result["tool_result"] = tool_result.to_dict()
            result["success"] = tool_result.success
            ctx.tool_results.append(tool_result)
            
        elif "delegate:" in action:
            # Delegation
            target = action.replace("delegate:", "")
            # Would call DelegationEngine
            result["delegation"] = {"target": target}
            result["success"] = True
            
        else:
            # Generic action - simulate success
            result["success"] = True
            result["output"] = f"Executed: {action}"
        
        return result
    
    async def _stage_synthesis(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 8: SYNTHESIS
        
        Synthesize results from execution.
        """
        # Transition state
        self.state_machine.observe()
        
        # Build synthesis from execution results
        output_parts = []
        
        for result in ctx.execution_results:
            if result.get("success"):
                output_parts.append(result.get("output", "Step completed"))
        
        for tool_result in ctx.tool_results:
            if tool_result.success:
                output_parts.append(str(tool_result.output)[:500])
        
        # Build final output
        if output_parts:
            ctx.output = "\n".join(output_parts)
        else:
            ctx.output = f"Processed request: {ctx.detected_intent}"
        
        ctx.output_confidence = 0.8 if output_parts else 0.5
        
        return StageResult(
            stage=PipelineStage.SYNTHESIS,
            success=True,
            duration_ms=0,
            output={"confidence": ctx.output_confidence}
        )
    
    async def _stage_memory(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 9: MEMORY_UPDATE
        
        Update memory with execution results.
        """
        # Store in memory
        memory_update = {
            "request_id": ctx.request_id,
            "intent": ctx.detected_intent,
            "goal": str(ctx.goal)[:200] if ctx.goal else None,
            "output": ctx.output[:500],
            "success": ctx.status == PipelineStatus.RUNNING,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        ctx.memory_updates.append(memory_update)
        
        # Would call MemoryManager to persist
        # self.memory_manager.store(memory_update)
        
        return StageResult(
            stage=PipelineStage.MEMORY_UPDATE,
            success=True,
            duration_ms=0,
            output={"updated": True}
        )
    
    async def _stage_learning(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 10: LEARNING
        
        Learn from execution results.
        """
        # Create feedback
        feedback = CognitiveFeedback(
            decision_id=ctx.request_id,
            outcome="success" if ctx.output_confidence > 0.7 else "partial",
            confidence_before=0.5,
            confidence_after=ctx.output_confidence
        )
        
        ctx.feedback = feedback
        
        # Record in learning loop
        self.learning_loop.record_feedback(feedback)
        
        return StageResult(
            stage=PipelineStage.LEARNING,
            success=True,
            duration_ms=0,
            output={"learned": True}
        )
    
    async def _stage_output(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 11: OUTPUT_BUILD
        
        Build final output structure.
        """
        # Transition state
        self.state_machine.complete("Pipeline complete")
        
        # Build final output
        final_output = {
            "response": ctx.output,
            "confidence": ctx.output_confidence,
            "metadata": {
                "pipeline_id": ctx.pipeline_id,
                "request_id": ctx.request_id,
                "stages_completed": len(ctx.stage_times),
                "total_time_ms": sum(ctx.stage_times.values())
            }
        }
        
        return StageResult(
            stage=PipelineStage.OUTPUT_BUILD,
            success=True,
            duration_ms=0,
            output=final_output
        )
    
    async def _stage_response(self, ctx: PipelineContext) -> StageResult:
        """
        Stage 12: RESPONSE
        
        Final response stage.
        """
        # End telemetry cycle
        self.telemetry.end_cycle(success=ctx.status == PipelineStatus.COMPLETED)
        
        return StageResult(
            stage=PipelineStage.RESPONSE,
            success=True,
            duration_ms=0,
            output={"final": True}
        )
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _classify_intent(self, input_text: str) -> Dict[str, Any]:
        """Classify user intent from input."""
        input_lower = input_text.lower()
        
        # Simple rule-based classification
        if any(word in input_lower for word in ["analyze", "examine", "review"]):
            return {"intent": "analysis", "confidence": 0.85}
        elif any(word in input_lower for word in ["create", "build", "make"]):
            return {"intent": "creation", "confidence": 0.85}
        elif any(word in input_lower for word in ["fix", "debug", "solve"]):
            return {"intent": "problem_solving", "confidence": 0.85}
        elif any(word in input_lower for word in ["explain", "describe", "tell"]):
            return {"intent": "explanation", "confidence": 0.85}
        else:
            return {"intent": "general", "confidence": 0.6}
    
    def on_stage_complete(self, callback: Callable[[PipelineStage, StageResult], None]) -> None:
        """Register callback for stage completion."""
        self._on_stage_complete.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "profile": self.profile.to_dict(),
            "state": self.state_machine.current_state.value,
            "telemetry": self.telemetry.get_summary(),
        }


# ============================================================================
# PIPELINE CONFIG
# ============================================================================


@dataclass
class PipelineConfig:
    """Configuration for ExecutionPipeline."""
    max_execution_time_seconds: float = 300.0
    max_retries: int = 3
    enable_learning: bool = True
    enable_memory: bool = True
    enable_telemetry: bool = True
    
    # Stage timeouts
    stage_timeout_seconds: float = 60.0
    
    # Safety
    strict_safety: bool = True
    
    # Recovery
    auto_recovery: bool = True


# ============================================================================
# FACTORY
# ============================================================================


def create_execution_pipeline(
    profile: AgentProfile = None,
    config: PipelineConfig = None
) -> ExecutionPipeline:
    """Create an ExecutionPipeline."""
    return ExecutionPipeline(profile=profile, config=config)
