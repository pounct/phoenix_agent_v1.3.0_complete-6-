"""
Phoenix Agent - Adaptation Engine
=================================

Moteur d'auto-adaptation du système.

La différence entre un agent qui apprend et un agent qui s'adapte:

    LearningLoop = APPRENDRE
        - "Cette stratégie a 80% de succès"
        - Capture de patterns
        - Suggestions pour l'utilisateur

    AdaptationEngine = S'ADAPTER
        - "Je dois changer mon seuil de délégation"
        - Modification automatique du comportement
        - Auto-optimisation du système

Sans AdaptationEngine:
    - Phoenix apprend mais ne change pas
    - Les seuils restent statiques
    - Pas d'optimisation automatique
    - Dépend de l'intervention humaine

Avec AdaptationEngine:
    - Auto-ajustement des seuils cognitifs
    - Optimisation des stratégies de délégation
    - Adaptation des politiques de récupération
    - Évolution continue du système

C'est LA couche qui transforme Phoenix en **système auto-évolutif**.

ADAPTATIONS:
    - Cognitive thresholds (delegation, memory, confidence)
    - Delegation strategies
    - Recovery policies
    - Memory policies
    - Resource allocation
    - Agent selection preferences

PRINCIPES:
    - Adaptation graduelle (pas de changements brusques)
    - Stabilité (éviter oscillations)
    - Réversibilité (possibilité de rollback)
    - Traçabilité (audit des adaptations)

Version: 1.0.0 (Self-Evolution Layer)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import json
import copy


logger = logging.getLogger("phoenix.adaptation")


# ==========================================
# ADAPTATION TYPES
# ==========================================

class AdaptationType(str, Enum):
    """Types d'adaptation."""
    # Cognitive thresholds
    DELEGATION_THRESHOLD = "delegation_threshold"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    MEMORY_THRESHOLD = "memory_threshold"
    ITERATION_THRESHOLD = "iteration_threshold"
    
    # Strategies
    DELEGATION_STRATEGY = "delegation_strategy"
    RECOVERY_STRATEGY = "recovery_strategy"
    MEMORY_STRATEGY = "memory_strategy"
    PLANNING_STRATEGY = "planning_strategy"
    
    # Policies
    RETRY_POLICY = "retry_policy"
    TIMEOUT_POLICY = "timeout_policy"
    PRIORITY_POLICY = "priority_policy"
    
    # Resource allocation
    RESOURCE_ALLOCATION = "resource_allocation"
    AGENT_SELECTION = "agent_selection"
    PARALLELISM_LEVEL = "parallelism_level"


class AdaptationTrigger(str, Enum):
    """Déclencheurs d'adaptation."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_FAILURE_RATE = "high_failure_rate"
    RESOURCE_PRESSURE = "resource_pressure"
    COGNITIVE_OVERLOAD = "cognitive_overload"
    EFFICIENCY_GAIN_POSSIBLE = "efficiency_gain"
    SUCCESS_PATTERN_DETECTED = "success_pattern"
    ANTI_PATTERN_DETECTED = "anti_pattern"
    MANUAL_REQUEST = "manual"
    SCHEDULED = "scheduled"


class AdaptationStatus(str, Enum):
    """Status d'une adaptation."""
    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    REJECTED = "rejected"  # Rejected by safety check


# ==========================================
# ADAPTATION RECORD
# ==========================================

@dataclass
class AdaptationRecord:
    """Enregistrement d'une adaptation."""
    adaptation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # What
    adaptation_type: AdaptationType = AdaptationType.DELEGATION_THRESHOLD
    trigger: AdaptationTrigger = AdaptationTrigger.MANUAL_REQUEST
    
    # Change
    parameter: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    
    # Impact
    impact_score: float = 0.0  # -1.0 to 1.0 (negative = bad, positive = good)
    confidence: float = 0.5
    
    # Status
    status: AdaptationStatus = AdaptationStatus.PENDING
    
    # Timestamps
    proposed_at: datetime = field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after: Dict[str, float] = field(default_factory=dict)
    
    # Rollback
    can_rollback: bool = True
    rollback_reason: str = ""
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "adaptation_id": self.adaptation_id,
            "type": self.adaptation_type.value,
            "trigger": self.trigger.value,
            "parameter": self.parameter,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "reason": self.reason,
            "impact_score": self.impact_score,
            "status": self.status.value,
            "can_rollback": self.can_rollback,
        }


