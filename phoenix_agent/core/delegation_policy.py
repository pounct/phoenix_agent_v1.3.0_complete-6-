"""
Phoenix Agent - Delegation Policy
=================================

Politique de délégation: Trigger → Action Mapping.

Le DelegationPolicy répond à:
    "Comment déléguer selon chaque trigger?"

C'est le mapping entre:
    - Ce qui a déclenché la délégation (Memory overflow, Low confidence, etc.)
    - Quelle action entreprendre (Delegate to specialist, Compress, Split, etc.)
    - Quel type d'agent cible

Sans ce composant, la délégation serait arbitraire.
Avec ce composant, la délégation devient systématique et prédictible.

Version: 0.6.0 (Delegation Policy Layer)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .capability_monitor import DelegationTrigger
from .decision_engine import CognitiveDecision


logger = logging.getLogger("phoenix.delegation_policy")


# ==========================================
# DELEGATION STRATEGY
# ==========================================

class DelegationStrategy(str, Enum):
    """Stratégies de délégation."""
    # Delegation
    DELEGATE_SPECIALIST = "delegate_specialist"      # Déléguer à un spécialiste
    DELEGATE_WORKER = "delegate_worker"              # Déléguer à un worker
    DELEGATE_PLANNER = "delegate_planner"            # Déléguer à un planner
    DELEGATE_PARALLEL = "delegate_parallel"          # Déléguer en parallèle
    
    # Task modification
    SPLIT_AND_DELEGATE = "split_and_delegate"        # Diviser puis déléguer
    SIMPLIFY_AND_CONTINUE = "simplify_and_continue"  # Simplifier et continuer
    
    # Memory management
    COMPRESS_AND_CONTINUE = "compress_and_continue"  # Compresser et continuer
    EXTERNALIZE_AND_CONTINUE = "externalize_and_continue"  # Externaliser
    
    # Recovery
    RETRY_WITH_FEEDBACK = "retry_with_feedback"      # Réessayer avec feedback
    CHANGE_APPROACH = "change_approach"              # Changer d'approche
    
    # No action
    NO_ACTION = "no_action"                          # Pas d'action requise


# ==========================================
# TARGET AGENT TYPE
# ==========================================

class TargetAgentType(str, Enum):
    """Types d'agents cibles pour la délégation."""
    # Specialists
    CODE_SPECIALIST = "code_specialist"
    RESEARCH_SPECIALIST = "research_specialist"
    ANALYSIS_SPECIALIST = "analysis_specialist"
    WRITING_SPECIALIST = "writing_specialist"
    
    # Functional
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    SUMMARIZER = "summarizer"
    
    # Generic
    GENERAL_WORKER = "general_worker"
    DOMAIN_EXPERT = "domain_expert"
    
    # Meta
    ORCHESTRATOR = "orchestrator"
    CRITIC = "critic"


# ==========================================
# DELEGATION ACTION
# ==========================================

@dataclass
class DelegationAction:
    """
    Action de délégation.
    
    Décrit EXACTEMENT ce qu'il faut faire.
    """
    strategy: DelegationStrategy
    target_agent_type: Optional[TargetAgentType] = None
    
    # Paramètres de l'action
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Priorité de l'action
    priority: int = 5  # 1-10, 10 = highest
    
    # Si cette action échoue, que faire?
    fallback_strategy: Optional[DelegationStrategy] = None
    
    # Description
    description: str = ""
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "target_agent_type": self.target_agent_type.value if self.target_agent_type else None,
            "params": self.params,
            "priority": self.priority,
            "description": self.description,
        }


# ==========================================
# POLICY RULE
# ==========================================

