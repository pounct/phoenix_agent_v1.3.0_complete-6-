"""
Reasoning Loop - The Deliberation Cycle
========================================

LAW 1: COGNITION MUST NEVER EXECUTE.

This is THE SANDBOX for thinking.

The Reasoning Loop:
    - Perceives state
    - Deliberates on options
    - Simulates outcomes
    - Evaluates alternatives
    - Produces INTENTIONS (not actions)

Critical Design:
    Reasoning Loop NEVER calls tools.
    Reasoning Loop NEVER executes actions.
    Reasoning Loop NEVER modifies external state.

    It ONLY thinks and produces intentions.

The Difference:
    Intention = "I want to delegate this task" (internal)
    Action = "Call delegation API" (external)

    Reasoning produces Intentions.
    Execution transforms Intentions to Actions.

This Creates:
    - Cognitive safety (sandbox)
    - Reversibility (simulation)
    - Predictability (planning)
    - Separation of concerns

The Loop:
    while reasoning:
        perceive(world_state)
        deliberate()
        simulate(options)
        evaluate(outcomes)
        commit_to_intention()

Version: 3.0.0 (Cognitive Kernel)
"""

from typing import Optional, List, Dict, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import asyncio


logger = logging.getLogger("phoenix.kernel.reasoning")


# ==========================================
# REASONING PHASE
# ==========================================

class ReasoningPhase(str, Enum):
    """Phases of the reasoning cycle."""
    PERCEIVING = "perceiving"           # Gathering state
    UNDERSTANDING = "understanding"     # Making sense of state
    DELIBERATING = "deliberating"       # Generating options
    SIMULATING = "simulating"           # Testing options
    EVALUATING = "evaluating"           # Scoring outcomes
    COMMITTING = "committing"           # Choosing intention
    IDLE = "idle"                       # No active reasoning


class IntentionType(str, Enum):
    """Types of intentions."""
    EXECUTE = "execute"                 # Execute a task
    DELEGATE = "delegate"               # Delegate to sub-agent
    PLAN = "plan"                       # Create a plan
    WAIT = "wait"                       # Wait for condition
    QUERY = "query"                     # Get more information
    RECOVER = "recover"                 # Recover from error
    ABORT = "abort"                     # Abort current operation
    REFLECT = "reflect"                 # Self-reflection


class DeliberationStatus(str, Enum):
    """Status of deliberation."""
    EXPLORING = "exploring"             # Still exploring options
    CONVERGING = "converging"           # Narrowing down
    DECIDED = "decided"                 # Made a decision
    STUCK = "stuck"                     # Cannot proceed
    TIMEOUT = "timeout"                 # Ran out of time


# ==========================================
# INTENTION (NOT ACTION)
# ==========================================

@dataclass
class Intention:
    """
    An INTENTION, not an action.
    
    This is what reasoning produces.
    Execution transforms intentions into actions.
    
    Difference:
        Intention: "I want to delegate task X to specialist Y"
        Action: "Call delegation API with task_id=X, agent=Y"
    
    Intentions are:
        - Internal (in the mind)
        - Reversible (can be reconsidered)
        - Simulated (can be tested)
        - Safe (no external effects)
    """
    # Identity
    intention_id: str
    intention_type: IntentionType
    
    # The intent
    description: str
    target: Optional[str] = None        # What this targets
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Reasoning context
    reasoning: str = ""                 # Why this intention
    confidence: float = 0.5
    priority: int = 5
    
    # Risk assessment
    estimated_risk: float = 0.0
    estimated_cost: float = 0.0
    estimated_duration_ms: float = 0.0
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    
    # Alternatives considered
    alternatives: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    
    # Simulation results
    simulated_outcome: Optional[str] = None
    simulation_confidence: float = 0.0
    
    @property
    def is_valid(self) -> bool:
        """Check if intention is still valid."""
        if self.valid_until is None:
            return True
        return datetime.utcnow() < self.valid_until
    
    @property
    def risk_level(self) -> str:
        """Get risk level string."""
        if self.estimated_risk < 0.3:
            return "low"
        elif self.estimated_risk < 0.7:
            return "medium"
        else:
            return "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intention_id": self.intention_id,
            "intention_type": self.intention_type.value,
            "description": self.description,
            "target": self.target,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "priority": self.priority,
            "estimated_risk": self.estimated_risk,
            "estimated_cost": self.estimated_cost,
            "risk_level": self.risk_level,
        }


