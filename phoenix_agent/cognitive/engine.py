"""
Phoenix Agent - Cognitive Engine
=================================

THE MODEL-AGNOSTIC ABSTRACTION.

Phoenix NEVER depends on a specific LLM.
Phoenix ONLY depends on CognitiveEngine capabilities.

This is the core distinction:
    - LLM = Model that reasons
    - Agent = System that acts, plans, remembers, orchestrates
    - CognitiveEngine = The bridge between them

Architecture:
    Phoenix Runtime
         │
         ▼
    CognitiveEngine.reason()
    CognitiveEngine.plan()
    CognitiveEngine.evaluate()
    CognitiveEngine.summarize()
    CognitiveEngine.reflect()
         │
         ▼
    CognitiveAdapter (LLMGateway, OpenAI, Ollama, etc.)
         │
         ▼
    Model Provider

Version: 1.3.0
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from uuid import uuid4
import logging


logger = logging.getLogger("phoenix.cognitive")


# ============================================================================
# COGNITIVE CAPABILITIES
# ============================================================================


class CognitiveCapability(str, Enum):
    """
    Capabilities that a cognitive engine can provide.
    
    These are the ONLY things Phoenix depends on.
    Phoenix does NOT depend on:
        - "OpenAI API"
        - "LLM Gateway"
        - "GPT-4"
    
    Phoenix depends on:
        - "Can reason?"
        - "Can plan?"
        - "Can evaluate?"
    """
    REASON = "reason"              # Logical reasoning
    PLAN = "plan"                  # Strategic planning
    EVALUATE = "evaluate"          # Result evaluation
    SUMMARIZE = "summarize"        # Content summarization
    REFLECT = "reflect"            # Self-reflection
    DECIDE = "decide"              # Decision making
    CLASSIFY = "classify"          # Classification
    EXTRACT = "extract"            # Information extraction
    GENERATE = "generate"          # Content generation


# ============================================================================
# REQUEST TYPES
# ============================================================================


@dataclass
class CognitiveRequest:
    """Base class for cognitive requests."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0


@dataclass
class ReasoningRequest(CognitiveRequest):
    """Request for logical reasoning."""
    problem: str = ""
    constraints: List[str] = field(default_factory=list)
    max_depth: int = 5
    style: str = "analytical"  # analytical, creative, critical


@dataclass
class PlanningRequest(CognitiveRequest):
    """Request for strategic planning."""
    goal: str = ""
    constraints: List[str] = field(default_factory=list)
    available_actions: List[str] = field(default_factory=list)
    horizon: int = 5  # Planning horizon


@dataclass
class EvaluationRequest(CognitiveRequest):
    """Request for result evaluation."""
    result: str = ""
    criteria: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SummarizationRequest(CognitiveRequest):
    """Request for content summarization."""
    content: str = ""
    max_length: int = 500
    style: str = "concise"  # concise, detailed, bullet_points
    focus: str = ""  # What to focus on


@dataclass
class ReflectionRequest(CognitiveRequest):
    """Request for self-reflection."""
    experience: str = ""
    outcome: str = ""
    learning_goals: List[str] = field(default_factory=list)


@dataclass
class DecisionRequest(CognitiveRequest):
    """Request for decision making."""
    options: List[Dict[str, Any]] = field(default_factory=list)
    criteria: List[str] = field(default_factory=list)
    context: str = ""
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive


# ============================================================================
# RESULT TYPES
# ============================================================================


@dataclass
class CognitiveResult:
    """Base class for cognitive results."""
    request_id: str = ""
    success: bool = False
    output: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    provider: str = "unknown"
    model: str = "unknown"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult(CognitiveResult):
    """Result of reasoning."""
    reasoning_chain: List[str] = field(default_factory=list)
    conclusion: str = ""
    assumptions: List[str] = field(default_factory=list)


@dataclass
class PlanningResult(CognitiveResult):
    """Result of planning."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    estimated_effort: float = 0.0
    risks: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult(CognitiveResult):
    """Result of evaluation."""
    score: float = 0.0
    passed: bool = False
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SummarizationResult(CognitiveResult):
    """Result of summarization."""
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    compression_ratio: float = 0.0


@dataclass
class ReflectionResult(CognitiveResult):
    """Result of reflection."""
    insights: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)


@dataclass
class DecisionResult(CognitiveResult):
    """Result of decision."""
    chosen_option: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    risk_assessment: Dict[str, float] = field(default_factory=dict)


# ============================================================================
# COGNITIVE ADAPTER INTERFACE
# ============================================================================


class CognitiveAdapter(ABC):
    """
    Abstract interface for cognitive providers.
    
    This is what Phoenix talks to. Phoenix NEVER talks to:
        - OpenAI API directly
        - Ollama API directly
        - LLM Gateway directly
    
    Each provider implements this interface:
        - LLMGatewayAdapter: Uses the LLM Gateway
        - OpenAIAdapter: Uses OpenAI directly
        - OllamaAdapter: Uses Ollama locally
        - MockCognitiveAdapter: For testing
    
    This makes Phoenix model-agnostic and future-proof.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider."""
        pass
    
    @property
    @abstractmethod
    def available_capabilities(self) -> List[CognitiveCapability]:
        """Capabilities this provider supports."""
        pass
    
    @abstractmethod
    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Perform logical reasoning."""
        pass
    
    @abstractmethod
    async def plan(self, request: PlanningRequest) -> PlanningResult:
        """Create a plan."""
        pass
    
    @abstractmethod
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate a result."""
        pass
    
    @abstractmethod
    async def summarize(self, request: SummarizationRequest) -> SummarizationResult:
        """Summarize content."""
        pass
    
    @abstractmethod
    async def reflect(self, request: ReflectionRequest) -> ReflectionResult:
        """Reflect on experience."""
        pass
    
    @abstractmethod
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        """Make a decision."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        pass
    
    def supports(self, capability: CognitiveCapability) -> bool:
        """Check if capability is supported."""
        return capability in self.available_capabilities


