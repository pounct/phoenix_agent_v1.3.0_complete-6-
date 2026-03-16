"""
Phoenix Agent - Result Synthesizer
==================================

Fusion et synthèse des résultats multi-agents.

Quand plusieurs agents travaillent sur une tâche (parallèle ou séquentiel),
il faut:
    1. Collecter leurs résultats
    2. Résoudre les conflits
    3. Fusionner en une réponse cohérente
    4. Attribuer la confiance finale

C'est le rôle du ResultSynthesizer.

Sans ce composant, multi-agent = chaos.
Avec ce composant, multi-agent = orchestration cohérente.

Architecture:
    SubAgent[] → Results[] → ResultSynthesizer → FinalResult

Version: 0.6.0 (Multi-Agent Result Fusion)
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import re

from .task import Task, TaskResult, TaskStatus
from .agent_role import AgentRoleType


logger = logging.getLogger("phoenix.result_synthesizer")


# ==========================================
# SYNTHESIS STRATEGY
# ==========================================

class SynthesisStrategy(str, Enum):
    """Stratégies de synthèse."""
    BEST_SINGLE = "best_single"           # Prendre le meilleur résultat unique
    SEQUENTIAL_MERGE = "sequential_merge" # Fusionner dans l'ordre
    PARALLEL_VOTE = "parallel_vote"       # Vote entre résultats parallèles
    HIERARCHICAL = "hierarchical"         # Fusion hiérarchique par rôle
    CONSENSUS = "consensus"               # Consensus entre résultats
    WEIGHTED_AVERAGE = "weighted_average" # Moyenne pondérée des confidences


# ==========================================
# RESULT CONFLICT
# ==========================================

class ConflictType(str, Enum):
    """Types de conflits entre résultats."""
    CONTRADICTION = "contradiction"       # Les résultats se contredisent
    INCOMPLETE = "incomplete"             # Certains résultats sont incomplets
    REDUNDANT = "redundant"               # Information redondante
    FORMAT_MISMATCH = "format_mismatch"   # Formats différents
    QUALITY_VARIANCE = "quality_variance" # Qualités très différentes


@dataclass
class ResultConflict:
    """Représente un conflit entre résultats."""
    conflict_type: ConflictType
    source_results: List[str]  # IDs des résultats en conflit
    description: str
    resolution_suggestion: str
    severity: float = 0.5  # 0.0 = minor, 1.0 = critical


# ==========================================
# AGENT RESULT
# ==========================================

@dataclass
class AgentResult:
    """
    Résultat d'un agent individuel.
    
    Encapsule le résultat avec métadonnées pour la synthèse.
    """
    agent_id: str
    agent_role: AgentRoleType
    task_id: str
    
    # Content
    content: str
    confidence: float = 0.8
    
    # Quality metrics
    quality_score: float = 0.8
    completeness: float = 1.0
    
    # Execution info
    execution_time_ms: float = 0.0
    iterations_used: int = 1
    tokens_used: int = 0
    
    # Status
    success: bool = True
    error: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Le résultat est valide."""
        return self.success and bool(self.content)
    
    @property
    def weight(self) -> float:
        """Poids pour la synthèse."""
        return self.confidence * self.quality_score * self.completeness


# ==========================================
# SYNTHESIS CONTEXT
# ==========================================

@dataclass
class SynthesisContext:
    """
    Contexte pour la synthèse.
    
    Inclut toutes les informations nécessaires.
    """
    original_task: Task
    results: List[AgentResult]
    
    # Task info
    task_type: str = "general"
    expected_format: str = "text"
    
    # Synthesis preferences
    prefer_quality: bool = True
    prefer_completeness: bool = True
    max_length: Optional[int] = None
    
    # Previous synthesis
    previous_attempts: int = 0


# ==========================================
# SYNTHESIS RESULT
# ==========================================