# ==========================================
# DELIBERATION CONTEXT
# ==========================================

@dataclass
class DeliberationContext:
    """
    Context for deliberation.
    
    Contains all information needed for reasoning.
    """
    # World state snapshot
    world_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Self state snapshot
    self_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Active intentions
    active_intentions: List[Intention] = field(default_factory=list)
    
    # Constraints
    constraints: List[str] = field(default_factory=list)
    hard_constraints: List[str] = field(default_factory=list)
    
    # Time budget
    time_budget_ms: float = 5000.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    # Cognitive budget
    max_options: int = 7
    max_simulations: int = 3
    
    # Current deliberation
    options_generated: List[Intention] = field(default_factory=list)
    simulations_run: int = 0
    status: DeliberationStatus = DeliberationStatus.EXPLORING
    
    @property
    def time_elapsed_ms(self) -> float:
        """Get elapsed time in ms."""
        return (datetime.utcnow() - self.started_at).total_seconds() * 1000
    
    @property
    def time_remaining_ms(self) -> float:
        """Get remaining time in ms."""
        return max(0, self.time_budget_ms - self.time_elapsed_ms)
    
    @property
    def is_time_limited(self) -> bool:
        """Check if time is limited."""
        return self.time_remaining_ms < self.time_budget_ms * 0.2


# ==========================================
# SIMULATION RESULT
# ==========================================

@dataclass
class SimulationResult:
    """
    Result of simulating an intention.
    
    Simulations are SAFE - they don't execute anything.
    They predict what would happen.
    """
    intention_id: str
    
    # Predicted outcome
    predicted_success: bool
    predicted_confidence: float
    
    # Predicted effects
    predicted_state_changes: Dict[str, Any] = field(default_factory=dict)
    predicted_side_effects: List[str] = field(default_factory=list)
    
    # Resource predictions
    predicted_cost: float = 0.0
    predicted_duration_ms: float = 0.0
    
    # Risk assessment
    risk_factors: List[str] = field(default_factory=list)
    mitigation_options: List[str] = field(default_factory=list)
    
    # Confidence in simulation
    simulation_quality: float = 0.5
    assumptions_made: List[str] = field(default_factory=list)
    
    def overall_score(self) -> float:
        """Calculate overall score for this simulation."""
        if not self.predicted_success:
            return 0.0
        
        return (
            self.predicted_confidence * 0.4 +
            self.simulation_quality * 0.3 +
            (1.0 - min(1.0, self.predicted_cost / 10.0)) * 0.3
        )


# ==========================================
# REASONING LOOP
# ==========================================

