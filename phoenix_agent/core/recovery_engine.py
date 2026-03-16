"""
Phoenix Agent - Recovery Engine
===============================

Moteur de récupération et gestion des échecs.

Sans RecoveryEngine:
    - Un agent échoue = système fragile
    - Pas de récupération automatique
    - Pas de dégradation gracieuse

Avec RecoveryEngine:
    - Récupération automatique sur erreur
    - Stratégies de fallback
    - Dégradation gracieuse
    - Retry intelligent

Architecture:
    AgentLoop → Error → RecoveryEngine → RecoveryStrategy → Continue/Delegate/Abort

STRATÉGIES:
    - RETRY: Réessayer avec ajustement
    - FALLBACK_AGENT: Utiliser un agent de fallback
    - REDUCE_SCOPE: Réduire la portée de la tâche
    - DECOMPOSE: Décomposer en sous-tâches
    - ESCALATE: Escalader à un agent superviseur
    - ABORT: Abandonner proprement

Version: 0.6.0 (Failure Recovery System)
"""

from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
import asyncio


logger = logging.getLogger("phoenix.recovery")


# ==========================================
# ERROR TYPE
# ==========================================

class ErrorType(str, Enum):
    """Types d'erreurs récupérables."""
    # LLM errors
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_CONTEXT_TOO_LONG = "llm_context_too_long"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    LLM_API_ERROR = "llm_api_error"
    
    # Agent errors
    AGENT_MAX_ITERATIONS = "agent_max_iterations"
    AGENT_LOW_CONFIDENCE = "agent_low_confidence"
    AGENT_MEMORY_OVERFLOW = "agent_memory_overflow"
    AGENT_COGNITIVE_FATIGUE = "agent_cognitive_fatigue"
    AGENT_STUCK = "agent_stuck"
    
    # Delegation errors
    DELEGATION_FAILED = "delegation_failed"
    DELEGATION_TIMEOUT = "delegation_timeout"
    NO_AVAILABLE_AGENT = "no_available_agent"
    DELEGATION_DEPTH_EXCEEDED = "delegation_depth_exceeded"
    
    # Task errors
    TASK_TOO_COMPLEX = "task_too_complex"
    TASK_INVALID = "task_invalid"
    TASK_TIMEOUT = "task_timeout"
    
    # System errors
    INTERNAL_ERROR = "internal_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


# ==========================================
# RECOVERY STRATEGY
# ==========================================

class RecoveryStrategy(str, Enum):
    """Stratégies de récupération."""
    # Retry strategies
    RETRY_IMMEDIATE = "retry_immediate"           # Réessayer tout de suite
    RETRY_WITH_BACKOFF = "retry_with_backoff"     # Réessayer avec délai
    RETRY_WITH_ADJUSTMENT = "retry_with_adjustment"  # Réessayer avec ajustements
    
    # Agent strategies
    FALLBACK_AGENT = "fallback_agent"             # Utiliser agent de fallback
    ESCALATE = "escalate"                         # Escalader au superviseur
    DELEGATE_DIFFERENT = "delegate_different"     # Déléguer à un autre agent
    
    # Task strategies
    REDUCE_SCOPE = "reduce_scope"                 # Réduire la portée
    DECOMPOSE_TASK = "decompose_task"             # Décomposer la tâche
    SIMPLIFY_TASK = "simplify_task"               # Simplifier la tâche
    
    # Memory strategies
    COMPRESS_MEMORY = "compress_memory"           # Compresser la mémoire
    RESET_CONTEXT = "reset_context"               # Réinitialiser le contexte
    
    # Terminal strategies
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Dégradation gracieuse
    PARTIAL_RESULT = "partial_result"              # Retourner résultat partiel
    ABORT = "abort"                               # Abandonner


# ==========================================
# ERROR CONTEXT
# ==========================================

