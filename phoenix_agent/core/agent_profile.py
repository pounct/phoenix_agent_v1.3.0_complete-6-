"""
Phoenix Agent - Agent Profile
=============================

Profil cognitif complet d'un agent.

L'AgentProfile définit QUI est l'agent et QUELLES sont ses limites.
C'est le "self-model" de l'agent - sa compréhension de lui-même.

C'est ce qui permet à un agent de dire:
    "Je sais que je ne peux pas gérer plus de X tokens."
    "Je sais que ma confiance diminue après Y itérations."
    "Je sais que je suis meilleur en CODE qu'en CREATIVE."

Sans ce self-model, un agent ne peut pas prendre de décisions intelligentes.

Version: 0.5.0 (Agent Self-Model)
"""

from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import logging

from .capability import (
    AgentCapability,
    CapabilityLimits,
    CapabilityResources,
    CapabilityRegistry,
    Domain,
)


logger = logging.getLogger("phoenix.agent_profile")


# ==========================================
# AGENT TYPE
# ==========================================

class AgentType(str, Enum):
    """Type d'agent."""
    ORCHESTRATOR = "orchestrator"     # Agent principal qui coordonne
    SPECIALIST = "specialist"         # Agent spécialisé
    WORKER = "worker"                 # Agent exécuteur
    SUPERVISOR = "supervisor"         # Agent qui supervise d'autres agents
    DELEGATOR = "delegator"           # Agent qui délègue principalement


# ==========================================
# AGENT STATE
# ==========================================

@dataclass
class AgentState:
    """
    État courant d'un agent.
    
    Suivi en temps réel des métriques cognitives.
    C'est ce qui permet de détecter QUAND déléguer.
    """
    # Utilisation actuelle
    current_tokens_used: int = 0
    current_iterations: int = 0
    current_reasoning_depth: int = 0
    current_tasks_completed: int = 0
    
    # Métriques de performance
    total_tokens_used: int = 0
    total_time_ms: float = 0.0
    total_successes: int = 0
    total_failures: int = 0
    
    # État cognitif
    current_confidence: float = 1.0
    current_load: float = 0.0  # 0.0 to 1.0
    cognitive_fatigue: float = 0.0  # Augmente avec le temps/usage
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def update_tokens(self, tokens: int) -> None:
        """Met à jour l'utilisation de tokens."""
        self.current_tokens_used = tokens
        self.total_tokens_used += tokens
        self._touch()
    
    def increment_iteration(self) -> int:
        """Incrémente les itérations."""
        self.current_iterations += 1
        self._touch()
        return self.current_iterations
    
    def increment_depth(self) -> int:
        """Incrémente la profondeur de raisonnement."""
        self.current_reasoning_depth += 1
        self._touch()
        return self.current_reasoning_depth
    
    def record_success(self) -> None:
        """Enregistre un succès."""
        self.total_successes += 1
        self.current_tasks_completed += 1
        self._update_fatigue(success=True)
        self._touch()
    
    def record_failure(self) -> None:
        """Enregistre un échec."""
        self.total_failures += 1
        self._update_fatigue(success=False)
        self._touch()
    
    def update_confidence(self, confidence: float) -> None:
        """Met à jour la confiance."""
        self.current_confidence = max(0.0, min(1.0, confidence))
        self._touch()
    
    def update_load(self, load: float) -> None:
        """Met à jour la charge."""
        self.current_load = max(0.0, min(1.0, load))
        self._touch()
    
    def _update_fatigue(self, success: bool) -> None:
        """Met à jour la fatigue cognitive."""
        # La fatigue augmente plus vite avec les échecs
        delta = 0.05 if success else 0.15
        self.cognitive_fatigue = min(1.0, self.cognitive_fatigue + delta)
    
    def _touch(self) -> None:
        """Met à jour le timestamp."""
        self.last_activity = datetime.utcnow()
    
    def reset_counters(self) -> None:
        """Réinitialise les compteurs de session."""
        self.current_tokens_used = 0
        self.current_iterations = 0
        self.current_reasoning_depth = 0
    
    def reset_fatigue(self) -> None:
        """Réinitialise la fatigue."""
        self.cognitive_fatigue = 0.0
        self.current_confidence = 1.0
    
    @property
    def success_rate(self) -> float:
        """Taux de succès."""
        total = self.total_successes + self.total_failures
        if total == 0:
            return 1.0
        return self.total_successes / total
    
    @property
    def is_tired(self) -> bool:
        """L'agent est fatigué (besoin de reset ou délégation)."""
        return self.cognitive_fatigue > 0.7


# ==========================================
# AGENT PROFILE
# ==========================================