class ReasoningLoop:
    """
    THE DELIBERATION CYCLE.
    
    This implements LAW 1: Cognition must never execute.
    
    The Reasoning Loop:
        1. Perceives world state
        2. Deliberates on options
        3. Simulates outcomes
        4. Evaluates alternatives
        5. Commits to intentions
    
    CRITICAL: This NEVER executes anything.
    It ONLY produces intentions.
    
    Architecture Position:
        Reasoning Loop is THE cognitive core.
        It thinks, plans, and decides.
        But it never acts.
        
        Execution Engine receives intentions and acts.
    
    Usage:
        reasoning = ReasoningLoop()
        
        # Set callbacks for state access
        reasoning.set_state_provider(world_state_manager.get_state)
        reasoning.set_self_provider(self_model.get_state)
        
        # Run deliberation cycle
        intentions = await reasoning.deliberate(context)
        
        # Intentions are passed to execution engine
        execution_engine.execute(intentions)
    
    The Sandbox Principle:
        - Reasoning happens in isolation
        - State is read-only during reasoning
        - Intentions are the only output
        - Execution happens separately
    """
    
    def __init__(
        self,
        max_deliberation_cycles: int = 5,
        default_time_budget_ms: float = 5000.0,
    ):
        self.max_deliberation_cycles = max_deliberation_cycles
        self.default_time_budget_ms = default_time_budget_ms
        
        # State providers (set externally)
        self._world_state_provider: Optional[Callable[[], Any]] = None
        self._self_state_provider: Optional[Callable[[], Any]] = None
        
        # Current deliberation
        self._current_context: Optional[DeliberationContext] = None
        self._current_phase = ReasoningPhase.IDLE
        
        # Intention tracking
        self._pending_intentions: List[Intention] = []
        self._committed_intentions: List[Intention] = []
        self._rejected_intentions: List[Intention] = []
        
        # Callbacks
        self._on_intention: Optional[Callable[[Intention], None]] = None
        self._on_phase_change: Optional[Callable[[ReasoningPhase, ReasoningPhase], None]] = None
        
        # Statistics
        self._total_deliberations = 0
        self._total_intentions_produced = 0
        
        logger.info("ReasoningLoop initialized (Cognition Sandbox)")
    
    # ==========================================
    # STATE PROVIDERS
    # ==========================================
    
    def set_world_state_provider(
        self,
        provider: Callable[[], Any],
    ) -> None:
        """Set provider for world state."""
        self._world_state_provider = provider
    
    def set_self_state_provider(
        self,
        provider: Callable[[], Any],
    ) -> None:
        """Set provider for self state."""
        self._self_state_provider = provider
    
    # ==========================================
    # MAIN DELIBERATION CYCLE
    # ==========================================
    
    async def deliberate(
        self,
        context: Optional[DeliberationContext] = None,
        goal: Optional[str] = None,
    ) -> List[Intention]:
        """
        Run the deliberation cycle.
        
        This is THE main method of the reasoning loop.
        
        Process:
            1. PERCEIVE: Gather state
            2. UNDERSTAND: Make sense of state
            3. DELIBERATE: Generate options
            4. SIMULATE: Test options
            5. EVALUATE: Score outcomes
            6. COMMIT: Choose intentions
        
        Returns:
            List of committed intentions (ready for execution)
        """
        self._total_deliberations += 1
        
        # Initialize context
        if context is None:
            context = DeliberationContext(
                time_budget_ms=self.default_time_budget_ms,
            )
        
        self._current_context = context
        
        # Run deliberation cycle
        for cycle in range(self.max_deliberation_cycles):
            if context.status == DeliberationStatus.DECIDED:
                break
            
            if context.time_remaining_ms < 100:
                context.status = DeliberationStatus.TIMEOUT
                break
            
            # Phase 1: Perceive
            await self._phase_perceive(context)
            
            # Phase 2: Understand
            await self._phase_understand(context)
            
            # Phase 3: Deliberate
            await self._phase_deliberate(context, goal)
            
            # Phase 4: Simulate
            await self._phase_simulate(context)
            
            # Phase 5: Evaluate
            await self._phase_evaluate(context)
        
        # Phase 6: Commit
        committed = await self._phase_commit(context)
        
        self._total_intentions_produced += len(committed)
        
        logger.info(
            f"Deliberation complete: {len(committed)} intentions, "
            f"status={context.status.value}"
        )
        
        return committed
    
    # ==========================================
    # DELIBERATION PHASES
    # ==========================================
    
    async def _phase_perceive(self, context: DeliberationContext) -> None:
        """
        Phase 1: Perceive world state.
        
        Gather current state snapshots.
        """
        self._set_phase(ReasoningPhase.PERCEIVING)
        
        # Get world state snapshot
        if self._world_state_provider:
            try:
                world_state = self._world_state_provider()
                context.world_state_snapshot = world_state.to_dict() if hasattr(world_state, 'to_dict') else {}
            except Exception as e:
                logger.error(f"World state provider error: {e}")
                context.world_state_snapshot = {}
        
        # Get self state snapshot
        if self._self_state_provider:
            try:
                self_state = self._self_state_provider()
                context.self_state_snapshot = self_state.to_dict() if hasattr(self_state, 'to_dict') else {}
            except Exception as e:
                logger.error(f"Self state provider error: {e}")
                context.self_state_snapshot = {}
        
        logger.debug(f"Perceived state: {len(context.world_state_snapshot)} world, {len(context.self_state_snapshot)} self")
    
    async def _phase_understand(self, context: DeliberationContext) -> None:
        """
        Phase 2: Understand current situation.
        
        Make sense of perceived state.
        """
        self._set_phase(ReasoningPhase.UNDERSTANDING)
        
        # Extract key information from state
        world = context.world_state_snapshot
        self_state = context.self_state_snapshot
        
        # Identify urgent issues
        if world.get("needs_attention"):
            for issue in world.get("needs_attention", []):
                context.constraints.append(f"address:{issue}")
        
        # Identify hard constraints
        if world.get("resource_pressure", 0) > 0.7:
            context.hard_constraints.append("conserve_resources")
        
        if self_state.get("cognitive", {}).get("fatigue") == "exhausted":
            context.hard_constraints.append("minimize_cognitive_load")
        
        # Time pressure
        if world.get("deadline_pressure", 0) > 0.7:
            context.constraints.append("time_critical")
        
        logger.debug(f"Understood: {len(context.constraints)} constraints, {len(context.hard_constraints)} hard")
    
    async def _phase_deliberate(
        self,
        context: DeliberationContext,
        goal: Optional[str] = None,
    ) -> None:
        """
        Phase 3: Generate options.
        
        Create potential intentions based on understanding.
        """
        self._set_phase(ReasoningPhase.DELIBERATING)
        
        world = context.world_state_snapshot
        self_state = context.self_state_snapshot
        
        # Generate options based on state
        options = []
        
        # Check for urgent tasks
        active_tasks = world.get("operational", {}).get("active_tasks", [])
        if active_tasks:
            for task in active_tasks[:context.max_options]:
                option = self._generate_task_intention(task, world, self_state)
                if option:
                    options.append(option)
        
        # Check for decisions needed
        pending = world.get("operational", {}).get("pending_decisions", [])
        if pending:
            for decision in pending[:3]:
                option = self._generate_decision_intention(decision, world, self_state)
                if option:
                    options.append(option)
        
        # Check for goal progress
        goal_progress = world.get("primary", {}).get("goal_progress", 0)
        if goal_progress < 0.3 and goal:
            option = self._generate_planning_intention(goal, world, self_state)
            if option:
                options.append(option)
        
        # Check for risks
        risk_level = world.get("primary", {}).get("risk_level", 0)
        if risk_level > 0.6:
            option = self._generate_risk_mitigation_intention(world, self_state)
            if option:
                options.append(option)
        
        # Check for resource issues
        resource_pressure = world.get("primary", {}).get("resource_pressure", 0)
        if resource_pressure > 0.7:
            option = self._generate_resource_intention(world, self_state)
            if option:
                options.append(option)
        
        # Check for fatigue
        fatigue = self_state.get("cognitive", {}).get("fatigue", "normal")
        if fatigue in ["tired", "exhausted", "critical"]:
            option = self._generate_recovery_intention(fatigue, world, self_state)
            if option:
                options.append(option)
        
        # Limit options
        context.options_generated = options[:context.max_options]
        
        # Update status
        if len(context.options_generated) > 0:
            context.status = DeliberationStatus.CONVERGING
        else:
            context.status = DeliberationStatus.STUCK
        
        logger.debug(f"Deliberated: {len(context.options_generated)} options generated")
    
    async def _phase_simulate(self, context: DeliberationContext) -> None:
        """
        Phase 4: Simulate options.
        
        Run mental simulations of potential intentions.
        
        CRITICAL: This is PURE simulation.
        No execution happens here.
        """
        self._set_phase(ReasoningPhase.SIMULATING)
        
        for option in context.options_generated:
            if context.simulations_run >= context.max_simulations:
                break
            
            # Run simulation
            simulation = self._simulate_intention(option, context)
            option.simulated_outcome = simulation.predicted_outcome
            option.simulation_confidence = simulation.simulation_quality
            
            # Update risk estimate
            option.estimated_risk = 1.0 - simulation.predicted_confidence
            
            context.simulations_run += 1
        
        logger.debug(f"Simulated: {context.simulations_run} options")
    
    async def _phase_evaluate(self, context: DeliberationContext) -> None:
        """
        Phase 5: Evaluate options.
        
        Score and rank intentions.
        """
        self._set_phase(ReasoningPhase.EVALUATING)
        
        # Score each option
        for option in context.options_generated:
            score = self._score_intention(option, context)
            option.confidence = score
        
        # Sort by confidence (descending)
        context.options_generated.sort(
            key=lambda i: i.confidence,
            reverse=True,
        )
        
        # Check for clear winner
        if context.options_generated:
            best = context.options_generated[0]
            if best.confidence > 0.7:
                context.status = DeliberationStatus.DECIDED
            elif best.confidence > 0.5 and len(context.options_generated) == 1:
                context.status = DeliberationStatus.DECIDED
        
        logger.debug(f"Evaluated: best confidence = {context.options_generated[0].confidence if context.options_generated else 0:.2f}")
    
    async def _phase_commit(self, context: DeliberationContext) -> List[Intention]:
        """
        Phase 6: Commit to intentions.
        
        Finalize and return intentions for execution.
        """
        self._set_phase(ReasoningPhase.COMMITTING)
        
        committed = []
        
        # Select top intentions
        for option in context.options_generated:
            if option.confidence >= 0.3:  # Minimum threshold
                committed.append(option)
                self._committed_intentions.append(option)
            else:
                self._rejected_intentions.append(option)
        
        # Trim history
        if len(self._committed_intentions) > 100:
            self._committed_intentions = self._committed_intentions[-100:]
        if len(self._rejected_intentions) > 100:
            self._rejected_intentions = self._rejected_intentions[-100:]
        
        self._set_phase(ReasoningPhase.IDLE)
        
        return committed
    
    # ==========================================
    # INTENTION GENERATION
    # ==========================================
    
    def _generate_task_intention(
        self,
        task: str,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for a task."""
        import uuid
        
        # Check capability
        can_execute = self_state.get("capabilities", {}).get("states", {}).get("execution", "unknown")
        
        if can_execute == "unreliable":
            # Need to delegate
            return Intention(
                intention_id=f"int-{uuid.uuid4().hex[:8]}",
                intention_type=IntentionType.DELEGATE,
                description=f"Delegate task: {task}",
                target=task,
                reasoning="Execution capability unreliable, delegation preferred",
                confidence=0.6,
                estimated_risk=0.3,
            )
        else:
            # Execute directly
            return Intention(
                intention_id=f"int-{uuid.uuid4().hex[:8]}",
                intention_type=IntentionType.EXECUTE,
                description=f"Execute task: {task}",
                target=task,
                reasoning="Direct execution with sufficient capability",
                confidence=0.7,
                estimated_risk=0.2,
            )
    
    def _generate_decision_intention(
        self,
        decision: str,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for a pending decision."""
        import uuid
        
        return Intention(
            intention_id=f"int-{uuid.uuid4().hex[:8]}",
            intention_type=IntentionType.QUERY,
            description=f"Gather info for decision: {decision}",
            target=decision,
            reasoning="Need more information to make decision",
            confidence=0.5,
            estimated_risk=0.1,
        )
    
    def _generate_planning_intention(
        self,
        goal: str,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for planning."""
        import uuid
        
        return Intention(
            intention_id=f"int-{uuid.uuid4().hex[:8]}",
            intention_type=IntentionType.PLAN,
            description=f"Create plan for goal: {goal}",
            target=goal,
            reasoning="Goal progress low, need better plan",
            confidence=0.6,
            estimated_risk=0.3,
            priority=8,
        )
    
    def _generate_risk_mitigation_intention(
        self,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for risk mitigation."""
        import uuid
        
        return Intention(
            intention_id=f"int-{uuid.uuid4().hex[:8]}",
            intention_type=IntentionType.RECOVER,
            description="Reduce current risk level",
            reasoning="High risk detected, need mitigation",
            confidence=0.7,
            estimated_risk=0.5,
            priority=9,
        )
    
    def _generate_resource_intention(
        self,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for resource management."""
        import uuid
        
        return Intention(
            intention_id=f"int-{uuid.uuid4().hex[:8]}",
            intention_type=IntentionType.DELEGATE,
            description="Delegate to reduce resource pressure",
            reasoning="Resource pressure high, delegation needed",
            confidence=0.6,
            estimated_risk=0.4,
        )
    
    def _generate_recovery_intention(
        self,
        fatigue: str,
        world: Dict[str, Any],
        self_state: Dict[str, Any],
    ) -> Optional[Intention]:
        """Generate intention for recovery."""
        import uuid
        
        if fatigue == "critical":
            return Intention(
                intention_id=f"int-{uuid.uuid4().hex[:8]}",
                intention_type=IntentionType.ABORT,
                description="Critical fatigue - abort current operations",
                reasoning="Cognitive resources critically depleted",
                confidence=0.9,
                estimated_risk=0.9,
                priority=10,
            )
        else:
            return Intention(
                intention_id=f"int-{uuid.uuid4().hex[:8]}",
                intention_type=IntentionType.REFLECT,
                description="Recovery reflection and consolidation",
                reasoning="Cognitive fatigue detected",
                confidence=0.7,
                estimated_risk=0.2,
            )
    
    # ==========================================
    # SIMULATION (PURE MENTAL)
    # ==========================================
    
    def _simulate_intention(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> SimulationResult:
        """
        Simulate an intention.
        
        CRITICAL: This is PURE MENTAL SIMULATION.
        No external effects.
        """
        # Base simulation on type
        if intention.intention_type == IntentionType.EXECUTE:
            return self._simulate_execution(intention, context)
        elif intention.intention_type == IntentionType.DELEGATE:
            return self._simulate_delegation(intention, context)
        elif intention.intention_type == IntentionType.PLAN:
            return self._simulate_planning(intention, context)
        elif intention.intention_type == IntentionType.RECOVER:
            return self._simulate_recovery(intention, context)
        else:
            return SimulationResult(
                intention_id=intention.intention_id,
                predicted_success=True,
                predicted_confidence=0.5,
                simulation_quality=0.3,
            )
    
    def _simulate_execution(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> SimulationResult:
        """Simulate execution intention."""
        self_state = context.self_state_snapshot
        
        # Check capability
        cap_confidence = self_state.get("capabilities", {}).get("confidence", 0.5)
        
        # Apply fatigue factor
        fatigue = self_state.get("cognitive", {}).get("fatigue", "normal")
        fatigue_factors = {
            "fresh": 1.0,
            "normal": 0.9,
            "tired": 0.7,
            "exhausted": 0.4,
            "critical": 0.2,
        }
        fatigue_factor = fatigue_factors.get(fatigue, 0.5)
        
        predicted_confidence = cap_confidence * fatigue_factor
        
        return SimulationResult(
            intention_id=intention.intention_id,
            predicted_success=predicted_confidence > 0.5,
            predicted_confidence=predicted_confidence,
            predicted_cost=0.5,
            predicted_duration_ms=1000.0,
            risk_factors=["capability", "fatigue"],
            simulation_quality=0.7,
        )
    
    def _simulate_delegation(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> SimulationResult:
        """Simulate delegation intention."""
        world = context.world_state_snapshot
        
        # Check agent availability
        agents = world.get("environment", {}).get("agent_availability", {})
        available_agents = sum(1 for available in agents.values() if available)
        
        if available_agents > 0:
            predicted_confidence = 0.7
            predicted_success = True
        else:
            predicted_confidence = 0.3
            predicted_success = False
        
        return SimulationResult(
            intention_id=intention.intention_id,
            predicted_success=predicted_success,
            predicted_confidence=predicted_confidence,
            predicted_cost=1.0,
            predicted_duration_ms=2000.0,
            risk_factors=["agent_availability", "communication"],
            simulation_quality=0.6,
        )
    
    def _simulate_planning(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> SimulationResult:
        """Simulate planning intention."""
        self_state = context.self_state_snapshot
        
        # Planning is generally safe
        cognitive_load = self_state.get("cognitive", {}).get("load", 0)
        
        if cognitive_load < 0.7:
            predicted_confidence = 0.8
        else:
            predicted_confidence = 0.5
        
        return SimulationResult(
            intention_id=intention.intention_id,
            predicted_success=True,
            predicted_confidence=predicted_confidence,
            predicted_cost=0.3,
            predicted_duration_ms=500.0,
            risk_factors=["cognitive_load"],
            simulation_quality=0.8,
        )
    
    def _simulate_recovery(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> SimulationResult:
        """Simulate recovery intention."""
        return SimulationResult(
            intention_id=intention.intention_id,
            predicted_success=True,
            predicted_confidence=0.8,
            predicted_cost=0.1,
            predicted_duration_ms=100.0,
            risk_factors=[],
            simulation_quality=0.9,
        )
    
    # ==========================================
    # SCORING
    # ==========================================
    
    def _score_intention(
        self,
        intention: Intention,
        context: DeliberationContext,
    ) -> float:
        """Score an intention."""
        score = intention.confidence  # Base score
        
        # Simulation bonus
        if intention.simulation_confidence > 0:
            score = score * 0.7 + intention.simulation_confidence * 0.3
        
        # Risk penalty
        score *= (1.0 - intention.estimated_risk * 0.3)
        
        # Priority bonus
        score += intention.priority * 0.02
        
        # Constraint satisfaction
        for constraint in context.hard_constraints:
            if constraint == "conserve_resources":
                if intention.intention_type == IntentionType.DELEGATE:
                    score *= 0.8  # Penalty for delegation when resources scarce
            elif constraint == "minimize_cognitive_load":
                if intention.intention_type in [IntentionType.PLAN, IntentionType.REFLECT]:
                    score *= 0.9
        
        return max(0.0, min(1.0, score))
    
    # ==========================================
    # PHASE MANAGEMENT
    # ==========================================
    
    def _set_phase(self, phase: ReasoningPhase) -> None:
        """Set current phase."""
        old_phase = self._current_phase
        self._current_phase = phase
        
        if old_phase != phase and self._on_phase_change:
            try:
                self._on_phase_change(old_phase, phase)
            except Exception as e:
                logger.error(f"Phase change callback error: {e}")
    
    # ==========================================
    # QUICK REASONING
    # ==========================================
    
    def quick_deliberate(
        self,
        options: List[Tuple[str, float, float]],  # (description, confidence, risk)
    ) -> Optional[Intention]:
        """
        Quick deliberation for simple choices.
        
        Useful for fast decisions when full cycle is overkill.
        """
        import uuid
        
        if not options:
            return None
        
        # Score and sort
        scored = [
            (desc, conf * (1 - risk * 0.3))
            for desc, conf, risk in options
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_desc, best_score = scored[0]
        
        return Intention(
            intention_id=f"int-{uuid.uuid4().hex[:8]}",
            intention_type=IntentionType.EXECUTE,
            description=best_desc,
            reasoning="Quick deliberation",
            confidence=best_score,
        )
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics."""
        return {
            "total_deliberations": self._total_deliberations,
            "total_intentions_produced": self._total_intentions_produced,
            "committed_intentions": len(self._committed_intentions),
            "rejected_intentions": len(self._rejected_intentions),
            "current_phase": self._current_phase.value,
        }
    
    def get_recent_intentions(self, limit: int = 10) -> List[Intention]:
        """Get recent committed intentions."""
        return self._committed_intentions[-limit:]

