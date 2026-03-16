"""
Phoenix Agent - Safety Engine
=============================

Safety Layer - The "conscience" of Phoenix.

Without this layer, Phoenix is UNSAFE for production.
With this layer, Phoenix has guardrails.

Architecture Decision:
    - Agents can make mistakes
    - Agents can get stuck in loops
    - Agents can exceed budgets
    - SafetyEngine prevents ALL of these

Key Responsibilities:
    1. Validate actions before execution
    2. Check permissions
    3. Detect and prevent loops
    4. Prevent runaway delegation
    5. Enforce rate limits
    6. Control costs

Production Requirement:
    This layer is MANDATORY for production deployment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4


# ============================================================================
# ENUMERATIONS
# ============================================================================


class SafetyLevel(Enum):
    """Safety enforcement level."""
    PERMISSIVE = "permissive"    # Log warnings, don't block
    MODERATE = "moderate"        # Block critical violations
    STRICT = "strict"            # Block all violations
    PARANOID = "paranoid"        # Block + audit everything


class ViolationType(Enum):
    """Types of safety violations."""
    # Permission violations
    UNAUTHORIZED_ACTION = "unauthorized_action"
    PERMISSION_DENIED = "permission_denied"
    
    # Resource violations
    COST_EXCEEDED = "cost_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    ITERATION_LIMIT_EXCEEDED = "iteration_limit_exceeded"
    
    # Behavior violations
    LOOP_DETECTED = "loop_detected"
    INFINITE_DELEGATION = "infinite_delegation"
    RECURSION_DEPTH = "recursion_depth"
    RUNAWAY_BEHAVIOR = "runaway_behavior"
    
    # Content violations
    INVALID_INPUT = "invalid_input"
    INVALID_OUTPUT = "invalid_output"
    MALFORMED_DATA = "malformed_data"
    
    # System violations
    SYSTEM_OVERLOAD = "system_overload"
    DEGRADED_STATE = "degraded_state"


class ViolationSeverity(Enum):
    """Severity of a violation."""
    INFO = "info"           # Just logging
    WARNING = "warning"     # Should be reviewed
    ERROR = "error"         # Action blocked
    CRITICAL = "critical"   # System intervention needed


# ============================================================================
# SAFETY VIOLATION
# ============================================================================


@dataclass
class SafetyViolation:
    """
    A safety violation record.
    
    Tracks what happened, when, and what was done about it.
    """
    violation_id: str = field(default_factory=lambda: str(uuid4()))
    violation_type: ViolationType = ViolationType.UNAUTHORIZED_ACTION
    severity: ViolationSeverity = ViolationSeverity.WARNING
    
    # Context
    agent_id: str = ""
    session_id: str = ""
    task_id: str = ""
    action: str = ""
    
    # Details
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Resolution
    action_taken: str = ""
    blocked: bool = False
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize violation."""
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "agent_id": self.agent_id,
            "action": self.action,
            "message": self.message,
            "blocked": self.blocked,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# SAFETY CHECK RESULT
# ============================================================================