@dataclass
class AgentProfile:
    """
    Profil complet d'un agent.
    
    C'est le "self-model" de l'agent - sa compréhension de:
        - Qui il est (identity)
        - Ce qu'il peut faire (capabilities)
        - Ses limites (limits)
        - Son état actuel (state)
    
    C'est LE composant central pour les décisions cognitives.
    
    Example:
        profile = AgentProfile(
            name="Phoenix-Main",
            agent_type=AgentType.ORCHESTRATOR,
            default_limits=CapabilityLimits(
                max_context_tokens=4000,
                max_iterations=10,
                max_reasoning_depth=5
            )
        )
        
        # Check si je peux continuer
        if profile.can_continue():
            # ...
        else:
            # Je dois déléguer
            await delegate()
    """
    # Identity
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Phoenix-Agent"
    agent_type: AgentType = AgentType.ORCHESTRATOR
    version: str = "0.5.0"
    
    # Default limits (global)
    default_limits: CapabilityLimits = field(default_factory=CapabilityLimits)
    
    # Default resources
    default_resources: CapabilityResources = field(default_factory=CapabilityResources)
    
    # Capabilities registry
    capabilities: CapabilityRegistry = field(default_factory=CapabilityRegistry)
    
    # Current state
    state: AgentState = field(default_factory=AgentState)
    
    # Domains de prédilection
    primary_domains: List[Domain] = field(default_factory=lambda: [Domain.GENERAL])
    secondary_domains: List[Domain] = field(default_factory=list)
    
    # ==========================================
    # CAPABILITY CHECKS
    # ==========================================
    
    def can_handle_domain(self, domain: Domain) -> bool:
        """Vérifie si l'agent peut gérer un domaine."""
        return (
            domain in self.primary_domains or
            domain in self.secondary_domains or
            Domain.GENERAL in self.primary_domains
        )
    
    def get_domain_proficiency(self, domain: Domain) -> float:
        """Retourne la compétence dans un domaine."""
        cap = self.capabilities.find_best(domain=domain)
        if cap:
            return cap.proficiency
        
        if domain in self.primary_domains:
            return 0.9
        elif domain in self.secondary_domains:
            return 0.6
        return 0.3  # Basique pour tout
    
    # ==========================================
    # LIMIT CHECKS (Core Cognitive Decisions)
    # ==========================================
    
    def can_continue(self) -> bool:
        """
        Vérifie si l'agent peut continuer.
        
        C'est UNE des fonctions les plus importantes.
        Elle répond à: "Est-ce que je suis encore capable de raisonner efficacement?"
        """
        limits = self.default_limits
        state = self.state
        
        # Check basic limits
        if state.current_tokens_used > limits.max_context_tokens:
            logger.info(f"Token limit reached: {state.current_tokens_used} > {limits.max_context_tokens}")
            return False
        
        if state.current_iterations >= limits.max_iterations:
            logger.info(f"Iteration limit reached: {state.current_iterations} >= {limits.max_iterations}")
            return False
        
        if state.current_reasoning_depth >= limits.max_reasoning_depth:
            logger.info(f"Reasoning depth limit reached: {state.current_reasoning_depth} >= {limits.max_reasoning_depth}")
            return False
        
        if state.current_confidence < limits.min_confidence_threshold:
            logger.info(f"Confidence too low: {state.current_confidence:.2f} < {limits.min_confidence_threshold}")
            return False
        
        if state.cognitive_fatigue > 0.8:
            logger.info(f"Cognitive fatigue too high: {state.cognitive_fatigue:.2f}")
            return False
        
        return True
    
    def should_delegate(self, reason: str = "") -> bool:
        """
        Vérifie si l'agent devrait déléguer.
        
        Plus nuancé que can_continue() - peut déléguer AVANT d'atteindre les limites.
        """
        limits = self.default_limits
        state = self.state
        
        # Déjà aux limites
        if not self.can_continue():
            return True
        
        # Approche des limites (proactive delegation)
        token_utilization = state.current_tokens_used / limits.max_context_tokens
        iteration_utilization = state.current_iterations / limits.max_iterations
        
        if token_utilization > limits.context_window_utilization_threshold:
            logger.info(f"Token utilization high: {token_utilization:.1%} > {limits.context_window_utilization_threshold:.1%}")
            return True
        
        if iteration_utilization > 0.7:
            logger.info(f"Iteration utilization high: {iteration_utilization:.1%}")
            return True
        
        # Fatigue cognitive
        if state.cognitive_fatigue > 0.5:
            logger.info(f"Cognitive fatigue elevated: {state.cognitive_fatigue:.2f}")
            return True
        
        # Charge élevée
        if state.current_load > 0.8:
            logger.info(f"Agent load high: {state.current_load:.2f}")
            return True
        
        return False
    
    def get_delegation_triggers(self) -> List[str]:
        """Retourne les triggers de délégation actifs."""
        triggers = []
        limits = self.default_limits
        state = self.state
        
        if state.current_tokens_used > limits.max_context_tokens:
            triggers.append("MEMORY_OVERFLOW")
        elif state.current_tokens_used > limits.max_context_tokens * limits.context_window_utilization_threshold:
            triggers.append("MEMORY_PRESSURE")
        
        if state.current_iterations >= limits.max_iterations:
            triggers.append("MAX_ITERATIONS")
        elif state.current_iterations > limits.max_iterations * 0.7:
            triggers.append("APPROACHING_ITERATION_LIMIT")
        
        if state.current_reasoning_depth >= limits.max_reasoning_depth:
            triggers.append("MAX_REASONING_DEPTH")
        
        if state.current_confidence < limits.min_confidence_threshold:
            triggers.append("LOW_CONFIDENCE")
        
        if state.cognitive_fatigue > 0.7:
            triggers.append("COGNITIVE_FATIGUE")
        elif state.cognitive_fatigue > 0.5:
            triggers.append("FATIGUE_WARNING")
        
        if state.current_load > 0.8:
            triggers.append("HIGH_LOAD")
        
        return triggers
    
    # ==========================================
    # RESOURCE CHECKS
    # ==========================================
    
    def has_token_budget(self, estimated_tokens: int) -> bool:
        """Vérifie si le budget de tokens est suffisant."""
        remaining = self.default_resources.token_budget - self.state.total_tokens_used
        return remaining >= estimated_tokens
    
    def has_time_budget(self, estimated_ms: float) -> bool:
        """Vérifie si le budget temps est suffisant."""
        remaining = self.default_resources.time_budget_ms - self.state.total_time_ms
        return remaining >= estimated_ms
    
    def has_tool(self, tool_name: str) -> bool:
        """Vérifie si un tool est disponible."""
        return self.default_resources.has_tool(tool_name)
    
    # ==========================================
    # STATE MANAGEMENT
    # ==========================================
    
    def start_task(self) -> None:
        """Démarre une nouvelle tâche."""
        self.state.reset_counters()
        logger.debug(f"Agent {self.name} starting new task")
    
    def complete_task(self, success: bool = True) -> None:
        """Complète la tâche courante."""
        if success:
            self.state.record_success()
        else:
            self.state.record_failure()
        logger.debug(f"Agent {self.name} completed task (success={success})")
    
    def reset(self) -> None:
        """Reset complet de l'agent."""
        self.state.reset_counters()
        self.state.reset_fatigue()
        logger.info(f"Agent {self.name} reset")
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type.value,
            "version": self.version,
            "state": {
                "current_tokens": self.state.current_tokens_used,
                "current_iterations": self.state.current_iterations,
                "current_depth": self.state.current_reasoning_depth,
                "confidence": self.state.current_confidence,
                "fatigue": self.state.cognitive_fatigue,
                "load": self.state.current_load,
                "success_rate": self.state.success_rate,
            },
            "limits": {
                "max_tokens": self.default_limits.max_context_tokens,
                "max_iterations": self.default_limits.max_iterations,
                "max_depth": self.default_limits.max_reasoning_depth,
            },
            "can_continue": self.can_continue(),
            "delegation_triggers": self.get_delegation_triggers(),
        }


# ==========================================
# PROFILE FACTORY
# ==========================================

def create_default_profile(
    name: str = "Phoenix-Agent",
    agent_type: AgentType = AgentType.ORCHESTRATOR,
    max_tokens: int = 4000,
    max_iterations: int = 10,
    max_depth: int = 5,
) -> AgentProfile:
    """Crée un profil par défaut."""
    limits = CapabilityLimits(
        max_context_tokens=max_tokens,
        max_iterations=max_iterations,
        max_reasoning_depth=max_depth,
    )
    
    return AgentProfile(
        name=name,
        agent_type=agent_type,
        default_limits=limits,
    )


def create_specialist_profile(
    name: str,
    domain: Domain,
    proficiency: float = 0.9,
    max_tokens: int = 2000,
) -> AgentProfile:
    """Crée un profil de spécialiste."""
    profile = create_default_profile(
        name=name,
        agent_type=AgentType.SPECIALIST,
        max_tokens=max_tokens,
    )
    
    profile.primary_domains = [domain]
    
    # Ajouter la capacité
    capability = AgentCapability(
        name=f"{domain.value}_specialist",
        domain=domain,
        proficiency=proficiency,
    )
    profile.capabilities.register(capability)
    
    return profile
