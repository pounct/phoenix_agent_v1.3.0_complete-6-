"""
Phoenix Agent - Telemetry
=========================

Couche d'observabilité pour Phoenix Agent Runtime.

Sans Telemetry:
    - Impossible de comprendre pourquoi l'agent délègue
    - Impossible de voir les patterns de décision
    - Debug difficile
    - Pas de métriques de performance

Avec Telemetry:
    - Metrics en temps réel
    - Traces d'exécution
    - Events système
    - Health monitoring
    - Performance analysis

ARCHITECTURE:
    AgentRuntimeController
    │
    └── AgentTelemetry
            │
            ├── MetricsCollector
            │   ├── counters
            │   ├── gauges
            │   └── histograms
            │
            ├── EventLogger
            │   └── events[]
            │
            ├── TraceCollector
            │   └── traces[]
            │
            └── HealthMonitor
                └── health_scores

METRICS TRACKED:
    - cycles_total, cycles_success, cycles_failed
    - decisions_total, decisions_by_type
    - delegations_total, delegations_success
    - memory_operations, memory_compression_ratio
    - recovery_attempts, recovery_success
    - latency_p50, latency_p95, latency_p99
    - tokens_used, iterations_count

EVENTS:
    - state_change, decision, delegation, recovery
    - memory_pressure, cognitive_fatigue
    - task_complete, task_failed

TRACES:
    - Execution spans with timing
    - Parent-child relationships
    - Annotations

Version: 0.8.0 (Observability Layer)
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import time
import json
import uuid


logger = logging.getLogger("phoenix.telemetry")


# ==========================================
# METRIC TYPES
# ==========================================

class MetricType(str, Enum):
    """Types de métriques."""
    COUNTER = "counter"      # Monotonic increasing
    GAUGE = "gauge"          # Can go up/down
    HISTOGRAM = "histogram"  # Distribution
    TIMER = "timer"          # Duration


class EventType(str, Enum):
    """Types d'events."""
    # Lifecycle
    RUNTIME_START = "runtime_start"
    RUNTIME_STOP = "runtime_stop"
    CYCLE_START = "cycle_start"
    CYCLE_END = "cycle_end"
    
    # State
    STATE_CHANGE = "state_change"
    
    # Decisions
    DECISION_MADE = "decision_made"
    DELEGATION_TRIGGERED = "delegation_triggered"
    DELEGATION_COMPLETE = "delegation_complete"
    
    # Memory
    MEMORY_PRESSURE = "memory_pressure"
    MEMORY_COMPRESS = "memory_compress"
    MEMORY_OVERFLOW = "memory_overflow"
    
    # Cognitive
    COGNITIVE_FATIGUE = "cognitive_fatigue"
    CONFIDENCE_LOW = "confidence_low"
    LOW_CONFIDENCE = "low_confidence"
    
    # Recovery
    RECOVERY_START = "recovery_start"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    
    # Task
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    
    # Health
    HEALTH_WARNING = "health_warning"
    HEALTH_CRITICAL = "health_critical"


# ==========================================
# METRIC
# ==========================================

@dataclass
class Metric:
    """Une métrique individuelle."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Labels for filtering
    labels: Dict[str, str] = field(default_factory=dict)
    
    # For histograms
    bucket: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


# ==========================================
# EVENT
# ==========================================

@dataclass
class TelemetryEvent:
    """Un event de télémétrie."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.STATE_CHANGE
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Context
    agent_id: str = ""
    session_id: str = ""
    task_id: str = ""
    
    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Severity: debug, info, warning, error
    severity: str = "info"
    
    # Message
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "data": self.data,
            "severity": self.severity,
            "message": self.message,
        }


# ==========================================
# TRACE SPAN
# ==========================================

@dataclass
class TraceSpan:
    """Un span de trace."""
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    
    # Naming
    operation_name: str = ""
    
    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    
    # Status
    status: str = "ok"  # ok, error, timeout
    
    # Context
    agent_id: str = ""
    task_id: str = ""
    
    # Tags
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Logs
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_finished(self) -> bool:
        return self.end_time is not None
    
    def finish(self, status: str = "ok") -> None:
        """Termine le span."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
    
    def log(self, message: str, **kwargs: Any) -> None:
        """Ajoute un log au span."""
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
        }


# ==========================================
# HEALTH CHECK
# ==========================================

@dataclass
class HealthCheck:
    """Résultat d'un health check."""
    component: str
    healthy: bool
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Score (0-1)
    score: float = 1.0


