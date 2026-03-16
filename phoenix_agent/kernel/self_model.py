"""
Self Model - Continuous Self Representation
============================================

LAW 3: AGENT MUST CONTINUOUSLY MODEL ITSELF.

This is NOT identity.
Identity = static (who I am).
Self Model = dynamic (how I'm doing).

The Self Model:
    - Tracks current performance
    - Tracks current load
    - Tracks current reliability
    - Tracks current strengths/weaknesses
    - Enables SELF-CALIBRATION

Why This Matters:
    Without self-model, agent is static.
    With self-model, agent ADAPTS.

Example Adaptations:
    - If delegation success ↓ → reduce delegation
    - If tool failures ↑ → change strategy
    - If cognitive load ↑ → simplify plans
    - If confidence ↓ → seek more information

This transforms:
    monitoring passif → adaptation active

Architecture Position:
    Self Model is the foundation for SelfRegulation.
    Regulation READS self-state, not just metrics.

Version: 3.0.0 (Cognitive Kernel)
"""

from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import logging
import math


logger = logging.getLogger("phoenix.kernel.self_model")


# ==========================================
# PERFORMANCE TREND
# ==========================================

class PerformanceTrend(str, Enum):
    """Trends in performance."""
    IMPROVING = "improving"         # Getting better
    STABLE = "stable"              # No significant change
    DECLINING = "declining"        # Getting worse
    VOLATILE = "volatile"          # Inconsistent
    UNKNOWN = "unknown"            # Not enough data


class CapabilityState(str, Enum):
    """State of a capability."""
    STRONG = "strong"              # High confidence, reliable
    PROFICIENT = "proficient"      # Good performance
    DEVELOPING = "developing"      # Learning, improving
    UNRELIABLE = "unreliable"      # Recent failures
    UNKNOWN = "unknown"            # Not enough data


class FatigueLevel(str, Enum):
    """Cognitive fatigue levels."""
    FRESH = "fresh"                # Full capacity
    NORMAL = "normal"              # Normal operation
    TIRED = "tired"                # Reduced capacity
    EXHAUSTED = "exhausted"        # Need recovery
    CRITICAL = "critical"          # Risk of failure


# ==========================================
# ADAPTIVE PARAMETER
# ==========================================

@dataclass
class AdaptiveParameter:
    """
    A parameter that adapts based on performance.
    
    Self-model uses these to calibrate behavior.
    """
    name: str
    current_value: float
    baseline_value: float
    min_value: float
    max_value: float
    
    # Adaptation history
    adjustments: List[Tuple[datetime, float, str]] = field(default_factory=list)
    
    # Performance correlation
    performance_correlation: float = 0.0
    last_adjustment_time: Optional[datetime] = None
    
    def adjust(self, delta: float, reason: str) -> float:
        """Adjust the parameter value."""
        old_value = self.current_value
        self.current_value = max(
            self.min_value,
            min(self.max_value, self.current_value + delta)
        )
        
        if abs(old_value - self.current_value) > 0.001:
            self.adjustments.append((
                datetime.utcnow(),
                self.current_value,
                reason,
            ))
            self.last_adjustment_time = datetime.utcnow()
        
        # Trim history
        if len(self.adjustments) > 100:
            self.adjustments = self.adjustments[-100:]
        
        return self.current_value
    
    def reset_to_baseline(self) -> None:
        """Reset to baseline value."""
        self.current_value = self.baseline_value
    
    def trend(self) -> str:
        """Get recent adjustment trend."""
        if len(self.adjustments) < 3:
            return "stable"
        
        recent = self.adjustments[-10:]
        values = [a[1] for a in recent]
        
        if values[-1] > values[0] + 0.1:
            return "increasing"
        elif values[-1] < values[0] - 0.1:
            return "decreasing"
        else:
            return "stable"


# ==========================================
# CAPABILITY METRICS
# ==========================================

