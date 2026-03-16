"""
Phoenix Agent - Agent Role
==========================

Rôles et spécialisations des agents Phoenix.

Tous les agents ne sont PAS identiques.
Un AgentRole définit:
    - Le type de travail (reasoning, execution, review, etc.)
    - Les domaines d'expertise
    - Les outils accessibles
    - Les limites spécifiques

Sans ce modèle, SubAgentPool devient juste une collection d'agents génériques.
Avec ce modèle, chaque agent a une IDENTITÉ et des COMPÉTENCES.

Architecture:
    AgentRole → AgentProfile → SubAgent → Execution

Version: 0.6.0 (Agent Specialization Model)
"""

from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from .capability import (
    Domain,
    CapabilityLimits,
    CapabilityResources,
)


logger = logging.getLogger("phoenix.agent_role")


# ==========================================
# AGENT ROLE TYPE
# ==========================================

class AgentRoleType(str, Enum):
    """
    Types de rôles d'agents.
    
    Chaque type a une responsabilité spécifique dans le système multi-agent.
    """
    # Meta-agents
    ORCHESTRATOR = "orchestrator"      # Coordonne les autres agents
    SUPERVISOR = "supervisor"          # Supervise et valide
    
    # Reasoning agents
    REASONER = "reasoner"              # Raisonnement et analyse
    PLANNER = "planner"                # Planification de tâches
    ANALYST = "analyst"                # Analyse de données
    
    # Execution agents
    EXECUTOR = "executor"              # Exécution de tâches
    RESEARCHER = "researcher"          # Recherche d'information
    CODER = "coder"                    # Génération de code
    WRITER = "writer"                  # Rédaction
    
    # Review agents
    REVIEWER = "reviewer"              # Révision et critique
    CRITIC = "critic"                  # Analyse critique
    VALIDATOR = "validator"            # Validation de résultats
    
    # Utility agents
    SUMMARIZER = "summarizer"          # Résumé et synthèse
    TRANSLATOR = "translator"          # Traduction/adaptation
    FORMATTER = "formatter"            # Formatage de sortie
    
    # Specialist agents
    DOMAIN_EXPERT = "domain_expert"    # Expert domaine spécifique
    TOOL_SPECIALIST = "tool_specialist"  # Expert outil spécifique
    
    # Worker agents
    WORKER = "worker"                  # Travailleur générique
    ASSISTANT = "assistant"            # Assistant polyvalent


# ==========================================
# ROLE CATEGORY
# ==========================================

class RoleCategory(str, Enum):
    """Catégories de rôles."""
    META = "meta"           # Orchestration, supervision
    REASONING = "reasoning" # Analyse, planification
    EXECUTION = "execution" # Travail concret
    REVIEW = "review"       # Validation, critique
    UTILITY = "utility"     # Fonctions utilitaires
    SPECIALIST = "specialist"  # Expertise pointue


# ==========================================
# AGENT ROLE
# ==========================================

