"""
Phoenix Agent - Context Builder
===============================

Construction du contexte pour l'agent.

Le Context Builder prépare le prompt qui sera envoyé à la gateway.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from ..contract.session import Message, Session


@dataclass
class ContextOptions:
    """Options de construction du contexte."""
    include_system: bool = True
    include_history: bool = True
    max_history_length: int = 10
    max_tokens: int = 4000  # Approximate
    format_style: str = "conversation"  # conversation, raw, structured


class ContextBuilder:
    """
    Constructeur de contexte pour l'agent.
    
    Responsabilités:
        - Assembler le contexte depuis la session
        - Appliquer les templates
        - Respecter les limites de tokens
    
    Example:
        builder = ContextBuilder()
        context = builder.build(session, options=ContextOptions(
            include_history=True,
            max_history_length=5
        ))
    """
    
    def __init__(
        self,
        default_system_prompt: str = "You are a helpful AI assistant."
    ):
        self.default_system_prompt = default_system_prompt
    
    def build(
        self,
        session: Session,
        user_input: str,
        options: Optional[ContextOptions] = None
    ) -> str:
        """
        Construit le prompt complet pour la gateway.
        
        Args:
            session: Session active
            user_input: Input utilisateur actuel
            options: Options de construction
            
        Returns:
            Prompt complet
        """
        options = options or ContextOptions()
        parts = []
        
        # 1. System prompt
        if options.include_system:
            system_msg = self._find_system_message(session)
            if system_msg:
                parts.append(f"[SYSTEM]: {system_msg.content}")
            else:
                parts.append(f"[SYSTEM]: {self.default_system_prompt}")
        
        # 2. History
        if options.include_history and session.messages:
            history_messages = self._filter_history(
                session.messages,
                max_length=options.max_history_length
            )
            for msg in history_messages:
                if msg.role == 'system':
                    continue  # Déjà inclus
                role_label = {
                    'user': 'USER',
                    'assistant': 'ASSISTANT',
                    'tool': f'TOOL({msg.metadata.get("tool_name", "unknown")})'
                }.get(msg.role, msg.role.upper())
                parts.append(f"[{role_label}]: {msg.content}")
        
        # 3. Current user input
        parts.append(f"[USER]: {user_input}")
        
        # 4. Truncate if needed
        full_context = "\n\n".join(parts)
        if len(full_context) > options.max_tokens * 4:  # Rough estimate
            full_context = self._truncate_context(
                full_context,
                max_chars=options.max_tokens * 4
            )
        
        return full_context
    
    def build_minimal(
        self,
        user_input: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Construit un prompt minimal sans historique.
        
        Args:
            user_input: Input utilisateur
            system_prompt: Prompt système (optionnel)
            
        Returns:
            Prompt minimal
        """
        if system_prompt:
            return f"[SYSTEM]: {system_prompt}\n\n[USER]: {user_input}"
        return user_input
    
    def _find_system_message(self, session: Session) -> Optional[Message]:
        """Trouve le message système dans la session."""
        for msg in session.messages:
            if msg.role == 'system':
                return msg
        return None
    
    def _filter_history(
        self,
        messages: List[Message],
        max_length: int
    ) -> List[Message]:
        """
        Filtre l'historique pour respecter max_length.
        
        Garde les messages les plus récents.
        """
        if len(messages) <= max_length:
            return messages
        
        # Garder system + récents
        result = []
        for msg in messages:
            if msg.role == 'system':
                result.insert(0, msg)
        
        # Ajouter les récents
        recent = [m for m in messages[-(max_length-1):] if m.role != 'system']
        result.extend(recent)
        
        return result
    
    def _truncate_context(
        self,
        context: str,
        max_chars: int
    ) -> str:
        """Tronque le contexte si trop long."""
        if len(context) <= max_chars:
            return context
        
        # Tronquer au milieu avec indicateur
        half = max_chars // 2
        return (
            context[:half] +
            "\n\n[... CONTEXT TRUNCATED ...]\n\n" +
            context[-half:]
        )
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estime le nombre de tokens.
        
        Approximation: 1 token ≈ 4 chars pour l'anglais.
        """
        return len(text) // 4