# ==========================================
# TELEMETRY CONFIG
# ==========================================

@dataclass
class TelemetryConfig:
    """Configuration de la télémétrie."""
    # Enabled
    enabled: bool = True
    
    # Sampling
    metrics_sample_rate: float = 1.0  # 1.0 = 100%
    events_sample_rate: float = 1.0
    traces_sample_rate: float = 0.1  # 10% by default
    
    # Retention
    max_events: int = 10000
    max_traces: int = 1000
    max_metrics: int = 10000
    
    # Intervals
    health_check_interval_s: float = 10.0
    metrics_export_interval_s: float = 60.0
    
    # Export
    export_enabled: bool = False
    export_endpoint: str = ""
    
    # Log level
    log_events: bool = True
    log_metrics: bool = False


# ==========================================
# METRICS COLLECTOR
# ==========================================

class MetricsCollector:
    """
    Collecteur de métriques.
    
    Gère counters, gauges, et histograms.
    """
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        
        # Storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        # All metrics for export
        self._metrics: List[Metric] = []
    
    # ==========================================
    # COUNTER
    # ==========================================
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Incrémente un counter."""
        key = self._make_key(name, labels or {})
        self._counters[key] += value
        
        self._record(Metric(
            name=name,
            metric_type=MetricType.COUNTER,
            value=self._counters[key],
            labels=labels or {},
        ))
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Récupère la valeur d'un counter."""
        key = self._make_key(name, labels or {})
        return self._counters.get(key, 0.0)
    
    # ==========================================
    # GAUGE
    # ==========================================
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Définit un gauge."""
        key = self._make_key(name, labels or {})
        self._gauges[key] = value
        
        self._record(Metric(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
        ))
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Récupère la valeur d'un gauge."""
        key = self._make_key(name, labels or {})
        return self._gauges.get(key, 0.0)
    
    # ==========================================
    # HISTOGRAM
    # ==========================================
    
    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Enregistre une valeur dans un histogram."""
        key = self._make_key(name, labels or {})
        self._histograms[key].append(value)
        
        self._record(Metric(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            value=value,
            labels=labels or {},
        ))
    
    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Calcule les stats d'un histogram."""
        key = self._make_key(name, labels or {})
        values = self._histograms.get(key, [])
        
        if not values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / n,
            "p50": sorted_values[int(n * 0.5)],
            "p95": sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1],
            "p99": sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1],
        }
    
    # ==========================================
    # TIMER
    # ==========================================
    
    def timer(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Enregistre un timer."""
        key = self._make_key(name, labels or {})
        self._timers[key].append(duration_ms)
        
        self._record(Metric(
            name=name,
            metric_type=MetricType.TIMER,
            value=duration_ms,
            labels=labels or {},
        ))
    
    def time(self, name: str, labels: Optional[Dict[str, str]] = None) -> "TimerContext":
        """Context manager pour mesurer le temps."""
        return TimerContext(self, name, labels)
    
    # ==========================================
    # HELPERS
    # ==========================================
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Crée une clé unique."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _record(self, metric: Metric) -> None:
        """Enregistre une métrique."""
        self._metrics.append(metric)
        
        # Limit
        if len(self._metrics) > self.max_metrics:
            self._metrics = self._metrics[-self.max_metrics:]
    
    def get_all_metrics(self) -> List[Metric]:
        """Retourne toutes les métriques."""
        return self._metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des métriques."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats("", {})  # Simplified
                for k in self._histograms
            },
            "total_metrics": len(self._metrics),
        }
    
    def clear(self) -> None:
        """Efface toutes les métriques."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._metrics.clear()


class TimerContext:
    """Context manager pour mesurer le temps."""
    
    def __init__(
        self,
        collector: MetricsCollector,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = 0.0
    
    def __enter__(self) -> "TimerContext":
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args: Any) -> None:
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.timer(self.name, duration_ms, self.labels)


# ==========================================
# EVENT LOGGER
# ==========================================

class EventLogger:
    """Logger d'events."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._events: List[TelemetryEvent] = []
    
    def log(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        message: str = "",
        agent_id: str = "",
        session_id: str = "",
        task_id: str = "",
    ) -> TelemetryEvent:
        """Log un event."""
        event = TelemetryEvent(
            event_type=event_type,
            data=data or {},
            severity=severity,
            message=message,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
        )
        
        self._events.append(event)
        
        # Limit
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        
        return event
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TelemetryEvent]:
        """Récupère les events."""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def get_event_count(self, event_type: Optional[EventType] = None) -> int:
        """Compte les events."""
        if event_type:
            return sum(1 for e in self._events if e.event_type == event_type)
        return len(self._events)
    
    def clear(self) -> None:
        """Efface les events."""
        self._events.clear()


# ==========================================
# TRACE COLLECTOR
# ==========================================

class TraceCollector:
    """Collecteur de traces."""
    
    def __init__(self, max_traces: int = 1000):
        self.max_traces = max_traces
        self._spans: Dict[str, TraceSpan] = {}  # span_id -> span
        self._traces: Dict[str, List[str]] = defaultdict(list)  # trace_id -> [span_ids]
        self._active_spans: Dict[str, TraceSpan] = {}
    
    def start_span(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        agent_id: str = "",
        task_id: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> TraceSpan:
        """Démarre un nouveau span."""
        trace_id = trace_id or str(uuid.uuid4())[:16]
        
        span = TraceSpan(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            agent_id=agent_id,
            task_id=task_id,
            tags=tags or {},
        )
        
        self._spans[span.span_id] = span
        self._traces[trace_id].append(span.span_id)
        self._active_spans[span.span_id] = span
        
        return span
    
    def end_span(self, span_id: str, status: str = "ok") -> Optional[TraceSpan]:
        """Termine un span."""
        span = self._active_spans.pop(span_id, None)
        if span:
            span.finish(status)
        return span
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Récupère tous les spans d'une trace."""
        span_ids = self._traces.get(trace_id, [])
        return [self._spans[sid] for sid in span_ids if sid in self._spans]
    
    def get_active_spans(self) -> List[TraceSpan]:
        """Retourne les spans actifs."""
        return list(self._active_spans.values())
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Récupère un span par ID."""
        return self._spans.get(span_id)
    
    def clear(self) -> None:
        """Efface les traces."""
        self._spans.clear()
        self._traces.clear()
        self._active_spans.clear()


# ==========================================
# HEALTH MONITOR
# ==========================================

class HealthMonitor:
    """Moniteur de santé des composants."""
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._last_results: Dict[str, HealthCheck] = {}
        self._history: List[Dict[str, HealthCheck]] = []
    
    def register_check(
        self,
        component: str,
        check_fn: Callable[[], HealthCheck],
    ) -> None:
        """Enregistre un health check."""
        self._checks[component] = check_fn
    
    def run_check(self, component: str) -> Optional[HealthCheck]:
        """Exécute un health check."""
        check_fn = self._checks.get(component)
        if check_fn:
            result = check_fn()
            self._last_results[component] = result
            return result
        return None
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Exécute tous les health checks."""
        results = {}
        for component in self._checks:
            results[component] = self.run_check(component) or HealthCheck(
                component=component,
                healthy=False,
                message="Check not found",
            )
        
        self._history.append(results)
        return results
    
    def get_last_results(self) -> Dict[str, HealthCheck]:
        """Retourne les derniers résultats."""
        return self._last_results.copy()
    
    def get_overall_health(self) -> float:
        """Calcule la santé globale (0-1)."""
        if not self._last_results:
            return 1.0
        
        scores = [r.score for r in self._last_results.values()]
        return sum(scores) / len(scores) if scores else 1.0
    
    def is_healthy(self) -> bool:
        """Vérifie si tout est sain."""
        return all(r.healthy for r in self._last_results.values())


# ==========================================
# AGENT TELEMETRY
# ==========================================

class AgentTelemetry:
    """
    Système de télémétrie complet pour Phoenix.
    
    C'est LE composant d'observabilité qui permet de comprendre
    ce qui se passe dans le runtime.
    
    Responsabilités:
        1. Collecter les métriques
        2. Logger les events
        3. Tracer les exécutions
        4. Monitorer la santé
        5. Exposer les données
    
    Architecture:
        AgentTelemetry
        │
        ├── MetricsCollector
        │   ├── counters (cycles, decisions, delegations)
        │   ├── gauges (health, load, memory)
        │   └── histograms (latency distribution)
        │
        ├── EventLogger
        │   └── events (state changes, decisions, errors)
        │
        ├── TraceCollector
        │   └── traces (execution spans)
        │
        └── HealthMonitor
            └── checks (component health)
    
    Example:
        telemetry = AgentTelemetry()
        
        # Track a cycle
        telemetry.start_cycle()
        # ... work ...
        telemetry.end_cycle(success=True)
        
        # Track a decision
        telemetry.record_decision("delegate_specialist", confidence=0.8)
        
        # Get stats
        stats = telemetry.get_stats()
        print(f"Cycles: {stats['cycles_total']}")
        print(f"Delegation rate: {stats['delegation_rate']}")
    """
    
    def __init__(
        self,
        agent_id: str = "",
        config: Optional[TelemetryConfig] = None,
    ):
        self.agent_id = agent_id
        self.config = config or TelemetryConfig()
        
        # Components
        self.metrics = MetricsCollector(max_metrics=self.config.max_metrics)
        self.events = EventLogger(max_events=self.config.max_events)
        self.traces = TraceCollector(max_traces=self.config.max_traces)
        self.health = HealthMonitor()
        
        # Current context
        self._current_trace_id: Optional[str] = None
        self._current_span: Optional[TraceSpan] = None
        
        # Session
        self._session_id: str = ""
        self._task_id: str = ""
        
        # Callbacks
        self._on_metric: List[Callable[[Metric], None]] = []
        self._on_event: List[Callable[[TelemetryEvent], None]] = []
        
        # Register default health checks
        self._setup_health_checks()
        
        logger.info(f"Telemetry initialized for agent {agent_id}")
    
    def _setup_health_checks(self) -> None:
        """Configure les health checks par défaut."""
        
        def check_memory() -> HealthCheck:
            utilization = self.metrics.get_gauge("memory_utilization")
            healthy = utilization < 0.9
            return HealthCheck(
                component="memory",
                healthy=healthy,
                score=1.0 - utilization,
                message=f"Memory utilization: {utilization:.1%}",
            )
        
        def check_decisions() -> HealthCheck:
            success_rate = self.metrics.get_gauge("decision_success_rate")
            healthy = success_rate > 0.5
            return HealthCheck(
                component="decisions",
                healthy=healthy,
                score=success_rate,
                message=f"Decision success rate: {success_rate:.1%}",
            )
        
        def check_delegations() -> HealthCheck:
            success_rate = self.metrics.get_gauge("delegation_success_rate")
            healthy = success_rate > 0.5 or success_rate == 0
            return HealthCheck(
                component="delegations",
                healthy=healthy,
                score=success_rate if success_rate > 0 else 1.0,
                message=f"Delegation success rate: {success_rate:.1%}",
            )
        
        self.health.register_check("memory", check_memory)
        self.health.register_check("decisions", check_decisions)
        self.health.register_check("delegations", check_delegations)
    
    # ==========================================
    # CONTEXT
    # ==========================================
    
    def set_context(
        self,
        session_id: str = "",
        task_id: str = "",
    ) -> None:
        """Définit le contexte."""
        self._session_id = session_id
        self._task_id = task_id
    
    # ==========================================
    # CYCLE TRACKING
    # ==========================================
    
    def start_cycle(self, cycle_id: str = "") -> None:
        """Enregistre le début d'un cycle."""
        self.metrics.increment("cycles_total")
        
        self._current_trace_id = str(uuid.uuid4())[:16]
        self._current_span = self.traces.start_span(
            operation_name=f"cycle_{cycle_id}",
            trace_id=self._current_trace_id,
            agent_id=self.agent_id,
            task_id=self._task_id,
            tags={"session": self._session_id},
        )
        
        self.events.log(
            event_type=EventType.CYCLE_START,
            message=f"Cycle started: {cycle_id}",
            agent_id=self.agent_id,
            session_id=self._session_id,
            task_id=self._task_id,
            data={"cycle_id": cycle_id},
        )
    
    def end_cycle(self, success: bool = True) -> None:
        """Enregistre la fin d'un cycle."""
        if success:
            self.metrics.increment("cycles_success")
        else:
            self.metrics.increment("cycles_failed")
        
        if self._current_span:
            self.traces.end_span(
                self._current_span.span_id,
                status="ok" if success else "error"
            )
        
        self.events.log(
            event_type=EventType.CYCLE_END,
            message=f"Cycle ended: {'success' if success else 'failed'}",
            agent_id=self.agent_id,
            session_id=self._session_id,
            task_id=self._task_id,
            severity="info" if success else "warning",
        )
    
    # ==========================================
    # STATE TRACKING
    # ==========================================
    
    def record_state_change(
        self,
        from_state: str,
        to_state: str,
        reason: str = "",
    ) -> None:
        """Enregistre un changement d'état."""
        self.events.log(
            event_type=EventType.STATE_CHANGE,
            message=f"State: {from_state} → {to_state}",
            agent_id=self.agent_id,
            session_id=self._session_id,
            task_id=self._task_id,
            data={
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
            },
        )
    
    # ==========================================
    # DECISION TRACKING
    # ==========================================
    
    def record_decision(
        self,
        decision: str,
        confidence: float = 0.8,
        triggers: Optional[List[str]] = None,
    ) -> None:
        """Enregistre une décision."""
        self.metrics.increment("decisions_total")
        self.metrics.increment(f"decisions_{decision}")
        self.metrics.histogram("decision_confidence", confidence)
        
        self.events.log(
            event_type=EventType.DECISION_MADE,
            message=f"Decision: {decision}",
            agent_id=self.agent_id,
            session_id=self._session_id,
            task_id=self._task_id,
            data={
                "decision": decision,
                "confidence": confidence,
                "triggers": triggers or [],
            },
        )
    
    # ==========================================
    # DELEGATION TRACKING
    # ==========================================
    
    def record_delegation(
        self,
        target_agent: str,
        task_id: str = "",
        success: bool = True,
    ) -> None:
        """Enregistre une délégation."""
        self.metrics.increment("delegations_total")
        if success:
            self.metrics.increment("delegations_success")
        else:
            self.metrics.increment("delegations_failed")
        
        self.events.log(
            event_type=EventType.DELEGATION_TRIGGERED if success else EventType.DELEGATION_COMPLETE,
            message=f"Delegation to {target_agent}: {'success' if success else 'failed'}",
            agent_id=self.agent_id,
            session_id=self._session_id,
            task_id=task_id or self._task_id,
            data={
                "target_agent": target_agent,
                "success": success,
            },
            severity="info" if success else "warning",
        )
    
    # ==========================================
    # MEMORY TRACKING
    # ==========================================
    
    def record_memory_utilization(self, utilization: float) -> None:
        """Enregistre l'utilisation mémoire."""
        self.metrics.gauge("memory_utilization", utilization)
        
        if utilization > 0.9:
            self.events.log(
                event_type=EventType.MEMORY_OVERFLOW,
                message=f"Memory overflow: {utilization:.1%}",
                agent_id=self.agent_id,
                severity="error",
                data={"utilization": utilization},
            )
        elif utilization > 0.7:
            self.events.log(
                event_type=EventType.MEMORY_PRESSURE,
                message=f"Memory pressure: {utilization:.1%}",
                agent_id=self.agent_id,
                severity="warning",
                data={"utilization": utilization},
            )
    
    def record_memory_operation(
        self,
        operation: str,
        tokens_before: int,
        tokens_after: int,
    ) -> None:
        """Enregistre une opération mémoire."""
        self.metrics.increment(f"memory_operations_{operation}")
        
        ratio = tokens_after / tokens_before if tokens_before > 0 else 1.0
        self.metrics.histogram("memory_compression_ratio", ratio)
        
        if operation == "compress":
            self.events.log(
                event_type=EventType.MEMORY_COMPRESS,
                message=f"Memory compressed: {tokens_before} → {tokens_after} tokens",
                agent_id=self.agent_id,
                data={"tokens_before": tokens_before, "tokens_after": tokens_after},
            )
    
    # ==========================================
    # RECOVERY TRACKING
    # ==========================================
    
    def record_recovery(
        self,
        error_type: str,
        strategy: str,
        success: bool,
    ) -> None:
        """Enregistre une récupération."""
        self.metrics.increment("recovery_attempts")
        self.metrics.increment(f"recovery_errors_{error_type}")
        self.metrics.increment(f"recovery_strategies_{strategy}")
        
        if success:
            self.metrics.increment("recovery_success")
        
        self.events.log(
            event_type=EventType.RECOVERY_SUCCESS if success else EventType.RECOVERY_FAILED,
            message=f"Recovery {'succeeded' if success else 'failed'}: {strategy} for {error_type}",
            agent_id=self.agent_id,
            severity="info" if success else "error",
            data={
                "error_type": error_type,
                "strategy": strategy,
                "success": success,
            },
        )
    
    # ==========================================
    # COGNITIVE TRACKING
    # ==========================================
    
    def record_cognitive_state(
        self,
        confidence: float,
        fatigue: float,
        load: float,
    ) -> None:
        """Enregistre l'état cognitif."""
        self.metrics.gauge("cognitive_confidence", confidence)
        self.metrics.gauge("cognitive_fatigue", fatigue)
        self.metrics.gauge("cognitive_load", load)
        
        if fatigue > 0.7:
            self.events.log(
                event_type=EventType.COGNITIVE_FATIGUE,
                message=f"Cognitive fatigue: {fatigue:.1%}",
                agent_id=self.agent_id,
                severity="warning",
                data={"fatigue": fatigue},
            )
        
        if confidence < 0.5:
            self.events.log(
                event_type=EventType.LOW_CONFIDENCE,
                message=f"Low confidence: {confidence:.1%}",
                agent_id=self.agent_id,
                severity="warning",
                data={"confidence": confidence},
            )
    
    # ==========================================
    # LATENCY TRACKING
    # ==========================================
    
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Enregistre une latence."""
        self.metrics.timer(f"latency_{operation}", latency_ms)
        self.metrics.histogram(f"latency_{operation}_histogram", latency_ms)
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes."""
        cycles_total = self.metrics.get_counter("cycles_total")
        cycles_success = self.metrics.get_counter("cycles_success")
        delegations_total = self.metrics.get_counter("delegations_total")
        delegations_success = self.metrics.get_counter("delegations_success")
        decisions_total = self.metrics.get_counter("decisions_total")
        
        return {
            # Counts
            "cycles_total": cycles_total,
            "cycles_success": cycles_success,
            "cycles_failed": self.metrics.get_counter("cycles_failed"),
            "decisions_total": decisions_total,
            "delegations_total": delegations_total,
            "delegations_success": delegations_success,
            "recovery_attempts": self.metrics.get_counter("recovery_attempts"),
            "recovery_success": self.metrics.get_counter("recovery_success"),
            
            # Rates
            "cycle_success_rate": cycles_success / cycles_total if cycles_total > 0 else 1.0,
            "delegation_rate": delegations_total / decisions_total if decisions_total > 0 else 0.0,
            "delegation_success_rate": delegations_success / delegations_total if delegations_total > 0 else 1.0,
            
            # Gauges
            "memory_utilization": self.metrics.get_gauge("memory_utilization"),
            "cognitive_confidence": self.metrics.get_gauge("cognitive_confidence"),
            "cognitive_fatigue": self.metrics.get_gauge("cognitive_fatigue"),
            "cognitive_load": self.metrics.get_gauge("cognitive_load"),
            
            # Health
            "health_score": self.health.get_overall_health(),
            "is_healthy": self.health.is_healthy(),
            
            # Events
            "events_count": self.events.get_event_count(),
            "traces_count": len(self.traces._spans),
        }
    
    def get_latency_stats(self, operation: str) -> Dict[str, float]:
        """Retourne les stats de latence."""
        return self.metrics.get_histogram_stats(f"latency_{operation}_histogram")
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[TelemetryEvent]:
        """Retourne les events."""
        return self.events.get_events(event_type=event_type, limit=limit)
    
    def run_health_check(self) -> Dict[str, HealthCheck]:
        """Exécute les health checks."""
        return self.health.run_all_checks()
    
    # ==========================================
    # EXPORT
    # ==========================================
    
    def export_metrics(self) -> List[Dict[str, Any]]:
        """Exporte les métriques."""
        return [m.to_dict() for m in self.metrics.get_all_metrics()]
    
    def export_events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Exporte les events."""
        return [e.to_dict() for e in self.events.get_events(limit=limit)]
    
    def export_traces(self) -> List[Dict[str, Any]]:
        """Exporte les traces."""
        traces = []
        for trace_id in self.traces._traces:
            spans = self.traces.get_trace(trace_id)
            traces.append({
                "trace_id": trace_id,
                "spans": [s.to_dict() for s in spans],
            })
        return traces
    
    # ==========================================
    # CLEAR
    # ==========================================
    
    def clear(self) -> None:
        """Efface toutes les données."""
        self.metrics.clear()
        self.events.clear()
        self.traces.clear()


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_telemetry(
    agent_id: str = "",
    config: Optional[TelemetryConfig] = None,
) -> AgentTelemetry:
    """Factory pour créer un système de télémétrie."""
    return AgentTelemetry(agent_id=agent_id, config=config)
