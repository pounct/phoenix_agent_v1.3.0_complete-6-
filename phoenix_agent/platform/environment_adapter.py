"""
Phoenix Agent - Environment Adapter
===================================

Environment Interface Layer - The "eyes and ears" of Phoenix.

Without this layer, Phoenix is isolated.
With this layer, Phoenix LIVES in an environment.

Architecture Decision:
    - Phoenix is NOT a closed system
    - Phoenix must integrate with external systems
    - EnvironmentAdapter provides the integration layer
    - Different environments = different adapters

Key Responsibilities:
    1. LLM Gateway connection (already exists via GatewayAdapter)
    2. Database connections (vector stores, relational, etc.)
    3. API connections (external services)
    4. File system access
    5. Message queues (async communication)
    6. Event bus (real-time events)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

# ============================================================================
# ENUMERATIONS
# ============================================================================


class ConnectionType(Enum):
    """Types of connections."""
    LLM_GATEWAY = "llm_gateway"
    DATABASE = "database"
    VECTOR_STORE = "vector_store"
    API = "api"
    FILESYSTEM = "filesystem"
    QUEUE = "queue"
    EVENT_BUS = "event_bus"
    CACHE = "cache"
    STORAGE = "storage"


class ConnectionStatus(Enum):
    """Status of a connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    CLOSED = "closed"


# ============================================================================
# BASE CONNECTION
# ============================================================================