@dataclass
class SafetyCheckResult:
    """
    Result of a safety check.
    
    Tells whether an action is allowed and why/why not.
    """
    check_id: str = field(default_factory=lambda: str(uuid4()))
    allowed: bool = True
    violations: List[SafetyViolation] = field(default_factory=list)
    
    # Warnings (allowed but flagged)
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Context
    check_type: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def has_violations(self) -> bool:
        """Check if there are any violations."""
        return len(self.violations) > 0
    
    @property
    def has_critical(self) -> bool:
        """Check if there are critical violations."""
        return any(
            v.severity == ViolationSeverity.CRITICAL
            for v in self.violations
        )
    
    def add_violation(
        self,
        violation_type: ViolationType,
        message: str,
        severity: ViolationSeverity = ViolationSeverity.WARNING,
        **kwargs
    ) -> SafetyViolation:
        """Add a violation."""
        violation = SafetyViolation(
            violation_type=violation_type,
            severity=severity,
            message=message,
            **kwargs
        )
        self.violations.append(violation)
        
        # Update allowed status based on severity and policy
        if severity in (ViolationSeverity.ERROR, ViolationSeverity.CRITICAL):
            self.allowed = False
        
        return violation
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize result."""
        return {
            "check_id": self.check_id,
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


# ============================================================================
# GUARDRAILS
# ============================================================================


@dataclass
class CostLimits:
    """Cost limits for safety."""
    max_cost_per_action: float = 1.0
    max_cost_per_task: float = 10.0
    max_cost_per_session: float = 100.0
    max_cost_per_day: float = 1000.0
    
    # Warning thresholds (percentage of limit)
    warning_threshold: float = 0.8  # Warn at 80% of limit


@dataclass
class RateLimits:
    """Rate limits for safety."""
    max_actions_per_second: float = 10.0
    max_actions_per_minute: int = 300
    max_delegations_per_minute: int = 30
    max_llm_calls_per_minute: int = 60
    
    # Burst allowance
    burst_size: int = 20
    burst_window_seconds: float = 1.0


@dataclass
class LoopLimits:
    """Limits to prevent loops."""
    max_iterations: int = 100
    max_same_action_retries: int = 3
    max_delegation_depth: int = 5
    max_recursion_depth: int = 10
    
    # Loop detection window
    detection_window_size: int = 20  # Check last N actions for loops
    
    # Thresholds
    similarity_threshold: float = 0.9  # Actions this similar = potential loop


@dataclass
class TimeLimits:
    """Time limits for safety."""
    max_action_time_seconds: float = 60.0
    max_task_time_seconds: float = 600.0
    max_session_time_seconds: float = 3600.0
    
    # Grace periods
    shutdown_grace_seconds: float = 30.0


@dataclass
class Guardrails:
    """
    Complete guardrails configuration.
    
    Defines ALL safety constraints for Phoenix.
    """
    cost: CostLimits = field(default_factory=CostLimits)
    rate: RateLimits = field(default_factory=RateLimits)
    loop: LoopLimits = field(default_factory=LoopLimits)
    time: TimeLimits = field(default_factory=TimeLimits)
    
    # Behavior constraints
    allowed_actions: Set[str] = field(default_factory=lambda: {"*"})
    blocked_actions: Set[str] = field(default_factory=set)
    restricted_params: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Permission settings
    require_approval_for: Set[str] = field(default_factory=set)
    approval_timeout_seconds: float = 300.0
    
    def is_action_allowed(self, action: str) -> Tuple[bool, Optional[str]]:
        """Check if an action is in the allowed list."""
        if "*" in self.allowed_actions:
            # Wildcard allowed, check block list
            if action in self.blocked_actions:
                return False, f"Action '{action}' is blocked"
            return True, None
        
        if action in self.blocked_actions:
            return False, f"Action '{action}' is blocked"
        
        if action not in self.allowed_actions:
            return False, f"Action '{action}' not in allowed list"
        
        return True, None
    
    def requires_approval(self, action: str) -> bool:
        """Check if an action requires approval."""
        return action in self.require_approval_for
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize guardrails."""
        return {
            "cost": {
                "max_cost_per_action": self.cost.max_cost_per_action,
                "max_cost_per_session": self.cost.max_cost_per_session,
            },
            "rate": {
                "max_actions_per_minute": self.rate.max_actions_per_minute,
                "max_delegations_per_minute": self.rate.max_delegations_per_minute,
            },
            "loop": {
                "max_iterations": self.loop.max_iterations,
                "max_delegation_depth": self.loop.max_delegation_depth,
            },
            "time": {
                "max_session_time_seconds": self.time.max_session_time_seconds,
            },
        }


# ============================================================================
# SAFETY CONFIG
# ============================================================================


@dataclass
class SafetyConfig:
    """Configuration for SafetyEngine."""
    safety_level: SafetyLevel = SafetyLevel.MODERATE
    
    # Guardrails
    guardrails: Guardrails = field(default_factory=Guardrails)
    
    # History
    max_violation_history: int = 1000
    max_action_history: int = 500
    
    # Auto-recovery
    auto_recover: bool = True
    recovery_cooldown_seconds: float = 60.0
    
    # Audit
    audit_all_actions: bool = False
    audit_critical_only: bool = True
    
    # Notification
    notify_on_violation: bool = True
    notify_on_critical: bool = True
    
    # Emergency stop
    emergency_stop_enabled: bool = True
    emergency_stop_threshold: int = 10  # Stop after N critical violations


# ============================================================================
# SAFETY ENGINE
# ============================================================================