@dataclass
class AgentRole:
    """
    Définition complète d'un rôle d'agent.
    
    Un rôle encapsule:
        - Type et catégorie
        - Domaines d'expertise
        - Compétences spécifiques
        - Limites adaptées au rôle
        - Outils accessibles
    
    Example:
        coder_role = AgentRole(
            role_type=AgentRoleType.CODER,
            category=RoleCategory.EXECUTION,
            domains=[Domain.CODE],
            skills=["python", "debugging", "refactoring"],
            limits=CapabilityLimits(max_iterations=20),
            tools=["python_repl", "file_read", "file_write"],
        )
        
        # Créer un agent avec ce rôle
        agent = SubAgent(
            config=SubAgentConfig(
                role=coder_role,
                ...
            )
        )
    """
    # Identity
    role_type: AgentRoleType
    name: str = ""
    description: str = ""
    
    # Classification
    category: RoleCategory = RoleCategory.EXECUTION
    
    # Expertise
    domains: List[Domain] = field(default_factory=lambda: [Domain.GENERAL])
    skills: List[str] = field(default_factory=list)
    
    # Capabilities
    limits: CapabilityLimits = field(default_factory=CapabilityLimits)
    resources: CapabilityResources = field(default_factory=CapabilityResources)
    
    # Tools
    tools: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    
    # Behavior
    can_delegate: bool = True
    can_use_subagents: bool = False
    max_subagent_depth: int = 0
    
    # Priority for task assignment
    priority: int = 5  # 1-10
    
    def __post_init__(self):
        if not self.name:
            self.name = self.role_type.value
    
    # ==========================================
    # COMPATIBILITY CHECKS
    # ==========================================
    
    def can_handle_domain(self, domain: Domain) -> bool:
        """Vérifie si le rôle peut gérer un domaine."""
        return (
            Domain.GENERAL in self.domains or
            domain in self.domains
        )
    
    def has_skill(self, skill: str) -> bool:
        """Vérifie si le rôle a une compétence."""
        return skill.lower() in [s.lower() for s in self.skills]
    
    def has_tool(self, tool: str) -> bool:
        """Vérifie si le rôle peut utiliser un outil."""
        return tool in self.tools and tool not in self.forbidden_tools
    
    def is_compatible_with_task(
        self,
        task_type: str,
        domain: Optional[Domain] = None,
        required_tools: Optional[List[str]] = None,
    ) -> bool:
        """
        Vérifie la compatibilité avec une tâche.
        
        Args:
            task_type: Type de tâche
            domain: Domaine requis
            required_tools: Outils requis
            
        Returns:
            True si compatible
        """
        # Check domain
        if domain and not self.can_handle_domain(domain):
            return False
        
        # Check tools
        if required_tools:
            for tool in required_tools:
                if not self.has_tool(tool):
                    return False
        
        return True
    
    def get_compatibility_score(
        self,
        task_type: str,
        domain: Optional[Domain] = None,
        required_skills: Optional[List[str]] = None,
    ) -> float:
        """
        Calcule un score de compatibilité (0.0 à 1.0).
        
        Plus le score est élevé, plus le rôle est adapté.
        """
        score = 0.5  # Base
        
        # Domain match
        if domain:
            if domain in self.domains:
                score += 0.3
            elif Domain.GENERAL in self.domains:
                score += 0.1
        
        # Skills match
        if required_skills:
            matching = sum(1 for s in required_skills if self.has_skill(s))
            total = len(required_skills)
            if total > 0:
                score += 0.2 * (matching / total)
        
        # Category match
        task_category_map = {
            "code": RoleCategory.EXECUTION,
            "research": RoleCategory.EXECUTION,
            "analysis": RoleCategory.REASONING,
            "planning": RoleCategory.REASONING,
            "review": RoleCategory.REVIEW,
            "summary": RoleCategory.UTILITY,
        }
        
        expected_category = task_category_map.get(task_type.lower())
        if expected_category and self.category == expected_category:
            score += 0.1
        
        return min(1.0, score)
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "role_type": self.role_type.value,
            "name": self.name,
            "category": self.category.value,
            "domains": [d.value for d in self.domains],
            "skills": self.skills,
            "tools": self.tools,
            "can_delegate": self.can_delegate,
            "priority": self.priority,
        }


# ==========================================
# PREDEFINED ROLES
# ==========================================

