"""
Phoenix Agent - Cognitive Memory Manager
========================================

Gestionnaire de mémoire cognitive avancé.

Version précédente (v0.4): Détection de pression mémoire seulement.
Cette version (v0.6): ACTIONS concrètes sur la mémoire.

Le MemoryManager applique les décisions cognitives:
    - compress(): Compresser le contexte
    - summarize(): Résumer l'historique
    - prune(): Élaguer les éléments peu importants
    - prioritize(): Réorganiser par importance
    - snapshot(): Sauvegarder l'état mémoire
    - restore(): Restaurer un état mémoire

Sans ce composant:
    - DecisionEngine ne peut pas agir sur la mémoire
    - Memory overflow = crash ou comportement imprévisible

Avec ce composant:
    - Contrôle explicite de la mémoire
    - Stratégies adaptatives
    - Récupération sur overflow

Architecture:
    CapabilityMonitor → MEMORY_PRESSURE
    DecisionEngine → COMPRESS_MEMORY
    MemoryManager.compress() → Context optimisé

Version: 0.6.0 (Active Memory Strategies)
"""

from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import json
import uuid

from ..contract.session import Message, Session


logger = logging.getLogger("phoenix.memory_manager")


# ==========================================
# MEMORY STRATEGY
# ==========================================

class MemoryStrategy(str, Enum):
    """Stratégies de gestion mémoire."""
    NONE = "none"                         # Aucune action
    SLIDING_WINDOW = "sliding_window"     # Fenêtre glissante
    SUMMARIZATION = "summarization"       # Résumé de l'historique
    PRIORITIZATION = "prioritization"     # Priorisation par importance
    PRUNING = "pruning"                   # Élagage des éléments faibles
    COMPRESSION = "compression"           # Compression agressive
    EXTERNALIZATION = "externalization"   # Externalisation (vector store)
    DELEGATION = "delegation"             # Déléguer pour vider le contexte


# ==========================================
# MEMORY ITEM
# ==========================================

@dataclass
class MemoryItem:
    """
    Élément de mémoire avec métadonnées.
    
    Permet d'associer des scores d'importance.
    """
    content: str
    role: str = "user"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Importance
    importance_score: float = 0.5
    relevance_score: float = 0.5
    recency_score: float = 1.0
    
    # Access
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def combined_score(self) -> float:
        """Score combiné pour la priorisation."""
        return (
            self.importance_score * 0.4 +
            self.relevance_score * 0.3 +
            self.recency_score * 0.3
        )
    
    def access(self) -> None:
        """Marque l'item comme accédé."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def estimate_tokens(self) -> int:
        """Estime le nombre de tokens."""
        return len(self.content) // 4


# ==========================================
# MEMORY SNAPSHOT
# ==========================================

@dataclass
class MemorySnapshot:
    """
    Snapshot de l'état mémoire.
    
    Permet de sauvegarder et restaurer l'état.
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Items
    items: List[MemoryItem] = field(default_factory=list)
    
    # Stats
    total_tokens: int = 0
    total_items: int = 0
    
    # Context
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Metadata
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "total_tokens": self.total_tokens,
            "total_items": self.total_items,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "reason": self.reason,
            "items_count": len(self.items),
        }


# ==========================================
# MEMORY STATS
# ==========================================

@dataclass
class MemoryStats:
    """Statistiques de mémoire."""
    total_items: int = 0
    total_tokens: int = 0
    max_tokens: int = 4000
    
    # Utilization
    utilization: float = 0.0
    
    # Strategy stats
    compression_count: int = 0
    summarization_count: int = 0
    pruning_count: int = 0
    
    # Snapshots
    snapshots_taken: int = 0
    snapshots_restored: int = 0
    
    @property
    def is_pressure(self) -> bool:
        """Pression mémoire."""
        return self.utilization > 0.7
    
    @property
    def is_overflow(self) -> bool:
        """Overflow mémoire."""
        return self.utilization >= 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": self.utilization,
            "is_pressure": self.is_pressure,
            "is_overflow": self.is_overflow,
            "compression_count": self.compression_count,
            "snapshots_taken": self.snapshots_taken,
        }


