"""
Phoenix Agent - Memory Manager
==============================

Gestionnaire de mémoire et contexte pour Phoenix.

Responsabilités:
    - Gérer la fenêtre de contexte
    - Compresser le contexte quand overflow
    - Externaliser la mémoire (v1+)
    - Préparer la délégation quand mémoire insuffisante

Architecture:
    Session → MemoryManager → Context (optimisé)

STRATÉGIES DE GESTION MÉMOIRE:
    1. Sliding window: Garder les N derniers messages
    2. Summarization: Résumer l'historique
    3. Prioritization: Garder les messages importants
    4. Delegation: Déléguer si contexte trop complexe

Version: 0.4.0 (Structure préparée)
Version: 1.0.0 (Implémentation complète prévue)
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..contract.session import Message, Session


logger = logging.getLogger("phoenix.memory_manager")


# ==========================================
# MEMORY STRATEGY
# ==========================================

class MemoryStrategy(str, Enum):
    """Stratégies de gestion mémoire."""
    SLIDING_WINDOW = "sliding_window"     # Garder les N derniers
    SUMMARIZATION = "summarization"         # Résumer l'historique
    PRIORITIZATION = "prioritization"       # Prioriser les importants
    DELEGATION = "delegation"               # Déléguer si overflow


# ==========================================
# MEMORY STATS
# ==========================================

@dataclass
class MemoryStats:
    """Statistiques de mémoire."""
    total_messages: int = 0
    total_tokens_estimate: int = 0
    window_messages: int = 0
    window_tokens_estimate: int = 0
    compression_ratio: float = 1.0
    overflow_count: int = 0


# ==========================================
# MEMORY WINDOW
# ==========================================

@dataclass
class MemoryWindow:
    """
    Fenêtre de mémoire active.
    
    Représente la partie du contexte actuellement utilisable.
    """
    messages: List[Message] = field(default_factory=list)
    summary: str = ""
    compressed: bool = False
    
    # Métadonnées
    original_message_count: int = 0
    tokens_estimate: int = 0
    
    @property
    def is_compressed(self) -> bool:
        return self.compressed or bool(self.summary)
    
    def to_context_string(self) -> str:
        """Convertit en string pour le contexte."""
        parts = []
        
        if self.summary:
            parts.append(f"[CONVERSATION SUMMARY]\n{self.summary}\n")
        
        for msg in self.messages:
            role_prefix = {
                'system': '[SYSTEM]',
                'user': '[USER]',
                'assistant': '[ASSISTANT]',
                'tool': '[TOOL]',
            }.get(msg.role, f'[{msg.role}]')
            parts.append(f"{role_prefix}: {msg.content}")
        
        return "\n\n".join(parts)


# ==========================================
# MEMORY MANAGER CONFIG
# ==========================================

@dataclass
class MemoryManagerConfig:
    """Configuration du gestionnaire de mémoire."""
    # Limites
    max_tokens: int = 4000
    max_messages: int = 50
    
    # Stratégies
    default_strategy: MemoryStrategy = MemoryStrategy.SLIDING_WINDOW
    compression_threshold: float = 0.8  # Compresser à 80% de max_tokens
    
    # Sliding window
    window_size: int = 10  # Nombre de messages à garder
    
    # Prioritization
    always_keep_system: bool = True
    always_keep_last_n: int = 3
    
    # Delegation threshold
    delegation_threshold: float = 0.95  # Déléguer si > 95% de max_tokens


# ==========================================
# MEMORY MANAGER
# ==========================================

class MemoryManager:
    """
    Gestionnaire de mémoire pour Phoenix.
    
    v0.4: Sliding window + estimation basique
    v1.0: Summarization + Vector memory + Delegation
    
    Responsabilités:
        - Estimer la taille du contexte
        - Appliquer la stratégie de gestion
        - Compresser si nécessaire
        - Préparer la délégation si overflow
    
    Example:
        config = MemoryManagerConfig(max_tokens=4000)
        manager = MemoryManager(config)
        
        # Analyser une session
        analysis = manager.analyze(session)
        
        if analysis.should_compress:
            window = manager.compress(session)
        elif analysis.should_delegate:
            # Préparer la délégation
            ...
    """
    
    def __init__(self, config: Optional[MemoryManagerConfig] = None):
        self.config = config or MemoryManagerConfig()
    
    # ==========================================
    # ANALYSIS
    # ==========================================
    
    def analyze(self, session: Session) -> "MemoryAnalysis":
        """
        Analyse une session pour déterminer l'action.
        
        Args:
            session: La session à analyser
            
        Returns:
            MemoryAnalysis avec recommandations
        """
        total_tokens = self._estimate_tokens(session)
        utilization = total_tokens / self.config.max_tokens
        
        should_compress = (
            utilization >= self.config.compression_threshold
            and len(session.messages) > self.config.window_size
        )
        
        should_delegate = (
            utilization >= self.config.delegation_threshold
        )
        
        return MemoryAnalysis(
            session_id=session.session_id,
            total_messages=len(session.messages),
            estimated_tokens=total_tokens,
            utilization=utilization,
            should_compress=should_compress,
            should_delegate=should_delegate,
            recommended_strategy=self._get_strategy(utilization),
        )
    
    def _estimate_tokens(self, session: Session) -> int:
        """Estime le nombre de tokens."""
        # Approximation: 1 token ≈ 4 chars
        total_chars = sum(len(m.content) for m in session.messages)
        return total_chars // 4
    
    def _get_strategy(self, utilization: float) -> MemoryStrategy:
        """Détermine la stratégie selon l'utilisation."""
        if utilization >= self.config.delegation_threshold:
            return MemoryStrategy.DELEGATION
        elif utilization >= self.config.compression_threshold:
            return MemoryStrategy.SUMMARIZATION
        else:
            return self.config.default_strategy
    
    # ==========================================
    # COMPRESSION
    # ==========================================
    
    def compress(
        self,
        session: Session,
        strategy: Optional[MemoryStrategy] = None
    ) -> MemoryWindow:
        """
        Compresse le contexte d'une session.
        
        v0.4: Sliding window simple
        v1.0: Summarization via LLM
        
        Args:
            session: La session à compresser
            strategy: Stratégie à utiliser (défaut: config)
            
        Returns:
            MemoryWindow compressée
        """
        strategy = strategy or self.config.default_strategy
        
        if strategy == MemoryStrategy.SLIDING_WINDOW:
            return self._sliding_window(session)
        elif strategy == MemoryStrategy.PRIORITIZATION:
            return self._prioritization(session)
        else:
            # Défaut: sliding window
            return self._sliding_window(session)
    
    def _sliding_window(self, session: Session) -> MemoryWindow:
        """Applique une sliding window."""
        messages = session.messages.copy()
        original_count = len(messages)
        
        # Garder system + derniers messages
        result = []
        
        # System message
        if self.config.always_keep_system:
            system_msgs = [m for m in messages if m.role == 'system']
            result.extend(system_msgs)
            messages = [m for m in messages if m.role != 'system']
        
        # Derniers messages
        keep_count = self.config.window_size - len(result)
        if len(messages) > keep_count:
            messages = messages[-keep_count:]
        
        result.extend(messages)
        
        return MemoryWindow(
            messages=result,
            compressed=True,
            original_message_count=original_count,
            tokens_estimate=self._estimate_tokens_from_messages(result),
        )
    
    def _prioritization(self, session: Session) -> MemoryWindow:
        """Priorise les messages importants."""
        messages = session.messages.copy()
        original_count = len(messages)
        
        # Scorer les messages
        scored = [(self._score_message(m), m) for m in messages]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Garder les meilleurs
        result = [m for _, m in scored[:self.config.window_size]]
        
        # Réordonner chronologiquement
        result.sort(key=lambda m: m.timestamp)
        
        return MemoryWindow(
            messages=result,
            compressed=True,
            original_message_count=original_count,
            tokens_estimate=self._estimate_tokens_from_messages(result),
        )
    
    def _score_message(self, message: Message) -> float:
        """Score un message pour la priorisation."""
        score = 1.0
        
        # System = haute priorité
        if message.role == 'system':
            score += 10.0
        
        # Messages récents = haute priorité
        # (sera ajusté par réordonnancement)
        
        # Longueur = plus de contenu
        score += min(len(message.content) / 1000, 5.0)
        
        return score
    
    def _estimate_tokens_from_messages(self, messages: List[Message]) -> int:
        """Estime les tokens d'une liste de messages."""
        return sum(len(m.content) for m in messages) // 4
    
    # ==========================================
    # CONTEXT BUILDING
    # ==========================================
    
    def build_context(
        self,
        session: Session,
        user_input: str,
        force_compress: bool = False,
    ) -> Tuple[str, MemoryWindow]:
        """
        Construit le contexte pour une requête.
        
        Args:
            session: La session
            user_input: L'input utilisateur
            force_compress: Forcer la compression
            
        Returns:
            (context_string, memory_window)
        """
        analysis = self.analyze(session)
        
        if force_compress or analysis.should_compress:
            window = self.compress(session)
        else:
            window = MemoryWindow(
                messages=session.messages,
                original_message_count=len(session.messages),
                tokens_estimate=analysis.estimated_tokens,
            )
        
        # Construire le contexte
        context = window.to_context_string()
        if user_input:
            context += f"\n\n[USER]: {user_input}"
        
        return context, window
    
    # ==========================================
    # SERIALIZATION
    # ==========================================
    
    def get_stats(self, session: Session) -> MemoryStats:
        """Retourne les stats de mémoire pour une session."""
        total_messages = len(session.messages)
        total_tokens = self._estimate_tokens(session)
        
        window = self.compress(session)
        
        return MemoryStats(
            total_messages=total_messages,
            total_tokens_estimate=total_tokens,
            window_messages=len(window.messages),
            window_tokens_estimate=window.tokens_estimate,
            compression_ratio=(
                window.tokens_estimate / total_tokens if total_tokens > 0 else 1.0
            ),
        )


# ==========================================
# MEMORY ANALYSIS
# ==========================================

@dataclass
class MemoryAnalysis:
    """Résultat de l'analyse mémoire."""
    session_id: str
    total_messages: int
    estimated_tokens: int
    utilization: float  # 0.0 to 1.0+
    should_compress: bool
    should_delegate: bool
    recommended_strategy: MemoryStrategy
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_messages": self.total_messages,
            "estimated_tokens": self.estimated_tokens,
            "utilization": self.utilization,
            "should_compress": self.should_compress,
            "should_delegate": self.should_delegate,
            "recommended_strategy": self.recommended_strategy.value,
        }