def get_predefined_roles() -> Dict[AgentRoleType, AgentRole]:
    """
    Retourne les rôles prédéfinis.
    
    Ces rôles couvrent les cas d'usage les plus courants.
    """
    return {
        # Meta-agents
        AgentRoleType.ORCHESTRATOR: AgentRole(
            role_type=AgentRoleType.ORCHESTRATOR,
            name="Phoenix Orchestrator",
            category=RoleCategory.META,
            description="Coordinates and delegates to other agents",
            domains=[Domain.GENERAL],
            skills=["coordination", "delegation", "planning"],
            limits=CapabilityLimits(
                max_context_tokens=8000,
                max_iterations=15,
                max_reasoning_depth=6,
            ),
            can_delegate=True,
            can_use_subagents=True,
            max_subagent_depth=3,
            priority=10,
        ),
        
        AgentRoleType.SUPERVISOR: AgentRole(
            role_type=AgentRoleType.SUPERVISOR,
            name="Supervisor",
            category=RoleCategory.META,
            description="Supervises and validates agent outputs",
            domains=[Domain.GENERAL],
            skills=["validation", "quality_control", "feedback"],
            can_delegate=False,
            priority=9,
        ),
        
        # Reasoning agents
        AgentRoleType.REASONER: AgentRole(
            role_type=AgentRoleType.REASONER,
            name="Deep Reasoner",
            category=RoleCategory.REASONING,
            description="Performs deep reasoning and analysis",
            domains=[Domain.REASONING, Domain.ANALYSIS],
            skills=["reasoning", "logic", "problem_solving"],
            limits=CapabilityLimits(
                max_reasoning_depth=10,
                max_iterations=20,
            ),
            priority=8,
        ),
        
        AgentRoleType.PLANNER: AgentRole(
            role_type=AgentRoleType.PLANNER,
            name="Task Planner",
            category=RoleCategory.REASONING,
            description="Plans and decomposes complex tasks",
            domains=[Domain.PLANNING, Domain.REASONING],
            skills=["planning", "decomposition", "prioritization"],
            limits=CapabilityLimits(
                max_iterations=10,
            ),
            can_delegate=True,
            can_use_subagents=True,
            max_subagent_depth=2,
            priority=8,
        ),
        
        AgentRoleType.ANALYST: AgentRole(
            role_type=AgentRoleType.ANALYST,
            name="Data Analyst",
            category=RoleCategory.REASONING,
            description="Analyzes data and provides insights",
            domains=[Domain.ANALYSIS, Domain.MATH],
            skills=["analysis", "statistics", "visualization"],
            tools=["data_read", "chart_generate"],
            priority=7,
        ),
        
        # Execution agents
        AgentRoleType.EXECUTOR: AgentRole(
            role_type=AgentRoleType.EXECUTOR,
            name="Task Executor",
            category=RoleCategory.EXECUTION,
            description="Executes assigned tasks efficiently",
            domains=[Domain.GENERAL],
            skills=["execution", "following_instructions"],
            limits=CapabilityLimits(
                max_iterations=25,
            ),
            priority=6,
        ),
        
        AgentRoleType.RESEARCHER: AgentRole(
            role_type=AgentRoleType.RESEARCHER,
            name="Researcher",
            category=RoleCategory.EXECUTION,
            description="Searches and gathers information",
            domains=[Domain.RESEARCH, Domain.GENERAL],
            skills=["research", "search", "synthesis"],
            tools=["web_search", "file_read"],
            priority=7,
        ),
        
        AgentRoleType.CODER: AgentRole(
            role_type=AgentRoleType.CODER,
            name="Code Specialist",
            category=RoleCategory.EXECUTION,
            description="Writes and debugs code",
            domains=[Domain.CODE],
            skills=["python", "javascript", "debugging", "refactoring"],
            tools=["python_repl", "file_read", "file_write"],
            limits=CapabilityLimits(
                max_iterations=30,
            ),
            priority=8,
        ),
        
        AgentRoleType.WRITER: AgentRole(
            role_type=AgentRoleType.WRITER,
            name="Content Writer",
            category=RoleCategory.EXECUTION,
            description="Creates and edits written content",
            domains=[Domain.WRITING, Domain.CREATIVE],
            skills=["writing", "editing", "formatting"],
            priority=6,
        ),
        
        # Review agents
        AgentRoleType.REVIEWER: AgentRole(
            role_type=AgentRoleType.REVIEWER,
            name="Quality Reviewer",
            category=RoleCategory.REVIEW,
            description="Reviews and provides feedback",
            domains=[Domain.GENERAL],
            skills=["review", "feedback", "quality_assurance"],
            priority=7,
        ),
        
        AgentRoleType.CRITIC: AgentRole(
            role_type=AgentRoleType.CRITIC,
            name="Critic",
            category=RoleCategory.REVIEW,
            description="Provides critical analysis and alternative perspectives",
            domains=[Domain.REASONING],
            skills=["critique", "analysis", "alternative_thinking"],
            limits=CapabilityLimits(
                max_reasoning_depth=8,
            ),
            priority=7,
        ),
        
        AgentRoleType.VALIDATOR: AgentRole(
            role_type=AgentRoleType.VALIDATOR,
            name="Result Validator",
            category=RoleCategory.REVIEW,
            description="Validates outputs against requirements",
            domains=[Domain.GENERAL],
            skills=["validation", "testing", "verification"],
            tools=["test_runner"],
            priority=7,
        ),
        
        # Utility agents
        AgentRoleType.SUMMARIZER: AgentRole(
            role_type=AgentRoleType.SUMMARIZER,
            name="Summarizer",
            category=RoleCategory.UTILITY,
            description="Summarizes and synthesizes content",
            domains=[Domain.GENERAL],
            skills=["summarization", "synthesis", "extraction"],
            limits=CapabilityLimits(
                max_context_tokens=12000,  # Can handle large context
            ),
            priority=5,
        ),
        
        AgentRoleType.WORKER: AgentRole(
            role_type=AgentRoleType.WORKER,
            name="General Worker",
            category=RoleCategory.EXECUTION,
            description="Performs general tasks",
            domains=[Domain.GENERAL],
            skills=["general_tasks"],
            limits=CapabilityLimits(
                max_iterations=15,
            ),
            priority=4,
        ),
        
        AgentRoleType.DOMAIN_EXPERT: AgentRole(
            role_type=AgentRoleType.DOMAIN_EXPERT,
            name="Domain Expert",
            category=RoleCategory.SPECIALIST,
            description="Expert in specific domain",
            domains=[Domain.GENERAL],
            skills=["domain_expertise"],
            limits=CapabilityLimits(
                max_reasoning_depth=12,
            ),
            priority=9,
        ),
    }