# ==========================================
# COMPRESSION RESULT
# ==========================================

@dataclass
class CompressionResult:
    """Résultat d'une compression mémoire."""
    success: bool
    original_tokens: int = 0
    compressed_tokens: int = 0
    
    # Strategy used
    strategy: MemoryStrategy = MemoryStrategy.NONE
    
    # Items
    items_removed: int = 0
    items_kept: int = 0
    
    # Summary (if summarization)
    summary: Optional[str] = None
    
    # Compression ratio
    @property
    def compression_ratio(self) -> float:
        if self.original_tokens == 0:
            return 1.0
        return self.compressed_tokens / self.original_tokens
    
    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.compressed_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio,
            "tokens_saved": self.tokens_saved,
            "strategy": self.strategy.value,
            "items_removed": self.items_removed,
            "items_kept": self.items_kept,
        }


# ==========================================
# MEMORY MANAGER CONFIG
# ==========================================

@dataclass
class MemoryManagerConfig:
    """Configuration du gestionnaire de mémoire."""
    # Limits
    max_tokens: int = 4000
    max_items: int = 50
    
    # Thresholds
    pressure_threshold: float = 0.7      # Détecter pression
    compression_threshold: float = 0.8   # Déclencher compression
    critical_threshold: float = 0.95     # Compression agressive
    
    # Strategies
    default_strategy: MemoryStrategy = MemoryStrategy.SLIDING_WINDOW
    
    # Sliding window
    window_size: int = 10
    always_keep_system: bool = True
    always_keep_last_n: int = 3
    
    # Prioritization weights
    importance_weight: float = 0.4
    relevance_weight: float = 0.3
    recency_weight: float = 0.3
    
    # Summarization
    summary_max_tokens: int = 500
    keep_full_last_n: int = 2  # Garder complets les N derniers messages
    
    # Pruning
    min_importance_to_keep: float = 0.3
    prune_aggressive_ratio: float = 0.5  # Enlever 50% en mode agressif


# ==========================================
# COGNITIVE MEMORY MANAGER
# ==========================================