@dataclass
class SynthesisResult:
    """
    Résultat de la synthèse.
    
    Le résultat final après fusion multi-agent.
    """
    # Final content
    content: str
    confidence: float
    
    # Sources
    source_agents: List[str]
    synthesis_strategy: SynthesisStrategy
    
    # Quality
    quality_score: float
    completeness: float
    
    # Conflicts resolved
    conflicts_resolved: List[ResultConflict] = field(default_factory=list)
    
    # Metrics
    total_execution_time_ms: float = 0.0
    total_tokens_used: int = 0
    total_iterations: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """La synthèse a réussi."""
        return bool(self.content) and self.confidence > 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "confidence": self.confidence,
            "source_agents": self.source_agents,
            "strategy": self.synthesis_strategy.value,
            "quality": self.quality_score,
            "conflicts_resolved": len(self.conflicts_resolved),
        }


# ==========================================
# RESULT SYNTHESIZER
# ==========================================

class ResultSynthesizer:
    """
    Synthétiseur de résultats multi-agents.
    
    Responsabilités:
        1. Collecter les résultats
        2. Détecter les conflits
        3. Résoudre les conflits
        4. Fusionner en résultat final
        5. Calculer confiance et qualité
    
    Example:
        synthesizer = ResultSynthesizer()
        
        # Ajouter des résultats
        synthesizer.add_result(agent_1_result)
        synthesizer.add_result(agent_2_result)
        
        # Synthétiser
        final = synthesizer.synthesize(
            task=original_task,
            strategy=SynthesisStrategy.PARALLEL_VOTE
        )
        
        print(final.content)
        print(f"Confidence: {final.confidence}")
    """
    
    def __init__(
        self,
        default_strategy: SynthesisStrategy = SynthesisStrategy.SEQUENTIAL_MERGE,
    ):
        self.default_strategy = default_strategy
        self._results: List[AgentResult] = []
    
    # ==========================================
    # RESULT COLLECTION
    # ==========================================
    
    def add_result(self, result: AgentResult) -> None:
        """Ajoute un résultat."""
        self._results.append(result)
        logger.debug(f"Added result from {result.agent_id}")
    
    def add_results(self, results: List[AgentResult]) -> None:
        """Ajoute plusieurs résultats."""
        self._results.extend(results)
    
    def clear(self) -> None:
        """Efface les résultats."""
        self._results.clear()
    
    # ==========================================
    # MAIN SYNTHESIS
    # ==========================================
    
    def synthesize(
        self,
        task: Task,
        strategy: Optional[SynthesisStrategy] = None,
    ) -> SynthesisResult:
        """
        Synthétise tous les résultats.
        
        C'est LA méthode centrale du ResultSynthesizer.
        
        Args:
            task: La tâche originale
            strategy: Stratégie de synthèse (défaut: self.default_strategy)
            
        Returns:
            SynthesisResult final
        """
        if not self._results:
            return self._empty_result(task)
        
        strategy = strategy or self.default_strategy
        
        # Filtrer les résultats valides
        valid_results = [r for r in self._results if r.is_valid]
        
        if not valid_results:
            return self._error_result(task, "No valid results")
        
        # Détecter les conflits
        conflicts = self._detect_conflicts(valid_results)
        
        # Choisir et appliquer la stratégie
        if strategy == SynthesisStrategy.BEST_SINGLE:
            content, confidence = self._synthesize_best_single(valid_results)
        elif strategy == SynthesisStrategy.SEQUENTIAL_MERGE:
            content, confidence = self._synthesize_sequential(valid_results, task)
        elif strategy == SynthesisStrategy.PARALLEL_VOTE:
            content, confidence = self._synthesize_vote(valid_results)
        elif strategy == SynthesisStrategy.HIERARCHICAL:
            content, confidence = self._synthesize_hierarchical(valid_results)
        else:
            content, confidence = self._synthesize_sequential(valid_results, task)
        
        # Calculer métriques
        total_time = sum(r.execution_time_ms for r in valid_results)
        total_tokens = sum(r.tokens_used for r in valid_results)
        total_iterations = sum(r.iterations_used for r in valid_results)
        
        # Qualité finale
        quality = self._calculate_quality(valid_results, conflicts)
        completeness = self._calculate_completeness(valid_results)
        
        return SynthesisResult(
            content=content,
            confidence=confidence,
            source_agents=[r.agent_id for r in valid_results],
            synthesis_strategy=strategy,
            quality_score=quality,
            completeness=completeness,
            conflicts_resolved=conflicts,
            total_execution_time_ms=total_time,
            total_tokens_used=total_tokens,
            total_iterations=total_iterations,
            metadata={
                "results_count": len(valid_results),
                "conflicts_count": len(conflicts),
            }
        )
    
    # ==========================================
    # SYNTHESIS STRATEGIES
    # ==========================================
    
    def _synthesize_best_single(
        self,
        results: List[AgentResult],
    ) -> Tuple[str, float]:
        """Sélectionne le meilleur résultat unique."""
        # Trier par poids
        sorted_results = sorted(results, key=lambda r: r.weight, reverse=True)
        best = sorted_results[0]
        
        logger.info(f"Best single: {best.agent_id} (weight={best.weight:.2f})")
        
        return best.content, best.confidence
    
    def _synthesize_sequential(
        self,
        results: List[AgentResult],
        task: Task,
    ) -> Tuple[str, float]:
        """Fusionne séquentiellement."""
        if len(results) == 1:
            return results[0].content, results[0].confidence
        
        # Construire la fusion
        parts = []
        total_confidence = 0.0
        total_weight = 0.0
        
        for i, result in enumerate(results):
            # Ajouter avec transition si nécessaire
            if i > 0:
                parts.append("\n\n")
            
            parts.append(result.content)
            
            # Moyenne pondérée
            total_confidence += result.confidence * result.weight
            total_weight += result.weight
        
        content = "".join(parts)
        confidence = total_confidence / total_weight if total_weight > 0 else 0.5
        
        logger.info(f"Sequential merge: {len(results)} results, confidence={confidence:.2f}")
        
        return content, confidence
    
    def _synthesize_vote(
        self,
        results: List[AgentResult],
    ) -> Tuple[str, float]:
        """Vote entre résultats parallèles."""
        if len(results) == 1:
            return results[0].content, results[0].confidence
        
        # Grouper par similarité
        groups = self._group_similar_results(results)
        
        # Prendre le groupe le plus large avec le meilleur score
        best_group = max(groups, key=lambda g: len(g) * sum(r.weight for r in g) / len(g))
        
        # Fusionner le groupe
        content = best_group[0].content  # Ou fusion
        
        # Confiance = proportion + qualité
        proportion = len(best_group) / len(results)
        avg_quality = sum(r.quality_score for r in best_group) / len(best_group)
        confidence = proportion * 0.5 + avg_quality * 0.5
        
        logger.info(f"Vote: {len(best_group)}/{len(results)} agree, confidence={confidence:.2f}")
        
        return content, confidence
    
    def _synthesize_hierarchical(
        self,
        results: List[AgentResult],
    ) -> Tuple[str, float]:
        """Fusion hiérarchique par rôle."""
        # Priorité des rôles
        role_priority = {
            AgentRoleType.ORCHESTRATOR: 10,
            AgentRoleType.SUPERVISOR: 9,
            AgentRoleType.REVIEWER: 8,
            AgentRoleType.VALIDATOR: 8,
            AgentRoleType.CRITIC: 7,
            AgentRoleType.REASONER: 6,
            AgentRoleType.ANALYST: 6,
            AgentRoleType.PLANNER: 5,
            AgentRoleType.EXECUTOR: 4,
            AgentRoleType.CODER: 4,
            AgentRoleType.WRITER: 4,
            AgentRoleType.RESEARCHER: 3,
            AgentRoleType.SUMMARIZER: 3,
            AgentRoleType.WORKER: 2,
        }
        
        # Trier par priorité de rôle puis par qualité
        sorted_results = sorted(
            results,
            key=lambda r: (
                role_priority.get(r.agent_role, 0),
                r.quality_score
            ),
            reverse=True
        )
        
        best = sorted_results[0]
        
        logger.info(f"Hierarchical: {best.agent_role.value} wins, quality={best.quality_score:.2f}")
        
        return best.content, best.confidence
    
    # ==========================================
    # CONFLICT DETECTION
    # ==========================================
    
    def _detect_conflicts(self, results: List[AgentResult]) -> List[ResultConflict]:
        """Détecte les conflits entre résultats."""
        conflicts = []
        
        if len(results) < 2:
            return conflicts
        
        # Check quality variance
        qualities = [r.quality_score for r in results]
        quality_variance = max(qualities) - min(qualities)
        
        if quality_variance > 0.5:
            conflicts.append(ResultConflict(
                conflict_type=ConflictType.QUALITY_VARIANCE,
                source_results=[r.agent_id for r in results],
                description=f"Quality varies from {min(qualities):.2f} to {max(qualities):.2f}",
                resolution_suggestion="Use hierarchical synthesis with best quality",
                severity=quality_variance,
            ))
        
        # Check completeness
        for result in results:
            if result.completeness < 0.5:
                conflicts.append(ResultConflict(
                    conflict_type=ConflictType.INCOMPLETE,
                    source_results=[result.agent_id],
                    description=f"Result from {result.agent_id} is incomplete",
                    resolution_suggestion="Combine with other results",
                    severity=1.0 - result.completeness,
                ))
        
        return conflicts
    
    def _group_similar_results(
        self,
        results: List[AgentResult],
        similarity_threshold: float = 0.7,
    ) -> List[List[AgentResult]]:
        """Groupe les résultats similaires."""
        groups: List[List[AgentResult]] = []
        
        for result in results:
            matched = False
            
            for group in groups:
                # Check similarity with first in group
                if self._calculate_similarity(result.content, group[0].content) >= similarity_threshold:
                    group.append(result)
                    matched = True
                    break
            
            if not matched:
                groups.append([result])
        
        return groups
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes."""
        # Simple word overlap
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    # ==========================================
    # QUALITY CALCULATIONS
    # ==========================================
    
    def _calculate_quality(
        self,
        results: List[AgentResult],
        conflicts: List[ResultConflict],
    ) -> float:
        """Calcule le score de qualité final."""
        if not results:
            return 0.0
        
        # Base quality
        avg_quality = sum(r.quality_score for r in results) / len(results)
        
        # Penalty for conflicts
        conflict_penalty = sum(c.severity * 0.1 for c in conflicts)
        
        # Final
        return max(0.0, min(1.0, avg_quality - conflict_penalty))
    
    def _calculate_completeness(self, results: List[AgentResult]) -> float:
        """Calcule la complétude."""
        if not results:
            return 0.0
        
        # Average completeness
        return sum(r.completeness for r in results) / len(results)
    
    # ==========================================
    # HELPERS
    # ==========================================
    
    def _empty_result(self, task: Task) -> SynthesisResult:
        """Résultat vide."""
        return SynthesisResult(
            content="",
            confidence=0.0,
            source_agents=[],
            synthesis_strategy=self.default_strategy,
            quality_score=0.0,
            completeness=0.0,
            metadata={"error": "No results to synthesize"},
        )
    
    def _error_result(self, task: Task, error: str) -> SynthesisResult:
        """Résultat d'erreur."""
        return SynthesisResult(
            content="",
            confidence=0.0,
            source_agents=[],
            synthesis_strategy=self.default_strategy,
            quality_score=0.0,
            completeness=0.0,
            metadata={"error": error},
        )
    
    # ==========================================
    # BATCH OPERATIONS
    # ==========================================
    
    def synthesize_all(
        self,
        task_results: Dict[str, List[AgentResult]],
        default_strategy: Optional[SynthesisStrategy] = None,
    ) -> Dict[str, SynthesisResult]:
        """
        Synthétise plusieurs tâches en parallèle.
        
        Args:
            task_results: Dict task_id → results
            default_strategy: Stratégie par défaut
            
        Returns:
            Dict task_id → synthesis_result
        """
        results = {}
        
        for task_id, agent_results in task_results.items():
            self.clear()
            self.add_results(agent_results)
            
            # Créer une tâche minimale
            task = Task(task_id=task_id, goal="")
            
            results[task_id] = self.synthesize(task, default_strategy)
        
        return results


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def synthesize_results(
    results: List[AgentResult],
    task: Task,
    strategy: SynthesisStrategy = SynthesisStrategy.SEQUENTIAL_MERGE,
) -> SynthesisResult:
    """
    Fonction utilitaire pour synthétiser rapidement.
    
    Example:
        final = synthesize_results(
            results=[result1, result2, result3],
            task=task,
            strategy=SynthesisStrategy.PARALLEL_VOTE
        )
    """
    synthesizer = ResultSynthesizer(default_strategy=strategy)
    synthesizer.add_results(results)
    return synthesizer.synthesize(task, strategy)
