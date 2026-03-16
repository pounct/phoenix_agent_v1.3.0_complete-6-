"""
Phoenix Agent - Learning Loop
=============================

Boucle de feedback cognitif pour l'amélioration continue.

La différence entre un Agent qui répète et un Agent qui apprend:

    Sans LearningLoop:
        - Les décisions sont répétées
        - Les erreurs sont refaites
        - Les patterns de succès ne sont pas capturés
        - Pas d'amélioration au fil du temps

    Avec LearningLoop:
        - Feedback entre décision et résultat
        - Capture des patterns de succès
        - Identification des anti-patterns
        - Ajustement des stratégies
        - Amélioration continue

C'est LE composant qui répond à:
    - "Ai-je déjà rencontré cette situation?"
    - "Qu'est-ce qui a fonctionné la dernière fois?"
    - "Pourquoi cette approche a-t-elle échoué?"
    - "Dois-je changer de stratégie?"

ARCHITECTURE:
    Decision → Action → Outcome → LearningLoop → Improved Decision

CAPABILITIES:
    - record_outcome(): Enregistrer un résultat
    - get_patterns(): Identifier les patterns
    - suggest_strategy(): Suggérer une stratégie
    - adjust_confidence(): Ajuster la confiance
    - identify_anti_patterns(): Identifier les erreurs récurrentes

MÉTRIQUES TRACKÉES:
    - Success rate par type de décision
    - Failure patterns
    - Confidence calibration
    - Strategy effectiveness
    - Recovery success patterns

Version: 1.0.0 (Cognitive Feedback Layer)
"""

from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import uuid
import json


logger = logging.getLogger("phoenix.learning_loop")


# ==========================================
# OUTCOME TYPE
# ==========================================

class OutcomeType(str, Enum):
    """Type de résultat."""
    SUCCESS = "success"                   # Réussite complète
    PARTIAL_SUCCESS = "partial_success"   # Réussite partielle
    FAILURE = "failure"                   # Échec
    TIMEOUT = "timeout"                   # Timeout
    CANCELLED = "cancelled"               # Annulé
    DELEGATED = "delegated"               # Délégué avec succès
    RECOVERED = "recovered"               # Récupéré après erreur
    ESCALATED = "escalated"               # Escaladé


class LearningCategory(str, Enum):
    """Catégorie d'apprentissage."""
    DECISION = "decision"       # Apprentissage sur les décisions
    STRATEGY = "strategy"       # Apprentissage sur les stratégies
    DELEGATION = "delegation"   # Apprentissage sur les délégations
    RECOVERY = "recovery"       # Apprentissage sur les récupérations
    MEMORY = "memory"           # Apprentissage sur la mémoire
    COGNITIVE = "cognitive"     # Apprentissage cognitif général


# ==========================================
# COGNITIVE FEEDBACK
# ==========================================

@dataclass
class CognitiveFeedback:
    """
    Feedback cognitif entre une décision et son résultat.
    
    C'est l'unité fondamentale d'apprentissage.
    """
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Decision context
    decision_type: str = ""           # Type de décision
    decision_context: Dict[str, Any] = field(default_factory=dict)
    
    # Outcome
    outcome_type: OutcomeType = OutcomeType.SUCCESS
    outcome_description: str = ""
    
    # Metrics
    confidence_before: float = 0.8    # Confiance avant décision
    confidence_after: float = 0.8     # Confiance après résultat
    confidence_delta: float = 0.0     # Changement de confiance
    
    # Time
    decision_time: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0.0
    
    # Resources used
    tokens_used: int = 0
    iterations_used: int = 0
    delegations_used: int = 0
    
    # Result details
    result_summary: str = ""
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    # Failure analysis (if failed)
    failure_reason: str = ""
    failure_category: str = ""        # cognitive, resource, external, etc.
    
    # Success pattern (if succeeded)
    success_factors: List[str] = field(default_factory=list)
    
    # Learning
    lessons_learned: List[str] = field(default_factory=list)
    suggested_adjustments: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    goal_id: str = ""
    session_id: str = ""
    
    @property
    def is_success(self) -> bool:
        """Le résultat est un succès."""
        return self.outcome_type in [
            OutcomeType.SUCCESS,
            OutcomeType.PARTIAL_SUCCESS,
            OutcomeType.DELEGATED,
            OutcomeType.RECOVERED,
        ]
    
    @property
    def is_failure(self) -> bool:
        """Le résultat est un échec."""
        return self.outcome_type in [
            OutcomeType.FAILURE,
            OutcomeType.TIMEOUT,
        ]
    
    @property
    def confidence_improved(self) -> bool:
        """La confiance a augmenté."""
        return self.confidence_delta > 0
    
    def calculate_delta(self) -> float:
        """Calcule le delta de confiance."""
        self.confidence_delta = self.confidence_after - self.confidence_before
        return self.confidence_delta
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "decision_type": self.decision_type,
            "outcome_type": self.outcome_type.value,
            "is_success": self.is_success,
            "confidence_delta": self.confidence_delta,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "failure_reason": self.failure_reason[:100] if self.failure_reason else None,
            "success_factors": self.success_factors[:3],
            "lessons_learned": self.lessons_learned[:3],
        }