class SafetyEngine:
    """
    Safety Engine - The "conscience" of Phoenix.
    
    This is the SAFETY layer. Without it, Phoenix is UNSAFE for production.
    
    Responsibilities:
        1. Validate actions before execution
        2. Check permissions
        3. Detect and prevent loops
        4. Prevent runaway delegation
        5. Enforce rate limits
        6. Control costs
        7. Emergency stop capability
    
    Architecture Decision:
        - Safety checks are NOT optional in production
        - Every action passes through safety checks
        - Violations are logged and can trigger alerts
        - System can auto-recover from some violations
    
    Usage:
        safety = SafetyEngine(config)
        
        # Check before action
        result = safety.check_action("delegate", context)
        if not result.allowed:
            # Handle violation
            pass
        
        # Record action for loop detection
        safety.record_action("search", params)
    """
    
    def __init__(self, config: SafetyConfig = None):
        self.config = config or SafetyConfig()
        self.guardrails = self.config.guardrails
        
        # Tracking
        self._action_history: List[Dict[str, Any]] = []
        self._violation_history: List[SafetyViolation] = []
        
        # Rate limiting state
        self._rate_counters: Dict[str, List[float]] = {}
        
        # Cost tracking
        self._cost_tracker: Dict[str, float] = {
            "session": 0.0,
            "task": 0.0,
            "day": 0.0,
        }
        
        # Session timing
        self._session_start: Optional[datetime] = None
        self._task_start: Optional[datetime] = None
        
        # Loop detection
        self._action_signatures: List[str] = []
        self._delegation_depth: int = 0
        
        # Emergency state
        self._emergency_stop: bool = False
        self._critical_count: int = 0
        
        # Recovery state
        self._last_violation_time: Optional[datetime] = None
        self._in_cooldown: bool = False
    
    # ========================================================================
    # Main Check Methods
    # ========================================================================
    
    def check_action(
        self,
        action: str,
        context: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> SafetyCheckResult:
        """
        Check if an action is allowed.
        
        This is the MAIN entry point for safety checks.
        
        Args:
            action: Action to check
            context: Execution context (agent_id, session_id, etc.)
            params: Action parameters
        
        Returns:
            SafetyCheckResult with allowed status and any violations
        """
        context = context or {}
        params = params or {}
        
        result = SafetyCheckResult(check_type="action")
        
        # Emergency stop check
        if self._emergency_stop:
            result.add_violation(
                ViolationType.SYSTEM_OVERLOAD,
                "Emergency stop activated - all actions blocked",
                ViolationSeverity.CRITICAL,
                action=action
            )
            return result
        
        # Run all checks
        self._check_permissions(action, context, result)
        self._check_rate_limits(action, context, result)
        self._check_cost_limits(action, context, result)
        self._check_time_limits(action, context, result)
        self._check_loop_detection(action, params, result)
        self._check_delegation_depth(action, context, result)
        
        # Log if auditing
        if self.config.audit_all_actions or (self.config.audit_critical_only and result.has_critical):
            self._audit_action(action, context, result)
        
        # Record violations
        for violation in result.violations:
            self._record_violation(violation)
        
        # Check for emergency stop
        if result.has_critical:
            self._critical_count += 1
            if (self.config.emergency_stop_enabled and 
                self._critical_count >= self.config.emergency_stop_threshold):
                self._emergency_stop = True
        
        return result
    
    def check_delegation(
        self,
        target_agent: str,
        task: str,
        context: Dict[str, Any] = None
    ) -> SafetyCheckResult:
        """
        Check if a delegation is allowed.
        
        Special checks for delegation to prevent runaway behavior.
        """
        result = SafetyCheckResult(check_type="delegation")
        context = context or {}
        
        # Check delegation depth
        if self._delegation_depth >= self.guardrails.loop.max_delegation_depth:
            result.add_violation(
                ViolationType.INFINITE_DELEGATION,
                f"Max delegation depth ({self.guardrails.loop.max_delegation_depth}) exceeded",
                ViolationSeverity.ERROR,
                action="delegate",
                details={"depth": self._delegation_depth, "target": target_agent}
            )
        
        # Check delegation rate
        key = "delegations"
        if not self._check_rate(key, self.guardrails.rate.max_delegations_per_minute):
            result.add_violation(
                ViolationType.RATE_LIMIT_EXCEEDED,
                "Delegation rate limit exceeded",
                ViolationSeverity.ERROR,
                action="delegate"
            )
        
        return result
    
    def check_cost(
        self,
        estimated_cost: float,
        context: Dict[str, Any] = None
    ) -> SafetyCheckResult:
        """
        Check if a cost is within limits.
        
        Use before expensive operations.
        """
        result = SafetyCheckResult(check_type="cost")
        context = context or {}
        
        # Check against limits
        if estimated_cost > self.guardrails.cost.max_cost_per_action:
            result.add_violation(
                ViolationType.COST_EXCEEDED,
                f"Cost {estimated_cost} exceeds per-action limit {self.guardrails.cost.max_cost_per_action}",
                ViolationSeverity.ERROR,
                details={"estimated": estimated_cost, "limit": self.guardrails.cost.max_cost_per_action}
            )
        
        # Check against session budget
        projected_session = self._cost_tracker["session"] + estimated_cost
        if projected_session > self.guardrails.cost.max_cost_per_session:
            result.add_violation(
                ViolationType.COST_EXCEEDED,
                f"Projected session cost {projected_session} exceeds limit",
                ViolationSeverity.WARNING,
                details={"current": self._cost_tracker["session"], "estimated": estimated_cost}
            )
        
        # Add warning if approaching limit
        if projected_session > self.guardrails.cost.max_cost_per_session * self.guardrails.cost.warning_threshold:
            result.warnings.append(
                f"Approaching session cost limit ({projected_session}/{self.guardrails.cost.max_cost_per_session})"
            )
        
        return result
    
    # ========================================================================
    # Individual Checks
    # ========================================================================
    
    def _check_permissions(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Check if action is permitted."""
        allowed, reason = self.guardrails.is_action_allowed(action)
        
        if not allowed:
            result.add_violation(
                ViolationType.PERMISSION_DENIED,
                reason or "Permission denied",
                ViolationSeverity.ERROR,
                action=action,
                agent_id=context.get("agent_id", "")
            )
        
        # Check if approval required
        if self.guardrails.requires_approval(action):
            result.warnings.append(f"Action '{action}' requires approval")
    
    def _check_rate_limits(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Check rate limits."""
        key = f"actions_{context.get('agent_id', 'default')}"
        
        if not self._check_rate(key, self.guardrails.rate.max_actions_per_minute):
            result.add_violation(
                ViolationType.RATE_LIMIT_EXCEEDED,
                "Action rate limit exceeded",
                ViolationSeverity.WARNING
                if self.config.safety_level == SafetyLevel.PERMISSIVE
                else ViolationSeverity.ERROR,
                action=action
            )
    
    def _check_cost_limits(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Check cost limits."""
        if self._cost_tracker["session"] > self.guardrails.cost.max_cost_per_session:
            result.add_violation(
                ViolationType.COST_EXCEEDED,
                f"Session cost limit exceeded: {self._cost_tracker['session']}",
                ViolationSeverity.ERROR,
                action=action
            )
    
    def _check_time_limits(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Check time limits."""
        if self._session_start:
            elapsed = (datetime.utcnow() - self._session_start).total_seconds()
            
            if elapsed > self.guardrails.time.max_session_time_seconds:
                result.add_violation(
                    ViolationType.TIME_LIMIT_EXCEEDED,
                    f"Session time limit exceeded: {elapsed}s",
                    ViolationSeverity.ERROR,
                    action=action
                )
            
            # Warning at 80%
            if elapsed > self.guardrails.time.max_session_time_seconds * 0.8:
                result.warnings.append(
                    f"Session approaching time limit ({elapsed}s / {self.guardrails.time.max_session_time_seconds}s)"
                )
    
    def _check_loop_detection(
        self,
        action: str,
        params: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Detect potential loops."""
        # Create action signature
        signature = self._create_action_signature(action, params)
        
        # Check for repeated actions
        recent = self._action_signatures[-self.guardrails.loop.detection_window_size:]
        
        if recent:
            # Count similar actions
            similar_count = sum(
                1 for s in recent
                if self._similarity(s, signature) > self.guardrails.loop.similarity_threshold
            )
            
            if similar_count >= self.guardrails.loop.max_same_action_retries:
                result.add_violation(
                    ViolationType.LOOP_DETECTED,
                    f"Potential loop detected: action repeated {similar_count} times",
                    ViolationSeverity.ERROR,
                    action=action,
                    details={"similar_count": similar_count, "signature": signature}
                )
    
    def _check_delegation_depth(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Check delegation depth."""
        if action == "delegate" and self._delegation_depth > 0:
            if self._delegation_depth >= self.guardrails.loop.max_delegation_depth:
                result.add_violation(
                    ViolationType.INFINITE_DELEGATION,
                    f"Delegation depth {self._delegation_depth} exceeds maximum",
                    ViolationSeverity.ERROR,
                    action=action
                )
    
    # ========================================================================
    # Rate Limiting Helpers
    # ========================================================================
    
    def _check_rate(self, key: str, limit: int) -> bool:
        """Check if rate limit is OK."""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        if key not in self._rate_counters:
            self._rate_counters[key] = []
        
        # Clean old entries
        self._rate_counters[key] = [
            t for t in self._rate_counters[key] if t > window_start
        ]
        
        # Check limit
        return len(self._rate_counters[key]) < limit
    
    def _record_rate(self, key: str) -> None:
        """Record a rate event."""
        now = time.time()
        if key not in self._rate_counters:
            self._rate_counters[key] = []
        self._rate_counters[key].append(now)
    
    # ========================================================================
    # Loop Detection Helpers
    # ========================================================================
    
    def _create_action_signature(self, action: str, params: Dict[str, Any]) -> str:
        """Create a signature for action comparison."""
        # Simple signature: action + sorted param keys
        param_keys = sorted(params.keys()) if params else []
        return f"{action}:{':'.join(param_keys)}"
    
    def _similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between two signatures."""
        if sig1 == sig2:
            return 1.0
        
        # Simple Jaccard similarity on parts
        parts1 = set(sig1.split(":"))
        parts2 = set(sig2.split(":"))
        
        if not parts1 or not parts2:
            return 0.0
        
        intersection = parts1 & parts2
        union = parts1 | parts2
        
        return len(intersection) / len(union)
    
    # ========================================================================
    # Recording & Tracking
    # ========================================================================
    
    def record_action(
        self,
        action: str,
        params: Dict[str, Any] = None,
        result: Any = None,
        cost: float = 0.0
    ) -> None:
        """
        Record an action for tracking.
        
        Call AFTER an action is executed.
        """
        # Record for loop detection
        signature = self._create_action_signature(action, params or {})
        self._action_signatures.append(signature)
        
        # Trim history
        if len(self._action_signatures) > self.config.max_action_history:
            self._action_signatures = self._action_signatures[-self.config.max_action_history:]
        
        # Record for rate limiting
        key = "actions"
        self._record_rate(key)
        
        # Track cost
        self._cost_tracker["session"] += cost
        self._cost_tracker["day"] += cost
        
        # Record action details
        self._action_history.append({
            "action": action,
            "params": params,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Trim history
        if len(self._action_history) > self.config.max_action_history:
            self._action_history = self._action_history[-self.config.max_action_history:]
    
    def record_cost(self, cost: float, category: str = "session") -> None:
        """Record a cost expenditure."""
        if category in self._cost_tracker:
            self._cost_tracker[category] += cost
    
    def enter_delegation(self) -> int:
        """Enter a delegation context, return new depth."""
        self._delegation_depth += 1
        return self._delegation_depth
    
    def exit_delegation(self) -> int:
        """Exit a delegation context, return new depth."""
        self._delegation_depth = max(0, self._delegation_depth - 1)
        return self._delegation_depth
    
    def _record_violation(self, violation: SafetyViolation) -> None:
        """Record a violation."""
        self._violation_history.append(violation)
        
        # Trim history
        if len(self._violation_history) > self.config.max_violation_history:
            self._violation_history = self._violation_history[-self.config.max_violation_history:]
        
        self._last_violation_time = datetime.utcnow()
    
    def _audit_action(
        self,
        action: str,
        context: Dict[str, Any],
        result: SafetyCheckResult
    ) -> None:
        """Audit an action (for compliance/debugging)."""
        # In production, would send to audit system
        pass
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def start_session(self, session_id: str = None) -> None:
        """Start a new session."""
        self._session_start = datetime.utcnow()
        self._cost_tracker["session"] = 0.0
        self._delegation_depth = 0
        self._action_signatures = []
        self._critical_count = 0
        self._emergency_stop = False
    
    def start_task(self, task_id: str = None) -> None:
        """Start a new task."""
        self._task_start = datetime.utcnow()
        self._cost_tracker["task"] = 0.0
    
    def end_session(self) -> Dict[str, Any]:
        """End session and return summary."""
        duration = 0.0
        if self._session_start:
            duration = (datetime.utcnow() - self._session_start).total_seconds()
        
        return {
            "duration_seconds": duration,
            "total_cost": self._cost_tracker["session"],
            "total_actions": len(self._action_history),
            "total_violations": len(self._violation_history),
            "max_delegation_depth": self._delegation_depth,
        }
    
    # ========================================================================
    # Emergency Controls
    # ========================================================================
    
    def emergency_stop(self, reason: str = "Manual activation") -> None:
        """Activate emergency stop."""
        self._emergency_stop = True
        self._record_violation(SafetyViolation(
            violation_type=ViolationType.SYSTEM_OVERLOAD,
            severity=ViolationSeverity.CRITICAL,
            message=f"Emergency stop activated: {reason}",
        ))
    
    def clear_emergency(self) -> None:
        """Clear emergency stop."""
        self._emergency_stop = False
        self._critical_count = 0
    
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop
    
    # ========================================================================
    # Recovery
    # ========================================================================
    
    def can_recover(self) -> bool:
        """Check if system can attempt recovery."""
        if not self.config.auto_recover:
            return False
        
        if self._in_cooldown:
            return False
        
        if self._emergency_stop:
            return False
        
        return True
    
    def enter_cooldown(self) -> None:
        """Enter cooldown period after violations."""
        self._in_cooldown = True
        # Cooldown would be cleared after timeout
    
    # ========================================================================
    # Status & Info
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current safety status."""
        return {
            "emergency_stop": self._emergency_stop,
            "critical_count": self._critical_count,
            "delegation_depth": self._delegation_depth,
            "session_cost": self._cost_tracker["session"],
            "action_count": len(self._action_history),
            "violation_count": len(self._violation_history),
            "safety_level": self.config.safety_level.value,
        }
    
    def get_violations(self, limit: int = 100) -> List[SafetyViolation]:
        """Get recent violations."""
        return self._violation_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get safety statistics."""
        total_violations = len(self._violation_history)
        
        if total_violations == 0:
            return {
                "total_violations": 0,
                "blocked_actions": 0,
            }
        
        by_type: Dict[ViolationType, int] = {}
        by_severity: Dict[ViolationSeverity, int] = {}
        blocked = 0
        
        for v in self._violation_history:
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
            if v.blocked:
                blocked += 1
        
        return {
            "total_violations": total_violations,
            "blocked_actions": blocked,
            "by_type": {t.value: c for t, c in by_type.items()},
            "by_severity": {s.value: c for s, c in by_severity.items()},
            "session_cost": self._cost_tracker["session"],
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine state."""
        return {
            "config": {
                "safety_level": self.config.safety_level.value,
                "guardrails": self.guardrails.to_dict(),
            },
            "status": self.get_status(),
            "statistics": self.get_statistics(),
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_safety_engine(
    safety_level: SafetyLevel = SafetyLevel.MODERATE,
    guardrails: Guardrails = None
) -> SafetyEngine:
    """Create a SafetyEngine with specified settings."""
    config = SafetyConfig(
        safety_level=safety_level,
        guardrails=guardrails or Guardrails()
    )
    return SafetyEngine(config=config)


def create_permissive_safety() -> SafetyEngine:
    """Create a permissive safety engine for development."""
    return create_safety_engine(SafetyLevel.PERMISSIVE)


def create_strict_safety() -> SafetyEngine:
    """Create a strict safety engine for production."""
    guardrails = Guardrails(
        cost=CostLimits(
            max_cost_per_action=0.5,
            max_cost_per_session=50.0
        ),
        loop=LoopLimits(
            max_iterations=50,
            max_delegation_depth=3
        )
    )
    return create_safety_engine(SafetyLevel.STRICT, guardrails)


def create_paranoid_safety() -> SafetyEngine:
    """Create a paranoid safety engine for sensitive environments."""
    guardrails = Guardrails(
        cost=CostLimits(
            max_cost_per_action=0.1,
            max_cost_per_session=10.0
        ),
        loop=LoopLimits(
            max_iterations=20,
            max_delegation_depth=2
        )
    )
    return create_safety_engine(SafetyLevel.PARANOID, guardrails)