@dataclass
class ErrorContext:
    """
    Contexte d'une erreur.
    
    Capture toutes les informations nécessaires pour la récupération.
    """
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: ErrorType = ErrorType.UNKNOWN
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    session_id: str = ""
    
    # State at error
    iteration: int = 0
    tokens_used: int = 0
    confidence: float = 1.0
    
    # History
    previous_errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    
    # Recoverable?
    recoverable: bool = True
    recovery_hint: str = ""
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_retryable(self) -> bool:
        """L'erreur est retentable."""
        return self.error_type in [
            ErrorType.LLM_TIMEOUT,
            ErrorType.LLM_RATE_LIMIT,
            ErrorType.LLM_API_ERROR,
            ErrorType.DELEGATION_TIMEOUT,
        ]
    
    @property
    def is_delegable(self) -> bool:
        """L'erreur peut être résolue par délégation."""
        return self.error_type in [
            ErrorType.AGENT_LOW_CONFIDENCE,
            ErrorType.AGENT_COGNITIVE_FATIGUE,
            ErrorType.TASK_TOO_COMPLEX,
            ErrorType.AGENT_STUCK,
        ]
    
    @property
    def requires_memory_action(self) -> bool:
        """Nécessite une action sur la mémoire."""
        return self.error_type in [
            ErrorType.LLM_CONTEXT_TOO_LONG,
            ErrorType.AGENT_MEMORY_OVERFLOW,
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "recoverable": self.recoverable,
            "retry_count": self.retry_count,
        }


# ==========================================
# RECOVERY RESULT
# ==========================================

@dataclass
class RecoveryResult:
    """Résultat d'une tentative de récupération."""
    success: bool
    strategy: RecoveryStrategy
    
    # Next action
    action: str = ""  # "continue", "retry", "delegate", "abort"
    
    # Context
    error_context: Optional[ErrorContext] = None
    
    # Adjustments
    adjustments: Dict[str, Any] = field(default_factory=dict)
    
    # Fallback info
    fallback_agent_id: Optional[str] = None
    decomposed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Message
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy.value,
            "action": self.action,
            "message": self.message,
            "fallback_agent_id": self.fallback_agent_id,
        }


# ==========================================
# RECOVERY RULE
# ==========================================

@dataclass
class RecoveryRule:
    """
    Règle de récupération.
    
    Format: IF error_type IN [types] THEN strategy
    """
    name: str
    error_types: List[ErrorType]
    strategy: RecoveryStrategy
    
    # Condition additionnelle
    condition: Optional[Callable[[ErrorContext], bool]] = None
    
    # Priorité
    priority: int = 0
    
    # Paramètres
    params: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, error: ErrorContext) -> bool:
        """Vérifie si la règle s'applique."""
        if error.error_type not in self.error_types:
            return False
        if self.condition and not self.condition(error):
            return False
        return True


# ==========================================
# RECOVERY ENGINE
# ==========================================

