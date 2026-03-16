"""
Phoenix Agent - Gateway Adapter
==============================

Adapter NATIF pour communiquer avec la LLM Gateway externe.

RÈGLES CRITIQUES:
    - Phoenix ne contient AUCUNE logique LLM
    - Phoenix CONSOMME la gateway comme service externe
    - Utilise DIRECTEMENT GenerateRequest/GenerateResponse
    - Pas de transformation intermédiaire

Architecture:
    Phoenix → GatewayAdapter → HTTP POST /v1/generate → LLM Gateway
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..contract.schemas import (
    GenerateRequest,
    GenerateResponse,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
)


logger = logging.getLogger("phoenix.gateway")


# ==========================================
# ADAPTER INTERFACE
# ==========================================

class GatewayAdapter(ABC):
    """
    Interface abstraite pour l'adapter gateway.
    
    Permet différents backends:
        - HTTPGatewayAdapter: Gateway réelle
        - MockGatewayAdapter: Tests
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        use_cache: bool = True
    ) -> GenerateResponse:
        """
        Génère une réponse via la gateway.
        
        Args:
            prompt: Prompt utilisateur (peut inclure contexte)
            model: Modèle cible
            use_cache: Utiliser le cache
            
        Returns:
            GenerateResponse de la gateway
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifie la disponibilité de la gateway."""
        pass


# ==========================================
# HTTP ADAPTER (Gateway Réelle)
# ==========================================

class HTTPGatewayAdapter(GatewayAdapter):
    """
    Adapter HTTP pour la LLM Gateway réelle.
    
    Envoie des GenerateRequest directement à POST /v1/generate.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._session = None
    
    async def _get_session(self):
        """Lazy init de la session HTTP."""
        if self._session is None:
            try:
                import aiohttp
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                self._session = aiohttp.ClientSession(
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            except ImportError:
                raise RuntimeError("aiohttp required: pip install aiohttp")
        return self._session
    
    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        use_cache: bool = True
    ) -> GenerateResponse:
        """Génère via HTTP POST /v1/generate."""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Construire la requête (format natif gateway)
            request = GenerateRequest(
                prompt=prompt,
                model=model,
                use_cache=use_cache
            )
            
            logger.debug(f"POST /v1/generate: model={model}, prompt_len={len(prompt)}")
            
            # POST vers la gateway
            async with session.post(
                f"{self.base_url}/v1/generate",
                json=request.model_dump()
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gateway error {response.status}: {error_text}")
                    return GenerateResponse(
                        response="",
                        latency_ms=latency_ms,
                        cached=False,
                        model=model
                    )
                
                data = await response.json()
                return GenerateResponse(**data)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Gateway request failed: {e}")
            return GenerateResponse(
                response="",
                latency_ms=latency_ms,
                cached=False,
                model=model
            )
    
    async def health_check(self) -> bool:
        """Vérifie /health."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Ferme la session."""
        if self._session:
            await self._session.close()
            self._session = None


# ==========================================
# MOCK ADAPTER (Tests)
# ==========================================

class MockGatewayAdapter(GatewayAdapter):
    """
    Adapter mock pour les tests.
    
    Simule la gateway sans appels HTTP.
    """
    
    def __init__(
        self,
        response_content: str = "This is a mock response from Phoenix.",
        latency_ms: float = 0.0,
        simulate_error: bool = False
    ):
        self.response_content = response_content
        self.latency_ms = latency_ms
        self.simulate_error = simulate_error
        
        # Stats
        self.call_count = 0
        self.last_request: Optional[Dict[str, Any]] = None
    
    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        use_cache: bool = True
    ) -> GenerateResponse:
        """Simule une réponse."""
        import asyncio
        
        self.call_count += 1
        self.last_request = {
            "prompt": prompt,
            "model": model,
            "use_cache": use_cache
        }
        
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
        
        if self.simulate_error:
            return GenerateResponse(
                response="",
                latency_ms=self.latency_ms,
                cached=False,
                model=model
            )
        
        # Simuler des tokens
        prompt_tokens = len(prompt.split())
        response_tokens = len(self.response_content.split())
        
        return GenerateResponse(
            response=self.response_content,
            latency_ms=self.latency_ms,
            cached=False,
            model=model,
            provider="mock",
            usage={
                "input_tokens": prompt_tokens,
                "output_tokens": response_tokens
            }
        )
    
    async def health_check(self) -> bool:
        return True
    
    def reset(self) -> None:
        self.call_count = 0
        self.last_request = None


# ==========================================
# FACTORY
# ==========================================

def create_gateway_adapter(
    mock: bool = False,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    mock_response: str = "Mock response from Phoenix."
) -> GatewayAdapter:
    """
    Factory pour créer un adapter.
    
    Args:
        mock: Si True, utilise MockGatewayAdapter
        base_url: URL de la gateway
        api_key: Clé API
        mock_response: Réponse du mock
        
    Returns:
        GatewayAdapter configuré
    """
    if mock:
        return MockGatewayAdapter(response_content=mock_response)
    
    return HTTPGatewayAdapter(base_url=base_url, api_key=api_key)
