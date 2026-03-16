"""
Phoenix Agent - Orchestrator
============================

Point d'entrée principal pour Phoenix Agent.

L'Orchestrator est MINIMAL - il délègue à l'AgentLoop.

RÈGLES:
    - Orchestrator ne contient PAS de logique LLM
    - Orchestrator ne contient PAS de logique agent
    - Orchestrator coordonne: Config → AgentLoop → Result
"""

import asyncio
from typing import Optional, AsyncIterator, List
from dataclasses import dataclass
import logging

from ..config import PhoenixConfig, get_config
from ..contract.schemas import DEFAULT_MODEL
from ..contract.events import AgentEvent
from ..gateway.adapter import GatewayAdapter, create_gateway_adapter
from .state import SessionState, SessionManager
from .agent_loop import AgentLoop, AgentLoopResult
from .context_builder import ContextBuilder


logger = logging.getLogger("phoenix.orchestrator")


# ==========================================
# RUN RESULT
# ==========================================

@dataclass
class RunResult:
    """
    Résultat d'une exécution Phoenix.
    
    Retourné par PhoenixOrchestrator.run()
    """
    session_id: str
    response: str
    status: str
    iterations: int
    total_tokens: int
    latency_ms: float
    model: str
    provider: Optional[str] = None
    cached: bool = False
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == 'completed'
    
    @property
    def is_error(self) -> bool:
        return self.status == 'error'
    
    @classmethod
    def from_agent_result(cls, result: AgentLoopResult) -> "RunResult":
        return cls(
            session_id=result.session_id,
            response=result.response,
            status=result.status,
            iterations=result.iterations,
            total_tokens=result.total_tokens,
            latency_ms=result.total_latency_ms,
            model=result.model,
            provider=result.provider,
            error=result.error
        )


# ==========================================
# PHOENIX ORCHESTRATOR
# ==========================================

class PhoenixOrchestrator:
    """
    Orchestrator Phoenix - Point d'entrée principal.
    
    MINIMAL: Délègue tout à l'AgentLoop.
    
    Example:
        # Simple
        orchestrator = PhoenixOrchestrator()
        result = await orchestrator.run("Hello!")
        print(result.response)
        
        # Avec mock pour tests
        orchestrator = PhoenixOrchestrator(mock=True)
        result = await orchestrator.run("Test")
        
        # Streaming
        async for event in orchestrator.run_stream("Hello"):
            print(event.event_type)
    """
    
    def __init__(
        self,
        config: Optional[PhoenixConfig] = None,
        adapter: Optional[GatewayAdapter] = None,
        mock: bool = False,
        mock_response: str = "Hello from Phoenix!",
    ):
        """
        Initialise l'orchestrator.
        
        Args:
            config: Configuration Phoenix
            adapter: Gateway adapter (créé si non fourni)
            mock: Utiliser un mock adapter
            mock_response: Réponse du mock
        """
        self.config = config or get_config()
        
        # Créer l'adapter
        if adapter:
            self.adapter = adapter
        elif mock:
            self.adapter = create_gateway_adapter(
                mock=True,
                mock_response=mock_response
            )
        else:
            self.adapter = create_gateway_adapter(
                base_url=self.config.gateway.base_url,
                api_key=self.config.gateway.api_key
            )
        
        # Créer l'agent loop
        self.agent_loop = AgentLoop(
            adapter=self.adapter,
            max_iterations=self.config.agent.max_iterations,
            enable_thinking=self.config.agent.enable_thinking
        )
        
        # Session manager
        self.session_manager = SessionManager()
        
        # Context builder
        self.context_builder = ContextBuilder()
    
    # ==========================================
    # MAIN RUN (Non-streaming)
    # ==========================================
    
    async def run(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> RunResult:
        """
        Exécute une requête Phoenix.
        
        Args:
            user_input: Input utilisateur
            session_id: ID de session (créé si non fourni)
            model: Modèle à utiliser
            
        Returns:
            RunResult
        """
        logger.info(f"Running Phoenix: input='{user_input[:50]}...'")
        
        # Créer ou récupérer la session
        session = self.session_manager.create(
            session_id=session_id,
            model=model,
            max_iterations=self.config.agent.max_iterations
        )
        
        # Exécuter l'agent loop
        result = await self.agent_loop.run(
            user_input=user_input,
            session=session,
            model=model
        )
        
        return RunResult.from_agent_result(result)
    
    # ==========================================
    # STREAMING RUN
    # ==========================================
    
    async def run_stream(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> AsyncIterator[AgentEvent]:
        """
        Exécute avec streaming d'events.
        
        Args:
            user_input: Input utilisateur
            session_id: ID de session
            model: Modèle
            
        Yields:
            AgentEvent (Think, Act, Observe, Complete/Error)
        """
        logger.info(f"Running Phoenix stream: input='{user_input[:50]}...'")
        
        # Créer la session
        session = self.session_manager.create(
            session_id=session_id,
            model=model,
            max_iterations=self.config.agent.max_iterations
        )
        
        # Stream les events
        async for event in self.agent_loop.run_stream(
            user_input=user_input,
            session=session,
            model=model
        ):
            yield event
    
    # ==========================================
    # SESSION MANAGEMENT
    # ==========================================
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Récupère une session."""
        return self.session_manager.get(session_id)
    
    def create_session(
        self,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL
    ) -> SessionState:
        """Crée une nouvelle session."""
        return self.session_manager.create(
            session_id=session_id,
            model=model
        )
    
    def list_sessions(self) -> List[str]:
        """Liste les sessions actives."""
        return self.session_manager.list_all()
    
    # ==========================================
    # CLEANUP
    # ==========================================
    
    async def close(self) -> None:
        """Ferme les ressources."""
        if hasattr(self.adapter, 'close'):
            await self.adapter.close()


# ==========================================
# FACTORY
# ==========================================

def create_orchestrator(
    mock: bool = False,
    mock_response: str = "Hello from Phoenix!",
    gateway_url: Optional[str] = None,
    gateway_api_key: Optional[str] = None,
    debug: bool = False,
) -> PhoenixOrchestrator:
    """
    Factory pour créer un orchestrator.
    
    Args:
        mock: Utiliser un mock
        mock_response: Réponse du mock
        gateway_url: URL de la gateway
        gateway_api_key: Clé API
        debug: Mode debug
        
    Returns:
        PhoenixOrchestrator configuré
    """
    config = get_config()
    
    if debug:
        config.debug = True
    
    if gateway_url:
        config.gateway.base_url = gateway_url
    if gateway_api_key:
        config.gateway.api_key = gateway_api_key
    
    return PhoenixOrchestrator(
        config=config,
        mock=mock,
        mock_response=mock_response
    )
