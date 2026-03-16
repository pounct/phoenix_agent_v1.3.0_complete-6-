"""
Phoenix Agent - Decision Engine
===============================

Moteur de décision cognitive centralisé.

Sépare clairement:
    - Detection: CapabilityMonitor détecte les signaux
    - Decision: DecisionEngine prend la décision
    - Action: DelegationEngine exécute l'action

C'est LE composant qui répond à: "Que dois-je faire maintenant?"

Décisions possibles:
    - CONTINUE: Continuer le travail
    - DELEGATE: Déléguer à un sub-agent
    - SPLIT: Diviser la tâche
    - COMPRESS: Compresser la mémoire
    - RETRY: Réessayer avec une autre approche
    - STOP: Arrêter et retourner le résultat

Version: 0.6.0 (Decision Layer)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from .agent_profile import AgentProfile
from .capability_monitor import (
    CapabilityMonitor,
    MonitoringResult,
    MonitoringDecision,
    DelegationTrigger,
)
from .task import Task, TaskComplexity


logger = logging.getLogger("phoenix.decision_engine")


# ==========================================
# COGNITIVE DECISION
# ==========================================

class CognitiveDecision(str, Enum):
    """
    Décisions cognitives possibles.
    
    C'est le vocabulaire de décision de l'agent.
    """
    # Continue working
    CONTINUE = "continue"                    # Tout va bien, continue
    CONTINUE_WITH_CAUTION = "continue_caution"  # Warning mais continue
    
    # Delegation
    DELEGATE_SPECIALIST = "delegate_specialist"  # Déléguer à spécialiste
    DELEGATE_WORKER = "delegate_worker"          # Déléguer à worker
    DELEGATE_PLANNER = "delegate_planner"        # Déléguer à planner
    
    # Task modification
    SPLIT_TASK = "split_task"                # Diviser la tâche
    SIMPLIFY_TASK = "simplify_task"          # Simplifier la tâche
    
    # Memory
    COMPRESS_MEMORY = "compress_memory"      # Compresser le contexte
    EXTERNALIZE_MEMORY = "externalize_memory"  # Externaliser en vector store
    
    # Recovery
    RETRY = "retry"                          # Réessayer
    RETRY_DIFFERENT_APPROACH = "retry_approach"  # Approche différente
    
    # Termination
    STOP_SUCCESS = "stop_success"            # Succès, arrêter
    STOP_PARTIAL = "stop_partial"            # Succès partiel
    STOP_FAILURE = "stop_failure"            # Échec, arrêter
    ABORT = "abort"                          # Abandonner


# ==========================================
# DECISION CONTEXT
# ==========================================

@dataclass
class DecisionContext:
    """
    Contexte pour une décision cognitive.
    
    Rassemble toute l'information nécessaire pour décider.
    """
    # Agent state
    profile: AgentProfile
    monitor_result: MonitoringResult
    
    # Task state
    current_task: Optional[Task] = None
    task_progress: float = 0.0
    
    # History
    previous_decisions: List["DecisionResult"] = field(default_factory=list)
    retry_count: int = 0
    delegation_count: int = 0
    
    # Constraints
    max_delegations: int = 5
    max_retries: int = 3
    max_task_splits: int = 3
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ==========================================
# DECISION RESULT
# ==========================================

@dataclass
class DecisionResult:
    """
    Résultat d'une décision cognitive.
    
    Contient la décision ET le raisonnement.
    """
    decision: CognitiveDecision
    reasoning: str
    confidence: float
    
    # Triggers qui ont mené à cette décision
    triggers: List[DelegationTrigger] = field(default_factory=list)
    
    # Actions recommandées
    recommended_actions: List[str] = field(default_factory=list)
    
    # Paramètres pour l'action
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Métadonnées
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def should_delegate(self) -> bool:
        """La décision implique une délégation."""
        return self.decision in [
            CognitiveDecision.DELEGATE_SPECIALIST,
            CognitiveDecision.DELEGATE_WORKER,
            CognitiveDecision.DELEGATE_PLANNER,
        ]
    
    @property
    def should_stop(self) -> bool:
        """La décision implique un arrêt."""
        return self.decision in [
            CognitiveDecision.STOP_SUCCESS,
            CognitiveDecision.STOP_PARTIAL,
            CognitiveDecision.STOP_FAILURE,
            CognitiveDecision.ABORT,
        ]
    
    @property
    def should_modify_task(self) -> bool:
        """La décision implique une modification de tâche."""
        return self.decision in [
            CognitiveDecision.SPLIT_TASK,
            CognitiveDecision.SIMPLIFY_TASK,
        ]
    
    @property
    def should_modify_memory(self) -> bool:
        """La décision implique une modification mémoire."""
        return self.decision in [
            CognitiveDecision.COMPRESS_MEMORY,
            CognitiveDecision.EXTERNALIZE_MEMORY,
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "triggers": [t.value for t in self.triggers],
            "recommended_actions": self.recommended_actions,
        }


# ==========================================
# DECISION RULE
# ==========================================

@dataclass
class DecisionRule:
    """
    Règle de décision.
    
    Si condition → alors décision
    """
    name: str
    condition: Callable[[DecisionContext], bool]
    decision: CognitiveDecision
    reasoning: str
    priority: int = 0  # Higher = evaluated first
    
    def evaluate(self, context: DecisionContext) -> Optional[DecisionResult]:
        """Évalue la règle."""
        if self.condition(context):
            return DecisionResult(
                decision=self.decision,
                reasoning=self.reasoning,
                confidence=0.8,
                triggers=context.monitor_result.triggers,
            )
        return None


# ==========================================
# DECISION ENGINE
# ==========================================

class DecisionEngine:
    """
    Moteur de décision cognitive.
    
    C'est le cerveau décisionnel de Phoenix. Il:
        - Prend le contexte (monitoring, task, history)
        - Applique les règles de décision
        - Retourne LA meilleure décision
    
    Architecture:
        CapabilityMonitor → signals
        DecisionEngine → decide
        DelegationEngine → execute
    
    Example:
        engine = DecisionEngine()
        
        context = DecisionContext(
            profile=agent_profile,
            monitor_result=monitor.check(),
            current_task=task
        )
        
        result = engine.decide(context)
        
        if result.should_delegate:
            await delegation_engine.delegate(result)
        elif result.should_stop:
            return final_result
        else:
            continue_work()
    """
    
    def __init__(
        self,
        profile: Optional[AgentProfile] = None,
        monitor: Optional[CapabilityMonitor] = None,
    ):
        self.profile = profile
        self.monitor = monitor
        
        # Règles de décision
        self._rules: List[DecisionRule] = []
        self._setup_default_rules()
        
        # Historique
        self._decision_history: List[DecisionResult] = []
    
    def _setup_default_rules(self) -> None:
        """Configure les règles par défaut."""
        
        # Règle 1: Abort sur conditions critiques
        self.add_rule(DecisionRule(
            name="abort_critical",
            condition=lambda ctx: (
                DelegationTrigger.MEMORY_OVERFLOW in ctx.monitor_result.triggers and
                ctx.retry_count >= ctx.max_retries
            ),
            decision=CognitiveDecision.ABORT,
            reasoning="Critical memory overflow with max retries reached",
            priority=100
        ))
        
        # Règle 2: Delegate specialist sur domain mismatch
        self.add_rule(DecisionRule(
            name="delegate_specialist_domain",
            condition=lambda ctx: (
                DelegationTrigger.DOMAIN_MISMATCH in ctx.monitor_result.triggers
            ),
            decision=CognitiveDecision.DELEGATE_SPECIALIST,
            reasoning="Task requires specialist with domain expertise",
            priority=90
        ))
        
        # Règle 3: Delegate sur low confidence
        self.add_rule(DecisionRule(
            name="delegate_low_confidence",
            condition=lambda ctx: (
                DelegationTrigger.LOW_CONFIDENCE in ctx.monitor_result.triggers and
                ctx.delegation_count < ctx.max_delegations
            ),
            decision=CognitiveDecision.DELEGATE_SPECIALIST,
            reasoning="Agent confidence too low, delegate to specialist",
            priority=85
        ))
        
        # Règle 4: Compress memory sur pressure
        self.add_rule(DecisionRule(
            name="compress_memory",
            condition=lambda ctx: (
                DelegationTrigger.MEMORY_PRESSURE in ctx.monitor_result.triggers
            ),
            decision=CognitiveDecision.COMPRESS_MEMORY,
            reasoning="Memory pressure detected, compress context",
            priority=80
        ))
        
        # Règle 5: Split task si trop complexe
        self.add_rule(DecisionRule(
            name="split_complex_task",
            condition=lambda ctx: (
                ctx.current_task is not None and
                ctx.current_task.complexity.value in ["complex", "expert"] and
                ctx.monitor_result.iteration_utilization > 0.5
            ),
            decision=CognitiveDecision.SPLIT_TASK,
            reasoning="Complex task with high iteration usage, split for efficiency",
            priority=75
        ))
        
        # Règle 6: Delegate sur max iterations
        self.add_rule(DecisionRule(
            name="delegate_max_iterations",
            condition=lambda ctx: (
                DelegationTrigger.MAX_ITERATIONS in ctx.monitor_result.triggers and
                ctx.delegation_count < ctx.max_delegations
            ),
            decision=CognitiveDecision.DELEGATE_WORKER,
            reasoning="Max iterations reached, delegate remaining work",
            priority=70
        ))
        
        # Règle 7: Retry sur erreur recoverable
        self.add_rule(DecisionRule(
            name="retry_recoverable",
            condition=lambda ctx: (
                ctx.monitor_result.decision == MonitoringDecision.WARNING and
                ctx.retry_count < ctx.max_retries
            ),
            decision=CognitiveDecision.RETRY,
            reasoning="Recoverable issue, retry with adjustment",
            priority=50
        ))
        
        # Règle 8: Continue si tout va bien
        self.add_rule(DecisionRule(
            name="continue_normal",
            condition=lambda ctx: (
                ctx.monitor_result.decision == MonitoringDecision.CONTINUE
            ),
            decision=CognitiveDecision.CONTINUE,
            reasoning="All systems nominal, continue execution",
            priority=10
        ))
    
    # ==========================================
    # RULE MANAGEMENT
    # ==========================================
    
    def add_rule(self, rule: DecisionRule) -> None:
        """Ajoute une règle de décision."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, name: str) -> bool:
        """Supprime une règle par nom."""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                return True
        return False
    
    def clear_rules(self) -> None:
        """Supprime toutes les règles."""
        self._rules.clear()
    
    # ==========================================
    # MAIN DECISION
    # ==========================================
    
    def decide(self, context: DecisionContext) -> DecisionResult:
        """
        Prend une décision cognitive.
        
        C'est LA méthode centrale du DecisionEngine.
        
        Args:
            context: Le contexte de décision
            
        Returns:
            DecisionResult avec la décision et le raisonnement
        """
        # Évaluer les règles par priorité
        for rule in self._rules:
            result = rule.evaluate(context)
            if result:
                # Enrichir le résultat
                result = self._enrich_result(result, context)
                
                # Enregistrer
                self._decision_history.append(result)
                
                logger.info(f"Decision: {result.decision.value} - {result.reasoning}")
                
                return result
        
        # Fallback: continue
        return DecisionResult(
            decision=CognitiveDecision.CONTINUE,
            reasoning="No rule matched, default to continue",
            confidence=0.5,
            triggers=context.monitor_result.triggers,
        )
    
    def _enrich_result(
        self,
        result: DecisionResult,
        context: DecisionContext
    ) -> DecisionResult:
        """Enrichit le résultat avec des actions recommandées."""
        actions = []
        params = {}
        
        if result.decision == CognitiveDecision.DELEGATE_SPECIALIST:
            actions.append("Find specialist agent with matching domain")
            if context.current_task:
                params["task_id"] = context.current_task.task_id
                params["required_domain"] = self._infer_required_domain(context)
        
        elif result.decision == CognitiveDecision.COMPRESS_MEMORY:
            actions.append("Run memory compression")
            actions.append("Prioritize recent and relevant context")
            params["compression_ratio"] = 0.5
        
        elif result.decision == CognitiveDecision.SPLIT_TASK:
            actions.append("Decompose task into subtasks")
            if context.current_task:
                params["task_id"] = context.current_task.task_id
                params["max_subtasks"] = 3
        
        elif result.decision == CognitiveDecision.RETRY:
            actions.append("Retry with adjusted parameters")
            params["retry_count"] = context.retry_count + 1
        
        result.recommended_actions = actions
        result.action_params = params
        
        return result
    
    def _infer_required_domain(self, context: DecisionContext) -> str:
        """Infère le domaine requis pour une tâche."""
        if context.current_task:
            return context.current_task.task_type.value
        return "general"
    
    # ==========================================
    # QUICK DECISIONS
    # ==========================================
    
    def should_continue(self, context: DecisionContext) -> bool:
        """Décision rapide: peut-on continuer?"""
        result = self.decide(context)
        return result.decision in [
            CognitiveDecision.CONTINUE,
            CognitiveDecision.CONTINUE_WITH_CAUTION,
        ]
    
    def should_delegate(self, context: DecisionContext) -> bool:
        """Décision rapide: doit-on déléguer?"""
        result = self.decide(context)
        return result.should_delegate
    
    def should_stop(self, context: DecisionContext) -> bool:
        """Décision rapide: doit-on arrêter?"""
        result = self.decide(context)
        return result.should_stop
    
    # ==========================================
    # HISTORY & ANALYTICS
    # ==========================================
    
    def get_history(self, limit: int = 10) -> List[DecisionResult]:
        """Retourne l'historique des décisions."""
        return self._decision_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de décision."""
        if not self._decision_history:
            return {"total_decisions": 0}
        
        decision_counts: Dict[str, int] = {}
        for result in self._decision_history:
            key = result.decision.value
            decision_counts[key] = decision_counts.get(key, 0) + 1
        
        return {
            "total_decisions": len(self._decision_history),
            "decision_distribution": decision_counts,
            "delegation_rate": sum(
                1 for r in self._decision_history if r.should_delegate
            ) / len(self._decision_history),
        }
