"""
Phoenix Agent - Runtime Controller
===================================

Le chef d'orchestre du runtime cognitif.

C'est LE composant qui transforme des composants isolés en SYSTÈME.

Sans RuntimeController:
    - AgentLoop, StateMachine, DecisionEngine... sont dispersés
    - Pas de coordination centralisée
    - Logique d'intégration éparpillée

Avec RuntimeController:
    - Cycle cognitif unifié: state → monitor → decide → act → synthesize → recover
    - Coordination centralisée
    - Contrôle d'exécction explicite
    - Observabilité native

Architecture:
    AgentRuntimeController
    │
    ├── AgentStateMachine (state control)
    ├── AgentProfile (self-awareness)
    ├── CapabilityMonitor (cognitive monitoring)
    ├── DecisionEngine (decision making)
    ├── PlannerEngine (strategic planning)
    ├── MemoryManager (memory strategies)
    ├── DelegationEngine (delegation execution)
    ├── DelegationPolicy (delegation rules)
    ├── MessageBus (inter-agent communication)
    ├── SubAgentPool (sub-agent management)
    ├── ResultSynthesizer (result fusion)
    ├── RecoveryEngine (failure recovery)
    └── AgentTelemetry (observability)

Execution Cycle (tick):
    while not finished:
        state_machine.transition()
        monitor.check()
        decision_engine.decide()
        memory_manager.apply()
        delegation_engine.execute()
        protocol.handle_messages()
        synthesizer.merge()
        recovery_engine.handle()

Version: 0.8.0 (Runtime Integration Layer)
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import time
import uuid

from .agent_state_machine import (
    AgentStateMachine,
    AgentExecutionState,
    StateCategory,
)
from .agent_profile import AgentProfile
from .capability_monitor import CapabilityMonitor, MonitoringResult
from .decision_engine import DecisionEngine, DecisionContext, DecisionResult, CognitiveDecision
from .memory_manager import MemoryManager
from .delegation import DelegationEngine, DelegationRequest, DelegationResponse
from .delegation_policy import DelegationPolicy
from .agent_protocol import MessageBus, AgentMessage
from .subagent import SubAgentPool
from .result_synthesizer import ResultSynthesizer, AgentResult
from .recovery_engine import RecoveryEngine, ErrorContext, RecoveryResult
from .task import Task, TaskStatus, TaskResult
from .execution_context import ExecutionContext


logger = logging.getLogger("phoenix.runtime_controller")


# ==========================================
# EXECUTION CYCLE
# ==========================================

class ExecutionCycle(str, Enum):
    """Phases d'un cycle d'exécution."""
    INITIALIZE = "initialize"
    MONITOR = "monitor"
    DECIDE = "decide"
    PLAN = "plan"
    ACT = "act"
    DELEGATE = "delegate"
    SYNTHESIZE = "synthesize"
    RECOVER = "recover"
    FINALIZE = "finalize"


@dataclass
class CycleResult:
    """Résultat d'un cycle d'exécution."""
    cycle: ExecutionCycle
    success: bool
    duration_ms: float
    
    # Context
    state_before: AgentExecutionState
    state_after: AgentExecutionState
    
    # Outputs
    decision: Optional[DecisionResult] = None
    monitoring: Optional[MonitoringResult] = None
    delegation: Optional[DelegationResponse] = None
    recovery: Optional[RecoveryResult] = None
    
    # Errors
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle": self.cycle.value,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "state_before": self.state_before.value,
            "state_after": self.state_after.value,
            "error": self.error,
        }


# ==========================================
# RUNTIME CONFIG
# ==========================================

@dataclass
class RuntimeConfig:
    """Configuration du runtime controller."""
    # Cycle control
    max_cycles: int = 100
    cycle_delay_ms: float = 0.0  # Delay between cycles
    
    # Timeouts
    cycle_timeout_ms: float = 60000.0
    delegation_timeout_ms: float = 30000.0
    
    # Recovery
    auto_recovery: bool = True
    max_recovery_attempts: int = 3
    
    # Monitoring
    monitor_interval_cycles: int = 1
    
    # Telemetry
    enable_telemetry: bool = True
    telemetry_interval_cycles: int = 5


# ==========================================
# RUNTIME STATUS
# ==========================================

@dataclass
class RuntimeStatus:
    """Status du runtime."""
    controller_id: str
    is_running: bool
    is_paused: bool
    
    # Current state
    current_state: AgentExecutionState
    current_cycle: int
    
    # Task
    current_task_id: Optional[str]
    
    # Metrics
    total_cycles: int
    total_decisions: int
    total_delegations: int
    total_recoveries: int
    
    # Health
    health_score: float
    last_error: Optional[str]
    
    # Timestamps
    started_at: Optional[datetime]
    last_cycle_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "controller_id": self.controller_id,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_state": self.current_state.value,
            "current_cycle": self.current_cycle,
            "current_task_id": self.current_task_id,
            "total_cycles": self.total_cycles,
            "total_decisions": self.total_decisions,
            "total_delegations": self.total_delegations,
            "health_score": self.health_score,
            "last_error": self.last_error,
        }


# ==========================================
# RUNTIME CONTROLLER
# ==========================================

class AgentRuntimeController:
    """
    Le chef d'orchestre du runtime Phoenix.
    
    C'est LE composant qui transforme les composants isolés en système intégré.
    
    Responsabilités:
        1. Orchestrer le cycle cognitif complet
        2. Coordonner tous les composants
        3. Gérer les transitions d'état
        4. Gérer les erreurs et récupérations
        5. Exposer l'observabilité
    
    Architecture:
        ┌─────────────────────────────────────────────────────┐
        │              AgentRuntimeController                  │
        │                                                      │
        │  ┌──────────────┐    ┌──────────────┐              │
        │  │ StateMachine │◄──►│   Profile    │              │
        │  └──────────────┘    └──────────────┘              │
        │         │                    │                      │
        │         ▼                    ▼                      │
        │  ┌──────────────┐    ┌──────────────┐              │
        │  │   Monitor    │───►│ DecisionEng  │              │
        │  └──────────────┘    └──────────────┘              │
        │         │                    │                      │
        │         ▼                    ▼                      │
        │  ┌──────────────┐    ┌──────────────┐              │
        │  │ MemoryMngr   │    │ DelegationEng│              │
        │  └──────────────┘    └──────────────┘              │
        │         │                    │                      │
        │         ▼                    ▼                      │
        │  ┌──────────────┐    ┌──────────────┐              │
        │  │   Protocol   │    │  Synthesizer │              │
        │  └──────────────┘    └──────────────┘              │
        │         │                    │                      │
        │         └────────┬───────────┘                      │
        │                  ▼                                  │
        │         ┌──────────────┐                           │
        │         │ RecoveryEng  │                           │
        │         └──────────────┘                           │
        │                  │                                  │
        │                  ▼                                  │
        │         ┌──────────────┐                           │
        │         │  Telemetry   │                           │
        │         └──────────────┘                           │
        └─────────────────────────────────────────────────────┘
    
    Example:
        # Create controller
        controller = AgentRuntimeController(
            profile=agent_profile,
            config=RuntimeConfig(max_cycles=50)
        )
        
        # Run a task
        result = await controller.run(task)
        
        # Or run step by step
        controller.start(task)
        while not controller.is_finished:
            await controller.tick()
        result = controller.get_result()
        
        # With streaming
        async for event in controller.run_stream(task):
            print(f"State: {event.state}")
    """
    
    def __init__(
        self,
        profile: Optional[AgentProfile] = None,
        config: Optional[RuntimeConfig] = None,
        
        # Component overrides (for testing/customization)
        state_machine: Optional[AgentStateMachine] = None,
        monitor: Optional[CapabilityMonitor] = None,
        decision_engine: Optional[DecisionEngine] = None,
        memory_manager: Optional[MemoryManager] = None,
        delegation_engine: Optional[DelegationEngine] = None,
        delegation_policy: Optional[DelegationPolicy] = None,
        protocol: Optional[MessageBus] = None,
        subagent_pool: Optional[SubAgentPool] = None,
        synthesizer: Optional[ResultSynthesizer] = None,
        recovery_engine: Optional[RecoveryEngine] = None,
    ):
        """
        Initialise le runtime controller.
        
        Args:
            profile: Agent profile (créé si None)
            config: Runtime config (default si None)
            state_machine: State machine (créée si None)
            monitor: Capability monitor (créé si None)
            decision_engine: Decision engine (créé si None)
            memory_manager: Memory manager (créé si None)
            delegation_engine: Delegation engine (créé si None)
            delegation_policy: Delegation policy (créé si None)
            protocol: Agent protocol (créé si None)
            subagent_pool: Sub-agent pool (créé si None)
            synthesizer: Result synthesizer (créé si None)
            recovery_engine: Recovery engine (créé si None)
        """
        self.controller_id = str(uuid.uuid4())
        self.config = config or RuntimeConfig()
        
        # Core components
        self.profile = profile or AgentProfile()
        self.state_machine = state_machine or AgentStateMachine()
        
        # Cognitive components
        self.monitor = monitor or CapabilityMonitor(self.profile)
        self.decision_engine = decision_engine or DecisionEngine(self.profile, self.monitor)
        
        # Memory
        self.memory_manager = memory_manager or MemoryManager()
        
        # Delegation
        self.delegation_engine = delegation_engine or DelegationEngine()
        self.delegation_policy = delegation_policy or DelegationPolicy()
        self.protocol = protocol or MessageBus()
        self.subagent_pool = subagent_pool or SubAgentPool()
        
        # Results
        self.synthesizer = synthesizer or ResultSynthesizer()
        
        # Recovery
        self.recovery_engine = recovery_engine or RecoveryEngine()
        
        # Execution context
        self._execution_context: Optional[ExecutionContext] = None
        
        # Cycle tracking
        self._cycle_count: int = 0
        self._cycle_history: List[CycleResult] = []
        
        # State
        self._is_running: bool = False
        self._is_paused: bool = False
        self._current_task: Optional[Task] = None
        self._pending_results: List[AgentResult] = []
        
        # Callbacks
        self._on_cycle_complete: List[Callable[[CycleResult], None]] = []
        self._on_state_change: List[Callable[[AgentExecutionState, AgentExecutionState], None]] = []
        self._on_decision: List[Callable[[DecisionResult], None]] = []
        self._on_delegation: List[Callable[[DelegationResponse], None]] = []
        
        # Register state change callback
        self.state_machine.on_state_change(self._handle_state_change)
        
        # Timestamps
        self._started_at: Optional[datetime] = None
        self._last_cycle_at: Optional[datetime] = None
        
        logger.info(f"RuntimeController {self.controller_id} initialized")
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    
    @property
    def is_running(self) -> bool:
        """Le runtime est en cours d'exécution."""
        return self._is_running
    
    @property
    def is_paused(self) -> bool:
        """Le runtime est en pause."""
        return self._is_paused
    
    @property
    def is_finished(self) -> bool:
        """L'exécution est terminée."""
        return self.state_machine.is_terminal
    
    @property
    def current_state(self) -> AgentExecutionState:
        """État actuel."""
        return self.state_machine.current_state
    
    @property
    def status(self) -> RuntimeStatus:
        """Status complet du runtime."""
        return RuntimeStatus(
            controller_id=self.controller_id,
            is_running=self._is_running,
            is_paused=self._is_paused,
            current_state=self.current_state,
            current_cycle=self._cycle_count,
            current_task_id=self._current_task.task_id if self._current_task else None,
            total_cycles=self._cycle_count,
            total_decisions=len(self.decision_engine.get_history()),
            total_delegations=len(self.delegation_engine._delegation_history),
            total_recoveries=len(self.recovery_engine._recovery_history),
            health_score=self._calculate_health(),
            last_error=self._get_last_error(),
            started_at=self._started_at,
            last_cycle_at=self._last_cycle_at,
        )
    
    # ==========================================
    # MAIN RUN
    # ==========================================
    
    async def run(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Exécute une tâche de manière complète.
        
        C'est le point d'entrée principal pour l'exécution.
        
        Args:
            task: La tâche à exécuter
            context: Contexte additionnel
            
        Returns:
            TaskResult
        """
        logger.info(f"Starting task: {task.task_id} - {task.goal[:50]}...")
        
        # Initialize
        self._start(task)
        
        # Main execution loop
        while not self.is_finished and self._cycle_count < self.config.max_cycles:
            # Check pause
            if self._is_paused:
                await asyncio.sleep(0.1)
                continue
            
            # Execute one cycle
            cycle_result = await self.tick()
            
            # Check for terminal state
            if self.state_machine.is_terminal:
                break
        
        # Finalize
        return self._finalize(task)
    
    async def run_stream(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[CycleResult]:
        """
        Exécute avec streaming des cycles.
        
        Yields:
            CycleResult après chaque cycle
        """
        logger.info(f"Starting streaming task: {task.task_id}")
        
        # Initialize
        self._start(task)
        
        # Main execution loop
        while not self.is_finished and self._cycle_count < self.config.max_cycles:
            # Check pause
            if self._is_paused:
                await asyncio.sleep(0.1)
                continue
            
            # Execute one cycle
            cycle_result = await self.tick()
            yield cycle_result
            
            # Check for terminal state
            if self.state_machine.is_terminal:
                break
    
    # ==========================================
    # TICK (Single Cycle)
    # ==========================================
    
    async def tick(self) -> CycleResult:
        """
        Exécute un seul cycle cognitif.
        
        C'est LA méthode centrale du runtime controller.
        
        Cycle:
            1. MONITOR: Check cognitive state
            2. DECIDE: Make decision
            3. ACT: Execute decision
            4. RECOVER: Handle errors if any
        
        Returns:
            CycleResult
        """
        start_time = time.time()
        state_before = self.current_state
        self._cycle_count += 1
        
        logger.debug(f"Tick #{self._cycle_count}: state={state_before.value}")
        
        try:
            # ==========================================
            # MONITOR PHASE
            # ==========================================
            monitoring_result = await self._monitor_phase()
            
            # ==========================================
            # DECIDE PHASE
            # ==========================================
            decision_result = await self._decide_phase(monitoring_result)
            
            # ==========================================
            # ACT PHASE
            # ==========================================
            action_result = await self._act_phase(decision_result)
            
            # Duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Create cycle result
            cycle_result = CycleResult(
                cycle=ExecutionCycle.ACT,
                success=True,
                duration_ms=duration_ms,
                state_before=state_before,
                state_after=self.current_state,
                monitoring=monitoring_result,
                decision=decision_result,
            )
            
            # Execute callbacks
            self._execute_cycle_callbacks(cycle_result)
            
            # Update telemetry
            self._last_cycle_at = datetime.utcnow()
            
            return cycle_result
            
        except Exception as e:
            logger.error(f"Tick #{self._cycle_count} failed: {e}")
            
            # Try recovery
            if self.config.auto_recovery:
                recovery_result = await self._recover_from_error(e)
                
                duration_ms = (time.time() - start_time) * 1000
                
                return CycleResult(
                    cycle=ExecutionCycle.RECOVER,
                    success=recovery_result.success,
                    duration_ms=duration_ms,
                    state_before=state_before,
                    state_after=self.current_state,
                    recovery=recovery_result,
                    error=str(e),
                )
            
            # No recovery - fail
            self.state_machine.fail(str(e))
            
            duration_ms = (time.time() - start_time) * 1000
            
            return CycleResult(
                cycle=ExecutionCycle.ACT,
                success=False,
                duration_ms=duration_ms,
                state_before=state_before,
                state_after=self.current_state,
                error=str(e),
            )
    
    # ==========================================
    # PHASES
    # ==========================================
    
    async def _monitor_phase(self) -> MonitoringResult:
        """Phase de monitoring cognitif."""
        # Transition to THINKING if needed
        if self.current_state == AgentExecutionState.IDLE:
            self.state_machine.start()
        elif self.current_state not in [AgentExecutionState.THINKING, AgentExecutionState.RECOVERING]:
            self.state_machine.think()
        
        # Check cognitive state
        result = self.monitor.check()
        
        logger.debug(f"Monitor: decision={result.decision.value}, triggers={[t.value for t in result.triggers]}")
        
        return result
    
    async def _decide_phase(self, monitoring: MonitoringResult) -> DecisionResult:
        """Phase de décision."""
        # Build decision context
        context = DecisionContext(
            profile=self.profile,
            monitor_result=monitoring,
            current_task=self._current_task,
            previous_decisions=self.decision_engine.get_history(limit=5),
            retry_count=len(self.recovery_engine.get_recovery_history()),
            delegation_count=len(self.delegation_engine._delegation_history),
        )
        
        # Make decision
        result = self.decision_engine.decide(context)
        
        logger.info(f"Decision: {result.decision.value} - {result.reasoning}")
        
        # Execute callbacks
        for callback in self._on_decision:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")
        
        return result
    
    async def _act_phase(self, decision: DecisionResult) -> Dict[str, Any]:
        """Phase d'action basée sur la décision."""
        result: Dict[str, Any] = {}
        
        # Handle based on decision type
        if decision.should_delegate:
            result = await self._handle_delegation(decision)
        
        elif decision.should_modify_memory:
            result = await self._handle_memory_action(decision)
        
        elif decision.should_modify_task:
            result = await self._handle_task_modification(decision)
        
        elif decision.should_stop:
            result = await self._handle_stop(decision)
        
        else:
            # CONTINUE - transition state
            if decision.decision == CognitiveDecision.CONTINUE:
                # Continue thinking/acting
                if self.current_state == AgentExecutionState.THINKING:
                    self.state_machine.act()
                elif self.current_state == AgentExecutionState.ACTING:
                    self.state_machine.observe()
                elif self.current_state == AgentExecutionState.OBSERVING:
                    self.state_machine.think()
        
        return result
    
    # ==========================================
    # ACTION HANDLERS
    # ==========================================
    
    async def _handle_delegation(self, decision: DecisionResult) -> Dict[str, Any]:
        """Gère une délégation."""
        logger.info(f"Handling delegation: {decision.decision.value}")
        
        # Transition state
        self.state_machine.delegate()
        
        # Create delegation request
        request = DelegationRequest(
            task=self._current_task,
            required_role=decision.action_params.get("required_role"),
            required_capabilities=decision.action_params.get("required_capabilities", []),
            context_to_share=decision.action_params.get("context", ""),
        )
        
        # Check policy
        policy_result = self.delegation_policy.evaluate(request)
        
        if not policy_result.allowed:
            logger.warning(f"Delegation blocked by policy: {policy_result.reason}")
            self.state_machine.fail(f"Delegation blocked: {policy_result.reason}")
            return {"success": False, "reason": policy_result.reason}
        
        # Execute delegation
        response = await self.delegation_engine.delegate(request)
        
        # Execute callbacks
        for callback in self._on_delegation:
            try:
                callback(response)
            except Exception as e:
                logger.error(f"Delegation callback error: {e}")
        
        # Handle response
        if response.success:
            # Transition to waiting
            self.state_machine.wait_for_results()
            
            # Simulate receiving results
            self.state_machine.receive_results()
            
            # Add result for synthesis
            if response.task_result:
                agent_result = AgentResult(
                    agent_id=response.assigned_agent_id or "unknown",
                    agent_role=self._infer_role(decision),
                    task_id=self._current_task.task_id if self._current_task else "",
                    content=response.task_result.result or "",
                    confidence=0.8,
                )
                self._pending_results.append(agent_result)
            
            # Transition to synthesizing
            self.state_machine.synthesize()
            
            # Synthesize results
            if self._pending_results:
                synthesis = self.synthesizer.synthesize(self._current_task)
                logger.info(f"Synthesis complete: confidence={synthesis.confidence:.2f}")
            
            return {"success": True, "response": response}
        else:
            self.state_machine.fail(response.error or "Delegation failed")
            return {"success": False, "error": response.error}
    
    async def _handle_memory_action(self, decision: DecisionResult) -> Dict[str, Any]:
        """Gère une action mémoire."""
        logger.info(f"Handling memory action: {decision.decision.value}")
        
        if decision.decision == CognitiveDecision.COMPRESS_MEMORY:
            # Apply memory compression
            compression_result = self.memory_manager.apply_strategy("compress")
            return {"success": True, "compression": compression_result}
        
        elif decision.decision == CognitiveDecision.EXTERNALIZE_MEMORY:
            # Externalize to vector store
            externalize_result = self.memory_manager.apply_strategy("externalize")
            return {"success": True, "externalize": externalize_result}
        
        return {"success": False, "reason": "Unknown memory action"}
    
    async def _handle_task_modification(self, decision: DecisionResult) -> Dict[str, Any]:
        """Gère une modification de tâche."""
        logger.info(f"Handling task modification: {decision.decision.value}")
        
        if decision.decision == CognitiveDecision.SPLIT_TASK:
            # Task splitting would be handled by PlannerEngine
            return {"success": True, "action": "split_task"}
        
        elif decision.decision == CognitiveDecision.SIMPLIFY_TASK:
            # Task simplification
            return {"success": True, "action": "simplify_task"}
        
        return {"success": False, "reason": "Unknown task modification"}
    
    async def _handle_stop(self, decision: DecisionResult) -> Dict[str, Any]:
        """Gère un arrêt."""
        logger.info(f"Handling stop: {decision.decision.value}")
        
        if decision.decision == CognitiveDecision.STOP_SUCCESS:
            self.state_machine.complete("Task completed successfully")
        elif decision.decision == CognitiveDecision.STOP_PARTIAL:
            self.state_machine.complete("Task completed with partial results")
        elif decision.decision == CognitiveDecision.STOP_FAILURE:
            self.state_machine.fail("Task failed")
        elif decision.decision == CognitiveDecision.ABORT:
            self.state_machine.abort("Task aborted")
        
        return {"success": True, "final_decision": decision.decision.value}
    
    # ==========================================
    # RECOVERY
    # ==========================================
    
    async def _recover_from_error(self, error: Exception) -> RecoveryResult:
        """Tente de récupérer d'une erreur."""
        logger.warning(f"Attempting recovery from: {error}")
        
        # Transition to recovering
        self.state_machine.recover()
        
        # Create error context
        error_context = self.recovery_engine.create_error_context(
            error=error,
            agent_id=self.profile.agent_id,
            task_id=self._current_task.task_id if self._current_task else "",
            iteration=self._cycle_count,
        )
        
        # Attempt recovery
        result = await self.recovery_engine.recover(error_context)
        
        if result.success:
            if result.action == "retry":
                self.state_machine.retry()
            elif result.action == "delegate":
                # Will delegate in next cycle
                pass
            else:
                self.state_machine.think()
        else:
            self.state_machine.fail(f"Recovery failed: {result.message}")
        
        return result
    
    # ==========================================
    # CONTROL METHODS
    # ==========================================
    
    def _start(self, task: Task) -> None:
        """Démarre l'exécution."""
        self._current_task = task
        self._is_running = True
        self._is_paused = False
        self._started_at = datetime.utcnow()
        self._cycle_count = 0
        
        # Create execution context
        self._execution_context = ExecutionContext(
            task_id=task.task_id,
            agent_id=self.profile.agent_id,
        )
        
        # Start state machine
        self.state_machine.start()
        
        logger.info(f"Runtime started for task: {task.task_id}")
    
    def pause(self) -> bool:
        """Met l'exécution en pause."""
        if self._is_running and not self._is_paused:
            self._is_paused = True
            self.state_machine.pause()
            logger.info("Runtime paused")
            return True
        return False
    
    def resume(self) -> bool:
        """Reprend l'exécution."""
        if self._is_running and self._is_paused:
            self._is_paused = False
            self.state_machine.resume()
            logger.info("Runtime resumed")
            return True
        return False
    
    def abort(self, reason: str = "User abort") -> None:
        """Abandonne l'exécution."""
        self.state_machine.abort(reason)
        self._is_running = False
        logger.warning(f"Runtime aborted: {reason}")
    
    def _finalize(self, task: Task) -> TaskResult:
        """Finalise l'exécution."""
        self._is_running = False
        
        # Determine status
        if self.current_state == AgentExecutionState.COMPLETED:
            status = TaskStatus.COMPLETED
        elif self.current_state == AgentExecutionState.ABORTED:
            status = TaskStatus.CANCELLED
        else:
            status = TaskStatus.FAILED
        
        # Synthesize final result
        final_content = ""
        final_confidence = 0.0
        
        if self._pending_results:
            synthesis = self.synthesizer.synthesize(task)
            final_content = synthesis.content
            final_confidence = synthesis.confidence
        
        # Create result
        result = TaskResult(
            task_id=task.task_id,
            status=status,
            result=final_content,
            confidence=final_confidence,
            metadata={
                "cycles": self._cycle_count,
                "decisions": len(self.decision_engine.get_history()),
                "delegations": len(self.delegation_engine._delegation_history),
                "recoveries": len(self.recovery_engine._recovery_history),
                "final_state": self.current_state.value,
            }
        )
        
        logger.info(f"Task finalized: {task.task_id} - {status.value}")
        
        return result
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_cycle_complete(self, callback: Callable[[CycleResult], None]) -> None:
        """Enregistre un callback de fin de cycle."""
        self._on_cycle_complete.append(callback)
    
    def on_state_change(
        self,
        callback: Callable[[AgentExecutionState, AgentExecutionState], None]
    ) -> None:
        """Enregistre un callback de changement d'état."""
        self._on_state_change.append(callback)
    
    def on_decision(self, callback: Callable[[DecisionResult], None]) -> None:
        """Enregistre un callback de décision."""
        self._on_decision.append(callback)
    
    def on_delegation(self, callback: Callable[[DelegationResponse], None]) -> None:
        """Enregistre un callback de délégation."""
        self._on_delegation.append(callback)
    
    def _handle_state_change(
        self,
        old_state: AgentExecutionState,
        new_state: AgentExecutionState
    ) -> None:
        """Gère les changements d'état."""
        for callback in self._on_state_change:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")
    
    def _execute_cycle_callbacks(self, result: CycleResult) -> None:
        """Exécute les callbacks de cycle."""
        for callback in self._on_cycle_complete:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Cycle callback error: {e}")
    
    # ==========================================
    # HELPERS
    # ==========================================
    
    def _infer_role(self, decision: DecisionResult) -> Any:
        """Infère le rôle depuis une décision."""
        from .agent_role import AgentRoleType
        
        role_map = {
            CognitiveDecision.DELEGATE_SPECIALIST: AgentRoleType.SPECIALIST,
            CognitiveDecision.DELEGATE_WORKER: AgentRoleType.WORKER,
            CognitiveDecision.DELEGATE_PLANNER: AgentRoleType.PLANNER,
        }
        return role_map.get(decision.decision, AgentRoleType.WORKER)
    
    def _calculate_health(self) -> float:
        """Calcule le score de santé."""
        # Base health
        health = 1.0
        
        # Penalize errors
        error_count = len(self.recovery_engine.get_error_history())
        health -= min(error_count * 0.1, 0.5)
        
        # Penalize high cognitive load
        metrics = self.monitor.get_metrics()
        load = metrics.get("cognitive", {}).get("load", 0)
        health -= load * 0.2
        
        return max(0.0, min(1.0, health))
    
    def _get_last_error(self) -> Optional[str]:
        """Récupère la dernière erreur."""
        history = self.recovery_engine.get_error_history(limit=1)
        if history:
            return history[0].error_message
        return None
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du runtime."""
        return {
            "controller_id": self.controller_id,
            "status": self.status.to_dict(),
            "state_machine": self.state_machine.get_stats(),
            "decision_engine": self.decision_engine.get_stats(),
            "delegation_engine": self.delegation_engine.get_stats(),
            "recovery_engine": self.recovery_engine.get_stats(),
            "monitor": self.monitor.get_metrics(),
            "profile": self.profile.to_dict(),
        }
    
    def get_cycle_history(self, limit: int = 20) -> List[CycleResult]:
        """Retourne l'historique des cycles."""
        return self._cycle_history[-limit:]


# ==========================================
# FACTORY
# ==========================================

def create_runtime_controller(
    profile: Optional[AgentProfile] = None,
    config: Optional[RuntimeConfig] = None,
) -> AgentRuntimeController:
    """Factory pour créer un runtime controller."""
    return AgentRuntimeController(
        profile=profile,
        config=config,
    )
