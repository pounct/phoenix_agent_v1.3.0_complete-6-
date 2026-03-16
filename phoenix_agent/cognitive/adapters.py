"""
Phoenix Agent - Cognitive Adapters
===================================

Concrete implementations of CognitiveAdapter for different providers.

Available adapters:
    - LLMGatewayAdapter: Uses the external LLM Gateway
    - OpenAIAdapter: Uses OpenAI API directly
    - OllamaAdapter: Uses Ollama locally
    - MockCognitiveAdapter: For testing (no real LLM)

The key architectural insight:
    Phoenix NEVER knows which adapter is being used.
    Phoenix ONLY knows CognitiveEngine capabilities.

This is what makes Phoenix truly model-agnostic.

Version: 1.3.0
"""

from __future__ import annotations

import asyncio
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import json

from .engine import (
    CognitiveAdapter,
    CognitiveCapability,
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
)


logger = logging.getLogger("phoenix.cognitive.adapters")


# ============================================================================
# ADAPTER CONFIGURATION
# ============================================================================


@dataclass
class AdapterConfig:
    """Configuration for cognitive adapters."""
    timeout_seconds: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.7
    model: str = "default"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AdapterStatus(str, Enum):
    """Status of an adapter."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ============================================================================
# BASE ADAPTER IMPLEMENTATION
# ============================================================================


class BaseCognitiveAdapter(CognitiveAdapter):
    """
    Base implementation with common functionality.
    
    Subclasses only need to implement:
        - _call_model(): The actual model API call
        - provider_name: The provider name
    """
    
    def __init__(self, config: AdapterConfig = None):
        self.config = config or AdapterConfig()
        self._status = AdapterStatus.UNKNOWN
        self._last_health_check: Optional[datetime] = None
    
    @property
    def available_capabilities(self) -> List[CognitiveCapability]:
        """All adapters support all capabilities by default."""
        return list(CognitiveCapability)
    
    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Perform reasoning via model."""
        prompt = self._build_reasoning_prompt(request)
        response = await self._call_model(prompt, request)
        
        return ReasoningResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            reasoning_chain=response.get("reasoning_chain", []),
            conclusion=response.get("conclusion", response.get("output", "")),
            assumptions=response.get("assumptions", []),
            error=response.get("error"),
        )
    
    async def plan(self, request: PlanningRequest) -> PlanningResult:
        """Create a plan via model."""
        prompt = self._build_planning_prompt(request)
        response = await self._call_model(prompt, request)
        
        return PlanningResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            steps=response.get("steps", []),
            dependencies=response.get("dependencies", []),
            estimated_effort=response.get("estimated_effort", 0.0),
            risks=response.get("risks", []),
            error=response.get("error"),
        )
    
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate a result via model."""
        prompt = self._build_evaluation_prompt(request)
        response = await self._call_model(prompt, request)
        
        return EvaluationResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            score=response.get("score", 0.0),
            passed=response.get("passed", False),
            issues=response.get("issues", []),
            recommendations=response.get("recommendations", []),
            error=response.get("error"),
        )
    
    async def summarize(self, request: SummarizationRequest) -> SummarizationResult:
        """Summarize content via model."""
        prompt = self._build_summarization_prompt(request)
        response = await self._call_model(prompt, request)
        
        return SummarizationResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            summary=response.get("summary", response.get("output", "")),
            key_points=response.get("key_points", []),
            compression_ratio=response.get("compression_ratio", 0.0),
            error=response.get("error"),
        )
    
    async def reflect(self, request: ReflectionRequest) -> ReflectionResult:
        """Reflect on experience via model."""
        prompt = self._build_reflection_prompt(request)
        response = await self._call_model(prompt, request)
        
        return ReflectionResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            insights=response.get("insights", []),
            lessons_learned=response.get("lessons_learned", []),
            improvement_areas=response.get("improvement_areas", []),
            error=response.get("error"),
        )
    
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        """Make a decision via model."""
        prompt = self._build_decision_prompt(request)
        response = await self._call_model(prompt, request)
        
        return DecisionResult(
            request_id=request.request_id,
            success=response.get("success", False),
            output=response.get("output", ""),
            confidence=response.get("confidence", 0.5),
            provider=self.provider_name,
            model=self.config.model,
            chosen_option=response.get("chosen_option", {}),
            reasoning=response.get("reasoning", ""),
            alternatives=response.get("alternatives", []),
            risk_assessment=response.get("risk_assessment", {}),
            error=response.get("error"),
        )
    
    # ========================================================================
    # ABSTRACT METHODS
    # ========================================================================
    
    @abstractmethod
    async def _call_model(
        self,
        prompt: str,
        request: Any
    ) -> Dict[str, Any]:
        """
        Call the underlying model.
        
        Subclasses implement this to integrate with their specific provider.
        """
        pass
    
    # ========================================================================
    # PROMPT BUILDERS
    # ========================================================================
    
    def _build_reasoning_prompt(self, request: ReasoningRequest) -> str:
        """Build a prompt for reasoning."""
        parts = [
            f"Problem: {request.problem}",
            "",
            "Perform logical reasoning to analyze this problem.",
        ]
        
        if request.constraints:
            parts.append(f"\nConstraints:\n" + "\n".join(f"- {c}" for c in request.constraints))
        
        if request.style:
            parts.append(f"\nReasoning style: {request.style}")
        
        parts.append("\nProvide your reasoning chain, assumptions, and conclusion.")
        
        return "\n".join(parts)
    
    def _build_planning_prompt(self, request: PlanningRequest) -> str:
        """Build a prompt for planning."""
        parts = [
            f"Goal: {request.goal}",
            "",
            "Create a detailed plan to achieve this goal.",
        ]
        
        if request.constraints:
            parts.append(f"\nConstraints:\n" + "\n".join(f"- {c}" for c in request.constraints))
        
        if request.available_actions:
            parts.append(f"\nAvailable actions:\n" + "\n".join(f"- {a}" for a in request.available_actions))
        
        parts.append(f"\nPlanning horizon: {request.horizon} steps")
        parts.append("\nProvide steps, dependencies, estimated effort, and risks.")
        
        return "\n".join(parts)
    
    def _build_evaluation_prompt(self, request: EvaluationRequest) -> str:
        """Build a prompt for evaluation."""
        parts = [
            f"Result to evaluate: {request.result}",
            "",
            "Evaluate this result against the criteria.",
        ]
        
        if request.criteria:
            parts.append(f"\nCriteria:\n" + "\n".join(f"- {c}" for c in request.criteria))
        
        if request.expected_outcome:
            parts.append(f"\nExpected outcome: {request.expected_outcome}")
        
        parts.append("\nProvide a score (0-1), pass/fail, issues, and recommendations.")
        
        return "\n".join(parts)
    
    def _build_summarization_prompt(self, request: SummarizationRequest) -> str:
        """Build a prompt for summarization."""
        parts = [
            f"Content to summarize:\n{request.content[:2000]}...",
            "",
            f"Summarize this content (max {request.max_length} characters).",
        ]
        
        if request.style:
            parts.append(f"Style: {request.style}")
        
        if request.focus:
            parts.append(f"Focus on: {request.focus}")
        
        parts.append("\nProvide summary and key points.")
        
        return "\n".join(parts)
    
    def _build_reflection_prompt(self, request: ReflectionRequest) -> str:
        """Build a prompt for reflection."""
        parts = [
            f"Experience: {request.experience}",
            "",
            "Reflect on this experience.",
        ]
        
        if request.outcome:
            parts.append(f"\nOutcome: {request.outcome}")
        
        if request.learning_goals:
            parts.append(f"\nLearning goals:\n" + "\n".join(f"- {g}" for g in request.learning_goals))
        
        parts.append("\nProvide insights, lessons learned, and areas for improvement.")
        
        return "\n".join(parts)
    
    def _build_decision_prompt(self, request: DecisionRequest) -> str:
        """Build a prompt for decision making."""
        parts = [
            "Make a decision among the following options:",
            "",
        ]
        
        for i, option in enumerate(request.options):
            parts.append(f"Option {i+1}: {option}")
        
        if request.criteria:
            parts.append(f"\nCriteria:\n" + "\n".join(f"- {c}" for c in request.criteria))
        
        if request.context:
            parts.append(f"\nContext: {request.context}")
        
        parts.append(f"\nRisk tolerance: {request.risk_tolerance}")
        parts.append("\nChoose the best option and explain your reasoning.")
        
        return "\n".join(parts)


# ============================================================================
# LLM GATEWAY ADAPTER
# ============================================================================


class LLMGatewayAdapter(BaseCognitiveAdapter):
    """
    Adapter for the external LLM Gateway.
    
    This is the PRIMARY adapter for production Phoenix deployments.
    The LLM Gateway handles:
        - Provider routing (OpenAI, Claude, etc.)
        - Caching
        - Rate limiting
        - Fallback chains
    
    Phoenix treats the Gateway as just another cognitive provider.
    Phoenix does NOT depend on the Gateway - it can use other adapters.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        config: AdapterConfig = None,
    ):
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or self.config.api_key
        self._session = None
    
    @property
    def provider_name(self) -> str:
        return "llm_gateway"
    
    async def _get_session(self):
        """Lazy init of HTTP session."""
        if self._session is None:
            try:
                import aiohttp
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                self._session = aiohttp.ClientSession(
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                )
            except ImportError:
                raise RuntimeError("aiohttp required: pip install aiohttp")
        return self._session
    
    async def _call_model(
        self,
        prompt: str,
        request: Any
    ) -> Dict[str, Any]:
        """Call the LLM Gateway."""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Build request
            payload = {
                "prompt": prompt,
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }
            
            # Call gateway
            async with session.post(
                f"{self.base_url}/v1/generate",
                json=payload
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gateway error {response.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"Gateway error: {response.status}",
                        "latency_ms": latency_ms,
                    }
                
                data = await response.json()
                
                return {
                    "success": True,
                    "output": data.get("response", ""),
                    "confidence": 0.8,  # Default confidence
                    "provider": data.get("provider", "llm_gateway"),
                    "latency_ms": latency_ms,
                }
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Gateway request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
            }
    
    async def health_check(self) -> bool:
        """Check gateway health."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                self._status = (
                    AdapterStatus.HEALTHY
                    if response.status == 200
                    else AdapterStatus.UNHEALTHY
                )
                self._last_health_check = datetime.utcnow()
                return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._status = AdapterStatus.UNHEALTHY
            self._last_health_check = datetime.utcnow()
            return False
    
    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None


# ============================================================================
# OPENAI ADAPTER
# ============================================================================


class OpenAIAdapter(BaseCognitiveAdapter):
    """
    Direct OpenAI API adapter.
    
    Use this when you want to bypass the LLM Gateway and call OpenAI directly.
    
    Note: Phoenix still doesn't know it's using OpenAI.
    Phoenix only knows it's using CognitiveEngine.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        config: AdapterConfig = None,
    ):
        super().__init__(config)
        self.api_key = api_key or self.config.api_key
        self.config.model = model
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    async def _get_client(self):
        """Lazy init of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai required: pip install openai")
        return self._client
    
    async def _call_model(
        self,
        prompt: str,
        request: Any
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            content = response.choices[0].message.content if response.choices else ""
            
            return {
                "success": True,
                "output": content,
                "confidence": 0.8,
                "provider": "openai",
                "model": self.config.model,
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"OpenAI request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
            }
    
    async def health_check(self) -> bool:
        """Check OpenAI API availability."""
        try:
            # Simple models list check
            client = await self._get_client()
            await client.models.list()
            self._status = AdapterStatus.HEALTHY
            self._last_health_check = datetime.utcnow()
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            self._status = AdapterStatus.UNHEALTHY
            self._last_health_check = datetime.utcnow()
            return False


# ============================================================================
# OLLAMA ADAPTER
# ============================================================================


class OllamaAdapter(BaseCognitiveAdapter):
    """
    Ollama local model adapter.
    
    Use this for local, offline model inference.
    Perfect for:
        - Development
        - Air-gapped environments
        - Cost-free operation
        - Privacy-sensitive applications
    
    Phoenix doesn't know it's using a local model.
    Phoenix just knows it has cognitive capabilities.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        config: AdapterConfig = None,
    ):
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.config.model = model
        self._session = None
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    async def _get_session(self):
        """Lazy init of HTTP session."""
        if self._session is None:
            try:
                import aiohttp
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                )
            except ImportError:
                raise RuntimeError("aiohttp required: pip install aiohttp")
        return self._session
    
    async def _call_model(
        self,
        prompt: str,
        request: Any
    ) -> Dict[str, Any]:
        """Call Ollama API."""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama error {response.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"Ollama error: {response.status}",
                        "latency_ms": latency_ms,
                    }
                
                data = await response.json()
                
                return {
                    "success": True,
                    "output": data.get("response", ""),
                    "confidence": 0.7,  # Slightly lower for local models
                    "provider": "ollama",
                    "model": self.config.model,
                    "latency_ms": latency_ms,
                }
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Ollama request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
            }
    
    async def health_check(self) -> bool:
        """Check Ollama availability."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                self._status = (
                    AdapterStatus.HEALTHY
                    if response.status == 200
                    else AdapterStatus.UNHEALTHY
                )
                self._last_health_check = datetime.utcnow()
                return response.status == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            self._status = AdapterStatus.UNHEALTHY
            self._last_health_check = datetime.utcnow()
            return False
    
    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None


# ============================================================================
# MOCK ADAPTER (For Testing)
# ============================================================================


class MockCognitiveAdapter(BaseCognitiveAdapter):
    """
    Mock adapter for testing.
    
    Returns predictable responses without calling any real model.
    Perfect for:
        - Unit tests
        - CI/CD pipelines
        - Development without API keys
    
    Phoenix code is IDENTICAL whether using Mock or real adapter.
    This proves Phoenix is truly model-agnostic.
    """
    
    def __init__(
        self,
        response_content: str = "Mock cognitive response",
        confidence: float = 0.8,
        simulate_latency_ms: float = 0.0,
    ):
        super().__init__()
        self.response_content = response_content
        self.confidence = confidence
        self.simulate_latency_ms = simulate_latency_ms
        
        # Stats
        self.call_count = 0
        self.last_request: Optional[str] = None
    
    @property
    def provider_name(self) -> str:
        return "mock"
    
    async def _call_model(
        self,
        prompt: str,
        request: Any
    ) -> Dict[str, Any]:
        """Return mock response."""
        self.call_count += 1
        self.last_request = prompt
        
        if self.simulate_latency_ms > 0:
            await asyncio.sleep(self.simulate_latency_ms / 1000)
        
        # Return different mock responses based on request type
        if isinstance(request, ReasoningRequest):
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "reasoning_chain": ["Step 1: Analysis", "Step 2: Evaluation", "Step 3: Conclusion"],
                "conclusion": self.response_content,
                "assumptions": ["Assumption 1", "Assumption 2"],
            }
        
        elif isinstance(request, PlanningRequest):
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "steps": [
                    {"step": 1, "action": "Initialize", "description": "Start the process"},
                    {"step": 2, "action": "Execute", "description": "Perform main task"},
                    {"step": 3, "action": "Complete", "description": "Finish and verify"},
                ],
                "dependencies": [{"from": "1", "to": "2"}, {"from": "2", "to": "3"}],
                "estimated_effort": 1.5,
                "risks": ["Risk 1: Potential delay"],
            }
        
        elif isinstance(request, EvaluationRequest):
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "score": 0.85,
                "passed": True,
                "issues": [],
                "recommendations": ["Recommendation 1: Continue monitoring"],
            }
        
        elif isinstance(request, SummarizationRequest):
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "summary": self.response_content,
                "key_points": ["Point 1", "Point 2", "Point 3"],
                "compression_ratio": 0.3,
            }
        
        elif isinstance(request, ReflectionRequest):
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "insights": ["Insight 1: Key learning"],
                "lessons_learned": ["Lesson 1: Important takeaway"],
                "improvement_areas": ["Area 1: Can be improved"],
            }
        
        elif isinstance(request, DecisionRequest):
            chosen = request.options[0] if request.options else {}
            return {
                "success": True,
                "output": self.response_content,
                "confidence": self.confidence,
                "provider": "mock",
                "chosen_option": chosen,
                "reasoning": "This option provides the best balance of benefits and risks.",
                "alternatives": request.options[1:] if len(request.options) > 1 else [],
                "risk_assessment": {"overall": 0.3},
            }
        
        return {
            "success": True,
            "output": self.response_content,
            "confidence": self.confidence,
            "provider": "mock",
        }
    
    async def health_check(self) -> bool:
        """Mock is always healthy."""
        self._status = AdapterStatus.HEALTHY
        self._last_health_check = datetime.utcnow()
        return True
    
    def reset(self) -> None:
        """Reset mock state."""
        self.call_count = 0
        self.last_request = None


# ============================================================================
# FACTORIES
# ============================================================================


def create_adapter(
    provider: str = "mock",
    **kwargs
) -> CognitiveAdapter:
    """
    Create a cognitive adapter by provider name.
    
    Args:
        provider: Provider name ("llm_gateway", "openai", "ollama", "mock")
        **kwargs: Provider-specific configuration
    
    Returns:
        Configured CognitiveAdapter
    
    Example:
        # Create LLM Gateway adapter
        adapter = create_adapter("llm_gateway", base_url="http://gateway:8000")
        
        # Create OpenAI adapter
        adapter = create_adapter("openai", api_key="sk-...", model="gpt-4")
        
        # Create Ollama adapter
        adapter = create_adapter("ollama", model="llama3")
        
        # Create mock for testing
        adapter = create_adapter("mock")
    """
    if provider == "llm_gateway":
        return LLMGatewayAdapter(**kwargs)
    elif provider == "openai":
        return OpenAIAdapter(**kwargs)
    elif provider == "ollama":
        return OllamaAdapter(**kwargs)
    elif provider == "mock":
        return MockCognitiveAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_adapter_from_config(config: Dict[str, Any]) -> CognitiveAdapter:
    """
    Create an adapter from a configuration dictionary.
    
    Example:
        config = {
            "provider": "openai",
            "api_key": "sk-...",
            "model": "gpt-4",
        }
        adapter = create_adapter_from_config(config)
    """
    provider = config.pop("provider", "mock")
    return create_adapter(provider, **config)