# ==========================================
# ROLE REGISTRY
# ==========================================

class RoleRegistry:
    """
    Registre des rôles disponibles.
    
    Permet de trouver le meilleur rôle pour une tâche.
    """
    
    def __init__(self):
        self._roles: Dict[str, AgentRole] = {}
        self._load_predefined()
    
    def _load_predefined(self) -> None:
        """Charge les rôles prédéfinis."""
        for role_type, role in get_predefined_roles().items():
            self._roles[role_type.value] = role
    
    def register(self, role: AgentRole) -> None:
        """Enregistre un rôle."""
        self._roles[role.role_type.value] = role
    
    def get(self, role_type: AgentRoleType) -> Optional[AgentRole]:
        """Récupère un rôle par type."""
        return self._roles.get(role_type.value)
    
    def get_by_name(self, name: str) -> Optional[AgentRole]:
        """Récupère un rôle par nom."""
        for role in self._roles.values():
            if role.name == name or role.role_type.value == name:
                return role
        return None
    
    def find_best_for_task(
        self,
        task_type: str,
        domain: Optional[Domain] = None,
        required_skills: Optional[List[str]] = None,
        required_tools: Optional[List[str]] = None,
    ) -> Optional[AgentRole]:
        """
        Trouve le meilleur rôle pour une tâche.
        
        Args:
            task_type: Type de tâche
            domain: Domaine requis
            required_skills: Compétences requises
            required_tools: Outils requis
            
        Returns:
            Le rôle le plus adapté ou None
        """
        candidates = []
        
        for role in self._roles.values():
            # Check basic compatibility
            if not role.is_compatible_with_task(task_type, domain, required_tools):
                continue
            
            # Calculate score
            score = role.get_compatibility_score(task_type, domain, required_skills)
            candidates.append((role, score))
        
        if not candidates:
            return None
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[0][0]
    
    def list_roles(self) -> List[AgentRole]:
        """Liste tous les rôles."""
        return list(self._roles.values())
    
    def list_by_category(self, category: RoleCategory) -> List[AgentRole]:
        """Liste les rôles par catégorie."""
        return [r for r in self._roles.values() if r.category == category]
    
    def list_by_domain(self, domain: Domain) -> List[AgentRole]:
        """Liste les rôles par domaine."""
        return [r for r in self._roles.values() if r.can_handle_domain(domain)]