class RecoveryEngine:
    """
    Moteur de récupération pour Phoenix.
    
    C'est LE composant qui garantit que le runtime ne s'arrête jamais
    sur une erreur, mais s'adapte.
    
    Responsabilités:
        - Classifier les erreurs
        - Choisir la stratégie de récupération
        - Exécuter la récupération
        - Tracker l'historique des erreurs
    
    Architecture:
        AgentLoop
            │
            ├── error occurs
            │
            └── RecoveryEngine.recover(error)
                    │
                    ├── classify_error()
                    ├── select_strategy()
                    └── execute_strategy()
                            │
                            ├── retry_with_backoff()
                            ├── fallback_agent()
                            ├── reduce_scope()
                            ├── decompose_task()
                            └── escalate()
    
    Example:
        engine = RecoveryEngine()
        
        # Enregistrer des handlers
        engine.register_handler(RecoveryStrategy.FALLBACK_AGENT, my_fallback_handler)
        
        # Dans l'agent loop
        try:
            result = await execute_task()
        except Exception as e:
            error_ctx = engine.create_error_context(e, agent_id, task_id)
            recovery = await engine.recover(error_ctx)
            
            if recovery.action == "retry":
                continue
            elif recovery.action == "delegate":
                await delegate(recovery.fallback_agent_id)
            else:
                abort()
    """
    
    # ==========================================
    # DEFAULT RULES
    # ==========================================
    
    DEFAULT_RULES: List[RecoveryRule] = [
        # LLM Errors
        RecoveryRule(
            name="llm_timeout_retry",
            error_types=[ErrorType.LLM_TIMEOUT],
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            priority=100,
            params={"max_retries": 3, "backoff_base": 2.0}
        ),
        RecoveryRule(
            name="llm_rate_limit_backoff",
            error_types=[ErrorType.LLM_RATE_LIMIT],
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            priority=100,
            params={"max_retries": 5, "backoff_base": 3.0}
        ),
        RecoveryRule(
            name="llm_context_compress",
            error_types=[ErrorType.LLM_CONTEXT_TOO_LONG],
            strategy=RecoveryStrategy.COMPRESS_MEMORY,
            priority=90,
        ),
        
        # Agent Errors
        RecoveryRule(
            name="agent_iterations_delegate",
            error_types=[ErrorType.AGENT_MAX_ITERATIONS],
            strategy=RecoveryStrategy.DELEGATE_DIFFERENT,
            priority=80,
        ),
        RecoveryRule(
            name="agent_confidence_specialist",
            error_types=[ErrorType.AGENT_LOW_CONFIDENCE],
            strategy=RecoveryStrategy.FALLBACK_AGENT,
            priority=80,
        ),
        RecoveryRule(
            name="agent_memory_compress",
            error_types=[ErrorType.AGENT_MEMORY_OVERFLOW],
            strategy=RecoveryStrategy.COMPRESS_MEMORY,
            priority=90,
        ),
        RecoveryRule(
            name="agent_fatigue_fresh",
            error_types=[ErrorType.AGENT_COGNITIVE_FATIGUE],
            strategy=RecoveryStrategy.FALLBACK_AGENT,
            priority=70,
        ),
        RecoveryRule(
            name="agent_stuck_decompose",
            error_types=[ErrorType.AGENT_STUCK],
            strategy=RecoveryStrategy.DECOMPOSE_TASK,
            priority=60,
        ),
        
        # Delegation Errors
        RecoveryRule(
            name="delegation_failed_different",
            error_types=[ErrorType.DELEGATION_FAILED, ErrorType.DELEGATION_TIMEOUT],
            strategy=RecoveryStrategy.DELEGATE_DIFFERENT,
            priority=70,
        ),
        RecoveryRule(
            name="no_agent_reduce",
            error_types=[ErrorType.NO_AVAILABLE_AGENT],
            strategy=RecoveryStrategy.REDUCE_SCOPE,
            priority=60,
        ),
        RecoveryRule(
            name="depth_exceeded_escalate",
            error_types=[ErrorType.DELEGATION_DEPTH_EXCEEDED],
            strategy=RecoveryStrategy.ESCALATE,
            priority=80,
        ),
        
        # Task Errors
        RecoveryRule(
            name="task_complex_decompose",
            error_types=[ErrorType.TASK_TOO_COMPLEX],
            strategy=RecoveryStrategy.DECOMPOSE_TASK,
            priority=70,
        ),
        RecoveryRule(
            name="task_invalid_abort",
            error_types=[ErrorType.TASK_INVALID],
            strategy=RecoveryStrategy.ABORT,
            priority=100,
        ),
        
        # Fallback
        RecoveryRule(
            name="unknown_graceful",
            error_types=[ErrorType.UNKNOWN, ErrorType.INTERNAL_ERROR],
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            priority=10,
        ),
    ]
    
    def __init__(
        self,
        max_retry_attempts: int = 3,
        max_escalation_level: int = 3,
    ):
        self.max_retry_attempts = max_retry_attempts
        self.max_escalation_level = max_escalation_level
        
        # Règles
        self._rules: List[RecoveryRule] = self.DEFAULT_RULES.copy()
        
        # Handlers
        self._handlers: Dict[RecoveryStrategy, Callable] = {}
        
        # Historique
        self._error_history: List[ErrorContext] = []
        self._recovery_history: List[RecoveryResult] = []
        
        # Stats
        self._total_errors = 0
        self._successful_recoveries = 0
    
    # ==========================================
    # ERROR CREATION
    # ==========================================
    
    def create_error_context(
        self,
        error: Exception,
        error_type: Optional[ErrorType] = None,
        agent_id: str = "",
        task_id: str = "",
        session_id: str = "",
        iteration: int = 0,
        tokens_used: int = 0,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ErrorContext:
        """
        Crée un contexte d'erreur depuis une exception.
        
        Args:
            error: L'exception
            error_type: Type d'erreur (auto-détecté si None)
            agent_id: ID de l'agent
            task_id: ID de la tâche
            session_id: ID de la session
            iteration: Itération courante
            tokens_used: Tokens utilisés
            confidence: Confiance courante
            metadata: Métadonnées additionnelles
            
        Returns:
            ErrorContext
        """
        # Auto-détection du type
        if error_type is None:
            error_type = self._classify_error(error)
        
        context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            agent_id=agent_id,
            task_id=task_id,
            session_id=session_id,
            iteration=iteration,
            tokens_used=tokens_used,
            confidence=confidence,
            metadata=metadata or {},
        )
        
        # Vérifier récupérabilité
        context.recoverable = self._is_recoverable(error_type)
        context.recovery_hint = self._get_recovery_hint(error_type)
        
        return context
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classifie une erreur automatiquement."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return ErrorType.LLM_TIMEOUT
        elif "rate limit" in error_str or "429" in error_str:
            return ErrorType.LLM_RATE_LIMIT
        elif "context" in error_str and ("long" in error_str or "length" in error_str):
            return ErrorType.LLM_CONTEXT_TOO_LONG
        elif "api" in error_str or "connection" in error_str:
            return ErrorType.LLM_API_ERROR
        elif "max iterations" in error_str:
            return ErrorType.AGENT_MAX_ITERATIONS
        elif "memory" in error_str or "overflow" in error_str:
            return ErrorType.AGENT_MEMORY_OVERFLOW
        elif "delegation" in error_str:
            if "timeout" in error_str:
                return ErrorType.DELEGATION_TIMEOUT
            return ErrorType.DELEGATION_FAILED
        else:
            return ErrorType.UNKNOWN
    
    def _is_recoverable(self, error_type: ErrorType) -> bool:
        """Vérifie si une erreur est récupérable."""
        non_recoverable = {
            ErrorType.TASK_INVALID,
        }
        return error_type not in non_recoverable
    
    def _get_recovery_hint(self, error_type: ErrorType) -> str:
        """Retourne un indice de récupération."""
        hints = {
            ErrorType.LLM_TIMEOUT: "Retry with exponential backoff",
            ErrorType.LLM_RATE_LIMIT: "Wait and retry",
            ErrorType.LLM_CONTEXT_TOO_LONG: "Compress or summarize context",
            ErrorType.AGENT_MAX_ITERATIONS: "Delegate remaining work",
            ErrorType.AGENT_LOW_CONFIDENCE: "Delegate to specialist",
            ErrorType.AGENT_MEMORY_OVERFLOW: "Compress memory or delegate",
            ErrorType.DELEGATION_FAILED: "Try different agent or reduce scope",
        }
        return hints.get(error_type, "Attempt recovery with default strategy")
    
    # ==========================================
    # MAIN RECOVERY
    # ==========================================
    
    async def recover(
        self,
        error: ErrorContext,
        context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResult:
        """
        Tente de récupérer d'une erreur.
        
        C'est LA méthode centrale du RecoveryEngine.
        
        Args:
            error: Le contexte d'erreur
            context: Contexte additionnel
            
        Returns:
            RecoveryResult avec la stratégie à appliquer
        """
        self._total_errors += 1
        self._error_history.append(error)
        
        logger.warning(
            f"Recovery triggered: {error.error_type.value} - {error.error_message[:100]}"
        )
        
        # Vérifier si récupérable
        if not error.recoverable:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ABORT,
                action="abort",
                error_context=error,
                message="Error is not recoverable",
            )
        
        # Vérifier nombre de retry
        if error.retry_count >= self.max_retry_attempts:
            logger.info(f"Max retry attempts ({self.max_retry_attempts}) reached")
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                action="degrade",
                error_context=error,
                message="Max retry attempts reached, degrading gracefully",
            )
        
        # Sélectionner la stratégie
        strategy = self._select_strategy(error)
        
        # Exécuter la stratégie
        result = await self._execute_strategy(strategy, error, context or {})
        
        if result.success:
            self._successful_recoveries += 1
        
        self._recovery_history.append(result)
        
        return result
    
    def _select_strategy(self, error: ErrorContext) -> RecoveryStrategy:
        """Sélectionne la meilleure stratégie pour une erreur."""
        # Trier par priorité
        sorted_rules = sorted(self._rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if rule.matches(error):
                logger.info(f"Selected strategy: {rule.strategy.value} (rule: {rule.name})")
                return rule.strategy
        
        # Fallback
        return RecoveryStrategy.GRACEFUL_DEGRADATION
    
    async def _execute_strategy(
        self,
        strategy: RecoveryStrategy,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Exécute une stratégie de récupération."""
        
        # Vérifier s'il y a un handler enregistré
        if strategy in self._handlers:
            handler = self._handlers[strategy]
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(error, context)
                else:
                    return handler(error, context)
            except Exception as e:
                logger.error(f"Recovery handler failed: {e}")
                return RecoveryResult(
                    success=False,
                    strategy=strategy,
                    action="abort",
                    error_context=error,
                    message=f"Recovery handler failed: {e}",
                )
        
        # Stratégies par défaut
        if strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            return self._retry_immediate(error)
        
        elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            return await self._retry_with_backoff(error)
        
        elif strategy == RecoveryStrategy.FALLBACK_AGENT:
            return self._fallback_agent(error, context)
        
        elif strategy == RecoveryStrategy.REDUCE_SCOPE:
            return self._reduce_scope(error, context)
        
        elif strategy == RecoveryStrategy.DECOMPOSE_TASK:
            return self._decompose_task(error, context)
        
        elif strategy == RecoveryStrategy.COMPRESS_MEMORY:
            return self._compress_memory(error, context)
        
        elif strategy == RecoveryStrategy.ESCALATE:
            return self._escalate(error, context)
        
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._graceful_degradation(error)
        
        elif strategy == RecoveryStrategy.ABORT:
            return RecoveryResult(
                success=False,
                strategy=strategy,
                action="abort",
                error_context=error,
                message="Recovery aborted",
            )
        
        else:
            return self._graceful_degradation(error)
    
    # ==========================================
    # BUILT-IN STRATEGIES
    # ==========================================
    
    def _retry_immediate(self, error: ErrorContext) -> RecoveryResult:
        """Retry immédiat."""
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.RETRY_IMMEDIATE,
            action="retry",
            error_context=error,
            message="Retrying immediately",
            adjustments={"retry_count": error.retry_count + 1},
        )
    
    async def _retry_with_backoff(self, error: ErrorContext) -> RecoveryResult:
        """Retry avec backoff exponentiel."""
        backoff_base = 2.0
        delay = backoff_base ** error.retry_count
        
        logger.info(f"Waiting {delay}s before retry (attempt {error.retry_count + 1})")
        await asyncio.sleep(delay)
        
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            action="retry",
            error_context=error,
            message=f"Retrying after {delay}s backoff",
            adjustments={
                "retry_count": error.retry_count + 1,
                "backoff_delay": delay,
            },
        )
    
    def _fallback_agent(
        self,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Utilise un agent de fallback."""
        # Chercher un agent de fallback
        fallback_agent = context.get("fallback_agent")
        available_agents = context.get("available_agents", [])
        
        if fallback_agent:
            return RecoveryResult(
                success=True,
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                action="delegate",
                error_context=error,
                fallback_agent_id=fallback_agent,
                message=f"Using fallback agent: {fallback_agent}",
            )
        
        if available_agents:
            # Prendre le premier disponible
            agent = available_agents[0]
            return RecoveryResult(
                success=True,
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                action="delegate",
                error_context=error,
                fallback_agent_id=agent,
                message=f"Using available agent: {agent}",
            )
        
        return RecoveryResult(
            success=False,
            strategy=RecoveryStrategy.FALLBACK_AGENT,
            action="reduce",
            error_context=error,
            message="No fallback agent available, reducing scope",
        )
    
    def _reduce_scope(
        self,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Réduit la portée de la tâche."""
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.REDUCE_SCOPE,
            action="continue",
            error_context=error,
            message="Reducing task scope to essential parts",
            adjustments={
                "reduced_scope": True,
                "skip_optional": True,
            },
        )
    
    def _decompose_task(
        self,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Décompose la tâche."""
        # v0.6: Décomposition simple
        # v1.0: Appel TaskManager
        
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.DECOMPOSE_TASK,
            action="delegate",
            error_context=error,
            message="Task decomposed into subtasks",
            decomposed_tasks=[
                {"subtask_id": f"{error.task_id}-1", "goal": "Part 1"},
                {"subtask_id": f"{error.task_id}-2", "goal": "Part 2"},
            ],
        )
    
    def _compress_memory(
        self,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Comprime la mémoire."""
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.COMPRESS_MEMORY,
            action="continue",
            error_context=error,
            message="Memory compression triggered",
            adjustments={
                "compress_memory": True,
                "compression_ratio": 0.6,
            },
        )
    
    def _escalate(
        self,
        error: ErrorContext,
        context: Dict[str, Any],
    ) -> RecoveryResult:
        """Escalade au superviseur."""
        supervisor_id = context.get("supervisor_agent", "supervisor")
        
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.ESCALATE,
            action="delegate",
            error_context=error,
            fallback_agent_id=supervisor_id,
            message=f"Escalating to supervisor: {supervisor_id}",
        )
    
    def _graceful_degradation(self, error: ErrorContext) -> RecoveryResult:
        """Dégradation gracieuse."""
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            action="degrade",
            error_context=error,
            message="Degrading gracefully with partial results",
            adjustments={
                "partial_result": True,
                "degraded_quality": True,
            },
        )
    
    # ==========================================
    # RULE MANAGEMENT
    # ==========================================
    
    def add_rule(self, rule: RecoveryRule) -> None:
        """Ajoute une règle de récupération."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, name: str) -> bool:
        """Supprime une règle."""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                return True
        return False
    
    # ==========================================
    # HANDLER REGISTRATION
    # ==========================================
    
    def register_handler(
        self,
        strategy: RecoveryStrategy,
        handler: Callable[[ErrorContext, Dict[str, Any]], RecoveryResult],
    ) -> None:
        """Enregistre un handler pour une stratégie."""
        self._handlers[strategy] = handler
        logger.info(f"Registered recovery handler for {strategy.value}")
    
    def unregister_handler(self, strategy: RecoveryStrategy) -> bool:
        """Désenregistre un handler."""
        if strategy in self._handlers:
            del self._handlers[strategy]
            return True
        return False
    
    # ==========================================
    # HISTORY & STATS
    # ==========================================
    
    def get_error_history(self, limit: int = 10) -> List[ErrorContext]:
        """Retourne l'historique des erreurs."""
        return self._error_history[-limit:]
    
    def get_recovery_history(self, limit: int = 10) -> List[RecoveryResult]:
        """Retourne l'historique des récupérations."""
        return self._recovery_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        if self._total_errors == 0:
            return {
                "total_errors": 0,
                "successful_recoveries": 0,
            }
        
        # Compter par type d'erreur
        error_counts: Dict[str, int] = {}
        for error in self._error_history:
            key = error.error_type.value
            error_counts[key] = error_counts.get(key, 0) + 1
        
        # Compter par stratégie
        strategy_counts: Dict[str, int] = {}
        for result in self._recovery_history:
            key = result.strategy.value
            strategy_counts[key] = strategy_counts.get(key, 0) + 1
        
        return {
            "total_errors": self._total_errors,
            "successful_recoveries": self._successful_recoveries,
            "recovery_rate": self._successful_recoveries / self._total_errors,
            "error_types": error_counts,
            "strategy_usage": strategy_counts,
        }
    
    def clear_history(self) -> None:
        """Efface l'historique."""
        self._error_history.clear()
        self._recovery_history.clear()


# ==========================================
# FACTORY
# ==========================================

def create_recovery_engine(
    max_retry_attempts: int = 3,
    max_escalation_level: int = 3,
) -> RecoveryEngine:
    """Factory pour créer un moteur de récupération."""
    return RecoveryEngine(
        max_retry_attempts=max_retry_attempts,
        max_escalation_level=max_escalation_level,
    )