class CognitiveMemoryManager:
    """
    Gestionnaire de mémoire cognitive.
    
    C'est LE composant qui applique les décisions cognitives liées à la mémoire.
    
    Responsabilités:
        - Surveiller l'utilisation mémoire
        - Compresser le contexte quand nécessaire
        - Résumer l'historique
        - Élaguer les éléments peu importants
        - Prioriser par importance
        - Sauvegarder/restaurer des snapshots
    
    Architecture:
        AgentLoop
            │
            ├── memory_manager.analyze()
            │       → MemoryStats, is_pressure
            │
            ├── DecisionEngine.decide()
            │       → COMPRESS_MEMORY
            │
            └── memory_manager.compress()
                    → CompressionResult, Context optimisé
    
    Example:
        config = MemoryManagerConfig(max_tokens=4000)
        manager = CognitiveMemoryManager(config)
        
        # Analyser
        stats = manager.analyze(session)
        
        if stats.is_pressure:
            # Compresser
            result = manager.compress(session, strategy=MemoryStrategy.SUMMARIZATION)
            print(f"Saved {result.tokens_saved} tokens")
        
        # Snapshot
        snapshot = manager.snapshot(session, reason="Before delegation")
        
        # Plus tard...
        manager.restore(snapshot, session)
    """
    
    def __init__(self, config: Optional[MemoryManagerConfig] = None):
        self.config = config or MemoryManagerConfig()
        self._snapshots: Dict[str, MemorySnapshot] = {}
        self._stats = MemoryStats(max_tokens=self.config.max_tokens)
    
    # ==========================================
    # ANALYSIS
    # ==========================================
    
    def analyze(self, session: Session) -> MemoryStats:
        """
        Analyse l'état mémoire d'une session.
        
        Args:
            session: La session à analyser
            
        Returns:
            MemoryStats avec l'état actuel
        """
        total_tokens = self._estimate_session_tokens(session)
        
        self._stats.total_items = len(session.messages)
        self._stats.total_tokens = total_tokens
        self._stats.utilization = total_tokens / self.config.max_tokens if self.config.max_tokens > 0 else 0
        
        return self._stats
    
    def _estimate_session_tokens(self, session: Session) -> int:
        """Estime les tokens d'une session."""
        return sum(len(m.content) for m in session.messages) // 4
    
    def _estimate_messages_tokens(self, messages: List[Message]) -> int:
        """Estime les tokens d'une liste de messages."""
        return sum(len(m.content) for m in messages) // 4
    
    def should_compress(self, session: Session) -> bool:
        """Vérifie si une compression est nécessaire."""
        stats = self.analyze(session)
        return stats.utilization >= self.config.compression_threshold
    
    def get_recommended_strategy(self, session: Session) -> MemoryStrategy:
        """Recommande une stratégie selon l'état."""
        stats = self.analyze(session)
        
        if stats.utilization >= self.config.critical_threshold:
            return MemoryStrategy.COMPRESSION
        elif stats.utilization >= self.config.compression_threshold:
            return MemoryStrategy.SUMMARIZATION
        elif stats.utilization >= self.config.pressure_threshold:
            return MemoryStrategy.PRIORITIZATION
        else:
            return MemoryStrategy.NONE
    
    # ==========================================
    # MAIN COMPRESSION
    # ==========================================
    
    def compress(
        self,
        session: Session,
        strategy: Optional[MemoryStrategy] = None,
        target_ratio: Optional[float] = None,
    ) -> Tuple[CompressionResult, List[Message]]:
        """
        Compresse le contexte d'une session.
        
        C'est LA méthode centrale pour réduire l'utilisation mémoire.
        
        Args:
            session: La session à compresser
            strategy: Stratégie à utiliser (auto si None)
            target_ratio: Ratio cible (ex: 0.5 = 50% de réduction)
            
        Returns:
            (CompressionResult, messages compressés)
        """
        # Choisir la stratégie
        if strategy is None:
            strategy = self.get_recommended_strategy(session)
        
        original_tokens = self._estimate_session_tokens(session)
        
        if original_tokens == 0:
            return CompressionResult(success=True, strategy=strategy), session.messages
        
        # Appliquer la stratégie
        if strategy == MemoryStrategy.SLIDING_WINDOW:
            messages, result = self._apply_sliding_window(session)
        elif strategy == MemoryStrategy.SUMMARIZATION:
            messages, result = self._apply_summarization(session)
        elif strategy == MemoryStrategy.PRIORITIZATION:
            messages, result = self._apply_prioritization(session)
        elif strategy == MemoryStrategy.PRUNING:
            messages, result = self._apply_pruning(session)
        elif strategy == MemoryStrategy.COMPRESSION:
            messages, result = self._apply_aggressive_compression(session)
        else:
            messages = session.messages
            result = CompressionResult(success=True, strategy=strategy)
        
        # Calculer les résultats
        result.original_tokens = original_tokens
        result.compressed_tokens = self._estimate_messages_tokens(messages)
        result.strategy = strategy
        
        # Mettre à jour les stats
        self._stats.compression_count += 1
        
        logger.info(
            f"Memory compressed: {original_tokens} → {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.1%}, strategy: {strategy.value})"
        )
        
        return result, messages
    
    # ==========================================
    # STRATEGIES
    # ==========================================
    
    def _apply_sliding_window(self, session: Session) -> Tuple[List[Message], CompressionResult]:
        """Applique une fenêtre glissante."""
        messages = session.messages.copy()
        original_count = len(messages)
        result = CompressionResult(success=True, strategy=MemoryStrategy.SLIDING_WINDOW)
        
        # Séparer les messages system
        system_msgs = []
        other_msgs = []
        
        for msg in messages:
            if msg.role == "system":
                system_msgs.append(msg)
            else:
                other_msgs.append(msg)
        
        # Garder les N derniers
        keep_count = self.config.window_size - len(system_msgs)
        if len(other_msgs) > keep_count:
            other_msgs = other_msgs[-keep_count:]
        
        result.items_kept = len(system_msgs) + len(other_msgs)
        result.items_removed = original_count - result.items_kept
        
        return system_msgs + other_msgs, result
    
    def _apply_summarization(self, session: Session) -> Tuple[List[Message], CompressionResult]:
        """Résume l'historique (v0.6: simulation)."""
        messages = session.messages.copy()
        original_count = len(messages)
        result = CompressionResult(success=True, strategy=MemoryStrategy.SUMMARIZATION)
        
        # v0.6: Simulation de résumé
        # v1.0: Appel LLM pour vrai résumé
        
        # Séparer system, historique, et récents
        system_msgs = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]
        
        if len(non_system) <= self.config.keep_full_last_n:
            result.items_kept = len(messages)
            result.items_removed = 0
            return messages, result
        
        # Garder les N derniers complets
        recent_msgs = non_system[-self.config.keep_full_last_n:]
        old_msgs = non_system[:-self.config.keep_full_last_n]
        
        # Créer un "résumé" simulé
        summary_content = self._create_summary(old_msgs)
        summary_msg = Message(
            role="system",
            content=f"[HISTORIQUE RÉSUMÉ]\n{summary_content}",
        )
        
        result.items_kept = len(system_msgs) + 1 + len(recent_msgs)
        result.items_removed = len(old_msgs) - 1  # -1 car le résumé remplace
        result.summary = summary_content
        
        self._stats.summarization_count += 1
        
        return system_msgs + [summary_msg] + recent_msgs, result
    
    def _create_summary(self, messages: List[Message]) -> str:
        """Crée un résumé des messages (simulation)."""
        # v0.6: Résumé simple
        # v1.0: Appel LLM
        
        if not messages:
            return ""
        
        # Compter par rôle
        roles = {}
        for msg in messages:
            roles[msg.role] = roles.get(msg.role, 0) + 1
        
        # Créer un résumé
        parts = [f"{count} message(s) {role}" for role, count in roles.items()]
        
        # Extraire les points clés (simulation)
        keywords = set()
        for msg in messages[:5]:  # Premiers messages
            words = msg.content.lower().split()[:10]
            keywords.update(w for w in words if len(w) > 4)
        
        summary = f"Conversation: {', '.join(parts)}. "
        if keywords:
            summary += f"Mots-clés: {', '.join(list(keywords)[:5])}."
        
        # Limiter la taille
        if len(summary) > self.config.summary_max_tokens * 4:
            summary = summary[:self.config.summary_max_tokens * 4]
        
        return summary
    
    def _apply_prioritization(self, session: Session) -> Tuple[List[Message], CompressionResult]:
        """Priorise par importance."""
        messages = session.messages.copy()
        original_count = len(messages)
        result = CompressionResult(success=True, strategy=MemoryStrategy.PRIORITIZATION)
        
        # Calculer les scores
        items = [self._message_to_item(m) for m in messages]
        
        # Trier par score
        items.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Garder les meilleurs + toujours garder les N derniers
        keep_count = self.config.window_size
        kept_items = items[:keep_count]
        
        # Ajouter les derniers messages
        last_n_ids = {id(messages[-i]) for i in range(1, min(self.config.always_keep_last_n + 1, len(messages) + 1))}
        for item, msg in zip(items, messages):
            if id(msg) in last_n_ids and item not in kept_items:
                kept_items.append(item)
        
        # Réordonner chronologiquement
        kept_items.sort(key=lambda x: x.timestamp)
        
        result.items_kept = len(kept_items)
        result.items_removed = original_count - result.items_kept
        
        return [self._item_to_message(item) for item in kept_items], result
    
    def _apply_pruning(self, session: Session) -> Tuple[List[Message], CompressionResult]:
        """Élague les éléments peu importants."""
        messages = session.messages.copy()
        original_count = len(messages)
        result = CompressionResult(success=True, strategy=MemoryStrategy.PRUNING)
        
        # Filtrer par importance
        items = [self._message_to_item(m) for m in messages]
        
        # Toujours garder system
        kept_items = [item for item in items if item.role == "system"]
        prunable = [item for item in items if item.role != "system"]
        
        # Élaguer par score
        for item in prunable:
            if item.importance_score >= self.config.min_importance_to_keep:
                kept_items.append(item)
        
        # Si pas assez de réduction, forcer
        if len(kept_items) > self.config.max_items * (1 - self.config.prune_aggressive_ratio):
            # Prendre les plus importants
            prunable.sort(key=lambda x: x.importance_score, reverse=True)
            keep_count = int(len(prunable) * (1 - self.config.prune_aggressive_ratio))
            kept_items = [item for item in items if item.role == "system"] + prunable[:keep_count]
        
        # Réordonner
        kept_items.sort(key=lambda x: x.timestamp)
        
        result.items_kept = len(kept_items)
        result.items_removed = original_count - result.items_kept
        
        self._stats.pruning_count += 1
        
        return [self._item_to_message(item) for item in kept_items], result
    
    def _apply_aggressive_compression(self, session: Session) -> Tuple[List[Message], CompressionResult]:
        """Compression agressive (combine stratégies)."""
        # D'abord summarization
        result1, messages = self._apply_summarization(session)
        
        # Puis pruning si encore trop
        if self._estimate_messages_tokens(messages) > self.config.max_tokens * 0.6:
            temp_session = type('TempSession', {}, {'messages': messages})()
            result2, messages = self._apply_pruning(temp_session)
        
        result = CompressionResult(
            success=True,
            strategy=MemoryStrategy.COMPRESSION,
            items_kept=len(messages),
            items_removed=result1.items_removed,
        )
        
        return messages, result
    
    # ==========================================
    # ITEM CONVERSION
    # ==========================================
    
    def _message_to_item(self, message: Message) -> MemoryItem:
        """Convertit un Message en MemoryItem."""
        item = MemoryItem(
            content=message.content,
            role=message.role,
            timestamp=message.timestamp,
        )
        
        # Calculer les scores
        item.importance_score = self._calculate_importance(message)
        item.relevance_score = 0.5  # Default
        item.recency_score = self._calculate_recency(message)
        
        return item
    
    def _item_to_message(self, item: MemoryItem) -> Message:
        """Convertit un MemoryItem en Message."""
        return Message(
            role=item.role,
            content=item.content,
            timestamp=item.timestamp,
        )
    
    def _calculate_importance(self, message: Message) -> float:
        """Calcule l'importance d'un message."""
        score = 0.5
        
        # System = haute importance
        if message.role == "system":
            score = 0.9
        elif message.role == "user":
            score = 0.7
        elif message.role == "assistant":
            score = 0.6
        
        # Longueur = potentiellement plus d'information
        length_factor = min(len(message.content) / 2000, 0.2)
        score += length_factor
        
        return min(1.0, score)
    
    def _calculate_recency(self, message: Message) -> float:
        """Calcule le score de récence."""
        age = (datetime.utcnow() - message.timestamp).total_seconds()
        
        # Décroissance exponentielle
        if age < 60:
            return 1.0
        elif age < 300:
            return 0.9
        elif age < 900:
            return 0.7
        elif age < 3600:
            return 0.5
        else:
            return 0.3
    
    # ==========================================
    # SNAPSHOT / RESTORE
    # ==========================================
    
    def snapshot(
        self,
        session: Session,
        reason: str = "",
        task_id: Optional[str] = None,
    ) -> MemorySnapshot:
        """
        Prend un snapshot de l'état mémoire.
        
        Args:
            session: La session à snapshoter
            reason: Raison du snapshot
            task_id: ID de la tâche associée
            
        Returns:
            MemorySnapshot
        """
        items = [self._message_to_item(m) for m in session.messages]
        
        snapshot = MemorySnapshot(
            items=items,
            total_tokens=self._estimate_session_tokens(session),
            total_items=len(items),
            session_id=getattr(session, 'session_id', None),
            task_id=task_id,
            reason=reason,
        )
        
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._stats.snapshots_taken += 1
        
        logger.info(f"Memory snapshot taken: {snapshot.snapshot_id} ({snapshot.total_tokens} tokens)")
        
        return snapshot
    
    def restore(
        self,
        snapshot: MemorySnapshot,
        session: Session,
    ) -> bool:
        """
        Restaure un snapshot dans une session.
        
        Args:
            snapshot: Le snapshot à restaurer
            session: La session cible
            
        Returns:
            True si succès
        """
        try:
            # Vider la session
            session.messages.clear()
            
            # Restaurer les messages
            for item in snapshot.items:
                session.messages.append(self._item_to_message(item))
            
            self._stats.snapshots_restored += 1
            
            logger.info(f"Memory snapshot restored: {snapshot.snapshot_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            return False
    
    def get_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """Récupère un snapshot par ID."""
        return self._snapshots.get(snapshot_id)
    
    def list_snapshots(self) -> List[MemorySnapshot]:
        """Liste tous les snapshots."""
        return list(self._snapshots.values())
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Supprime un snapshot."""
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def build_context(
        self,
        session: Session,
        user_input: str,
        force_compress: bool = False,
    ) -> Tuple[str, CompressionResult]:
        """
        Construit le contexte optimisé.
        
        Args:
            session: La session
            user_input: L'input utilisateur
            force_compress: Forcer la compression
            
        Returns:
            (context_string, compression_result)
        """
        if force_compress or self.should_compress(session):
            result, messages = self.compress(session)
        else:
            messages = session.messages
            result = CompressionResult(success=True, strategy=MemoryStrategy.NONE)
        
        # Construire le string de contexte
        parts = []
        for msg in messages:
            role_prefix = {
                'system': '[SYSTEM]',
                'user': '[USER]',
                'assistant': '[ASSISTANT]',
            }.get(msg.role, f'[{msg.role}]')
            parts.append(f"{role_prefix}: {msg.content}")
        
        context = "\n\n".join(parts)
        if user_input:
            context += f"\n\n[USER]: {user_input}"
        
        return context, result
    
    def get_stats(self) -> MemoryStats:
        """Retourne les statistiques."""
        return self._stats
    
    def clear_snapshots(self) -> int:
        """Efface tous les snapshots."""
        count = len(self._snapshots)
        self._snapshots.clear()
        return count


# ==========================================
# ALIASES
# ==========================================

# Pour compatibilité avec v0.4
MemoryManager = CognitiveMemoryManager
MemoryWindow = List[Message]
MemoryAnalysis = MemoryStats


# ==========================================
# FACTORY
# ==========================================

def create_memory_manager(
    max_tokens: int = 4000,
    max_items: int = 50,
    default_strategy: MemoryStrategy = MemoryStrategy.SLIDING_WINDOW,
) -> CognitiveMemoryManager:
    """Factory pour créer un gestionnaire de mémoire."""
    config = MemoryManagerConfig(
        max_tokens=max_tokens,
        max_items=max_items,
        default_strategy=default_strategy,
    )
    return CognitiveMemoryManager(config)
