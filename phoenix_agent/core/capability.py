"""
Phoenix Agent - Agent Capability
=================================

Définit les capacités et limites d'un agent.

Une capacité n'est pas juste une compétence - c'est une
combinaison de:
    - Compétence (skill)
    - Limites (limits)
    - Ressources (resources)
    - Coût (cost)

C'est ce qui permet à un agent de dire:
    "Je PEUX faire ça, MAIS ça va me coûter X tokens et Y temps."
    ou
    "Je ne PEUX PAS faire ça efficacement → je délègue."

Version: 0.5.0 (Cognitive Capability Model)
"""

from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger("phoenix.capability")


# ==========================================
# DOMAIN TYPES
# ==========================================

class Domain(str, Enum):
    """Domaines de compétence."""
    GENERAL = "general"
    CODE = "code"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    MATH = "math"
    CREATIVE = "creative"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTION = "execution"


# ==========================================
# RESOURCE TYPE
# ==========================================

class ResourceType(str, Enum):
    """Types de ressources consommables."""
    TOKENS = "tokens"
    TIME_MS = "time_ms"
    ITERATIONS = "iterations"
    MEMORY = "memory"
    API_CALLS = "api_calls"


# ==========================================
# CAPABILITY LIMITS
# ==========================================

@dataclass
class CapabilityLimits:
    """
    Limites d'une capacité.
    
    Définit QUAND une capacité devient inefficace ou impossible.
    
    Example:
        limits = CapabilityLimits(
            max_tokens=4000,
            max_iterations=10,
            max_reasoning_depth=5,
            confidence_threshold=0.7
        )
        
        if current_tokens > limits.max_tokens:
            # Déclencher délégation
            ...
    """
    # Context & Memory
    max_context_tokens: int = 4000
    max_context_messages: int = 50
    context_window_utilization_threshold: float = 0.8  # 80% = déléguer
    
    # Reasoning
    max_reasoning_depth: int = 5
    max_iterations: int = 10
    max_subtasks: int = 10
    
    # Confidence
    min_confidence_threshold: float = 0.6
    confidence_degradation_rate: float = 0.1  # Par itération
    
    # Performance
    max_latency_ms: float = 60000.0  # 1 minute
    max_cost_tokens: int = 100000
    
    # Complexity
    max_task_complexity: str = "complex"  # simple, moderate, complex, expert
    max_hierarchy_depth: int = 3
    
    def is_exceeded(
        self,
        current_tokens: int = 0,
        current_iterations: int = 0,
        current_depth: int = 0,
        current_confidence: float = 1.0,
    ) -> bool:
        """Vérifie si une limite est dépassée."""
        return (
            current_tokens > self.max_context_tokens or
            current_iterations > self.max_iterations or
            current_depth > self.max_reasoning_depth or
            current_confidence < self.min_confidence_threshold
        )
    
    def get_exceeded_limits(
        self,
        current_tokens: int = 0,
        current_iterations: int = 0,
        current_depth: int = 0,
        current_confidence: float = 1.0,
        current_latency_ms: float = 0.0,
    ) -> List[str]:
        """Retourne la liste des limites dépassées."""
        exceeded = []
        
        if current_tokens > self.max_context_tokens:
            exceeded.append("CONTEXT_TOKENS")
        if current_iterations > self.max_iterations:
            exceeded.append("ITERATIONS")
        if current_depth > self.max_reasoning_depth:
            exceeded.append("REASONING_DEPTH")
        if current_confidence < self.min_confidence_threshold:
            exceeded.append("CONFIDENCE")
        if current_latency_ms > self.max_latency_ms:
            exceeded.append("LATENCY")
        
        return exceeded


# ==========================================
# CAPABILITY RESOURCES
# ==========================================

@dataclass
class CapabilityResources:
    """
    Ressources disponibles pour une capacité.
    
    Ce que l'agent PEUT utiliser pour cette capacité.
    """
    # Token budget
    token_budget: int = 100000
    
    # Time budget
    time_budget_ms: float = 300000.0  # 5 minutes
    
    # Tool access
    available_tools: List[str] = field(default_factory=list)
    
    # External access
    can_search_web: bool = False
    can_call_api: bool = False
    can_read_files: bool = False
    can_write_files: bool = False
    
    # Memory
    can_use_vector_memory: bool = False
    can_use_long_term_memory: bool = False
    
    # Delegation
    can_delegate: bool = True
    max_delegations: int = 5
    
    def has_tool(self, tool_name: str) -> bool:
        """Vérifie si un tool est disponible."""
        return tool_name in self.available_tools


