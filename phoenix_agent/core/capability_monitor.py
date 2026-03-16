"""
Phoenix Agent - Capability Monitor
===================================

Surveillance en temps réel des capacités cognitives de l'agent.

Le CapabilityMonitor est LE composant qui permet à un agent de dire:
    "Je sens que je perds en efficacité → je devrais déléguer."

C'est le "self-awareness" de l'agent.

Métriques surveillées:
    - Context window utilization
    - Iteration count
    - Reasoning depth
    - Confidence level
    - Cognitive fatigue
    - Load level

Décisions:
    - CONTINUE: L'agent peut continuer efficacement
    - DELEGATE: L'agent devrait déléguer
    - ABORT: L'agent doit arrêter

Version: 0.5.0 (Cognitive Self-Monitoring)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import time

from .agent_profile import AgentProfile, AgentState
from .capability import CapabilityLimits, CapabilityAssessment


logger = logging.getLogger("phoenix.capability_monitor")


# ==========================================
# MONITORING DECISION
# ==========================================

class MonitoringDecision(str, Enum):
    """Décision du monitoring."""
    CONTINUE = "continue"       # Continue normalement
    WARNING = "warning"         # Continue mais attention
    DELEGATE = "delegate"       # Devrait déléguer
    ABORT = "abort"             # Doit arrêter


# ==========================================
# DELEGATION TRIGGER
# ==========================================

class DelegationTrigger(str, Enum):
    """
    Triggers de délégation cognitive.
    
    Ce sont les Raisons pour lesquelles un agent décide de déléguer.
    Basées sur les limites cognitives, pas juste la complexité.
    """
    # Memory
    MEMORY_OVERFLOW = "memory_overflow"               # Context window full
    MEMORY_PRESSURE = "memory_pressure"               # Approaching limit
    
    # Iterations
    MAX_ITERATIONS = "max_iterations"                 # Trop d'itérations
    APPROACHING_ITERATION_LIMIT = "approaching_iteration_limit"
    
    # Reasoning
    MAX_REASONING_DEPTH = "max_reasoning_depth"       # Trop profond
    REASONING_STUCK = "reasoning_stuck"               # Pas de progrès
    
    # Confidence
    LOW_CONFIDENCE = "low_confidence"                 # Confiance < seuil
    CONFIDENCE_DEGRADATION = "confidence_degradation" # Confiance baisse
    
    # Cognitive State
    COGNITIVE_FATIGUE = "cognitive_fatigue"           # Fatigue élevée
    HIGH_LOAD = "high_load"                           # Trop chargé
    
    # Task
    TASK_TOO_COMPLEX = "task_too_complex"             # Complexité > capacité
    DOMAIN_MISMATCH = "domain_mismatch"               # Mauvais domaine
    
    # Resources
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    TIME_BUDGET_EXCEEDED = "time_budget_exceeded"
    TOOL_UNAVAILABLE = "tool_unavailable"
    
    # Quality
    QUALITY_DEGRADATION = "quality_degradation"       # Qualité baisse
    REPEATING_PATTERNS = "repeating_patterns"         # Boucles


# ==========================================
# MONITORING RESULT
# ==========================================

@dataclass
class MonitoringResult:
    """
    Résultat du monitoring.
    
    Répond à: "Quel est mon état cognitif et que dois-je faire?"
    """
    decision: MonitoringDecision
    triggers: List[DelegationTrigger] = field(default_factory=list)
    
    # Métriques actuelles
    token_utilization: float = 0.0
    iteration_utilization: float = 0.0
    depth_utilization: float = 0.0
    current_confidence: float = 1.0
    fatigue_level: float = 0.0
    load_level: float = 0.0
    
    # Recommandations
    recommendations: List[str] = field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def should_delegate(self) -> bool:
        """Doit déléguer."""
        return self.decision in [MonitoringDecision.DELEGATE, MonitoringDecision.ABORT]
    
    @property
    def is_warning(self) -> bool:
        """Est en warning."""
        return self.decision == MonitoringDecision.WARNING
    
    @property
    def can_continue(self) -> bool:
        """Peut continuer."""
        return self.decision in [MonitoringDecision.CONTINUE, MonitoringDecision.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "triggers": [t.value for t in self.triggers],
            "metrics": {
                "token_utilization": self.token_utilization,
                "iteration_utilization": self.iteration_utilization,
                "depth_utilization": self.depth_utilization,
                "confidence": self.current_confidence,
                "fatigue": self.fatigue_level,
                "load": self.load_level,
            },
            "recommendations": self.recommendations,
        }


# ==========================================
# MONITORING CONFIG
# ==========================================

@dataclass
class MonitoringConfig:
    """Configuration du monitoring."""
    # Seuils de warning (avant délégation)
    token_warning_threshold: float = 0.7
    iteration_warning_threshold: float = 0.7
    depth_warning_threshold: float = 0.7
    
    # Seuils de délégation
    token_delegation_threshold: float = 0.85
    iteration_delegation_threshold: float = 0.9
    depth_delegation_threshold: float = 0.9
    
    # Confiance
    confidence_warning_threshold: float = 0.7
    confidence_delegation_threshold: float = 0.5
    
    # Fatigue
    fatigue_warning_threshold: float = 0.5
    fatigue_delegation_threshold: float = 0.7
    
    # Load
    load_warning_threshold: float = 0.7
    load_delegation_threshold: float = 0.9
    
    # Intervalles de check
    check_interval_iterations: int = 1
    check_interval_tokens: int = 500


# ==========================================
# CAPABILITY MONITOR
# ==========================================

class CapabilityMonitor:
    """
    Moniteur des capacités cognitives de l'agent.
    
    C'est le composant de "self-awareness" qui permet à l'agent
    de surveiller son propre état et décider QUAND déléguer.
    
    Architecture:
        AgentLoop
            │
            ├── CapabilityMonitor.check()
            │       │
            │       ├── Analyze state
            │       ├── Check limits
            │       └── Return decision
            │
            └── Decision:
                    CONTINUE → Continue
                    WARNING → Continue + log
                    DELEGATE → Trigger delegation
                    ABORT → Stop
    
    Example:
        monitor = CapabilityMonitor(profile)
        
        # Dans AgentLoop
        while can_continue:
            result = monitor.check()
            
            if result.should_delegate:
                await delegate_subtask(task)
                continue
            
            # ... continue reasoning ...
    """
    
    def __init__(
        self,
        profile: AgentProfile,
        config: Optional[MonitoringConfig] = None,
    ):
        self.profile = profile
        self.config = config or MonitoringConfig()
        
        # Historique
        self._history: List[MonitoringResult] = []
        self._last_check: Optional[datetime] = None
        self._checks_count: int = 0
    
    # ==========================================
    # MAIN CHECK
    # ==========================================
    
    def check(
        self,
        current_tokens: Optional[int] = None,
        current_iterations: Optional[int] = None,
        current_depth: Optional[int] = None,
        current_confidence: Optional[float] = None,
    ) -> MonitoringResult:
        """
        Effectue un check complet des capacités.
        
        C'est LA méthode centrale du monitoring cognitif.
        
        Args:
            current_tokens: Tokens actuels (si None, utilise state)
            current_iterations: Itérations actuelles
            current_depth: Profondeur actuelle
            current_confidence: Confiance actuelle
            
        Returns:
            MonitoringResult avec décision
        """
        limits = self.profile.default_limits
        state = self.profile.state
        
        # Utiliser les valeurs fournies ou l'état
        tokens = current_tokens if current_tokens is not None else state.current_tokens_used
        iterations = current_iterations if current_iterations is not None else state.current_iterations
        depth = current_depth if current_depth is not None else state.current_reasoning_depth
        confidence = current_confidence if current_confidence is not None else state.current_confidence
        
        # Calculer les utilisations
        token_util = tokens / limits.max_context_tokens if limits.max_context_tokens > 0 else 0
        iter_util = iterations / limits.max_iterations if limits.max_iterations > 0 else 0
        depth_util = depth / limits.max_reasoning_depth if limits.max_reasoning_depth > 0 else 0
        
        # Collecter les triggers
        triggers: List[DelegationTrigger] = []
        recommendations: List[str] = []
        
        # Check memory
        if token_util >= 1.0:
            triggers.append(DelegationTrigger.MEMORY_OVERFLOW)
            recommendations.append("Memory full: consider delegating remaining work")
        elif token_util >= self.config.token_delegation_threshold:
            triggers.append(DelegationTrigger.MEMORY_PRESSURE)
            recommendations.append("Memory pressure high: prepare for delegation")
        elif token_util >= self.config.token_warning_threshold:
            recommendations.append("Memory usage elevated")
        
        # Check iterations
        if iter_util >= 1.0:
            triggers.append(DelegationTrigger.MAX_ITERATIONS)
            recommendations.append("Max iterations reached: must delegate or stop")
        elif iter_util >= self.config.iteration_delegation_threshold:
            triggers.append(DelegationTrigger.APPROACHING_ITERATION_LIMIT)
            recommendations.append("Approaching iteration limit: consider delegating")
        elif iter_util >= self.config.iteration_warning_threshold:
            recommendations.append("Iteration count elevated")
        
        # Check reasoning depth
        if depth_util >= 1.0:
            triggers.append(DelegationTrigger.MAX_REASONING_DEPTH)
            recommendations.append("Max reasoning depth reached: must delegate")
        elif depth_util >= self.config.depth_delegation_threshold:
            recommendations.append("Reasoning depth elevated")
        
        # Check confidence
        if confidence <= self.config.confidence_delegation_threshold:
            triggers.append(DelegationTrigger.LOW_CONFIDENCE)
            recommendations.append("Confidence too low: delegate to specialist")
        elif confidence <= self.config.confidence_warning_threshold:
            triggers.append(DelegationTrigger.CONFIDENCE_DEGRADATION)
            recommendations.append("Confidence dropping: monitor closely")
        
        # Check fatigue
        if state.cognitive_fatigue >= self.config.fatigue_delegation_threshold:
            triggers.append(DelegationTrigger.COGNITIVE_FATIGUE)
            recommendations.append("Cognitive fatigue high: reset or delegate")
        elif state.cognitive_fatigue >= self.config.fatigue_warning_threshold:
            recommendations.append("Cognitive fatigue building")
        
        # Check load
        if state.current_load >= self.config.load_delegation_threshold:
            triggers.append(DelegationTrigger.HIGH_LOAD)
            recommendations.append("Agent overloaded: delegate to reduce load")
        elif state.current_load >= self.config.load_warning_threshold:
            recommendations.append("Agent load elevated")
        
        # Déterminer la décision
        decision = self._determine_decision(triggers, token_util, iter_util, confidence, state.cognitive_fatigue)
        
        # Créer le résultat
        result = MonitoringResult(
            decision=decision,
            triggers=triggers,
            token_utilization=token_util,
            iteration_utilization=iter_util,
            depth_utilization=depth_util,
            current_confidence=confidence,
            fatigue_level=state.cognitive_fatigue,
            load_level=state.current_load,
            recommendations=recommendations,
        )
        
        # Enregistrer
        self._history.append(result)
        self._last_check = datetime.utcnow()
        self._checks_count += 1
        
        # Log si warning ou delegation
        if decision == MonitoringDecision.WARNING:
            logger.warning(f"Capability warning: {recommendations}")
        elif decision in [MonitoringDecision.DELEGATE, MonitoringDecision.ABORT]:
            logger.info(f"Delegation triggered: {[t.value for t in triggers]}")
        
        return result
    
    def _determine_decision(
        self,
        triggers: List[DelegationTrigger],
        token_util: float,
        iter_util: float,
        confidence: float,
        fatigue: float,
    ) -> MonitoringDecision:
        """Détermine la décision basée sur les triggers."""
        # ABORT: Limites critiques dépassées
        critical_triggers = {
            DelegationTrigger.MEMORY_OVERFLOW,
            DelegationTrigger.MAX_ITERATIONS,
            DelegationTrigger.MAX_REASONING_DEPTH,
        }
        
        if any(t in critical_triggers for t in triggers):
            # Si aussi fatigue ou low confidence → abort
            if fatigue > 0.8 or confidence < 0.3:
                return MonitoringDecision.ABORT
            return MonitoringDecision.DELEGATE
        
        # DELEGATE: Triggers importants
        delegation_triggers = {
            DelegationTrigger.MEMORY_PRESSURE,
            DelegationTrigger.APPROACHING_ITERATION_LIMIT,
            DelegationTrigger.LOW_CONFIDENCE,
            DelegationTrigger.COGNITIVE_FATIGUE,
            DelegationTrigger.HIGH_LOAD,
            DelegationTrigger.DOMAIN_MISMATCH,
        }
        
        if any(t in delegation_triggers for t in triggers):
            return MonitoringDecision.DELEGATE
        
        # WARNING: Utilisation élevée
        if (token_util > self.config.token_warning_threshold or
            iter_util > self.config.iteration_warning_threshold or
            fatigue > self.config.fatigue_warning_threshold or
            confidence < self.config.confidence_warning_threshold):
            return MonitoringDecision.WARNING
        
        # CONTINUE: Tout va bien
        return MonitoringDecision.CONTINUE
    
    # ==========================================
    # QUICK CHECKS
    # ==========================================
    
    def can_continue(self) -> bool:
        """Check rapide si l'agent peut continuer."""
        result = self.check()
        return result.can_continue
    
    def should_delegate(self) -> bool:
        """Check rapide si l'agent devrait déléguer."""
        result = self.check()
        return result.should_delegate
    
    def get_status(self) -> str:
        """Retourne le statut en texte."""
        result = self.check()
        
        if result.decision == MonitoringDecision.CONTINUE:
            return "healthy"
        elif result.decision == MonitoringDecision.WARNING:
            return "warning"
        elif result.decision == MonitoringDecision.DELEGATE:
            return "should_delegate"
        else:
            return "critical"
    
    # ==========================================
    # METRICS
    # ==========================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques actuelles."""
        state = self.profile.state
        limits = self.profile.default_limits
        
        return {
            "tokens": {
                "current": state.current_tokens_used,
                "max": limits.max_context_tokens,
                "utilization": state.current_tokens_used / limits.max_context_tokens if limits.max_context_tokens > 0 else 0,
            },
            "iterations": {
                "current": state.current_iterations,
                "max": limits.max_iterations,
                "utilization": state.current_iterations / limits.max_iterations if limits.max_iterations > 0 else 0,
            },
            "depth": {
                "current": state.current_reasoning_depth,
                "max": limits.max_reasoning_depth,
                "utilization": state.current_reasoning_depth / limits.max_reasoning_depth if limits.max_reasoning_depth > 0 else 0,
            },
            "cognitive": {
                "confidence": state.current_confidence,
                "fatigue": state.cognitive_fatigue,
                "load": state.current_load,
            },
            "performance": {
                "success_rate": state.success_rate,
                "tasks_completed": state.current_tasks_completed,
            },
        }
    
    def get_history(self, limit: int = 10) -> List[MonitoringResult]:
        """Retourne l'historique des checks."""
        return self._history[-limit:]
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_delegate(
        self,
        callback: Callable[[MonitoringResult], None]
    ) -> None:
        """Enregistre un callback pour la délégation."""
        self._delegate_callback = callback
    
    def check_and_notify(self) -> MonitoringResult:
        """Check et notifie si délégation nécessaire."""
        result = self.check()
        
        if result.should_delegate and hasattr(self, '_delegate_callback'):
            self._delegate_callback(result)
        
        return result