@dataclass
class ConnectionMetrics:
    """Metrics for a connection."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    avg_latency_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def record_success(self, latency_ms: float, bytes_in: int = 0, bytes_out: int = 0) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_bytes_sent += bytes_out
        self.total_bytes_received += bytes_in
        self.last_request_time = datetime.utcnow()
        # Exponential moving average for latency
        self.avg_latency_ms = (self.avg_latency_ms * 0.9) + (latency_ms * 0.1)
    
    def record_failure(self, error: str) -> None:
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_error = error
        self.last_error_time = datetime.utcnow()
        self.last_request_time = datetime.utcnow()


class BaseConnection(ABC):
    """
    Base class for all connections.
    
    Connections represent external systems that Phoenix integrates with.
    """
    
    def __init__(
        self,
        connection_id: str,
        connection_type: ConnectionType,
        name: str = ""
    ):
        self.connection_id = connection_id
        self.connection_type = connection_type
        self.name = name or connection_id
        self.status = ConnectionStatus.DISCONNECTED
        self.metrics = ConnectionMetrics()
        self._config: Dict[str, Any] = {}
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check connection health."""
        pass
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.status in (ConnectionStatus.CONNECTED, ConnectionStatus.DEGRADED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize connection info."""
        return {
            "connection_id": self.connection_id,
            "connection_type": self.connection_type.value,
            "name": self.name,
            "status": self.status.value,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": (
                    self.metrics.successful_requests / self.metrics.total_requests
                    if self.metrics.total_requests > 0 else 1.0
                ),
                "avg_latency_ms": self.metrics.avg_latency_ms,
            },
        }


# ============================================================================
# LLM GATEWAY CONNECTION
# ============================================================================


@dataclass
class LLMGatewayConfig:
    """Configuration for LLM Gateway connection."""
    endpoint: str = ""
    api_key: str = ""
    default_model: str = "gpt-4"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: float = 60.0
    retry_count: int = 3
    
    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 90000
    
    # Models
    available_models: List[str] = field(default_factory=lambda: ["gpt-4", "gpt-3.5-turbo"])


class LLMGatewayConnection(BaseConnection):
    """
    Connection to LLM Gateway.
    
    This is the PRIMARY connection for Phoenix cognition.
    Phoenix does NOT contain LLM logic - it delegates to the gateway.
    """
    
    def __init__(
        self,
        connection_id: str = None,
        config: LLMGatewayConfig = None
    ):
        super().__init__(
            connection_id=connection_id or f"llm_{uuid4().hex[:8]}",
            connection_type=ConnectionType.LLM_GATEWAY,
            name="LLM Gateway"
        )
        self.config = config or LLMGatewayConfig()
        self._client: Any = None
    
    async def connect(self) -> bool:
        """Connect to LLM Gateway."""
        self.status = ConnectionStatus.CONNECTING
        
        try:
            # In production, this would create actual client
            # For now, we simulate successful connection
            self.status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from gateway."""
        self._client = None
        self.status = ConnectionStatus.DISCONNECTED
    
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check gateway health."""
        if not self.is_connected():
            return False, "Not connected"
        
        # In production, would ping the gateway
        return True, None
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Request completion from LLM.
        
        This is the main method for LLM interactions.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to LLM Gateway")
        
        start_time = datetime.utcnow()
        
        try:
            # In production, this would call actual LLM API
            # For now, return simulated response
            result = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Simulated LLM response"
                    }
                }],
                "model": model or self.config.default_model,
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.record_success(
                latency_ms,
                bytes_in=150,
                bytes_out=len(str(messages))
            )
            
            return result
            
        except Exception as e:
            self.metrics.record_failure(str(e))
            raise


# ============================================================================
# DATABASE CONNECTION
# ============================================================================


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    connection_string: str = ""
    database_type: str = "postgresql"  # postgresql, mysql, sqlite, mongodb
    pool_size: int = 10
    max_overflow: int = 20
    timeout_seconds: float = 30.0
    
    # Query settings
    default_limit: int = 100
    max_limit: int = 10000


class DatabaseConnection(BaseConnection):
    """
    Connection to a database.
    
    Supports relational and NoSQL databases.
    """
    
    def __init__(
        self,
        connection_id: str = None,
        config: DatabaseConfig = None
    ):
        super().__init__(
            connection_id=connection_id or f"db_{uuid4().hex[:8]}",
            connection_type=ConnectionType.DATABASE,
            name="Database"
        )
        self.config = config or DatabaseConfig()
        self._pool: Any = None
    
    async def connect(self) -> bool:
        """Connect to database."""
        self.status = ConnectionStatus.CONNECTING
        
        try:
            # In production, create connection pool
            self.status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._pool:
            # In production, close pool
            pass
        self._pool = None
        self.status = ConnectionStatus.DISCONNECTED
    
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check database health."""
        if not self.is_connected():
            return False, "Not connected"
        
        # In production, would execute SELECT 1 or similar
        return True, None
    
    async def query(
        self,
        query: str,
        params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query."""
        if not self.is_connected():
            raise ConnectionError("Not connected to database")
        
        start_time = datetime.utcnow()
        
        try:
            # In production, execute actual query
            result = []
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.record_success(latency_ms)
            
            return result
            
        except Exception as e:
            self.metrics.record_failure(str(e))
            raise
    
    async def insert(
        self,
        table: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Insert a record."""
        pass
    
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> int:
        """Update records."""
        pass
    
    async def delete(
        self,
        table: str,
        where: Dict[str, Any]
    ) -> int:
        """Delete records."""
        pass


# ============================================================================
# API CONNECTION
# ============================================================================


@dataclass
class APIConfig:
    """Configuration for external API connection."""
    base_url: str = ""
    api_key: str = ""
    auth_type: str = "bearer"  # bearer, basic, api_key, oauth
    timeout_seconds: float = 30.0
    retry_count: int = 3
    
    # Headers
    default_headers: Dict[str, str] = field(default_factory=dict)
    
    # Rate limiting
    rate_limit_per_second: float = 10.0


class APIConnection(BaseConnection):
    """
    Connection to an external API.
    
    Provides HTTP client functionality for external services.
    """
    
    def __init__(
        self,
        connection_id: str = None,
        config: APIConfig = None
    ):
        super().__init__(
            connection_id=connection_id or f"api_{uuid4().hex[:8]}",
            connection_type=ConnectionType.API,
            name="External API"
        )
        self.config = config or APIConfig()
        self._session: Any = None
    
    async def connect(self) -> bool:
        """Initialize API connection."""
        self.status = ConnectionStatus.CONNECTING
        
        try:
            # In production, create HTTP session
            self.status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Close API session."""
        if self._session:
            # In production, close session
            pass
        self._session = None
        self.status = ConnectionStatus.DISCONNECTED
    
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check API health."""
        # In production, would ping health endpoint
        return self.is_connected(), None
    
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Make an API request."""
        if not self.is_connected():
            raise ConnectionError("Not connected to API")
        
        start_time = datetime.utcnow()
        
        try:
            # In production, make actual HTTP request
            result = {"status": "success", "data": {}}
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.record_success(latency_ms)
            
            return result
            
        except Exception as e:
            self.metrics.record_failure(str(e))
            raise
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request."""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """POST request."""
        return await self.request("POST", endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """PUT request."""
        return await self.request("PUT", endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request."""
        return await self.request("DELETE", endpoint, **kwargs)


# ============================================================================
# FILESYSTEM CONNECTION
# ============================================================================


@dataclass
class FileSystemConfig:
    """Configuration for filesystem connection."""
    root_path: str = "/tmp"
    read_only: bool = False
    max_file_size_mb: int = 100
    allowed_extensions: List[str] = field(default_factory=list)
    
    # Security
    sandbox_mode: bool = True
    allow_symlinks: bool = False


class FileSystemConnection(BaseConnection):
    """
    Connection to filesystem.
    
    Provides file operations with security constraints.
    """
    
    def __init__(
        self,
        connection_id: str = None,
        config: FileSystemConfig = None
    ):
        super().__init__(
            connection_id=connection_id or f"fs_{uuid4().hex[:8]}",
            connection_type=ConnectionType.FILESYSTEM,
            name="Filesystem"
        )
        self.config = config or FileSystemConfig()
    
    async def connect(self) -> bool:
        """Initialize filesystem access."""
        # In production, would verify root_path exists and is accessible
        self.status = ConnectionStatus.CONNECTED
        return True
    
    async def disconnect(self) -> None:
        """Close filesystem access."""
        self.status = ConnectionStatus.DISCONNECTED
    
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check filesystem is accessible."""
        # In production, would check root_path exists
        return self.is_connected(), None
    
    async def read_file(self, path: str) -> bytes:
        """Read file contents."""
        if not self.is_connected():
            raise ConnectionError("Filesystem not connected")
        
        # In production, read actual file
        # Apply sandbox checks
        return b""
    
    async def write_file(self, path: str, content: bytes) -> bool:
        """Write file contents."""
        if not self.is_connected():
            raise ConnectionError("Filesystem not connected")
        
        if self.config.read_only:
            raise PermissionError("Filesystem is read-only")
        
        # In production, write actual file
        return True
    
    async def list_dir(self, path: str) -> List[str]:
        """List directory contents."""
        if not self.is_connected():
            raise ConnectionError("Filesystem not connected")
        
        # In production, list actual directory
        return []
    
    async def delete(self, path: str) -> bool:
        """Delete file or directory."""
        if not self.is_connected():
            raise ConnectionError("Filesystem not connected")
        
        if self.config.read_only:
            raise PermissionError("Filesystem is read-only")
        
        return True
    
    async def stat(self, path: str) -> Dict[str, Any]:
        """Get file/directory stats."""
        return {
            "path": path,
            "exists": False,
            "is_file": False,
            "is_dir": False,
            "size": 0,
        }


# ============================================================================
# QUEUE CONNECTION
# ============================================================================


@dataclass
class QueueConfig:
    """Configuration for message queue connection."""
    queue_type: str = "redis"  # redis, rabbitmq, sqs, kafka
    endpoint: str = ""
    queue_name: str = "phoenix_tasks"
    consumer_group: str = "phoenix_workers"
    
    # Settings
    visibility_timeout_seconds: int = 300
    max_retries: int = 3
    dead_letter_queue: str = "phoenix_dlq"


class QueueConnection(BaseConnection):
    """
    Connection to message queue.
    
    Provides async task queue functionality.
    """
    
    def __init__(
        self,
        connection_id: str = None,
        config: QueueConfig = None
    ):
        super().__init__(
            connection_id=connection_id or f"queue_{uuid4().hex[:8]}",
            connection_type=ConnectionType.QUEUE,
            name="Message Queue"
        )
        self.config = config or QueueConfig()
        self._client: Any = None
    
    async def connect(self) -> bool:
        """Connect to queue."""
        self.status = ConnectionStatus.CONNECTING
        
        try:
            # In production, connect to actual queue
            self.status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from queue."""
        self._client = None
        self.status = ConnectionStatus.DISCONNECTED
    
    async def health_check(self) -> tuple[bool, Optional[str]]:
        """Check queue health."""
        return self.is_connected(), None
    
    async def send(
        self,
        message: Dict[str, Any],
        delay_seconds: int = 0
    ) -> str:
        """Send a message to the queue."""
        if not self.is_connected():
            raise ConnectionError("Queue not connected")
        
        # In production, send to actual queue
        message_id = str(uuid4())
        
        self.metrics.record_success(0)
        return message_id
    
    async def receive(
        self,
        max_messages: int = 10,
        wait_seconds: int = 20
    ) -> List[Dict[str, Any]]:
        """Receive messages from queue."""
        if not self.is_connected():
            raise ConnectionError("Queue not connected")
        
        # In production, receive from actual queue
        return []
    
    async def acknowledge(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        return True
    
    async def fail(self, message_id: str, error: str) -> bool:
        """Mark message as failed."""
        return True


# ============================================================================
# ENVIRONMENT CONFIG
# ============================================================================


@dataclass
class EnvironmentConfig:
    """Configuration for the entire environment."""
    name: str = "default"
    
    # Connections
    llm_gateway: Optional[LLMGatewayConfig] = None
    database: Optional[DatabaseConfig] = None
    api: Optional[APIConfig] = None
    filesystem: Optional[FileSystemConfig] = None
    queue: Optional[QueueConfig] = None
    
    # Global settings
    auto_connect: bool = True
    health_check_interval_seconds: int = 30
    
    # Fallback
    enable_fallbacks: bool = True
    degraded_mode_enabled: bool = True


@dataclass
class EnvironmentStatus:
    """Status of the environment."""
    connected: bool = False
    connections: Dict[str, ConnectionStatus] = field(default_factory=dict)
    healthy: bool = False
    degraded: bool = False
    last_health_check: Optional[datetime] = None
    
    # Summary
    total_connections: int = 0
    healthy_connections: int = 0
    degraded_connections: int = 0
    failed_connections: int = 0


# ============================================================================
# ENVIRONMENT ADAPTER
# ============================================================================


class EnvironmentAdapter:
    """
    Environment Interface - The "eyes and ears" of Phoenix.
    
    This is the INTEGRATION layer. Without it, Phoenix is isolated.
    With it, Phoenix lives in an environment with access to:
        - LLM Gateway (for cognition)
        - Databases (for persistence)
        - APIs (for external services)
        - Filesystems (for storage)
        - Queues (for async tasks)
    
    Architecture Decision:
        - Phoenix is NOT a closed system
        - All external access goes through EnvironmentAdapter
        - Connections are managed centrally
        - Health is monitored continuously
    
    Usage:
        env = EnvironmentAdapter(config)
        await env.connect()
        
        llm = env.get_llm_gateway()
        result = await llm.complete(messages)
        
        db = env.get_database()
        records = await db.query("SELECT * FROM tasks")
    """
    
    def __init__(self, config: EnvironmentConfig = None):
        self.config = config or EnvironmentConfig()
        self.status = EnvironmentStatus()
        
        # Connections registry
        self._connections: Dict[str, BaseConnection] = {}
        self._by_type: Dict[ConnectionType, List[str]] = {
            t: [] for t in ConnectionType
        }
        
        # Health monitoring
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
    
    # ========================================================================
    # Connection Management
    # ========================================================================
    
    def register_connection(self, connection: BaseConnection) -> bool:
        """Register a connection."""
        if connection.connection_id in self._connections:
            return False
        
        self._connections[connection.connection_id] = connection
        self._by_type[connection.connection_type].append(connection.connection_id)
        self.status.total_connections += 1
        
        return True
    
    def unregister_connection(self, connection_id: str) -> bool:
        """Unregister a connection."""
        if connection_id not in self._connections:
            return False
        
        connection = self._connections.pop(connection_id)
        self._by_type[connection.connection_type].remove(connection_id)
        self.status.total_connections -= 1
        
        return True
    
    def get_connection(self, connection_id: str) -> Optional[BaseConnection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)
    
    def get_connections_by_type(self, connection_type: ConnectionType) -> List[BaseConnection]:
        """Get all connections of a type."""
        return [
            self._connections[cid]
            for cid in self._by_type[connection_type]
        ]
    
    # ========================================================================
    # Convenience Accessors
    # ========================================================================
    
    def get_llm_gateway(self) -> Optional[LLMGatewayConnection]:
        """Get the LLM Gateway connection."""
        connections = self.get_connections_by_type(ConnectionType.LLM_GATEWAY)
        return connections[0] if connections else None
    
    def get_database(self) -> Optional[DatabaseConnection]:
        """Get the primary database connection."""
        connections = self.get_connections_by_type(ConnectionType.DATABASE)
        return connections[0] if connections else None
    
    def get_api(self, connection_id: str = None) -> Optional[APIConnection]:
        """Get an API connection."""
        if connection_id:
            conn = self.get_connection(connection_id)
            return conn if isinstance(conn, APIConnection) else None
        
        connections = self.get_connections_by_type(ConnectionType.API)
        return connections[0] if connections else None
    
    def get_filesystem(self) -> Optional[FileSystemConnection]:
        """Get the filesystem connection."""
        connections = self.get_connections_by_type(ConnectionType.FILESYSTEM)
        return connections[0] if connections else None
    
    def get_queue(self) -> Optional[QueueConnection]:
        """Get the queue connection."""
        connections = self.get_connections_by_type(ConnectionType.QUEUE)
        return connections[0] if connections else None
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    async def connect(self) -> bool:
        """
        Connect to all registered services.
        
        This initializes the environment and makes Phoenix operational.
        """
        self.status.connected = False
        results = {}
        
        for connection_id, connection in self._connections.items():
            try:
                success = await connection.connect()
                results[connection_id] = success
                self.status.connections[connection_id] = connection.status
                
                if success:
                    self.status.healthy_connections += 1
                else:
                    self.status.failed_connections += 1
                    
            except Exception as e:
                results[connection_id] = False
                self.status.connections[connection_id] = ConnectionStatus.ERROR
                self.status.failed_connections += 1
        
        # Determine overall status
        self.status.connected = self.status.healthy_connections > 0
        self.status.healthy = self.status.failed_connections == 0
        self.status.degraded = (
            self.status.failed_connections > 0 and
            self.status.healthy_connections > 0
        )
        
        # Start health monitoring
        if self.status.connected:
            self._running = True
            self._health_task = asyncio.create_task(self._health_monitor())
        
        return self.status.connected
    
    async def disconnect(self) -> None:
        """Disconnect from all services."""
        self._running = False
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        for connection in self._connections.values():
            try:
                await connection.disconnect()
            except Exception:
                pass
        
        self.status.connected = False
        self.status.healthy = False
    
    async def _health_monitor(self) -> None:
        """Background health monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self.health_check_all()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
    
    # ========================================================================
    # Health Checks
    # ========================================================================
    
    async def health_check_all(self) -> Dict[str, tuple[bool, Optional[str]]]:
        """Check health of all connections."""
        results = {}
        
        self.status.healthy_connections = 0
        self.status.degraded_connections = 0
        self.status.failed_connections = 0
        
        for connection_id, connection in self._connections.items():
            if connection.is_connected():
                healthy, message = await connection.health_check()
                results[connection_id] = (healthy, message)
                
                if healthy:
                    connection.status = ConnectionStatus.CONNECTED
                    self.status.healthy_connections += 1
                else:
                    connection.status = ConnectionStatus.DEGRADED
                    self.status.degraded_connections += 1
            else:
                results[connection_id] = (False, "Not connected")
                self.status.failed_connections += 1
            
            self.status.connections[connection_id] = connection.status
        
        self.status.last_health_check = datetime.utcnow()
        
        # Update overall status
        self.status.healthy = self.status.failed_connections == 0
        self.status.degraded = (
            self.status.failed_connections > 0 and
            self.status.healthy_connections > 0
        )
        
        return results
    
    # ========================================================================
    # Setup Helpers
    # ========================================================================
    
    async def setup_from_config(self) -> bool:
        """Setup environment from configuration."""
        # LLM Gateway
        if self.config.llm_gateway:
            llm = LLMGatewayConnection(config=self.config.llm_gateway)
            self.register_connection(llm)
        
        # Database
        if self.config.database:
            db = DatabaseConnection(config=self.config.database)
            self.register_connection(db)
        
        # API
        if self.config.api:
            api = APIConnection(config=self.config.api)
            self.register_connection(api)
        
        # Filesystem
        if self.config.filesystem:
            fs = FileSystemConnection(config=self.config.filesystem)
            self.register_connection(fs)
        
        # Queue
        if self.config.queue:
            queue = QueueConnection(config=self.config.queue)
            self.register_connection(queue)
        
        # Connect if auto_connect
        if self.config.auto_connect:
            return await self.connect()
        
        return True
    
    # ========================================================================
    # Status & Info
    # ========================================================================
    
    def get_status(self) -> EnvironmentStatus:
        """Get current environment status."""
        return self.status
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get info about all connections."""
        return [conn.to_dict() for conn in self._connections.values()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize environment state."""
        return {
            "name": self.config.name,
            "status": {
                "connected": self.status.connected,
                "healthy": self.status.healthy,
                "degraded": self.status.degraded,
                "connections": {
                    k: v.value for k, v in self.status.connections.items()
                },
            },
            "connections": self.get_connection_info(),
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_environment_adapter(
    config: EnvironmentConfig = None,
    auto_setup: bool = True
) -> EnvironmentAdapter:
    """
    Create an environment adapter.
    
    Args:
        config: Environment configuration
        auto_setup: Automatically setup from config
    
    Returns:
        Configured EnvironmentAdapter
    """
    adapter = EnvironmentAdapter(config=config)
    
    if auto_setup and config:
        # This would be async in real usage
        pass
    
    return adapter


def create_minimal_environment(
    llm_endpoint: str = "",
    llm_api_key: str = ""
) -> EnvironmentAdapter:
    """Create a minimal environment with just LLM gateway."""
    config = EnvironmentConfig(
        llm_gateway=LLMGatewayConfig(
            endpoint=llm_endpoint,
            api_key=llm_api_key
        )
    )
    
    return EnvironmentAdapter(config=config)


def create_full_environment(
    llm_endpoint: str = "",
    llm_api_key: str = "",
    db_connection_string: str = "",
    api_base_url: str = "",
    queue_endpoint: str = "",
    fs_root_path: str = ""
) -> EnvironmentAdapter:
    """Create a full environment with all connections."""
    config = EnvironmentConfig(
        llm_gateway=LLMGatewayConfig(
            endpoint=llm_endpoint,
            api_key=llm_api_key
        ),
        database=DatabaseConfig(
            connection_string=db_connection_string
        ),
        api=APIConfig(
            base_url=api_base_url
        ),
        queue=QueueConfig(
            endpoint=queue_endpoint
        ),
        filesystem=FileSystemConfig(
            root_path=fs_root_path
        )
    )
    
    return EnvironmentAdapter(config=config)