# ==========================================
# CAPABILITY COST
# ==========================================

@dataclass
class CapabilityCost:
    """
    Coût d'utilisation d'une capacité.
    
    Estimation du coût pour exécuter une tâche avec cette capacité.
    """
    estimated_tokens: int = 0
    estimated_time_ms: float = 0.0
    estimated_iterations: int = 1
    
    # Coût de délégation (si applicable)
    delegation_overhead_tokens: int = 500
    delegation_overhead_ms: float = 1000.0
    
    def total_cost_tokens(self, with_delegation: bool = False) -> int:
        """Calcule le coût total en tokens."""
        total = self.estimated_tokens
        if with_delegation:
            total += self.delegation_overhead_tokens
        return total
    
    def total_cost_ms(self, with_delegation: bool = False) -> float:
        """Calcule le coût total en temps."""
        total = self.estimated_time_ms
        if with_delegation:
            total += self.delegation_overhead_ms
        return total


# ==========================================
# AGENT CAPABILITY
# ==========================================

@dataclass
class AgentCapability:
    """
    Capacité complète d'un agent.
    
    Combine:
        - Domaine d'expertise
        - Niveau de compétence
        - Limites
        - Ressources
        - Coût estimé
    
    C'est le modèle central pour la décision cognitive:
        "Puis-je faire ça efficacement?"
    
    Example:
        capability = AgentCapability(
            domain=Domain.CODE,
            proficiency=0.9,
            limits=CapabilityLimits(max_tokens=4000),
            resources=CapabilityResources(token_budget=50000)
        )
        
        # Est-ce que je peux gérer cette tâche?
        assessment = capability.assess(task_complexity="complex", estimated_tokens=3000)
        
        if assessment.can_execute:
            result = await execute()
        else:
            # Déléguer
            await delegate()
    """
    # Identity
    name: str
    domain: Domain
    
    # Proficiency (0.0 to 1.0)
    proficiency: float = 0.8
    
    # Components
    limits: CapabilityLimits = field(default_factory=CapabilityLimits)
    resources: CapabilityResources = field(default_factory=CapabilityResources)
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # ==========================================
    # ASSESSMENT
    # ==========================================
    
    def assess(
        self,
        task_complexity: str = "simple",
        estimated_tokens: int = 0,
        estimated_iterations: int = 1,
        required_domain: Optional[Domain] = None,
    ) -> "CapabilityAssessment":
        """
        Évalue si l'agent peut exécuter une tâche.
        
        C'est LE cœur de la décision cognitive.
        
        Args:
            task_complexity: Complexité de la tâche
            estimated_tokens: Tokens estimés
            estimated_iterations: Itérations estimées
            required_domain: Domaine requis (optionnel)
            
        Returns:
            CapabilityAssessment avec recommandation
        """
        can_execute = True
        reasons: List[str] = []
        warnings: List[str] = []
        
        # Check domain match
        domain_match = True
        if required_domain and required_domain != Domain.GENERAL:
            domain_match = (
                self.domain == required_domain or
                self.domain == Domain.GENERAL
            )
            if not domain_match:
                can_execute = False
                reasons.append(f"Domain mismatch: need {required_domain.value}, have {self.domain.value}")
        
        # Check complexity
        complexity_order = ["simple", "moderate", "complex", "expert"]
        task_complexity_idx = complexity_order.index(task_complexity)
        max_complexity_idx = complexity_order.index(self.limits.max_task_complexity)
        
        if task_complexity_idx > max_complexity_idx:
            can_execute = False
            reasons.append(f"Task too complex: {task_complexity} > {self.limits.max_task_complexity}")
        
        # Check tokens
        if estimated_tokens > self.limits.max_context_tokens:
            can_execute = False
            reasons.append(f"Token limit exceeded: {estimated_tokens} > {self.limits.max_context_tokens}")
        elif estimated_tokens > self.limits.max_context_tokens * self.limits.context_window_utilization_threshold:
            warnings.append(f"Token usage high: {estimated_tokens} / {self.limits.max_context_tokens}")
        
        # Check iterations
        if estimated_iterations > self.limits.max_iterations:
            can_execute = False
            reasons.append(f"Iteration limit exceeded: {estimated_iterations} > {self.limits.max_iterations}")
        
        # Check resources
        if estimated_tokens > self.resources.token_budget:
            warnings.append(f"Token budget warning: {estimated_tokens} / {self.resources.token_budget}")
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            domain_match=domain_match,
            complexity_match=task_complexity_idx <= max_complexity_idx,
            token_margin=self.limits.max_context_tokens - estimated_tokens,
            proficiency=self.proficiency
        )
        
        # Recommendation
        if confidence < self.limits.min_confidence_threshold:
            can_execute = False
            reasons.append(f"Confidence too low: {confidence:.2f} < {self.limits.min_confidence_threshold}")
        
        should_delegate = (
            not can_execute or
            confidence < 0.7 or
            len(warnings) > 1
        )
        
        return CapabilityAssessment(
            capability_name=self.name,
            domain=self.domain,
            can_execute=can_execute,
            should_delegate=should_delegate,
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
            estimated_cost=CapabilityCost(
                estimated_tokens=estimated_tokens,
                estimated_iterations=estimated_iterations
            )
        )
    
    def _calculate_confidence(
        self,
        domain_match: bool,
        complexity_match: bool,
        token_margin: int,
        proficiency: float
    ) -> float:
        """Calcule la confiance d'exécution."""
        confidence = proficiency
        
        if not domain_match:
            confidence *= 0.5
        
        if not complexity_match:
            confidence *= 0.3
        
        # Token margin bonus/malus
        if token_margin > 2000:
            confidence *= 1.1  # Bonus
        elif token_margin < 500:
            confidence *= 0.8  # Malus
        
        return min(1.0, max(0.0, confidence))