@dataclass
class CapabilityMetrics:
    """Metrics for a single capability."""
    capability_name: str
    
    # Success tracking
    total_attempts: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Recent performance
    recent_outcomes: deque = field(default_factory=lambda: deque(maxlen=20))
    
    # Timing
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    
    # Cost
    total_cost: float = 0.0
    avg_cost: float = 0.0
    
    # State
    state: CapabilityState = CapabilityState.UNKNOWN
    confidence: float = 0.5
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.5
        return self.success_count / self.total_attempts
    
    @property
    def recent_success_rate(self) -> float:
        """Calculate recent success rate."""
        if not self.recent_outcomes:
            return 0.5
        return sum(1 for o in self.recent_outcomes if o) / len(self.recent_outcomes)
    
    def record_outcome(
        self,
        success: bool,
        time_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Record an outcome."""
        self.total_attempts += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        self.recent_outcomes.append(success)
        
        if time_ms > 0:
            self.total_time_ms += time_ms
            self.avg_time_ms = self.total_time_ms / self.total_attempts
        
        if cost > 0:
            self.total_cost += cost
            self.avg_cost = self.total_cost / self.total_attempts
        
        self.last_used = datetime.utcnow()
        self._update_state()
    
    def _update_state(self) -> None:
        """Update capability state based on performance."""
        if self.total_attempts < 3:
            self.state = CapabilityState.UNKNOWN
            self.confidence = 0.5
            return
        
        recent_rate = self.recent_success_rate
        overall_rate = self.success_rate
        
        # Update confidence
        self.confidence = (recent_rate * 0.7 + overall_rate * 0.3)
        
        # Determine state
        if recent_rate >= 0.9 and self.total_attempts >= 10:
            self.state = CapabilityState.STRONG
        elif recent_rate >= 0.7:
            self.state = CapabilityState.PROFICIENT
        elif recent_rate >= 0.5:
            self.state = CapabilityState.DEVELOPING
        else:
            self.state = CapabilityState.UNRELIABLE


# ==========================================
# SELF STATE
# ==========================================

@dataclass
class SelfState:
    """
    Current state of the agent's self-model.
    
    This is a SNAPSHOT of self-awareness at a point in time.
    """
    # Identity (relatively stable)
    agent_id: str
    agent_name: str
    role: str
    
    # Performance (dynamic)
    overall_success_rate: float = 0.5
    recent_success_rate: float = 0.5
    performance_trend: PerformanceTrend = PerformanceTrend.UNKNOWN
    
    # Capability (per-capability metrics)
    capability_metrics: Dict[str, CapabilityMetrics] = field(default_factory=dict)
    strong_capabilities: List[str] = field(default_factory=list)
    weak_capabilities: List[str] = field(default_factory=list)
    
    # Cognitive state
    cognitive_load: float = 0.0
    fatigue_level: FatigueLevel = FatigueLevel.NORMAL
    attention_capacity: float = 1.0
    
    # Resource state
    token_usage_rate: float = 0.0
    time_usage_rate: float = 0.0
    delegation_usage_rate: float = 0.0
    
    # Reliability
    reliability_score: float = 0.5
    confidence_calibration: float = 0.5  # How well confidence predicts success
    
    # Trends
    success_trend: PerformanceTrend = PerformanceTrend.UNKNOWN
    reliability_trend: PerformanceTrend = PerformanceTrend.UNKNOWN
    
    # Adaptive parameters
    adaptive_parameters: Dict[str, AdaptiveParameter] = field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_capability_state(self, capability: str) -> CapabilityState:
        """Get state of a capability."""
        if capability in self.capability_metrics:
            return self.capability_metrics[capability].state
        return CapabilityState.UNKNOWN
    
    def get_capability_confidence(self, capability: str) -> float:
        """Get confidence for a capability."""
        if capability in self.capability_metrics:
            return self.capability_metrics[capability].confidence
        return 0.5
    
    def is_capable(self, capability: str, min_confidence: float = 0.5) -> bool:
        """Check if capable with sufficient confidence."""
        return self.get_capability_confidence(capability) >= min_confidence
    
    def get_fatigue_factor(self) -> float:
        """Get factor to apply to predictions based on fatigue."""
        factors = {
            FatigueLevel.FRESH: 1.0,
            FatigueLevel.NORMAL: 0.9,
            FatigueLevel.TIRED: 0.7,
            FatigueLevel.EXHAUSTED: 0.4,
            FatigueLevel.CRITICAL: 0.2,
        }
        return factors.get(self.fatigue_level, 0.5)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "performance": {
                "overall_success_rate": self.overall_success_rate,
                "recent_success_rate": self.recent_success_rate,
                "performance_trend": self.performance_trend.value,
            },
            "capabilities": {
                "strong": self.strong_capabilities,
                "weak": self.weak_capabilities,
                "states": {
                    k: v.state.value for k, v in self.capability_metrics.items()
                },
            },
            "cognitive": {
                "load": self.cognitive_load,
                "fatigue": self.fatigue_level.value,
                "attention_capacity": self.attention_capacity,
            },
            "reliability": {
                "score": self.reliability_score,
                "trend": self.reliability_trend.value,
            },
            "adaptive_parameters": {
                k: {
                    "current": v.current_value,
                    "baseline": v.baseline_value,
                    "trend": v.trend(),
                }
                for k, v in self.adaptive_parameters.items()
            },
        }


# ==========================================
# SELF MODEL
# ==========================================

class SelfModel:
    """
    THE CONTINUOUS SELF REPRESENTATION.
    
    This implements LAW 3: Agent must continuously model itself.
    
    The Self Model:
        - Continuously updates self-state
        - Tracks performance across capabilities
        - Calibrates confidence
        - Detects fatigue
        - Enables self-adaptation
    
    Key Distinction:
        Identity = who I am (static)
        Self Model = how I'm doing (dynamic)
    
    Usage:
        self_model = SelfModel(agent_id="phoenix-main")
        
        # Record outcomes
        self_model.record_outcome("delegation", success=True)
        self_model.record_outcome("planning", success=False)
        
        # Get current state
        state = self_model.get_state()
        
        # Check capability
        if state.is_capable("complex_planning"):
            proceed()
        
        # Get adaptive parameter
        risk_tolerance = self_model.get_parameter("risk_tolerance")
    
    Adaptation:
        Self-model drives self-regulation.
        When self-state changes, regulation adjusts.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str = "",
        role: str = "agent",
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name or agent_id
        self.role = role
        
        # Current self-state
        self._state = SelfState(
            agent_id=agent_id,
            agent_name=self.agent_name,
            role=role,
        )
        
        # Outcome history
        self._outcome_history: deque = deque(maxlen=100)
        
        # Capability tracking
        self._capability_metrics: Dict[str, CapabilityMetrics] = {}
        
        # Time-series for trend detection
        self._success_history: deque = deque(maxlen=50)
        self._reliability_history: deque = deque(maxlen=50)
        self._load_history: deque = deque(maxlen=20)
        
        # Adaptive parameters
        self._setup_adaptive_parameters()
        
        # Callbacks
        self._on_state_change: Optional[Callable[[SelfState], None]] = None
        
        # Statistics
        self._total_updates = 0
        
        logger.info(f"SelfModel initialized for {agent_id}")
    
    def _setup_adaptive_parameters(self) -> None:
        """Setup adaptive parameters for self-regulation."""
        self._state.adaptive_parameters = {
            "risk_tolerance": AdaptiveParameter(
                name="risk_tolerance",
                current_value=0.5,
                baseline_value=0.5,
                min_value=0.1,
                max_value=0.9,
            ),
            "delegation_willingness": AdaptiveParameter(
                name="delegation_willingness",
                current_value=0.5,
                baseline_value=0.5,
                min_value=0.0,
                max_value=1.0,
            ),
            "exploration_rate": AdaptiveParameter(
                name="exploration_rate",
                current_value=0.2,
                baseline_value=0.2,
                min_value=0.0,
                max_value=0.5,
            ),
            "confidence_threshold": AdaptiveParameter(
                name="confidence_threshold",
                current_value=0.5,
                baseline_value=0.5,
                min_value=0.3,
                max_value=0.9,
            ),
            "planning_depth": AdaptiveParameter(
                name="planning_depth",
                current_value=3.0,
                baseline_value=3.0,
                min_value=1.0,
                max_value=10.0,
            ),
        }
    
    # ==========================================
    # OUTCOME RECORDING
    # ==========================================
    
    def record_outcome(
        self,
        capability: str,
        success: bool,
        time_ms: float = 0.0,
        cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an outcome for a capability.
        
        This updates both the capability metrics and overall state.
        """
        # Record in capability metrics
        if capability not in self._capability_metrics:
            self._capability_metrics[capability] = CapabilityMetrics(
                capability_name=capability
            )
        
        self._capability_metrics[capability].record_outcome(success, time_ms, cost)
        
        # Record in overall history
        self._outcome_history.append({
            "capability": capability,
            "success": success,
            "time_ms": time_ms,
            "cost": cost,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
        })
        
        # Update success history
        self._success_history.append(success)
        
        # Trigger state update
        self._update_state()
        
        logger.debug(f"Recorded outcome: {capability} = {'SUCCESS' if success else 'FAILURE'}")
    
    def record_cognitive_load(self, load: float) -> None:
        """Record current cognitive load."""
        self._load_history.append(load)
        self._state.cognitive_load = load
        self._update_fatigue()
    
    def _update_fatigue(self) -> None:
        """Update fatigue level based on load history."""
        if not self._load_history:
            return
        
        avg_load = sum(self._load_history) / len(self._load_history)
        recent_load = list(self._load_history)[-5:]
        recent_avg = sum(recent_load) / len(recent_load) if recent_load else 0
        
        # Determine fatigue
        if recent_avg < 0.3:
            self._state.fatigue_level = FatigueLevel.FRESH
        elif recent_avg < 0.5:
            self._state.fatigue_level = FatigueLevel.NORMAL
        elif recent_avg < 0.7:
            self._state.fatigue_level = FatigueLevel.TIRED
        elif recent_avg < 0.85:
            self._state.fatigue_level = FatigueLevel.EXHAUSTED
        else:
            self._state.fatigue_level = FatigueLevel.CRITICAL
    
    # ==========================================
    # STATE UPDATE
    # ==========================================
    
    def _update_state(self) -> None:
        """Update the self-state based on recent history."""
        self._total_updates += 1
        old_state = copy.copy(self._state)
        
        # Update overall success rate
        if self._success_history:
            self._state.overall_success_rate = sum(1 for s in self._success_history if s) / len(self._success_history)
            
            # Recent (last 10)
            recent = list(self._success_history)[-10:]
            self._state.recent_success_rate = sum(recent) / len(recent)
        
        # Update performance trend
        self._state.performance_trend = self._calculate_trend(self._success_history)
        
        # Update capability metrics in state
        self._state.capability_metrics = self._capability_metrics.copy()
        
        # Update strong/weak capabilities
        self._state.strong_capabilities = [
            k for k, v in self._capability_metrics.items()
            if v.state == CapabilityState.STRONG
        ]
        self._state.weak_capabilities = [
            k for k, v in self._capability_metrics.items()
            if v.state == CapabilityState.UNRELIABLE
        ]
        
        # Update reliability
        self._update_reliability()
        
        # Update timestamp
        self._state.timestamp = datetime.utcnow()
        
        # Callback
        if self._on_state_change and self._state_changed(old_state, self._state):
            try:
                self._on_state_change(self._state)
            except Exception as e:
                logger.error(f"Self-state change callback error: {e}")
    
    def _update_reliability(self) -> None:
        """Update reliability score based on performance."""
        # Reliability = consistency + success rate
        if len(self._success_history) < 5:
            self._state.reliability_score = 0.5
            return
        
        # Calculate variance (consistency)
        outcomes = [1.0 if s else 0.0 for s in self._success_history]
        mean = sum(outcomes) / len(outcomes)
        variance = sum((o - mean) ** 2 for o in outcomes) / len(outcomes)
        consistency = 1.0 - min(1.0, variance * 2)
        
        # Reliability = consistency * success_rate
        self._state.reliability_score = consistency * self._state.overall_success_rate
        
        # Record for trend
        self._reliability_history.append(self._state.reliability_score)
        
        # Update trend
        self._state.reliability_trend = self._calculate_trend(self._reliability_history)
    
    def _calculate_trend(self, history: deque) -> PerformanceTrend:
        """Calculate trend from history."""
        if len(history) < 5:
            return PerformanceTrend.UNKNOWN
        
        values = list(history)
        n = len(values)
        
        first_half = values[:n//2]
        second_half = values[n//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        diff = second_avg - first_avg
        
        # Calculate variance for volatility
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        
        if variance > 0.15:
            return PerformanceTrend.VOLATILE
        elif diff > 0.1:
            return PerformanceTrend.IMPROVING
        elif diff < -0.1:
            return PerformanceTrend.DECLINING
        else:
            return PerformanceTrend.STABLE
    
    def _state_changed(self, old: SelfState, new: SelfState) -> bool:
        """Check if state meaningfully changed."""
        return (
            abs(old.overall_success_rate - new.overall_success_rate) > 0.05 or
            old.performance_trend != new.performance_trend or
            old.fatigue_level != new.fatigue_level or
            abs(old.reliability_score - new.reliability_score) > 0.05
        )
    
    # ==========================================
    # STATE ACCESS
    # ==========================================
    
    def get_state(self) -> SelfState:
        """Get current self-state."""
        return self._state
    
    def get_capability_metrics(self, capability: str) -> Optional[CapabilityMetrics]:
        """Get metrics for a specific capability."""
        return self._capability_metrics.get(capability)
    
    def get_capability_state(self, capability: str) -> CapabilityState:
        """Get state of a capability."""
        return self._state.get_capability_state(capability)
    
    def is_capable(self, capability: str, min_confidence: float = 0.5) -> bool:
        """Check if capable with sufficient confidence."""
        return self._state.is_capable(capability, min_confidence)
    
    # ==========================================
    # ADAPTIVE PARAMETERS
    # ==========================================
    
    def get_parameter(self, name: str) -> float:
        """Get current value of an adaptive parameter."""
        if name in self._state.adaptive_parameters:
            return self._state.adaptive_parameters[name].current_value
        return 0.5
    
    def adjust_parameter(
        self,
        name: str,
        delta: float,
        reason: str,
    ) -> float:
        """Adjust an adaptive parameter."""
        if name not in self._state.adaptive_parameters:
            logger.warning(f"Unknown adaptive parameter: {name}")
            return 0.5
        
        return self._state.adaptive_parameters[name].adjust(delta, reason)
    
    def calibrate_from_performance(self) -> Dict[str, float]:
        """
        Calibrate parameters based on performance.
        
        This is called by self-regulation to adjust behavior.
        """
        adjustments = {}
        
        state = self.get_state()
        
        # If doing well, can take more risks
        if state.overall_success_rate > 0.8 and state.performance_trend == PerformanceTrend.IMPROVING:
            adjustments["risk_tolerance"] = self.adjust_parameter(
                "risk_tolerance", 0.05, "Good performance, increasing risk tolerance"
            )
            adjustments["exploration_rate"] = self.adjust_parameter(
                "exploration_rate", 0.02, "Good performance, increasing exploration"
            )
        
        # If struggling, be more conservative
        elif state.overall_success_rate < 0.5 or state.performance_trend == PerformanceTrend.DECLINING:
            adjustments["risk_tolerance"] = self.adjust_parameter(
                "risk_tolerance", -0.05, "Poor performance, reducing risk tolerance"
            )
            adjustments["confidence_threshold"] = self.adjust_parameter(
                "confidence_threshold", 0.05, "Poor performance, raising threshold"
            )
        
        # If tired, simplify
        if state.fatigue_level in [FatigueLevel.TIRED, FatigueLevel.EXHAUSTED]:
            adjustments["planning_depth"] = self.adjust_parameter(
                "planning_depth", -1.0, "Fatigue, reducing planning depth"
            )
        
        # If delegation is working, do more
        if "delegation" in self._capability_metrics:
            del_rate = self._capability_metrics["delegation"].recent_success_rate
            if del_rate > 0.8:
                adjustments["delegation_willingness"] = self.adjust_parameter(
                    "delegation_willingness", 0.05, "Delegation successful"
                )
            elif del_rate < 0.5:
                adjustments["delegation_willingness"] = self.adjust_parameter(
                    "delegation_willingness", -0.05, "Delegation struggling"
                )
        
        return adjustments
    
    # ==========================================
    # PREDICTIONS
    # ==========================================
    
    def predict_success_probability(
        self,
        capability: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Predict probability of success for a capability.
        
        Uses self-model to calibrate prediction.
        """
        base_confidence = self.get_capability_confidence(capability)
        
        # Apply fatigue factor
        fatigue_factor = self._state.get_fatigue_factor()
        
        # Apply recent trend
        trend_factor = 1.0
        if self._state.performance_trend == PerformanceTrend.IMPROVING:
            trend_factor = 1.1
        elif self._state.performance_trend == PerformanceTrend.DECLINING:
            trend_factor = 0.9
        
        # Apply reliability
        reliability_factor = self._state.reliability_score
        
        # Combined prediction
        prediction = (
            base_confidence *
            fatigue_factor *
            trend_factor *
            (0.5 + 0.5 * reliability_factor)
        )
        
        return max(0.0, min(1.0, prediction))
    
    def get_capability_confidence(self, capability: str) -> float:
        """Get confidence for a capability."""
        if capability in self._capability_metrics:
            return self._capability_metrics[capability].confidence
        return 0.5
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_state_change(self, callback: Callable[[SelfState], None]) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get self-model statistics."""
        return {
            "agent_id": self.agent_id,
            "total_updates": self._total_updates,
            "outcome_history_size": len(self._outcome_history),
            "tracked_capabilities": len(self._capability_metrics),
            "current_state": self._state.to_dict(),
        }


# Import copy for state updates
import copy