# ==========================================
# PATTERN RECORD
# ==========================================

@dataclass
class PatternRecord:
    """Enregistrement d'un pattern identifié."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pattern_type: str = ""           # success, failure, anti-pattern, optimal
    pattern_name: str = ""
    description: str = ""
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)  # When this applies
    
    # Actions
    recommended_action: str = ""
    avoid_actions: List[str] = field(default_factory=list)
    
    # Confidence
    confidence: float = 0.5
    sample_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Learning rate
    learning_rate: float = 0.1       # How fast to adjust
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        """Taux de succès."""
        if self.sample_count == 0:
            return 0.0
        return self.success_count / self.sample_count
    
    def update(self, success: bool) -> None:
        """Met à jour le pattern."""
        self.sample_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # Update confidence using exponential moving average
        self.confidence = (
            (1 - self.learning_rate) * self.confidence +
            self.learning_rate * (1.0 if success else 0.0)
        )
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "pattern_name": self.pattern_name,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "sample_count": self.sample_count,
        }


# ==========================================
# STRATEGY RECORD
# ==========================================

@dataclass
class StrategyRecord:
    """Enregistrement d'une stratégie."""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    strategy_name: str = ""
    description: str = ""
    
    # Applicability
    applicable_contexts: List[str] = field(default_factory=list)
    applicable_goal_types: List[str] = field(default_factory=list)
    applicable_task_types: List[str] = field(default_factory=list)
    
    # Effectiveness
    effectiveness_score: float = 0.5
    total_applications: int = 0
    successful_applications: int = 0
    
    # Resources
    avg_tokens_used: float = 0.0
    avg_time_ms: float = 0.0
    avg_iterations: float = 0.0
    
    # Adjustments
    parameter_adjustments: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Taux de succès."""
        if self.total_applications == 0:
            return 0.0
        return self.successful_applications / self.total_applications
    
    def record_application(
        self,
        success: bool,
        tokens: int = 0,
        time_ms: float = 0.0,
        iterations: int = 0,
    ) -> None:
        """Enregistre une application de la stratégie."""
        self.total_applications += 1
        if success:
            self.successful_applications += 1
        
        # Update averages
        n = self.total_applications
        self.avg_tokens_used = (self.avg_tokens_used * (n - 1) + tokens) / n
        self.avg_time_ms = (self.avg_time_ms * (n - 1) + time_ms) / n
        self.avg_iterations = (self.avg_iterations * (n - 1) + iterations) / n
        
        # Update effectiveness
        self.effectiveness_score = self.success_rate
        self.last_used = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "effectiveness": self.effectiveness_score,
            "success_rate": self.success_rate,
            "total_applications": self.total_applications,
            "avg_time_ms": self.avg_time_ms,
        }


# ==========================================
# LEARNING CONFIG
# ==========================================

@dataclass
class LearningConfig:
    """Configuration du LearningLoop."""
    # History
    max_feedback_history: int = 10000
    max_pattern_history: int = 1000
    
    # Learning rates
    default_learning_rate: float = 0.1
    confidence_adjustment_rate: float = 0.05
    
    # Pattern detection
    min_samples_for_pattern: int = 5
    pattern_confidence_threshold: float = 0.7
    
    # Anti-pattern detection
    anti_pattern_threshold: float = 0.3  # Success rate below = anti-pattern
    
    # Strategy recommendation
    strategy_recommendation_threshold: float = 0.6
    
    # Cleanup
    cleanup_interval_hours: int = 24
    old_pattern_threshold_days: int = 30


# ==========================================
# LEARNING LOOP
# ==========================================

class LearningLoop:
    """
    Boucle de feedback cognitif pour l'amélioration continue.
    
    C'est LE composant qui permet à l'agent de devenir meilleur.
    
    Responsabilités:
        1. Enregistrer les résultats des décisions
        2. Identifier les patterns de succès/échec
        3. Suggérer des ajustements de stratégie
        4. Ajuster les niveaux de confiance
        5. Prédire les meilleurs choix futurs
    
    Architecture:
        DecisionEngine.decide()
                │
                ▼
        execute_action()
                │
                ▼
        LearningLoop.record_outcome()
                │
                ├── Update patterns
                ├── Update strategies
                ├── Adjust confidence
                └── Store for future reference
                │
                ▼
        Next decision uses learned knowledge
    
    Example:
        learning = LearningLoop()
        
        # Record an outcome
        feedback = CognitiveFeedback(
            decision_type="delegate_specialist",
            outcome_type=OutcomeType.SUCCESS,
            confidence_before=0.7,
            confidence_after=0.85,
            success_factors=["accurate_domain_detection"],
        )
        learning.record_outcome(feedback)
        
        # Get suggestions
        suggestion = learning.suggest_strategy(
            context={"domain": "python", "complexity": "high"}
        )
        
        # Get confidence adjustment
        adjusted = learning.adjust_confidence(
            base_confidence=0.7,
            decision_type="delegate_specialist",
        )
    """
    
    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()
        
        # Feedback history
        self._feedback_history: List[CognitiveFeedback] = []
        
        # Patterns
        self._patterns: Dict[str, PatternRecord] = {}
        self._success_patterns: List[str] = []
        self._failure_patterns: List[str] = []
        self._anti_patterns: List[str] = []
        
        # Strategies
        self._strategies: Dict[str, StrategyRecord] = {}
        
        # Category tracking
        self._category_stats: Dict[LearningCategory, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "failure": 0}
        )
        
        # Decision tracking
        self._decision_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "avg_confidence_delta": 0.0}
        )
        
        # Confidence calibration
        self._confidence_calibration: Dict[str, List[float]] = defaultdict(list)
        
        # Callbacks
        self._on_pattern_discovered: List[Callable[[PatternRecord], None]] = []
        self._on_anti_pattern_detected: List[Callable[[PatternRecord], None]] = []
        
        # Stats
        self._total_outcomes = 0
        self._total_success = 0
        self._total_failure = 0
        
        logger.info("LearningLoop initialized")
    
    # ==========================================
    # RECORD OUTCOME
    # ==========================================
    
    def record_outcome(self, feedback: CognitiveFeedback) -> None:
        """
        Enregistre un résultat de décision.
        
        C'est LA méthode centrale du LearningLoop.
        
        Args:
            feedback: Le feedback cognitif
        """
        # Calculate delta
        feedback.calculate_delta()
        
        # Store
        self._feedback_history.append(feedback)
        self._total_outcomes += 1
        
        if feedback.is_success:
            self._total_success += 1
        else:
            self._total_failure += 1
        
        # Update stats
        self._update_decision_stats(feedback)
        self._update_category_stats(feedback)
        self._update_confidence_calibration(feedback)
        
        # Detect patterns
        self._detect_patterns(feedback)
        
        # Update strategies
        self._update_strategies(feedback)
        
        # Limit history
        if len(self._feedback_history) > self.config.max_feedback_history:
            self._feedback_history = self._feedback_history[-self.config.max_feedback_history:]
        
        logger.debug(
            f"Recorded outcome: {feedback.decision_type} → {feedback.outcome_type.value} "
            f"(delta: {feedback.confidence_delta:+.2f})"
        )
    
    def _update_decision_stats(self, feedback: CognitiveFeedback) -> None:
        """Met à jour les stats par type de décision."""
        stats = self._decision_stats[feedback.decision_type]
        stats["total"] += 1
        
        if feedback.is_success:
            stats["success"] += 1
        
        # Update average confidence delta
        n = stats["total"]
        old_avg = stats["avg_confidence_delta"]
        stats["avg_confidence_delta"] = (old_avg * (n - 1) + feedback.confidence_delta) / n
    
    def _update_category_stats(self, feedback: CognitiveFeedback) -> None:
        """Met à jour les stats par catégorie."""
        # Infer category from decision type
        category = self._infer_category(feedback.decision_type)
        
        stats = self._category_stats[category]
        stats["total"] += 1
        
        if feedback.is_success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
    
    def _infer_category(self, decision_type: str) -> LearningCategory:
        """Infère la catégorie d'une décision."""
        if "delegate" in decision_type.lower():
            return LearningCategory.DELEGATION
        elif "recover" in decision_type.lower():
            return LearningCategory.RECOVERY
        elif "memory" in decision_type.lower():
            return LearningCategory.MEMORY
        elif "strategy" in decision_type.lower():
            return LearningCategory.STRATEGY
        else:
            return LearningCategory.DECISION
    
    def _update_confidence_calibration(self, feedback: CognitiveFeedback) -> None:
        """Met à jour la calibration de confiance."""
        # Track predicted vs actual
        key = f"{feedback.decision_type}_{feedback.confidence_before:.1f}"
        actual = 1.0 if feedback.is_success else 0.0
        self._confidence_calibration[key].append(actual)
        
        # Limit
        if len(self._confidence_calibration[key]) > 100:
            self._confidence_calibration[key] = self._confidence_calibration[key][-100:]
    
    # ==========================================
    # PATTERN DETECTION
    # ==========================================
    
    def _detect_patterns(self, feedback: CognitiveFeedback) -> None:
        """Détecte les patterns depuis le feedback."""
        # Create pattern key from conditions
        pattern_key = self._create_pattern_key(feedback)
        
        if pattern_key not in self._patterns:
            self._create_pattern(pattern_key, feedback)
        else:
            self._update_pattern(pattern_key, feedback)
    
    def _create_pattern_key(self, feedback: CognitiveFeedback) -> str:
        """Crée une clé de pattern."""
        # Simplified: decision_type + context hash
        context_hash = hash(json.dumps(feedback.decision_context, sort_keys=True, default=str))
        return f"{feedback.decision_type}_{abs(context_hash) % 1000}"
    
    def _create_pattern(self, pattern_key: str, feedback: CognitiveFeedback) -> None:
        """Crée un nouveau pattern."""
        pattern = PatternRecord(
            pattern_type="success" if feedback.is_success else "failure",
            pattern_name=f"Pattern: {feedback.decision_type}",
            description=f"Pattern for {feedback.decision_type} decisions",
            conditions=feedback.decision_context.copy(),
            recommended_action=feedback.decision_type if feedback.is_success else "",
            avoid_actions=[feedback.decision_type] if not feedback.is_success else [],
            sample_count=1,
            success_count=1 if feedback.is_success else 0,
            failure_count=0 if feedback.is_success else 1,
        )
        
        self._patterns[pattern_key] = pattern
        logger.debug(f"Created pattern: {pattern_key}")
    
    def _update_pattern(self, pattern_key: str, feedback: CognitiveFeedback) -> None:
        """Met à jour un pattern existant."""
        pattern = self._patterns[pattern_key]
        pattern.update(feedback.is_success)
        
        # Check for anti-pattern
        if (pattern.sample_count >= self.config.min_samples_for_pattern and
            pattern.success_rate < self.config.anti_pattern_threshold):
            
            pattern.pattern_type = "anti-pattern"
            
            if pattern_key not in self._anti_patterns:
                self._anti_patterns.append(pattern_key)
                
                # Callback
                for callback in self._on_anti_pattern_detected:
                    try:
                        callback(pattern)
                    except Exception as e:
                        logger.error(f"Anti-pattern callback error: {e}")
                
                logger.warning(f"Anti-pattern detected: {pattern_key}")
        
        # Check for success pattern
        elif (pattern.sample_count >= self.config.min_samples_for_pattern and
              pattern.success_rate >= self.config.pattern_confidence_threshold):
            
            pattern.pattern_type = "success"
            
            if pattern_key not in self._success_patterns:
                self._success_patterns.append(pattern_key)
                
                # Callback
                for callback in self._on_pattern_discovered:
                    try:
                        callback(pattern)
                    except Exception as e:
                        logger.error(f"Pattern callback error: {e}")
    
    # ==========================================
    # STRATEGY MANAGEMENT
    # ==========================================
    
    def _update_strategies(self, feedback: CognitiveFeedback) -> None:
        """Met à jour les enregistrements de stratégie."""
        strategy_name = feedback.decision_type
        
        if strategy_name not in self._strategies:
            self._strategies[strategy_name] = StrategyRecord(
                strategy_name=strategy_name,
                description=f"Strategy: {strategy_name}",
            )
        
        self._strategies[strategy_name].record_application(
            success=feedback.is_success,
            tokens=feedback.tokens_used,
            time_ms=feedback.execution_time_ms,
            iterations=feedback.iterations_used,
        )
    
    # ==========================================
    # SUGGESTIONS
    # ==========================================
    
    def suggest_strategy(
        self,
        context: Dict[str, Any],
        decision_type: Optional[str] = None,
    ) -> Optional[StrategyRecord]:
        """
        Suggère la meilleure stratégie pour un contexte.
        
        Args:
            context: Le contexte actuel
            decision_type: Type de décision (optionnel)
            
        Returns:
            La meilleure stratégie ou None
        """
        candidates = []
        
        for strategy in self._strategies.values():
            # Check effectiveness
            if strategy.effectiveness_score < self.config.strategy_recommendation_threshold:
                continue
            
            # Check applicability
            if strategy.total_applications < self.config.min_samples_for_pattern:
                continue
            
            candidates.append(strategy)
        
        # Sort by effectiveness
        candidates.sort(key=lambda s: s.effectiveness_score, reverse=True)
        
        return candidates[0] if candidates else None
    
    def suggest_decision(
        self,
        decision_types: List[str],
        context: Dict[str, Any],
    ) -> Tuple[Optional[str], float]:
        """
        Suggère le meilleur type de décision.
        
        Args:
            decision_types: Types de décision possibles
            context: Le contexte
            
        Returns:
            (decision_type, confidence)
        """
        best_decision = None
        best_score = -1.0
        
        for decision_type in decision_types:
            stats = self._decision_stats.get(decision_type)
            
            if stats and stats["total"] >= self.config.min_samples_for_pattern:
                score = stats["success"] / stats["total"]
                
                # Bonus for positive confidence delta
                if stats["avg_confidence_delta"] > 0:
                    score += 0.1
                
                if score > best_score:
                    best_score = score
                    best_decision = decision_type
        
        return best_decision, best_score
    
    def get_pattern_for_context(
        self,
        context: Dict[str, Any],
    ) -> Optional[PatternRecord]:
        """Récupère le pattern applicable à un contexte."""
        # Find matching pattern
        for pattern_key, pattern in self._patterns.items():
            if self._context_matches(context, pattern.conditions):
                return pattern
        
        return None
    
    def _context_matches(
        self,
        context: Dict[str, Any],
        conditions: Dict[str, Any],
    ) -> bool:
        """Vérifie si un contexte match des conditions."""
        for key, value in conditions.items():
            if key in context:
                if context[key] != value:
                    return False
        return True
    
    # ==========================================
    # CONFIDENCE ADJUSTMENT
    # ==========================================
    
    def adjust_confidence(
        self,
        base_confidence: float,
        decision_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Ajuste la confiance basée sur l'apprentissage.
        
        Args:
            base_confidence: Confiance de base
            decision_type: Type de décision
            context: Contexte optionnel
            
        Returns:
            Confiance ajustée
        """
        stats = self._decision_stats.get(decision_type)
        
        if not stats or stats["total"] < self.config.min_samples_for_pattern:
            return base_confidence
        
        # Calculate adjustment based on historical performance
        success_rate = stats["success"] / stats["total"]
        avg_delta = stats["avg_confidence_delta"]
        
        # Adjustment formula
        adjustment = (success_rate - 0.5) * self.config.confidence_adjustment_rate
        adjustment += avg_delta * self.config.confidence_adjustment_rate
        
        # Apply adjustment
        adjusted = base_confidence + adjustment
        
        # Clamp
        return max(0.1, min(1.0, adjusted))
    
    def get_confidence_calibration_error(self, decision_type: str) -> float:
        """Calcule l'erreur de calibration de confiance."""
        errors = []
        
        for key, actuals in self._confidence_calibration.items():
            if decision_type in key:
                # Extract predicted confidence
                try:
                    predicted = float(key.split("_")[-1])
                    actual = sum(actuals) / len(actuals)
                    errors.append(abs(predicted - actual))
                except (ValueError, IndexError):
                    continue
        
        return sum(errors) / len(errors) if errors else 0.0
    
    # ==========================================
    # ANTI-PATTERN DETECTION
    # ==========================================
    
    def identify_anti_patterns(self) -> List[PatternRecord]:
        """Identifie tous les anti-patterns."""
        return [
            self._patterns[key]
            for key in self._anti_patterns
            if key in self._patterns
        ]
    
    def is_anti_pattern(self, decision_type: str, context: Dict[str, Any]) -> bool:
        """Vérifie si une décision dans un contexte est un anti-pattern."""
        for key in self._anti_patterns:
            pattern = self._patterns.get(key)
            if pattern and decision_type in pattern.pattern_name:
                if self._context_matches(context, pattern.conditions):
                    return True
        return False
    
    # ==========================================
    # QUERY
    # ==========================================
    
    def get_decision_stats(self, decision_type: str) -> Dict[str, Any]:
        """Retourne les stats pour un type de décision."""
        return self._decision_stats.get(decision_type, {"total": 0})
    
    def get_category_stats(self, category: LearningCategory) -> Dict[str, Any]:
        """Retourne les stats pour une catégorie."""
        return self._category_stats.get(category, {"total": 0})
    
    def get_success_patterns(self) -> List[PatternRecord]:
        """Retourne les patterns de succès."""
        return [
            self._patterns[key]
            for key in self._success_patterns
            if key in self._patterns
        ]
    
    def get_failure_patterns(self) -> List[PatternRecord]:
        """Retourne les patterns d'échec."""
        return [
            self._patterns[key]
            for key in self._failure_patterns
            if key in self._patterns
        ]
    
    def get_recent_feedback(self, limit: int = 20) -> List[CognitiveFeedback]:
        """Retourne le feedback récent."""
        return self._feedback_history[-limit:]
    
    def get_feedback_for_decision(
        self,
        decision_type: str,
        limit: int = 10,
    ) -> List[CognitiveFeedback]:
        """Retourne le feedback pour un type de décision."""
        return [
            f for f in self._feedback_history
            if f.decision_type == decision_type
        ][-limit:]
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques globales."""
        success_rate = (
            self._total_success / self._total_outcomes
            if self._total_outcomes > 0 else 0.0
        )
        
        return {
            "total_outcomes": self._total_outcomes,
            "total_success": self._total_success,
            "total_failure": self._total_failure,
            "overall_success_rate": success_rate,
            "patterns_discovered": len(self._patterns),
            "success_patterns": len(self._success_patterns),
            "anti_patterns": len(self._anti_patterns),
            "strategies_tracked": len(self._strategies),
            "decision_types_tracked": len(self._decision_stats),
        }
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'apprentissage."""
        # Top strategies
        top_strategies = sorted(
            self._strategies.values(),
            key=lambda s: s.effectiveness_score,
            reverse=True
        )[:5]
        
        # Worst decisions
        worst_decisions = sorted(
            [
                (dt, stats)
                for dt, stats in self._decision_stats.items()
                if stats["total"] >= self.config.min_samples_for_pattern
            ],
            key=lambda x: x[1]["success"] / x[1]["total"]
        )[:5]
        
        return {
            "overall_stats": self.get_overall_stats(),
            "top_strategies": [s.to_dict() for s in top_strategies],
            "worst_decisions": [
                {"decision_type": dt, **stats}
                for dt, stats in worst_decisions
            ],
            "anti_pattern_count": len(self._anti_patterns),
        }
    
    # ==========================================
    # CLEAR
    # ==========================================
    
    def clear_history(self) -> None:
        """Efface l'historique."""
        self._feedback_history.clear()
        logger.info("Learning history cleared")
    
    def reset(self) -> None:
        """Réinitialise tout."""
        self._feedback_history.clear()
        self._patterns.clear()
        self._success_patterns.clear()
        self._failure_patterns.clear()
        self._anti_patterns.clear()
        self._strategies.clear()
        self._category_stats.clear()
        self._decision_stats.clear()
        self._confidence_calibration.clear()
        
        self._total_outcomes = 0
        self._total_success = 0
        self._total_failure = 0
        
        logger.info("LearningLoop reset")
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_pattern_discovered(
        self,
        callback: Callable[[PatternRecord], None]
    ) -> None:
        """Callback pour découverte de pattern."""
        self._on_pattern_discovered.append(callback)
    
    def on_anti_pattern_detected(
        self,
        callback: Callable[[PatternRecord], None]
    ) -> None:
        """Callback pour détection d'anti-pattern."""
        self._on_anti_pattern_detected.append(callback)


# ==========================================
# FACTORY
# ==========================================

def create_learning_loop(config: Optional[LearningConfig] = None) -> LearningLoop:
    """Factory pour créer un LearningLoop."""
    return LearningLoop(config=config)