# ============================================================================
# COGNITIVE ENGINE
# ============================================================================


@dataclass
class CognitiveConfig:
    """Configuration for CognitiveEngine."""
    default_timeout: float = 60.0
    max_retries: int = 3
    fallback_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: float = 3600.0  # 1 hour
    log_requests: bool = True


class CognitiveEngine:
    """
    THE MODEL-AGNOSTIC COGNITIVE ENGINE.
    
    This is what Phoenix Runtime uses. The key insight:
    
        Phoenix does NOT use an LLM.
        Phoenix uses COGNITIVE CAPABILITIES.
    
    Example:
        # Phoenix Runtime code:
        engine = CognitiveEngine(adapter=LLMGatewayAdapter())
        
        # Use cognitive capabilities, NOT LLM-specific APIs
        result = await engine.reason(
            "Analyze this architecture for scalability issues"
        )
        
        # Switch providers WITHOUT changing Phoenix
        engine = CognitiveEngine(adapter=OllamaAdapter())
        result = await engine.reason("...")  # Same API!
    
    This makes Phoenix:
        - Portable: Works with any model
        - Independent: No vendor lock-in
        - Future-proof: New models just need an adapter
        - Testable: Mock adapter for testing
    """
    
    def __init__(
        self,
        adapter: CognitiveAdapter,
        config: CognitiveConfig = None,
        fallback_adapter: Optional[CognitiveAdapter] = None,
    ):
        self.adapter = adapter
        self.config = config or CognitiveConfig()
        self.fallback_adapter = fallback_adapter
        
        # Cache
        self._cache: Dict[str, CognitiveResult] = {}
        
        # Stats
        self._request_count = 0
        self._total_latency_ms = 0.0
        
        logger.info(
            f"CognitiveEngine initialized with provider: {adapter.provider_name}"
        )
    
    # ========================================================================
    # CORE CAPABILITIES
    # ========================================================================
    
    async def reason(
        self,
        problem: str,
        constraints: List[str] = None,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> ReasoningResult:
        """
        Perform logical reasoning.
        
        This is NOT "call GPT-4".
        This is "use cognitive capability to reason".
        
        The adapter decides HOW to reason:
        - LLMGatewayAdapter: Uses LLM Gateway
        - OpenAIAdapter: Uses OpenAI API
        - OllamaAdapter: Uses local Ollama
        - RuleBasedAdapter: Uses rules (no LLM needed)
        """
        request = ReasoningRequest(
            problem=problem,
            constraints=constraints or [],
            context=context or {},
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.reason(request),
            CognitiveCapability.REASON,
            request.request_id
        )
    
    async def plan(
        self,
        goal: str,
        constraints: List[str] = None,
        available_actions: List[str] = None,
        **kwargs
    ) -> PlanningResult:
        """
        Create a strategic plan.
        
        Phoenix uses this for task decomposition and execution planning.
        """
        request = PlanningRequest(
            goal=goal,
            constraints=constraints or [],
            available_actions=available_actions or [],
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.plan(request),
            CognitiveCapability.PLAN,
            request.request_id
        )
    
    async def evaluate(
        self,
        result: str,
        criteria: List[str] = None,
        expected_outcome: str = "",
        **kwargs
    ) -> EvaluationResult:
        """
        Evaluate a result against criteria.
        
        Phoenix uses this for quality assessment and success validation.
        """
        request = EvaluationRequest(
            result=result,
            criteria=criteria or [],
            expected_outcome=expected_outcome,
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.evaluate(request),
            CognitiveCapability.EVALUATE,
            request.request_id
        )
    
    async def summarize(
        self,
        content: str,
        max_length: int = 500,
        style: str = "concise",
        **kwargs
    ) -> SummarizationResult:
        """
        Summarize content.
        
        Phoenix uses this for memory compression and context management.
        """
        request = SummarizationRequest(
            content=content,
            max_length=max_length,
            style=style,
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.summarize(request),
            CognitiveCapability.SUMMARIZE,
            request.request_id
        )
    
    async def reflect(
        self,
        experience: str,
        outcome: str = "",
        **kwargs
    ) -> ReflectionResult:
        """
        Reflect on an experience.
        
        Phoenix uses this for learning and self-improvement.
        """
        request = ReflectionRequest(
            experience=experience,
            outcome=outcome,
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.reflect(request),
            CognitiveCapability.REFLECT,
            request.request_id
        )
    
    async def decide(
        self,
        options: List[Dict[str, Any]],
        criteria: List[str] = None,
        context: str = "",
        **kwargs
    ) -> DecisionResult:
        """
        Make a decision among options.
        
        Phoenix uses this for action selection and delegation choices.
        """
        request = DecisionRequest(
            options=options,
            criteria=criteria or [],
            context=context,
            **kwargs
        )
        
        return await self._execute_with_fallback(
            lambda a: a.decide(request),
            CognitiveCapability.DECIDE,
            request.request_id
        )
    
    # ========================================================================
    # EXECUTION HELPERS
    # ========================================================================
    
    async def _execute_with_fallback(
        self,
        executor: Callable[[CognitiveAdapter], Any],
        capability: CognitiveCapability,
        request_id: str,
    ) -> CognitiveResult:
        """Execute with fallback support."""
        start_time = time.time()
        self._request_count += 1
        
        # Check cache
        if self.config.cache_enabled:
            cache_key = f"{capability.value}:{request_id}"
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {capability}")
                return self._cache[cache_key]
        
        # Try primary adapter
        try:
            if self.adapter.supports(capability):
                result = await self._execute_with_retry(executor, self.adapter)
                self._record_success(result, start_time)
                
                if self.config.cache_enabled:
                    self._cache[cache_key] = result
                
                return result
        except Exception as e:
            logger.warning(f"Primary adapter failed: {e}")
            
            # Try fallback
            if self.config.fallback_enabled and self.fallback_adapter:
                if self.fallback_adapter.supports(capability):
                    try:
                        result = await executor(self.fallback_adapter)
                        self._record_success(result, start_time)
                        return result
                    except Exception as e2:
                        logger.error(f"Fallback adapter also failed: {e2}")
        
        # Return failure
        latency_ms = (time.time() - start_time) * 1000
        return CognitiveResult(
            request_id=request_id,
            success=False,
            error=f"Capability {capability} not available",
            latency_ms=latency_ms,
        )
    
    async def _execute_with_retry(
        self,
        executor: Callable[[CognitiveAdapter], Any],
        adapter: CognitiveAdapter,
    ) -> CognitiveResult:
        """Execute with retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await executor(adapter)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise last_error
    
    def _record_success(self, result: CognitiveResult, start_time: float) -> None:
        """Record successful execution."""
        result.latency_ms = (time.time() - start_time) * 1000
        self._total_latency_ms += result.latency_ms
    
    # ========================================================================
    # CAPABILITY QUERIES
    # ========================================================================
    
    @property
    def available_capabilities(self) -> List[CognitiveCapability]:
        """Get available capabilities."""
        return self.adapter.available_capabilities
    
    def supports(self, capability: CognitiveCapability) -> bool:
        """Check if capability is supported."""
        return self.adapter.supports(capability)
    
    async def health_check(self) -> bool:
        """Check cognitive engine health."""
        try:
            primary = await self.adapter.health_check()
            if primary:
                return True
            if self.fallback_adapter:
                return await self.fallback_adapter.health_check()
            return False
        except Exception:
            return False
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        avg_latency = (
            self._total_latency_ms / self._request_count
            if self._request_count > 0 else 0
        )
        
        return {
            "provider": self.adapter.provider_name,
            "request_count": self._request_count,
            "total_latency_ms": self._total_latency_ms,
            "average_latency_ms": avg_latency,
            "cache_size": len(self._cache),
            "capabilities": [c.value for c in self.available_capabilities],
        }
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()


# ============================================================================
# FACTORY
# ============================================================================


def create_cognitive_engine(
    adapter: CognitiveAdapter,
    config: CognitiveConfig = None,
    fallback_adapter: Optional[CognitiveAdapter] = None,
) -> CognitiveEngine:
    """
    Create a CognitiveEngine.
    
    Example:
        # Using LLM Gateway
        from phoenix_agent.cognitive import LLMGatewayAdapter
        engine = create_cognitive_engine(LLMGatewayAdapter())
        
        # Using Ollama locally
        from phoenix_agent.cognitive import OllamaAdapter
        engine = create_cognitive_engine(OllamaAdapter())
        
        # With fallback
        engine = create_cognitive_engine(
            adapter=LLMGatewayAdapter(),
            fallback_adapter=OllamaAdapter()  # Fallback to local
        )
    """
    return CognitiveEngine(
        adapter=adapter,
        config=config,
        fallback_adapter=fallback_adapter,
    )