# ==========================================
# ADAPTATION RULE
# ==========================================

@dataclass
class AdaptationRule:
    """Règle d'adaptation."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # Condition
    trigger: AdaptationTrigger = AdaptationTrigger.PERFORMANCE_DEGRADATION
    condition: Callable[[Dict[str, Any]], bool] = lambda ctx: False
    
    # Action
    adaptation_type: AdaptationType = AdaptationType.DELEGATION_THRESHOLD
    parameter: str = ""
    adjustment: Callable[[Any, Dict[str, Any]], Any] = lambda v, ctx: v
    
    # Constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_adjustment: float = 0.2  # Max 20% change
    
    # Priority
    priority: int = 5
    cooldown_minutes: int = 30
    
    # Safety
    requires_confirmation: bool = False
    can_rollback: bool = True
    
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Vérifie si la règle doit se déclencher."""
        # Check cooldown
        if self.last_triggered:
            elapsed = (datetime.utcnow() - self.last_triggered).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                return False
        
        return self.condition(context)
    
    def apply(self, current_value: Any, context: Dict[str, Any]) -> Any:
        """Applique l'ajustement."""
        new_value = self.adjustment(current_value, context)
        
        # Apply constraints
        if self.min_value is not None and isinstance(new_value, (int, float)):
            new_value = max(self.min_value, new_value)
        
        if self.max_value is not None and isinstance(new_value, (int, float)):
            new_value = min(self.max_value, new_value)
        
        return new_value


# ==========================================
# ADAPTATION ENGINE CONFIG
# ==========================================

@dataclass
class AdaptationConfig:
    """Configuration de l'AdaptationEngine."""
    # General
    enabled: bool = True
    auto_apply: bool = True
    
    # Constraints
    max_adaptations_per_hour: int = 10
    max_adjustment_per_adaptation: float = 0.2  # 20% max change
    min_stability_period_minutes: int = 5
    
    # Safety
    require_confirmation_for_critical: bool = True
    critical_adaptation_types: List[AdaptationType] = field(
        default_factory=lambda: [
            AdaptationType.DELEGATION_STRATEGY,
            AdaptationType.RECOVERY_STRATEGY,
        ]
    )
    
    # Impact evaluation
    impact_evaluation_period_s: float = 300.0  # 5 minutes
    auto_rollback_on_negative_impact: bool = True
    negative_impact_threshold: float = -0.3
    
    # History
    max_history_size: int = 1000
    rollback_window_hours: int = 24


# ==========================================
# ADAPTATION ENGINE
# ==========================================