# ==========================================
# CAPABILITY ASSESSMENT
# ==========================================

@dataclass
class CapabilityAssessment:
    """
    Résultat de l'évaluation d'une capacité.
    
    Décision: Puis-je faire ça? Dois-je déléguer?
    """
    capability_name: str
    domain: Domain
    can_execute: bool
    should_delegate: bool
    confidence: float
    
    # Details
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Cost
    estimated_cost: CapabilityCost = field(default_factory=CapabilityCost)
    
    @property
    def is_recommended(self) -> bool:
        """L'exécution est recommandée."""
        return self.can_execute and not self.should_delegate
    
    @property
    def delegation_recommended(self) -> bool:
        """La délégation est recommandée."""
        return self.should_delegate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability_name,
            "domain": self.domain.value,
            "can_execute": self.can_execute,
            "should_delegate": self.should_delegate,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "estimated_tokens": self.estimated_cost.estimated_tokens,
        }


# ==========================================
# CAPABILITY REGISTRY
# ==========================================

class CapabilityRegistry:
    """
    Registre des capacités d'un agent.
    
    Permet de gérer multiples capacités et trouver
    la meilleure pour une tâche.
    """
    
    def __init__(self):
        self._capabilities: Dict[str, AgentCapability] = {}
    
    def register(self, capability: AgentCapability) -> None:
        """Enregistre une capacité."""
        self._capabilities[capability.name] = capability
    
    def get(self, name: str) -> Optional[AgentCapability]:
        """Récupère une capacité par nom."""
        return self._capabilities.get(name)
    
    def get_for_domain(self, domain: Domain) -> List[AgentCapability]:
        """Récupère les capacités pour un domaine."""
        return [c for c in self._capabilities.values() if c.domain == domain]
    
    def find_best(
        self,
        domain: Optional[Domain] = None,
        task_complexity: str = "simple",
        estimated_tokens: int = 0,
    ) -> Optional[AgentCapability]:
        """Trouve la meilleure capacité pour une tâche."""
        candidates = list(self._capabilities.values())
        
        if domain:
            candidates = [c for c in candidates if c.domain == domain or c.domain == Domain.GENERAL]
        
        if not candidates:
            return None
        
        # Trier par confiance estimée
        def score(c: AgentCapability) -> float:
            assessment = c.assess(
                task_complexity=task_complexity,
                estimated_tokens=estimated_tokens
            )
            return assessment.confidence if assessment.can_execute else 0.0
        
        candidates.sort(key=score, reverse=True)
        return candidates[0]
    
    def list_all(self) -> List[AgentCapability]:
        """Liste toutes les capacités."""
        return list(self._capabilities.values())
