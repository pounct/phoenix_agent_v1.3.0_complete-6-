"""
Phoenix Agent - Agent Loop
=========================

Le cœur du runtime Phoenix: Think → Act → Observe.

C'est ici que se trouve la logique d'orchestration de l'agent.

Cycle Agent Loop:
    1. THINK: Analyser la demande, construire le contexte
    2. ACT: Appeler la gateway (LLM)
    3. OBSERVE: Analyser la réponse
    4. REPEAT si nécessaire (max_iterations)

IMPORTANT:
    - Phoenix ne contient AUCUNE logique LLM
    - Phoenix délègue TOUT à la gateway
    - L'agent loop gère uniquement le cycle
"""

import asyncio
import time
from typing import AsyncIterator, Optional, Callable, Any
from dataclasses import dataclass
import logging

from ..contract.schemas import DEFAULT_MODEL
from ..contract.events import (
    AgentEvent,
    ThinkEvent,
    ActEvent,
    ObserveEvent,
    CompleteEvent,
    ErrorEvent,
)
from ..gateway.adapter import GatewayAdapter
from .state import SessionState
from .context_builder import ContextBuilder, ContextOptions


logger = logging.getLogger("phoenix.agent_loop")


# ==========================================
# AGENT LOOP RESULT
# ==========================================

@dataclass
class AgentLoopResult:
    """
    Résultat d'une exécution de l'agent loop.
    
    Contient la réponse finale et les statistiques.
    """
    session_id: str
    response: str
    status: str  # 'completed', 'error', 'max_iterations'
    iterations: int
    total_tokens: int
    total_latency_ms: float
    model: str
    provider: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == 'completed'


# ==========================================
# AGENT LOOP
# ==========================================