class AdaptationEngine:
    """
    Moteur d'auto-adaptation du système Phoenix.
    
    C'est LE composant qui permet à Phoenix de changer son propre comportement.
    
    Responsabilités:
        1. Détecter les opportunités d'adaptation
        2. Proposer et appliquer les adaptations
        3. Évaluer l'impact des adaptations
        4. Rollback si nécessaire
        5. Maintenir la stabilité du système
    
    Architecture:
        LearningLoop
            │
            └── AdaptationEngine
                    │
                    ├── detect_adaptation_needs()
                    ├── propose_adaptation()
                    ├── apply_adaptation()
                    ├── evaluate_impact()
                    └── rollback()
    
    Example:
        adaptation = AdaptationEngine()
        
        # Connect to components
        adaptation.register_parameter(
            "delegation_threshold",
            get_value=lambda: 0.8,
            set_value=lambda v: set_threshold(v),
        )
        
        # Detect and apply
        adaptations = adaptation.detect_adaptation_needs(context)
        
        for adapt in adaptations:
            if adaptation.should_apply(adapt):
                adaptation.apply_adaptation(adapt)
        
        # Later: evaluate impact
        impact = adaptation.evaluate_impact(adapt.adaptation_id)
        
        if impact < -0.3:
            adaptation.rollback(adapt.adaptation_id)
    """
    
    def __init__(
        self,
        config: Optional[AdaptationConfig] = None,
    ):
        self.config = config or AdaptationConfig()
        
        # Parameters registry
        self._parameters: Dict[str, Dict[str, Any]] = {}
        
        # Adaptation rules
        self._rules: Dict[str, AdaptationRule] = {}
        self._setup_default_rules()
        
        # History
        self._history: List[AdaptationRecord] = []
        self._recent_adaptations: List[str] = []  # IDs
        
        # Current state
        self._adaptations_this_hour = 0
        self._hour_reset: datetime = datetime.utcnow()
        
        # Callbacks
        self._on_adaptation_proposed: List[Callable[[AdaptationRecord], None]] = []
        self._on_adaptation_applied: List[Callable[[AdaptationRecord], None]] = []
        self._on_adaptation_rolled_back: List[Callable[[AdaptationRecord], None]] = []
        
        # Stats
        self._total_proposed = 0
        self._total_applied = 0
        self._total_rolled_back = 0
        
        logger.info("AdaptationEngine initialized")
    
    # ==========================================
    # PARAMETER REGISTRY
    # ==========================================
    
    def register_parameter(
        self,
        name: str,
        get_value: Callable[[], Any],
        set_value: Callable[[Any], None],
        parameter_type: str = "float",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> None:
        """Enregistre un paramètre adaptable."""
        self._parameters[name] = {
            "get_value": get_value,
            "set_value": set_value,
            "type": parameter_type,
            "min_value": min_value,
            "max_value": max_value,
        }
        
        logger.info(f"Registered adaptable parameter: {name}")
    
    def get_parameter(self, name: str) -> Optional[Any]:
        """Récupère la valeur d'un paramètre."""
        if name not in self._parameters:
            return None
        
        return self._parameters[name]["get_value"]()
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """Définit la valeur d'un paramètre."""
        if name not in self._parameters:
            return False
        
        # Validate
        param = self._parameters[name]
        
        if param["min_value"] is not None and value < param["min_value"]:
            return False
        
        if param["max_value"] is not None and value > param["max_value"]:
            return False
        
        param["set_value"](value)
        return True
    
    # ==========================================
    # DEFAULT RULES
    # ==========================================
    
    def _setup_default_rules(self) -> None:
        """Configure les règles d'adaptation par défaut."""
        
        # Rule 1: Increase delegation threshold on high failure rate
        self.add_rule(AdaptationRule(
            rule_id="increase_delegation_on_failure",
            name="Increase Delegation Threshold",
            description="Increase delegation threshold when failure rate is high",
            trigger=AdaptationTrigger.HIGH_FAILURE_RATE,
            condition=lambda ctx: ctx.get("failure_rate", 0) > 0.3,
            adaptation_type=AdaptationType.DELEGATION_THRESHOLD,
            parameter="delegation_threshold",
            adjustment=lambda v, ctx: min(0.9, v + 0.05),
            priority=8,
            cooldown_minutes=30,
        ))
        
        # Rule 2: Decrease delegation threshold on high success
        self.add_rule(AdaptationRule(
            rule_id="decrease_delegation_on_success",
            name="Decrease Delegation Threshold",
            description="Decrease delegation threshold when success rate is high",
            trigger=AdaptationTrigger.SUCCESS_PATTERN_DETECTED,
            condition=lambda ctx: ctx.get("success_rate", 0) > 0.9,
            adaptation_type=AdaptationType.DELEGATION_THRESHOLD,
            parameter="delegation_threshold",
            adjustment=lambda v, ctx: max(0.5, v - 0.05),
            priority=6,
            cooldown_minutes=60,
        ))
        
        # Rule 3: Adjust memory threshold on pressure
        self.add_rule(AdaptationRule(
            rule_id="adjust_memory_on_pressure",
            name="Adjust Memory Threshold",
            description="Lower memory threshold when pressure is high",
            trigger=AdaptationTrigger.RESOURCE_PRESSURE,
            condition=lambda ctx: ctx.get("memory_pressure", 0) > 0.8,
            adaptation_type=AdaptationType.MEMORY_THRESHOLD,
            parameter="memory_threshold",
            adjustment=lambda v, ctx: max(0.6, v - 0.1),
            priority=9,
            cooldown_minutes=15,
        ))
        
        # Rule 4: Adjust confidence threshold on cognitive overload
        self.add_rule(AdaptationRule(
            rule_id="adjust_confidence_on_overload",
            name="Adjust Confidence Threshold",
            description="Raise confidence threshold when cognitive load is high",
            trigger=AdaptationTrigger.COGNITIVE_OVERLOAD,
            condition=lambda ctx: ctx.get("cognitive_load", 0) > 0.8,
            adaptation_type=AdaptationType.CONFIDENCE_THRESHOLD,
            parameter="confidence_threshold",
            adjustment=lambda v, ctx: min(0.9, v + 0.05),
            priority=7,
            cooldown_minutes=20,
        ))
        
        # Rule 5: Reduce retry on anti-pattern
        self.add_rule(AdaptationRule(
            rule_id="reduce_retry_on_antipattern",
            name="Reduce Retry Count",
            description="Reduce retry count when anti-pattern detected",
            trigger=AdaptationTrigger.ANTI_PATTERN_DETECTED,
            condition=lambda ctx: ctx.get("anti_pattern_detected", False),
            adaptation_type=AdaptationType.RETRY_POLICY,
            parameter="max_retries",
            adjustment=lambda v, ctx: max(1, int(v) - 1) if isinstance(v, int) else v,
            priority=5,
            cooldown_minutes=60,
        ))
        
        logger.info(f"Setup {len(self._rules)} default adaptation rules")
    
    # ==========================================
    # RULE MANAGEMENT
    # ==========================================
    
    def add_rule(self, rule: AdaptationRule) -> None:
        """Ajoute une règle d'adaptation."""
        self._rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Supprime une règle."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def get_rules(self) -> List[AdaptationRule]:
        """Retourne toutes les règles."""
        return list(self._rules.values())
    
    # ==========================================
    # DETECTION
    # ==========================================
    
    def detect_adaptation_needs(
        self,
        context: Dict[str, Any],
    ) -> List[AdaptationRecord]:
        """
        Détecte les besoins d'adaptation.
        
        C'est LA méthode centrale pour la détection automatique.
        
        Args:
            context: Le contexte système actuel
            
        Returns:
            Liste des adaptations proposées
        """
        if not self.config.enabled:
            return []
        
        adaptations = []
        
        # Check each rule
        for rule in sorted(self._rules.values(), key=lambda r: -r.priority):
            if not rule.should_trigger(context):
                continue
            
            # Get current value
            if rule.parameter not in self._parameters:
                continue
            
            current_value = self.get_parameter(rule.parameter)
            
            if current_value is None:
                continue
            
            # Calculate new value
            new_value = rule.apply(current_value, context)
            
            # Check if actually different
            if new_value == current_value:
                continue
            
            # Create adaptation record
            record = AdaptationRecord(
                adaptation_type=rule.adaptation_type,
                trigger=rule.trigger,
                parameter=rule.parameter,
                old_value=current_value,
                new_value=new_value,
                reason=f"Rule: {rule.name}",
                can_rollback=rule.can_rollback,
                requires_confirmation=(
                    rule.requires_confirmation or
                    rule.adaptation_type in self.config.critical_adaptation_types
                ),
                context=context.copy(),
                metadata={"rule_id": rule.rule_id},
            )
            
            # Capture metrics before
            record.metrics_before = self._capture_metrics()
            
            adaptations.append(record)
            
            # Mark rule as triggered
            rule.last_triggered = datetime.utcnow()
        
        self._total_proposed += len(adaptations)
        
        return adaptations
    
    def _capture_metrics(self) -> Dict[str, float]:
        """Capture les métriques actuelles."""
        # This would integrate with Telemetry
        return {
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # ==========================================
    # APPLICATION
    # ==========================================
    
    def should_apply(self, adaptation: AdaptationRecord) -> bool:
        """Vérifie si une adaptation peut être appliquée."""
        # Check hour limit
        self._reset_hour_counter()
        
        if self._adaptations_this_hour >= self.config.max_adaptations_per_hour:
            logger.warning("Max adaptations per hour reached")
            return False
        
        # Check if requires confirmation
        if adaptation.requires_confirmation and not self.config.auto_apply:
            return False
        
        # Check stability period
        if self._recent_adaptations:
            last_time = self._history[-1].applied_at if self._history else None
            if last_time:
                elapsed = (datetime.utcnow() - last_time).total_seconds() / 60
                if elapsed < self.config.min_stability_period_minutes:
                    logger.debug("Within stability period")
                    return False
        
        return True
    
    def apply_adaptation(
        self,
        adaptation: AdaptationRecord,
    ) -> bool:
        """
        Applique une adaptation.
        
        C'est LA méthode centrale pour l'application.
        
        Args:
            adaptation: L'adaptation à appliquer
            
        Returns:
            True si appliquée avec succès
        """
        if not self.should_apply(adaptation):
            adaptation.status = AdaptationStatus.REJECTED
            return False
        
        try:
            # Apply the change
            success = self.set_parameter(
                adaptation.parameter,
                adaptation.new_value
            )
            
            if not success:
                adaptation.status = AdaptationStatus.FAILED
                return False
            
            # Update record
            adaptation.status = AdaptationStatus.APPLIED
            adaptation.applied_at = datetime.utcnow()
            
            # Track
            self._history.append(adaptation)
            self._recent_adaptations.append(adaptation.adaptation_id)
            self._adaptations_this_hour += 1
            self._total_applied += 1
            
            # Limit history
            if len(self._history) > self.config.max_history_size:
                self._history = self._history[-self.config.max_history_size:]
            
            # Callback
            for callback in self._on_adaptation_applied:
                try:
                    callback(adaptation)
                except Exception as e:
                    logger.error(f"Adaptation callback error: {e}")
            
            logger.info(
                f"Applied adaptation: {adaptation.parameter} "
                f"{adaptation.old_value} → {adaptation.new_value}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Adaptation failed: {e}")
            adaptation.status = AdaptationStatus.FAILED
            return False
    
    def _reset_hour_counter(self) -> None:
        """Reset le compteur horaire."""
        now = datetime.utcnow()
        if (now - self._hour_reset).total_seconds() >= 3600:
            self._adaptations_this_hour = 0
            self._hour_reset = now
    
    # ==========================================
    # IMPACT EVALUATION
    # ==========================================
    
    def evaluate_impact(
        self,
        adaptation_id: str,
        current_metrics: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Évalue l'impact d'une adaptation.
        
        Args:
            adaptation_id: ID de l'adaptation
            current_metrics: Métriques actuelles
            
        Returns:
            Score d'impact (-1.0 à 1.0)
        """
        adaptation = self._find_adaptation(adaptation_id)
        if not adaptation:
            return 0.0
        
        # Capture current metrics if not provided
        current_metrics = current_metrics or self._capture_metrics()
        
        # Calculate impact
        impact = self._calculate_impact(
            adaptation.metrics_before,
            current_metrics,
            adaptation.adaptation_type,
        )
        
        adaptation.metrics_after = current_metrics
        adaptation.impact_score = impact
        
        # Auto-rollback if negative
        if (
            self.config.auto_rollback_on_negative_impact and
            impact < self.config.negative_impact_threshold and
            adaptation.can_rollback
        ):
            logger.warning(f"Auto-rolling back adaptation {adaptation_id} due to negative impact")
            self.rollback(adaptation_id)
        
        return impact
    
    def _calculate_impact(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
        adaptation_type: AdaptationType,
    ) -> float:
        """Calcule l'impact d'une adaptation."""
        # Simplified impact calculation
        # In reality, this would be more sophisticated
        
        # Success rate change
        success_before = before.get("success_rate", 0.8)
        success_after = after.get("success_rate", 0.8)
        success_delta = success_after - success_before
        
        # Latency change (lower is better)
        latency_before = before.get("avg_latency_ms", 1000)
        latency_after = after.get("avg_latency_ms", 1000)
        latency_factor = 0
        if latency_before > 0:
            latency_factor = (latency_before - latency_after) / latency_before
        
        # Combine
        impact = success_delta * 0.7 + latency_factor * 0.3
        
        return max(-1.0, min(1.0, impact))
    
    # ==========================================
    # ROLLBACK
    # ==========================================
    
    def rollback(self, adaptation_id: str) -> bool:
        """
        Annule une adaptation.
        
        Args:
            adaptation_id: ID de l'adaptation
            
        Returns:
            True si rollback réussi
        """
        adaptation = self._find_adaptation(adaptation_id)
        if not adaptation:
            return False
        
        if not adaptation.can_rollback:
            logger.warning(f"Adaptation {adaptation_id} cannot be rolled back")
            return False
        
        if adaptation.status != AdaptationStatus.APPLIED:
            return False
        
        # Check rollback window
        if adaptation.applied_at:
            elapsed_hours = (
                datetime.utcnow() - adaptation.applied_at
            ).total_seconds() / 3600
            
            if elapsed_hours > self.config.rollback_window_hours:
                logger.warning(f"Adaptation {adaptation_id} outside rollback window")
                return False
        
        try:
            # Revert the change
            success = self.set_parameter(
                adaptation.parameter,
                adaptation.old_value
            )
            
            if not success:
                return False
            
            # Update record
            adaptation.status = AdaptationStatus.ROLLED_BACK
            adaptation.rolled_back_at = datetime.utcnow()
            
            self._total_rolled_back += 1
            
            # Callback
            for callback in self._on_adaptation_rolled_back:
                try:
                    callback(adaptation)
                except Exception as e:
                    logger.error(f"Rollback callback error: {e}")
            
            logger.info(
                f"Rolled back adaptation: {adaptation.parameter} "
                f"{adaptation.new_value} → {adaptation.old_value}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def _find_adaptation(self, adaptation_id: str) -> Optional[AdaptationRecord]:
        """Trouve une adaptation par ID."""
        for adaptation in self._history:
            if adaptation.adaptation_id == adaptation_id:
                return adaptation
        return None
    
    def rollback_all_recent(self, hours: int = 1) -> int:
        """Rollback toutes les adaptations récentes."""
        rolled_back = 0
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        for adaptation in reversed(self._history):
            if adaptation.applied_at and adaptation.applied_at >= cutoff:
                if self.rollback(adaptation.adaptation_id):
                    rolled_back += 1
        
        return rolled_back
    
    # ==========================================
    # QUERY
    # ==========================================
    
    def get_history(self, limit: int = 50) -> List[AdaptationRecord]:
        """Retourne l'historique des adaptations."""
        return self._history[-limit:]
    
    def get_recent_adaptations(self, hours: int = 24) -> List[AdaptationRecord]:
        """Retourne les adaptations récentes."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            a for a in self._history
            if a.applied_at and a.applied_at >= cutoff
        ]
    
    def get_parameter_history(
        self,
        parameter: str,
    ) -> List[AdaptationRecord]:
        """Retourne l'historique d'un paramètre."""
        return [
            a for a in self._history
            if a.parameter == parameter
        ]
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return {
            "enabled": self.config.enabled,
            "total_proposed": self._total_proposed,
            "total_applied": self._total_applied,
            "total_rolled_back": self._total_rolled_back,
            "apply_rate": self._total_applied / self._total_proposed if self._total_proposed > 0 else 0,
            "rollback_rate": self._total_rolled_back / self._total_applied if self._total_applied > 0 else 0,
            "adaptations_this_hour": self._adaptations_this_hour,
            "history_size": len(self._history),
            "rules_count": len(self._rules),
            "parameters_count": len(self._parameters),
        }
    
    def get_parameter_report(self) -> List[Dict[str, Any]]:
        """Retourne un rapport des paramètres."""
        report = []
        
        for name, param in self._parameters.items():
            current = param["get_value"]()
            history = self.get_parameter_history(name)
            
            report.append({
                "name": name,
                "type": param["type"],
                "current_value": current,
                "min_value": param["min_value"],
                "max_value": param["max_value"],
                "adaptations_count": len(history),
                "last_adapted": (
                    history[-1].applied_at.isoformat()
                    if history else None
                ),
            })
        
        return report
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_adaptation_proposed(
        self,
        callback: Callable[[AdaptationRecord], None]
    ) -> None:
        """Callback pour proposition."""
        self._on_adaptation_proposed.append(callback)
    
    def on_adaptation_applied(
        self,
        callback: Callable[[AdaptationRecord], None]
    ) -> None:
        """Callback pour application."""
        self._on_adaptation_applied.append(callback)
    
    def on_adaptation_rolled_back(
        self,
        callback: Callable[[AdaptationRecord], None]
    ) -> None:
        """Callback pour rollback."""
        self._on_adaptation_rolled_back.append(callback)


# ==========================================
# FACTORY
# ==========================================

def create_adaptation_engine(
    config: Optional[AdaptationConfig] = None,
) -> AdaptationEngine:
    """Factory pour créer un AdaptationEngine."""
    return AdaptationEngine(config=config)