@dataclass
class PolicyRule:
    """
    Règle de politique de délégation.
    
    Format:
        IF trigger IN [triggers] AND conditions
        THEN action
    """
    name: str
    triggers: List[DelegationTrigger]
    action: DelegationAction
    conditions: Callable[[Dict[str, Any]], bool] = lambda x: True
    priority: int = 0
    
    def matches(
        self,
        trigger: DelegationTrigger,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Vérifie si la règle correspond."""
        if trigger not in self.triggers:
            return False
        
        context = context or {}
        return self.conditions(context)


# ==========================================
# DELEGATION POLICY
# ==========================================

class DelegationPolicy:
    """
    Politique de délégation Phoenix.
    
    Définit COMMENT réagir à chaque trigger cognitif.
    
    Architecture:
        Trigger (Detection) → Policy (Mapping) → Action (Execution)
        
    Example:
        MEMORY_OVERFLOW → delegate to worker (keep context minimal)
        LOW_CONFIDENCE → delegate to specialist
        DOMAIN_MISMATCH → delegate to domain expert
        MAX_ITERATIONS → split task and delegate parts
        
    Usage:
        policy = DelegationPolicy()
        
        trigger = DelegationTrigger.MEMORY_OVERFLOW
        action = policy.get_action(trigger, context={"tokens": 5000})
        
        if action.strategy == DelegationStrategy.DELEGATE_WORKER:
            await delegation_engine.delegate(action)
    """
    
    def __init__(self):
        self._rules: List[PolicyRule] = []
        self._setup_default_rules()
        
        # Historique des actions
        self._action_history: List[Dict[str, Any]] = []
    
    # ==========================================
    # DEFAULT RULES SETUP
    # ==========================================
    
    def _setup_default_rules(self) -> None:
        """Configure les règles par défaut."""
        
        # === MEMORY TRIGGERS ===
        
        # Memory overflow → Delegate to worker (keep context minimal)
        self.add_rule(PolicyRule(
            name="memory_overflow_delegate",
            triggers=[DelegationTrigger.MEMORY_OVERFLOW],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_WORKER,
                target_agent_type=TargetAgentType.GENERAL_WORKER,
                priority=9,
                params={
                    "include_minimal_context": True,
                    "compress_before_delegate": True,
                },
                fallback_strategy=DelegationStrategy.COMPRESS_AND_CONTINUE,
                description="Memory full: delegate remaining work to worker",
            ),
            priority=100
        ))
        
        # Memory pressure → Try compress first
        self.add_rule(PolicyRule(
            name="memory_pressure_compress",
            triggers=[DelegationTrigger.MEMORY_PRESSURE],
            action=DelegationAction(
                strategy=DelegationStrategy.COMPRESS_AND_CONTINUE,
                priority=7,
                params={
                    "compression_ratio": 0.6,
                    "keep_last_n_messages": 5,
                },
                description="Memory pressure: compress context",
            ),
            priority=90
        ))
        
        # === ITERATION TRIGGERS ===
        
        # Max iterations → Split and delegate
        self.add_rule(PolicyRule(
            name="max_iterations_split",
            triggers=[DelegationTrigger.MAX_ITERATIONS],
            action=DelegationAction(
                strategy=DelegationStrategy.SPLIT_AND_DELEGATE,
                target_agent_type=TargetAgentType.EXECUTOR,
                priority=8,
                params={
                    "max_subtasks": 3,
                    "parallel_execution": True,
                },
                description="Max iterations: split task and delegate",
            ),
            priority=85
        ))
        
        # Approaching iteration limit → Plan better
        self.add_rule(PolicyRule(
            name="approaching_iterations_plan",
            triggers=[DelegationTrigger.APPROACHING_ITERATION_LIMIT],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_PLANNER,
                target_agent_type=TargetAgentType.PLANNER,
                priority=6,
                params={
                    "request_plan_refinement": True,
                },
                description="Approaching limit: get planning help",
            ),
            priority=80
        ))
        
        # === CONFIDENCE TRIGGERS ===
        
        # Low confidence → Delegate to specialist
        self.add_rule(PolicyRule(
            name="low_confidence_specialist",
            triggers=[DelegationTrigger.LOW_CONFIDENCE],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_SPECIALIST,
                target_agent_type=TargetAgentType.DOMAIN_EXPERT,
                priority=8,
                params={
                    "include_full_context": True,
                    "request_confidence_boost": True,
                },
                description="Low confidence: delegate to specialist",
            ),
            priority=75
        ))
        
        # Confidence degradation → Change approach
        self.add_rule(PolicyRule(
            name="confidence_degradation_retry",
            triggers=[DelegationTrigger.CONFIDENCE_DEGRADATION],
            action=DelegationAction(
                strategy=DelegationStrategy.CHANGE_APPROACH,
                priority=6,
                params={
                    "analyze_what_went_wrong": True,
                    "suggest_alternative_approach": True,
                },
                description="Confidence dropping: try different approach",
            ),
            priority=70
        ))
        
        # === COGNITIVE STATE TRIGGERS ===
        
        # Cognitive fatigue → Delegate to fresh worker
        self.add_rule(PolicyRule(
            name="fatigue_delegate",
            triggers=[DelegationTrigger.COGNITIVE_FATIGUE],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_WORKER,
                target_agent_type=TargetAgentType.GENERAL_WORKER,
                priority=7,
                params={
                    "fresh_agent": True,
                    "reset_context": False,
                },
                description="Cognitive fatigue: delegate to fresh agent",
            ),
            priority=65
        ))
        
        # High load → Parallel delegation
        self.add_rule(PolicyRule(
            name="high_load_parallel",
            triggers=[DelegationTrigger.HIGH_LOAD],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_PARALLEL,
                target_agent_type=TargetAgentType.GENERAL_WORKER,
                priority=6,
                params={
                    "max_parallel_agents": 3,
                },
                description="High load: parallel delegation",
            ),
            priority=60
        ))
        
        # === DOMAIN/TRIGGERS ===
        
        # Domain mismatch → Domain expert
        self.add_rule(PolicyRule(
            name="domain_mismatch_expert",
            triggers=[DelegationTrigger.DOMAIN_MISMATCH],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_SPECIALIST,
                target_agent_type=TargetAgentType.DOMAIN_EXPERT,
                priority=9,
                params={
                    "include_full_context": True,
                },
                description="Domain mismatch: delegate to domain expert",
            ),
            priority=95
        ))
        
        # Task too complex → Planner then split
        self.add_rule(PolicyRule(
            name="task_complex_planner",
            triggers=[DelegationTrigger.TASK_TOO_COMPLEX],
            action=DelegationAction(
                strategy=DelegationStrategy.SPLIT_AND_DELEGATE,
                target_agent_type=TargetAgentType.PLANNER,
                priority=8,
                params={
                    "first_plan": True,
                    "then_delegate": True,
                },
                description="Task complex: plan then delegate",
            ),
            priority=88
        ))
        
        # Reasoning stuck → Get fresh perspective
        self.add_rule(PolicyRule(
            name="reasoning_stuck_critic",
            triggers=[DelegationTrigger.REASONING_STUCK],
            action=DelegationAction(
                strategy=DelegationStrategy.DELEGATE_SPECIALIST,
                target_agent_type=TargetAgentType.CRITIC,
                priority=7,
                params={
                    "request_alternative_perspective": True,
                },
                description="Reasoning stuck: get critic perspective",
            ),
            priority=72
        ))
    
    # ==========================================
    # RULE MANAGEMENT
    # ==========================================
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Ajoute une règle."""
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
    # MAIN ACTION RESOLUTION
    # ==========================================
    
    def get_action(
        self,
        trigger: DelegationTrigger,
        context: Optional[Dict[str, Any]] = None,
    ) -> DelegationAction:
        """
        Résout l'action pour un trigger donné.
        
        C'est LA méthode centrale du DelegationPolicy.
        
        Args:
            trigger: Le trigger détecté
            context: Contexte additionnel
            
        Returns:
            DelegationAction à exécuter
        """
        context = context or {}
        
        # Trouver la première règle qui match
        for rule in self._rules:
            if rule.matches(trigger, context):
                action = rule.action
                
                # Enrichir avec le contexte
                action.params.update(context)
                
                # Enregistrer
                self._action_history.append({
                    "trigger": trigger.value,
                    "action": action.to_dict(),
                    "rule": rule.name,
                })
                
                logger.info(f"Policy action: {trigger.value} → {action.strategy.value}")
                
                return action
        
        # Fallback: no action
        return DelegationAction(
            strategy=DelegationStrategy.NO_ACTION,
            description="No matching policy rule",
        )
    
    def get_action_for_decision(
        self,
        decision: CognitiveDecision,
        triggers: List[DelegationTrigger],
        context: Optional[Dict[str, Any]] = None,
    ) -> DelegationAction:
        """
        Résout l'action pour une décision cognitive.
        
        Combine la décision avec les triggers pour trouver la meilleure action.
        """
        context = context or {}
        context["decision"] = decision.value
        
        # Prioriser les triggers
        priority_order = [
            DelegationTrigger.MEMORY_OVERFLOW,
            DelegationTrigger.DOMAIN_MISMATCH,
            DelegationTrigger.LOW_CONFIDENCE,
            DelegationTrigger.MAX_ITERATIONS,
            DelegationTrigger.COGNITIVE_FATIGUE,
            DelegationTrigger.TASK_TOO_COMPLEX,
            DelegationTrigger.MEMORY_PRESSURE,
            DelegationTrigger.HIGH_LOAD,
        ]
        
        for priority_trigger in priority_order:
            if priority_trigger in triggers:
                return self.get_action(priority_trigger, context)
        
        # Fallback sur le premier trigger
        if triggers:
            return self.get_action(triggers[0], context)
        
        # No triggers
        return DelegationAction(
            strategy=DelegationStrategy.NO_ACTION,
            description="No triggers to resolve",
        )
    
    # ==========================================
    # BATCH RESOLUTION
    # ==========================================
    
    def resolve_triggers(
        self,
        triggers: List[DelegationTrigger],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[DelegationAction]:
        """
        Résout les actions pour plusieurs triggers.
        
        Retourne une liste d'actions ordonnée par priorité.
        """
        actions = []
        seen_strategies = set()
        
        for trigger in triggers:
            action = self.get_action(trigger, context)
            
            # Éviter les doublons de stratégie
            if action.strategy not in seen_strategies:
                actions.append(action)
                seen_strategies.add(action.strategy)
        
        # Trier par priorité
        actions.sort(key=lambda a: a.priority, reverse=True)
        
        return actions
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la politique."""
        if not self._action_history:
            return {"total_actions": 0, "rules_count": len(self._rules)}
        
        strategy_counts: Dict[str, int] = {}
        trigger_counts: Dict[str, int] = {}
        
        for entry in self._action_history:
            strategy = entry["action"]["strategy"]
            trigger = entry["trigger"]
            
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        return {
            "total_actions": len(self._action_history),
            "rules_count": len(self._rules),
            "strategy_distribution": strategy_counts,
            "trigger_distribution": trigger_counts,
        }
    
    def clear_history(self) -> None:
        """Efface l'historique."""
        self._action_history.clear()


# ==========================================
# POLICY BUILDER (Fluent API)
# ==========================================

class PolicyBuilder:
    """
    Builder fluent pour créer des politiques personnalisées.
    
    Example:
        policy = (
            PolicyBuilder()
            .on_trigger(DelegationTrigger.MEMORY_OVERFLOW)
            .delegate_to(TargetAgentType.GENERAL_WORKER)
            .with_params(include_minimal_context=True)
            .fallback_to(DelegationStrategy.COMPRESS_AND_CONTINUE)
            .build()
        )
    """
    
    def __init__(self):
        self._policy = DelegationPolicy()
        self._current_triggers: List[DelegationTrigger] = []
        self._current_action: Optional[DelegationAction] = None
    
    def on_trigger(self, trigger: DelegationTrigger) -> "PolicyBuilder":
        """Définit le trigger."""
        self._current_triggers.append(trigger)
        return self
    
    def on_triggers(self, triggers: List[DelegationTrigger]) -> "PolicyBuilder":
        """Définit plusieurs triggers."""
        self._current_triggers.extend(triggers)
        return self
    
    def delegate_to(self, agent_type: TargetAgentType) -> "PolicyBuilder":
        """Définit la cible de délégation."""
        self._current_action = DelegationAction(
            strategy=DelegationStrategy.DELEGATE_SPECIALIST,
            target_agent_type=agent_type,
        )
        return self
    
    def compress(self, ratio: float = 0.6) -> "PolicyBuilder":
        """Définit une action de compression."""
        self._current_action = DelegationAction(
            strategy=DelegationStrategy.COMPRESS_AND_CONTINUE,
            params={"compression_ratio": ratio},
        )
        return self
    
    def split(self, max_subtasks: int = 3) -> "PolicyBuilder":
        """Définit une action de split."""
        self._current_action = DelegationAction(
            strategy=DelegationStrategy.SPLIT_AND_DELEGATE,
            params={"max_subtasks": max_subtasks},
        )
        return self
    
    def with_params(self, **params) -> "PolicyBuilder":
        """Ajoute des paramètres."""
        if self._current_action:
            self._current_action.params.update(params)
        return self
    
    def with_priority(self, priority: int) -> "PolicyBuilder":
        """Définit la priorité."""
        if self._current_action:
            self._current_action.priority = priority
        return self
    
    def fallback_to(self, strategy: DelegationStrategy) -> "PolicyBuilder":
        """Définit le fallback."""
        if self._current_action:
            self._current_action.fallback_strategy = strategy
        return self
    
    def named(self, name: str) -> "PolicyBuilder":
        """Nomme la règle."""
        self._rule_name = name
        return self
    
    def add(self) -> "PolicyBuilder":
        """Ajoute la règle à la politique."""
        if self._current_triggers and self._current_action:
            rule = PolicyRule(
                name=getattr(self, '_rule_name', f"custom_rule_{len(self._policy._rules)}"),
                triggers=self._current_triggers,
                action=self._current_action,
            )
            self._policy.add_rule(rule)
            
            # Reset pour la prochaine règle
            self._current_triggers = []
            self._current_action = None
        
        return self
    
    def build(self) -> DelegationPolicy:
        """Construit la politique."""
        # Ajouter la dernière règle si non ajoutée
        if self._current_triggers and self._current_action:
            self.add()
        
        return self._policy