class AgentLoop:
    """
    Agent Loop Phoenix - Think → Act → Observe.
    
    Le cœur du runtime. Gère le cycle d'exécution de l'agent
    en déléguant la génération à la gateway.
    
    Example:
        adapter = MockGatewayAdapter(response_content="Hello!")
        loop = AgentLoop(adapter=adapter)
        
        result = await loop.run(
            user_input="Say hello",
            model="llama3.2:latest"
        )
        print(result.response)
    """
    
    def __init__(
        self,
        adapter: GatewayAdapter,
        max_iterations: int = 10,
        enable_thinking: bool = True,
        system_prompt: str = "You are a helpful AI assistant.",
        context_builder: Optional[ContextBuilder] = None,
    ):
        """
        Initialise l'agent loop.
        
        Args:
            adapter: Gateway adapter pour les appels LLM
            max_iterations: Maximum d'itérations
            enable_thinking: Activer la phase think
            system_prompt: Prompt système
            context_builder: Builder de contexte (créé si non fourni)
        """
        self.adapter = adapter
        self.max_iterations = max_iterations
        self.enable_thinking = enable_thinking
        self.system_prompt = system_prompt
        self.context_builder = context_builder or ContextBuilder(
            default_system_prompt=system_prompt
        )
    
    # ==========================================
    # MAIN RUN (Non-streaming)
    # ==========================================
    
    async def run(
        self,
        user_input: str,
        session: Optional[SessionState] = None,
        model: str = DEFAULT_MODEL,
    ) -> AgentLoopResult:
        """
        Exécute l'agent loop (non-streaming).
        
        Args:
            user_input: Input utilisateur
            session: Session existante (optionnel)
            model: Modèle à utiliser
            
        Returns:
            AgentLoopResult
        """
        start_time = time.time()
        
        # Créer ou utiliser la session
        if session is None:
            from .state import SessionState
            session = SessionState(model=model, max_iterations=self.max_iterations)
        
        session.start()
        session.add_system(self.system_prompt)
        session.add_user(user_input)
        
        total_tokens = 0
        total_latency = 0.0
        last_response = ""
        last_provider = None
        
        try:
            # ==========================================
            # THINK: Construire le contexte
            # ==========================================
            iteration = session.increment_iteration()
            
            # Utiliser ContextBuilder (CORRECTION: connecté!)
            prompt = self.context_builder.build(
                session=session.session,
                user_input=user_input,
                options=ContextOptions(include_history=True)
            )
            
            # Enregistrer l'event Think (CORRECTION: events enregistrés)
            think_event = ThinkEvent.create(
                session_id=session.session_id,
                iteration=iteration,
                reasoning=f"Processing: {user_input[:100]}...",
                context_summary=f"Context: {len(prompt)} chars"
            )
            session.record_event(think_event)
            
            # ==========================================
            # ACT: Appeler la gateway
            # ==========================================
            act_event = ActEvent.create_llm_call(
                session_id=session.session_id,
                iteration=iteration,
                model=model,
                prompt_length=len(prompt)
            )
            session.record_event(act_event)
            
            response = await self.adapter.generate(
                prompt=prompt,
                model=model,
                use_cache=True
            )
            
            total_latency += response.latency_ms
            if response.usage:
                total_tokens += response.usage.get('total_tokens', 0)
            
            last_response = response.response
            last_provider = response.provider
            
            # ==========================================
            # OBSERVE: Analyser la réponse
            # ==========================================
            observe_event = ObserveEvent.create_llm_response(
                session_id=session.session_id,
                iteration=iteration,
                response=response.response,
                latency_ms=response.latency_ms,
                cached=response.cached
            )
            session.record_event(observe_event)
            
            # Ajouter la réponse à la session
            session.add_assistant(response.response)
            
            # ==========================================
            # COMPLETE: Finaliser
            # ==========================================
            complete_event = CompleteEvent.create(
                session_id=session.session_id,
                status='completed',
                final_response=response.response,
                total_iterations=iteration,
                total_tokens=total_tokens
            )
            session.record_event(complete_event)
            
            session.complete()
            
            return AgentLoopResult(
                session_id=session.session_id,
                response=response.response,
                status='completed',
                iterations=iteration,
                total_tokens=total_tokens,
                total_latency_ms=total_latency,
                model=response.model,
                provider=last_provider
            )
            
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            session.fail()
            
            # Enregistrer l'event Error (CORRECTION: events enregistrés)
            error_event = ErrorEvent.create(
                session_id=session.session_id,
                iteration=session.iteration,
                error_code='AGENT_LOOP_ERROR',
                error_message=str(e),
                recoverable=False
            )
            session.record_event(error_event)
            
            return AgentLoopResult(
                session_id=session.session_id,
                response="",
                status='error',
                iterations=session.iteration,
                total_tokens=total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                model=model,
                error=str(e)
            )
    
    # ==========================================
    # STREAMING RUN
    # ==========================================
    
    async def run_stream(
        self,
        user_input: str,
        session: Optional[SessionState] = None,
        model: str = DEFAULT_MODEL,
    ) -> AsyncIterator[AgentEvent]:
        """
        Exécute l'agent loop avec streaming d'events.
        
        Args:
            user_input: Input utilisateur
            session: Session existante
            model: Modèle
            
        Yields:
            AgentEvent (Think, Act, Observe, Complete/Error)
        """
        start_time = time.time()
        
        # Créer ou utiliser la session
        if session is None:
            from .state import SessionState
            session = SessionState(model=model, max_iterations=self.max_iterations)
        
        session.start()
        session.add_system(self.system_prompt)
        session.add_user(user_input)
        
        total_tokens = 0
        total_latency = 0.0
        
        try:
            # ==========================================
            # THINK: Construire le contexte
            # ==========================================
            iteration = session.increment_iteration()
            
            # Utiliser ContextBuilder (CORRECTION: connecté!)
            prompt = self.context_builder.build(
                session=session.session,
                user_input=user_input,
                options=ContextOptions(include_history=True)
            )
            
            if self.enable_thinking:
                think_event = ThinkEvent.create(
                    session_id=session.session_id,
                    iteration=iteration,
                    reasoning=f"Processing user input: {user_input[:100]}...",
                    context_summary=f"Context: {len(prompt)} chars"
                )
                session.record_event(think_event)
                yield think_event
            
            # ==========================================
            # ACT: Appeler la gateway
            # ==========================================
            act_event = ActEvent.create_llm_call(
                session_id=session.session_id,
                iteration=iteration,
                model=model,
                prompt_length=len(prompt)
            )
            session.record_event(act_event)
            yield act_event
            
            # CALL GATEWAY
            response = await self.adapter.generate(
                prompt=prompt,
                model=model,
                use_cache=True
            )
            
            total_latency += response.latency_ms
            if response.usage:
                total_tokens += response.usage.get('total_tokens', 0)
            
            # ==========================================
            # OBSERVE: Analyser la réponse
            # ==========================================
            observe_event = ObserveEvent.create_llm_response(
                session_id=session.session_id,
                iteration=iteration,
                response=response.response,
                latency_ms=response.latency_ms,
                cached=response.cached
            )
            session.record_event(observe_event)
            yield observe_event
            
            # Update session
            session.add_assistant(response.response)
            session.complete()
            
            # ==========================================
            # COMPLETE: Finaliser
            # ==========================================
            complete_event = CompleteEvent.create(
                session_id=session.session_id,
                status='completed',
                final_response=response.response,
                total_iterations=iteration,
                total_tokens=total_tokens
            )
            session.record_event(complete_event)
            yield complete_event
            
        except Exception as e:
            logger.error(f"Agent loop stream error: {e}")
            session.fail()
            
            # Enregistrer l'event Error (CORRECTION: events enregistrés)
            error_event = ErrorEvent.create(
                session_id=session.session_id,
                iteration=session.iteration,
                error_code='AGENT_LOOP_ERROR',
                error_message=str(e),
                recoverable=False
            )
            session.record_event(error_event)
            yield error_event
