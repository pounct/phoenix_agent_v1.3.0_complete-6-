"""
Phoenix Agent - Agent State Machine
====================================

Machine d'états pour contrôler les transitions d'exécution des agents.

Sans une machine d'états explicite:
    - Race conditions possibles
    - Boucles infinies
    - États morts (dead states)
    - Impossible de debugger

Avec cette machine d'états:
    - Transitions contrôlées
    - Prévention des états invalides
    - Traçabilité complète
    - Récupération sur erreur

Architecture:
    AgentLoop → AgentStateMachine → State Transitions → Actions

ÉTATS:
    IDLE: En attente
    THINKING: Analyse en cours
    ACTING: Appel LLM en cours
    DELEGATING: Délégation en cours
    WAITING_RESULTS: Attente de résultats de sub-agents
    SYNTHESIZING: Fusion des résultats
    COMPLETED: Terminé avec succès
    FAILED: Échec
    RECOVERING: Récupération après erreur

Version: 0.6.0 (Runtime State Control)
"""

from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid


logger = logging.getLogger("phoenix.state_machine")


# ==========================================
# AGENT EXECUTION STATE
# ==========================================

class AgentExecutionState(str, Enum):
    """
    États d'exécution d'un agent.
    
    Ces états représentent le cycle de vie complet d'une exécution.
    """
    # Initial states
    IDLE = "idle"                          # En attente, prêt à démarrer
    INITIALIZING = "initializing"          # Initialisation en cours
    
    # Active states
    THINKING = "thinking"                  # Phase Think (analyse)
    ACTING = "acting"                      # Phase Act (appel LLM)
    OBSERVING = "observing"                # Phase Observe (analyse réponse)
    
    # Delegation states
    DELEGATING = "delegating"              # Délégation en cours
    WAITING_RESULTS = "waiting_results"    # Attente de résultats
    RECEIVING_RESULTS = "receiving_results"  # Réception des résultats
    
    # Synthesis states
    SYNTHESIZING = "synthesizing"          # Fusion des résultats
    
    # Terminal states
    COMPLETED = "completed"                # Succès
    FAILED = "failed"                      # Échec
    ABORTED = "aborted"                    # Annulé
    
    # Recovery states
    RECOVERING = "recovering"              # Récupération après erreur
    RETRYING = "retrying"                  # Nouvelle tentative
    
    # Special states
    PAUSED = "paused"                      # En pause
    SUSPENDED = "suspended"                # Suspendu (attente externe)


# ==========================================
# STATE CATEGORY
# ==========================================

class StateCategory(str, Enum):
    """Catégories d'états."""
    INITIAL = "initial"       # États initiaux
    ACTIVE = "active"         # États actifs (travail en cours)
    WAITING = "waiting"       # États d'attente
    TERMINAL = "terminal"     # États terminaux
    RECOVERY = "recovery"     # États de récupération


def get_state_category(state: AgentExecutionState) -> StateCategory:
    """Retourne la catégorie d'un état."""
    if state in [AgentExecutionState.IDLE, AgentExecutionState.INITIALIZING]:
        return StateCategory.INITIAL
    elif state in [
        AgentExecutionState.THINKING,
        AgentExecutionState.ACTING,
        AgentExecutionState.OBSERVING,
        AgentExecutionState.SYNTHESIZING,
    ]:
        return StateCategory.ACTIVE
    elif state in [
        AgentExecutionState.DELEGATING,
        AgentExecutionState.WAITING_RESULTS,
        AgentExecutionState.RECEIVING_RESULTS,
        AgentExecutionState.PAUSED,
        AgentExecutionState.SUSPENDED,
    ]:
        return StateCategory.WAITING
    elif state in [
        AgentExecutionState.COMPLETED,
        AgentExecutionState.FAILED,
        AgentExecutionState.ABORTED,
    ]:
        return StateCategory.TERMINAL
    elif state in [
        AgentExecutionState.RECOVERING,
        AgentExecutionState.RETRYING,
    ]:
        return StateCategory.RECOVERY
    return StateCategory.ACTIVE


# ==========================================
# STATE TRANSITION
# ==========================================

@dataclass
class StateTransition:
    """
    Représente une transition entre états.
    
    Capture le changement d'état avec contexte.
    """
    from_state: AgentExecutionState
    to_state: AgentExecutionState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Contexte
    reason: str = ""
    trigger: str = ""  # manual, auto, error, timeout
    
    # Métadonnées
    duration_in_previous_state_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_terminal_transition(self) -> bool:
        """La transition mène à un état terminal."""
        return get_state_category(self.to_state) == StateCategory.TERMINAL


# ==========================================
# TRANSITION RULE
# ==========================================

@dataclass
class TransitionRule:
    """
    Règle de transition.
    
    Définit QUAND une transition est autorisée.
    """
    from_state: AgentExecutionState
    to_state: AgentExecutionState
    
    # Condition optionnelle
    condition: Optional[Callable[[], bool]] = None
    
    # Action à exécuter lors de la transition
    on_transition: Optional[Callable[[], None]] = None
    
    # Validation avant transition
    validator: Optional[Callable[[], bool]] = None
    
    # Métadonnées
    name: str = ""
    description: str = ""
    
    def is_valid(self) -> bool:
        """Vérifie si la transition est valide."""
        if self.validator:
            return self.validator()
        if self.condition:
            return self.condition()
        return True


# ==========================================
# AGENT STATE MACHINE
# ==========================================

class AgentStateMachine:
    """
    Machine d'états pour le contrôle d'exécution des agents.
    
    C'est LE composant qui garantit la stabilité du runtime.
    
    Responsabilités:
        - Contrôler les transitions d'état
        - Prévenir les états invalides
        - Tracer l'historique des transitions
        - Exécuter des actions sur transition
        - Permettre la récupération sur erreur
    
    Architecture:
        AgentLoop
            │
            ├── state_machine.current_state
            │
            ├── state_machine.transition(NEW_STATE)
            │       │
            │       ├── Validate transition
            │       ├── Execute pre-actions
            │       ├── Change state
            │       ├── Execute post-actions
            │       └── Log transition
            │
            └── Continue execution
    
    Example:
        state_machine = AgentStateMachine()
        
        # Démarrer
        state_machine.start()
        
        # Transitions
        state_machine.transition(AgentExecutionState.THINKING)
        state_machine.transition(AgentExecutionState.ACTING)
        state_machine.transition(AgentExecutionState.OBSERVING)
        
        # Terminal
        state_machine.complete()
        
        # Check
        if state_machine.is_terminal:
            print("Execution finished")
    """
    
    # ==========================================
    # TRANSITIONS AUTORISÉES PAR DÉFAUT
    # ==========================================
    
    DEFAULT_ALLOWED_TRANSITIONS: Dict[AgentExecutionState, Set[AgentExecutionState]] = {
        AgentExecutionState.IDLE: {
            AgentExecutionState.INITIALIZING,
        },
        AgentExecutionState.INITIALIZING: {
            AgentExecutionState.THINKING,
            AgentExecutionState.FAILED,
        },
        AgentExecutionState.THINKING: {
            AgentExecutionState.ACTING,
            AgentExecutionState.DELEGATING,
            AgentExecutionState.COMPLETED,
            AgentExecutionState.FAILED,
            AgentExecutionState.PAUSED,
        },
        AgentExecutionState.ACTING: {
            AgentExecutionState.OBSERVING,
            AgentExecutionState.FAILED,
            AgentExecutionState.RECOVERING,
        },
        AgentExecutionState.OBSERVING: {
            AgentExecutionState.THINKING,
            AgentExecutionState.ACTING,
            AgentExecutionState.DELEGATING,
            AgentExecutionState.SYNTHESIZING,
            AgentExecutionState.COMPLETED,
            AgentExecutionState.FAILED,
            AgentExecutionState.RETRYING,
        },
        AgentExecutionState.DELEGATING: {
            AgentExecutionState.WAITING_RESULTS,
            AgentExecutionState.FAILED,
            AgentExecutionState.RECOVERING,
        },
        AgentExecutionState.WAITING_RESULTS: {
            AgentExecutionState.RECEIVING_RESULTS,
            AgentExecutionState.FAILED,
            AgentExecutionState.RECOVERING,
            AgentExecutionState.SUSPENDED,
        },
        AgentExecutionState.RECEIVING_RESULTS: {
            AgentExecutionState.SYNTHESIZING,
            AgentExecutionState.THINKING,
            AgentExecutionState.FAILED,
        },
        AgentExecutionState.SYNTHESIZING: {
            AgentExecutionState.COMPLETED,
            AgentExecutionState.FAILED,
            AgentExecutionState.RECOVERING,
        },
        AgentExecutionState.COMPLETED: set(),  # Terminal
        AgentExecutionState.FAILED: {
            AgentExecutionState.RECOVERING,
            AgentExecutionState.RETRYING,
            AgentExecutionState.ABORTED,
        },
        AgentExecutionState.ABORTED: set(),  # Terminal
        AgentExecutionState.RECOVERING: {
            AgentExecutionState.THINKING,
            AgentExecutionState.DELEGATING,
            AgentExecutionState.FAILED,
            AgentExecutionState.ABORTED,
        },
        AgentExecutionState.RETRYING: {
            AgentExecutionState.THINKING,
            AgentExecutionState.FAILED,
        },
        AgentExecutionState.PAUSED: {
            AgentExecutionState.THINKING,
            AgentExecutionState.ABORTED,
        },
        AgentExecutionState.SUSPENDED: {
            AgentExecutionState.WAITING_RESULTS,
            AgentExecutionState.ABORTED,
        },
    }
    
    def __init__(
        self,
        initial_state: AgentExecutionState = AgentExecutionState.IDLE,
        state_machine_id: Optional[str] = None,
    ):
        """
        Initialise la machine d'états.
        
        Args:
            initial_state: État initial
            state_machine_id: ID unique (auto-généré si None)
        """
        self.state_machine_id = state_machine_id or str(uuid.uuid4())
        self._current_state = initial_state
        self._previous_state: Optional[AgentExecutionState] = None
        
        # Transitions autorisées (peut être étendu)
        self._allowed_transitions = self.DEFAULT_ALLOWED_TRANSITIONS.copy()
        
        # Historique des transitions
        self._transition_history: List[StateTransition] = []
        
        # Règles de transition personnalisées
        self._custom_rules: Dict[str, TransitionRule] = {}
        
        # Callbacks
        self._on_state_change_callbacks: List[Callable[[AgentExecutionState, AgentExecutionState], None]] = []
        self._on_terminal_callbacks: List[Callable[[AgentExecutionState], None]] = []
        
        # Timing
        self._state_entered_at: datetime = datetime.utcnow()
        self._total_runtime_ms: float = 0.0
        
        # Compteurs
        self._transition_count: int = 0
        self._error_count: int = 0
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    
    @property
    def current_state(self) -> AgentExecutionState:
        """État actuel."""
        return self._current_state
    
    @property
    def previous_state(self) -> Optional[AgentExecutionState]:
        """État précédent."""
        return self._previous_state
    
    @property
    def is_terminal(self) -> bool:
        """L'état actuel est terminal."""
        return get_state_category(self._current_state) == StateCategory.TERMINAL
    
    @property
    def is_active(self) -> bool:
        """L'agent est en cours d'exécution active."""
        return get_state_category(self._current_state) in [
            StateCategory.ACTIVE,
            StateCategory.WAITING,
            StateCategory.RECOVERY,
        ]
    
    @property
    def is_recovering(self) -> bool:
        """L'agent est en récupération."""
        return get_state_category(self._current_state) == StateCategory.RECOVERY
    
    @property
    def state_category(self) -> StateCategory:
        """Catégorie de l'état actuel."""
        return get_state_category(self._current_state)
    
    @property
    def transition_count(self) -> int:
        """Nombre de transitions effectuées."""
        return self._transition_count
    
    @property
    def time_in_current_state_ms(self) -> float:
        """Temps passé dans l'état actuel."""
        return (datetime.utcnow() - self._state_entered_at).total_seconds() * 1000
    
    # ==========================================
    # TRANSITION CHECKS
    # ==========================================
    
    def can_transition_to(self, target_state: AgentExecutionState) -> bool:
        """
        Vérifie si la transition vers target_state est autorisée.
        
        Args:
            target_state: L'état cible
            
        Returns:
            True si la transition est autorisée
        """
        # Vérifier si l'état actuel permet des transitions
        allowed = self._allowed_transitions.get(self._current_state, set())
        return target_state in allowed
    
    def get_allowed_transitions(self) -> Set[AgentExecutionState]:
        """Retourne les transitions autorisées depuis l'état actuel."""
        return self._allowed_transitions.get(self._current_state, set())
    
    # ==========================================
    # MAIN TRANSITION
    # ==========================================
    
    def transition(
        self,
        target_state: AgentExecutionState,
        reason: str = "",
        trigger: str = "manual",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Effectue une transition vers un nouvel état.
        
        C'est LA méthode centrale de la machine d'états.
        
        Args:
            target_state: L'état cible
            reason: Raison de la transition
            trigger: Déclencheur (manual, auto, error, timeout)
            metadata: Métadonnées additionnelles
            
        Returns:
            True si la transition a réussi
            
        Raises:
            InvalidStateTransitionError: Si la transition n'est pas autorisée
        """
        # Vérifier si la transition est autorisée
        if not self.can_transition_to(target_state):
            logger.error(
                f"Invalid transition: {self._current_state.value} → {target_state.value}"
            )
            return False
        
        # Créer la transition
        duration_in_previous = self.time_in_current_state_ms
        
        transition = StateTransition(
            from_state=self._current_state,
            to_state=target_state,
            reason=reason,
            trigger=trigger,
            duration_in_previous_state_ms=duration_in_previous,
            metadata=metadata or {},
        )
        
        # Exécuter les callbacks pre-transition
        self._execute_pre_transition_callbacks(transition)
        
        # Effectuer la transition
        old_state = self._current_state
        self._previous_state = old_state
        self._current_state = target_state
        self._state_entered_at = datetime.utcnow()
        self._transition_count += 1
        self._total_runtime_ms += duration_in_previous
        
        # Enregistrer dans l'historique
        self._transition_history.append(transition)
        
        # Log
        logger.info(
            f"State transition: {old_state.value} → {target_state.value} "
            f"(reason: {reason}, duration: {duration_in_previous:.1f}ms)"
        )
        
        # Exécuter les callbacks post-transition
        self._execute_post_transition_callbacks(old_state, target_state)
        
        # Callback terminal
        if self.is_terminal:
            self._execute_terminal_callbacks(target_state)
        
        return True
    
    def _execute_pre_transition_callbacks(self, transition: StateTransition) -> None:
        """Exécute les callbacks pre-transition."""
        # Vérifier les règles personnalisées
        rule_key = f"{transition.from_state.value}→{transition.to_state.value}"
        rule = self._custom_rules.get(rule_key)
        
        if rule and rule.on_transition:
            try:
                rule.on_transition()
            except Exception as e:
                logger.error(f"Error in transition callback: {e}")
    
    def _execute_post_transition_callbacks(
        self,
        old_state: AgentExecutionState,
        new_state: AgentExecutionState
    ) -> None:
        """Exécute les callbacks post-transition."""
        for callback in self._on_state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def _execute_terminal_callbacks(self, final_state: AgentExecutionState) -> None:
        """Exécute les callbacks pour états terminaux."""
        for callback in self._on_terminal_callbacks:
            try:
                callback(final_state)
            except Exception as e:
                logger.error(f"Error in terminal callback: {e}")
    
    # ==========================================
    # CONVENIENCE METHODS
    # ==========================================
    
    def start(self) -> bool:
        """Démarre l'exécution (IDLE → INITIALIZING → THINKING)."""
        if self._current_state != AgentExecutionState.IDLE:
            return False
        
        if self.transition(AgentExecutionState.INITIALIZING, reason="Starting execution"):
            return self.transition(AgentExecutionState.THINKING, reason="Ready to think")
        return False
    
    def think(self) -> bool:
        """Passe à l'état THINKING."""
        return self.transition(AgentExecutionState.THINKING, trigger="auto")
    
    def act(self) -> bool:
        """Passe à l'état ACTING."""
        return self.transition(AgentExecutionState.ACTING, trigger="auto")
    
    def observe(self) -> bool:
        """Passe à l'état OBSERVING."""
        return self.transition(AgentExecutionState.OBSERVING, trigger="auto")
    
    def delegate(self, target_agent: Optional[str] = None) -> bool:
        """Passe à l'état DELEGATING."""
        return self.transition(
            AgentExecutionState.DELEGATING,
            reason=f"Delegating to {target_agent}" if target_agent else "Delegating",
            metadata={"target_agent": target_agent}
        )
    
    def wait_for_results(self) -> bool:
        """Passe à l'état WAITING_RESULTS."""
        return self.transition(AgentExecutionState.WAITING_RESULTS, trigger="auto")
    
    def receive_results(self) -> bool:
        """Passe à l'état RECEIVING_RESULTS."""
        return self.transition(AgentExecutionState.RECEIVING_RESULTS, trigger="auto")
    
    def synthesize(self) -> bool:
        """Passe à l'état SYNTHESIZING."""
        return self.transition(AgentExecutionState.SYNTHESIZING, trigger="auto")
    
    def complete(self, reason: str = "Success") -> bool:
        """Passe à l'état COMPLETED."""
        return self.transition(AgentExecutionState.COMPLETED, reason=reason)
    
    def fail(self, error: str = "") -> bool:
        """Passe à l'état FAILED."""
        self._error_count += 1
        return self.transition(
            AgentExecutionState.FAILED,
            reason=error,
            trigger="error",
            metadata={"error": error}
        )
    
    def abort(self, reason: str = "Aborted") -> bool:
        """Passe à l'état ABORTED."""
        return self.transition(AgentExecutionState.ABORTED, reason=reason)
    
    def recover(self) -> bool:
        """Passe à l'état RECOVERING."""
        return self.transition(AgentExecutionState.RECOVERING, trigger="auto")
    
    def retry(self) -> bool:
        """Passe à l'état RETRYING."""
        return self.transition(AgentExecutionState.RETRYING, trigger="auto")
    
    def pause(self) -> bool:
        """Passe à l'état PAUSED."""
        return self.transition(AgentExecutionState.PAUSED, trigger="manual")
    
    def resume(self) -> bool:
        """Reprend l'exécution depuis PAUSED."""
        if self._current_state == AgentExecutionState.PAUSED:
            return self.transition(AgentExecutionState.THINKING, reason="Resumed")
        return False
    
    # ==========================================
    # CALLBACKS
    # ==========================================
    
    def on_state_change(
        self,
        callback: Callable[[AgentExecutionState, AgentExecutionState], None]
    ) -> None:
        """Enregistre un callback sur changement d'état."""
        self._on_state_change_callbacks.append(callback)
    
    def on_terminal(
        self,
        callback: Callable[[AgentExecutionState], None]
    ) -> None:
        """Enregistre un callback sur état terminal."""
        self._on_terminal_callbacks.append(callback)
    
    # ==========================================
    # CUSTOM RULES
    # ==========================================
    
    def add_transition_rule(self, rule: TransitionRule) -> None:
        """Ajoute une règle de transition personnalisée."""
        rule_key = f"{rule.from_state.value}→{rule.to_state.value}"
        self._custom_rules[rule_key] = rule
    
    def allow_transition(
        self,
        from_state: AgentExecutionState,
        to_state: AgentExecutionState
    ) -> None:
        """Autorise une transition additionnelle."""
        if from_state not in self._allowed_transitions:
            self._allowed_transitions[from_state] = set()
        self._allowed_transitions[from_state].add(to_state)
    
    def disallow_transition(
        self,
        from_state: AgentExecutionState,
        to_state: AgentExecutionState
    ) -> None:
        """Interdit une transition."""
        if from_state in self._allowed_transitions:
            self._allowed_transitions[from_state].discard(to_state)
    
    # ==========================================
    # HISTORY & ANALYTICS
    # ==========================================
    
    def get_history(self, limit: int = 10) -> List[StateTransition]:
        """Retourne l'historique des transitions."""
        return self._transition_history[-limit:]
    
    def get_full_history(self) -> List[StateTransition]:
        """Retourne l'historique complet."""
        return self._transition_history.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la machine d'états."""
        # Calculer le temps par état
        state_durations: Dict[str, List[float]] = {}
        for transition in self._transition_history:
            state = transition.from_state.value
            if state not in state_durations:
                state_durations[state] = []
            state_durations[state].append(transition.duration_in_previous_state_ms)
        
        avg_durations = {
            state: sum(durations) / len(durations)
            for state, durations in state_durations.items()
        }
        
        # Compter les transitions par type
        transition_counts: Dict[str, int] = {}
        for transition in self._transition_history:
            key = f"{transition.from_state.value}→{transition.to_state.value}"
            transition_counts[key] = transition_counts.get(key, 0) + 1
        
        return {
            "state_machine_id": self.state_machine_id,
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "is_terminal": self.is_terminal,
            "transition_count": self._transition_count,
            "error_count": self._error_count,
            "total_runtime_ms": self._total_runtime_ms,
            "time_in_current_state_ms": self.time_in_current_state_ms,
            "average_state_durations_ms": avg_durations,
            "transition_counts": transition_counts,
        }
    
    def get_state_sequence(self) -> List[str]:
        """Retourne la séquence des états visités."""
        sequence = [AgentExecutionState.IDLE.value]
        for transition in self._transition_history:
            sequence.append(transition.to_state.value)
        return sequence
    
    # ==========================================
    # RESET
    # ==========================================
    
    def reset(self) -> None:
        """Réinitialise la machine d'états."""
        self._current_state = AgentExecutionState.IDLE
        self._previous_state = None
        self._transition_history.clear()
        self._state_entered_at = datetime.utcnow()
        self._total_runtime_ms = 0.0
        self._transition_count = 0
        self._error_count = 0
        logger.info(f"State machine {self.state_machine_id} reset")
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "state_machine_id": self.state_machine_id,
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "is_terminal": self.is_terminal,
            "transition_count": self._transition_count,
            "stats": self.get_stats(),
        }


# ==========================================
# EXCEPTIONS
# ==========================================

class InvalidStateTransitionError(Exception):
    """Erreur de transition d'état invalide."""
    
    def __init__(
        self,
        from_state: AgentExecutionState,
        to_state: AgentExecutionState,
        message: str = ""
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.message = message or f"Invalid transition: {from_state.value} → {to_state.value}"
        super().__init__(self.message)


# ==========================================
# FACTORY
# ==========================================

def create_state_machine(
    initial_state: AgentExecutionState = AgentExecutionState.IDLE,
) -> AgentStateMachine:
    """Factory pour créer une machine d'états."""
    return AgentStateMachine(initial_state=initial_state)
