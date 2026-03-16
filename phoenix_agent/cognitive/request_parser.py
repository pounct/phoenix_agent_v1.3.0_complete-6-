"""
Phoenix Agent - Request Parser & Task Builder
==============================================

Request vs Task Separation - THE KEY TO TRUE AGENT AUTONOMY.

CRITICAL DISTINCTION:
    Request = External input (what comes from outside)
    Task = Internal work unit (what Phoenix manages internally)

Why this matters:
    - Requests are untrusted, variable format, user-driven
    - Tasks are controlled, tracked, agent-driven

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                      EXTERNAL WORLD                          │
    │                                                              │
    │   User Input, API Calls, Events, Messages, Triggers         │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    REQUEST LAYER                             │
    │                                                              │
    │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
    │   │   Request   │───▶│   Request   │───▶│  Request    │   │
    │   │  (raw)      │    │   Parser    │    │  Analysis   │   │
    │   └─────────────┘    └─────────────┘    └─────────────┘   │
    │                                                │            │
    └────────────────────────────────────────────────│────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     TASK LAYER                               │
    │                                                              │
    │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
    │   │    Task     │───▶│   Task      │───▶│  TaskGraph  │   │
    │   │   Builder   │    │   Entity    │    │  (internal) │   │
    │   └─────────────┘    └─────────────┘    └─────────────┘   │
    │                                                │            │
    └────────────────────────────────────────────────│────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   EXECUTION ENGINE                           │
    │                                                              │
    │   TaskGraphExecutor → Agents → Results                      │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

This separation enables:
    1. Autonomous behavior: Phoenix controls tasks, not requests
    2. Task optimization: Decompose, prioritize, schedule
    3. Cost tracking: Per-task costs, not just per-request
    4. Learning: Task-level patterns, not just request-level
    5. Recovery: Task-level retry, not just request-level

Version: 1.3.0
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from uuid import uuid4
import logging
import re

from .task_entity import (
    TaskEntity,
    TaskIdentity,
    TaskLifecycleState,
    TaskDependency,
    TaskDependencyType,
    create_task_entity,
    create_task_identity,
)


logger = logging.getLogger("phoenix.cognitive.request_parser")


# ============================================================================
# REQUEST TYPES
# ============================================================================


class RequestType(str, Enum):
    """Types of external requests."""
    USER_MESSAGE = "user_message"        # Direct user message
    API_CALL = "api_call"                # API request
    EVENT = "event"                      # System event
    SCHEDULED = "scheduled"              # Scheduled task
    DELEGATION = "delegation"            # Delegation from another agent
    TRIGGER = "trigger"                  # Triggered by condition
    INTERNAL = "internal"                # Internal system request


class RequestIntent(str, Enum):
    """Detected intents from requests."""
    QUERY = "query"                      # Simple question
    COMMAND = "command"                  # Action command
    ANALYSIS = "analysis"                # Analysis request
    CREATION = "creation"                # Create something
    MODIFICATION = "modification"        # Modify something
    DELEGATION = "delegation"            # Delegate to specialist
    CLARIFICATION = "clarification"      # Ask for clarification
    FEEDBACK = "feedback"                # Provide feedback
    UNKNOWN = "unknown"                  # Unknown intent


class RequestComplexity(str, Enum):
    """Complexity assessment of request."""
    SIMPLE = "simple"                    # Single step, direct response
    MODERATE = "moderate"                # Multi-step, some planning
    COMPLEX = "complex"                  # Multi-step, decomposition needed
    EXPERT = "expert"                    # Requires specialist agent


# ============================================================================
# REQUEST ANALYSIS
# ============================================================================


@dataclass
class RequestAnalysis:
    """
    Analysis result of an external request.
    
    This is what RequestParser produces before TaskBuilder creates tasks.
    """
    # Identity
    request_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Classification
    request_type: RequestType = RequestType.USER_MESSAGE
    detected_intent: RequestIntent = RequestIntent.UNKNOWN
    complexity: RequestComplexity = RequestComplexity.MODERATE
    confidence: float = 0.0
    
    # Content
    original_input: str = ""
    normalized_input: str = ""
    extracted_entities: List[str] = field(default_factory=list)
    key_topics: List[str] = field(default_factory=list)
    
    # Task suggestions
    suggested_tasks: List[Dict[str, Any]] = field(default_factory=list)
    requires_decomposition: bool = False
    requires_delegation: bool = False
    suggested_agents: List[str] = field(default_factory=list)
    
    # Constraints
    constraints: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    priority: int = 5
    
    # Metadata
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    analysis_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "request_type": self.request_type.value,
            "detected_intent": self.detected_intent.value,
            "complexity": self.complexity.value,
            "confidence": self.confidence,
            "original_input": self.original_input[:200],
            "normalized_input": self.normalized_input[:200],
            "extracted_entities": self.extracted_entities,
            "key_topics": self.key_topics,
            "suggested_tasks": self.suggested_tasks,
            "requires_decomposition": self.requires_decomposition,
            "requires_delegation": self.requires_delegation,
            "suggested_agents": self.suggested_agents,
            "constraints": self.constraints,
            "priority": self.priority,
            "analysis_time_ms": self.analysis_time_ms,
        }


# ============================================================================
# REQUEST PARSER
# ============================================================================


class RequestParser:
    """
    Parse external requests into structured analysis.
    
    This is the ENTRY POINT for all external inputs.
    It transforms raw requests into RequestAnalysis objects.
    
    Features:
        - Intent detection
        - Complexity assessment
        - Entity extraction
        - Task suggestion
        - Constraint extraction
    
    The parser does NOT create tasks - that's TaskBuilder's job.
    This separation allows for:
        - Multiple parsing strategies
        - Request validation
        - Request transformation
        - Request logging
    """
    
    def __init__(
        self,
        intent_patterns: Dict[str, List[str]] = None,
        complexity_thresholds: Dict[str, Any] = None,
    ):
        # Default intent patterns
        self.intent_patterns = intent_patterns or self._default_intent_patterns()
        
        # Default complexity thresholds
        self.complexity_thresholds = complexity_thresholds or {
            "simple_max_words": 10,
            "moderate_max_words": 50,
            "complex_max_words": 200,
        }
        
        # Custom analyzers
        self._custom_analyzers: List[Callable] = []
    
    def _default_intent_patterns(self) -> Dict[str, List[str]]:
        """Default patterns for intent detection."""
        return {
            RequestIntent.QUERY.value: [
                "what", "how", "why", "when", "where", "who", "which",
                "explain", "describe", "tell me", "show me",
            ],
            RequestIntent.COMMAND.value: [
                "do", "run", "execute", "perform", "start", "stop",
                "create", "delete", "update", "move", "copy",
            ],
            RequestIntent.ANALYSIS.value: [
                "analyze", "examine", "review", "evaluate", "assess",
                "compare", "contrast", "investigate", "study",
            ],
            RequestIntent.CREATION.value: [
                "create", "build", "make", "generate", "design",
                "develop", "construct", "write", "compose",
            ],
            RequestIntent.MODIFICATION.value: [
                "modify", "change", "update", "edit", "fix",
                "improve", "refactor", "transform", "convert",
            ],
            RequestIntent.DELEGATION.value: [
                "delegate", "assign", "forward", "hand off",
                "pass to", "let specialist", "expert",
            ],
        }
    
    def parse(
        self,
        input_data: Any,
        request_type: RequestType = RequestType.USER_MESSAGE,
        metadata: Dict[str, Any] = None,
    ) -> RequestAnalysis:
        """
        Parse an input into a RequestAnalysis.
        
        Args:
            input_data: The raw input (string, dict, etc.)
            request_type: Type of request
            metadata: Additional metadata
        
        Returns:
            RequestAnalysis with detected intent, complexity, etc.
        """
        start_time = time.time()
        
        # Normalize input
        if isinstance(input_data, str):
            original = input_data
            normalized = self._normalize_text(input_data)
        elif isinstance(input_data, dict):
            original = input_data.get("content", str(input_data))
            normalized = self._normalize_text(original)
        else:
            original = str(input_data)
            normalized = self._normalize_text(original)
        
        # Create analysis
        analysis = RequestAnalysis(
            request_type=request_type,
            original_input=original,
            normalized_input=normalized,
            metadata=metadata or {},
        )
        
        # Detect intent
        analysis.detected_intent = self._detect_intent(normalized)
        
        # Assess complexity
        analysis.complexity = self._assess_complexity(normalized, metadata)
        
        # Extract entities and topics
        analysis.extracted_entities = self._extract_entities(normalized)
        analysis.key_topics = self._extract_topics(normalized)
        
        # Suggest tasks
        analysis.suggested_tasks = self._suggest_tasks(analysis)
        
        # Determine if decomposition/delegation needed
        analysis.requires_decomposition = analysis.complexity in [
            RequestComplexity.COMPLEX,
            RequestComplexity.EXPERT
        ]
        
        # Extract constraints
        analysis.constraints = self._extract_constraints(normalized)
        
        # Extract priority
        analysis.priority = self._extract_priority(normalized, metadata)
        
        # Run custom analyzers
        for analyzer in self._custom_analyzers:
            try:
                analyzer(analysis)
            except Exception as e:
                logger.warning(f"Custom analyzer failed: {e}")
        
        # Record timing
        analysis.analysis_time_ms = (time.time() - start_time) * 1000
        
        # Set confidence based on analysis quality
        analysis.confidence = self._calculate_confidence(analysis)
        
        return analysis
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        return text
    
    def _detect_intent(self, text: str) -> RequestIntent:
        """Detect intent from text."""
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return RequestIntent(intent)
        
        # Check for question mark
        if "?" in text:
            return RequestIntent.QUERY
        
        return RequestIntent.UNKNOWN
    
    def _assess_complexity(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> RequestComplexity:
        """Assess complexity of request."""
        word_count = len(text.split())
        
        # Check for complexity indicators
        complex_indicators = [
            "multiple", "several", "various", "comprehensive",
            "detailed", "thorough", "complete", "full",
            "step by step", "and then", "after that",
            "integrate", "combine", "merge", "coordinate",
        ]
        
        expert_indicators = [
            "expert", "specialist", "professional", "advanced",
            "complex analysis", "deep dive", "comprehensive review",
        ]
        
        # Check for indicators
        has_complex = any(ind in text for ind in complex_indicators)
        has_expert = any(ind in text for ind in expert_indicators)
        
        # Check metadata
        if metadata:
            if metadata.get("requires_planning"):
                has_complex = True
            if metadata.get("requires_specialist"):
                has_expert = True
        
        # Determine complexity
        if has_expert or word_count > self.complexity_thresholds["complex_max_words"]:
            return RequestComplexity.EXPERT
        elif has_complex or word_count > self.complexity_thresholds["moderate_max_words"]:
            return RequestComplexity.COMPLEX
        elif word_count > self.complexity_thresholds["simple_max_words"]:
            return RequestComplexity.MODERATE
        else:
            return RequestComplexity.SIMPLE
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text."""
        entities = []
        
        # Simple pattern matching for common entities
        # In production, use NER model
        
        # Quoted strings
        quotes = re.findall(r'"([^"]+)"', text)
        entities.extend(quotes)
        
        # Code-like patterns
        code_patterns = re.findall(r'\b[A-Z_][A-Z0-9_]*\b', text)
        entities.extend(code_patterns[:5])  # Limit
        
        # File-like patterns
        file_patterns = re.findall(r'\b[\w-]+\.[\w]+\b', text)
        entities.extend(file_patterns[:5])
        
        return list(set(entities))
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        # Simple keyword extraction
        # In production, use proper NLP
        
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "and", "but", "or", "nor", "so", "yet", "both", "either",
            "neither", "not", "only", "own", "same", "than", "too",
            "very", "just", "also", "now", "here", "there", "when",
            "where", "why", "how", "all", "each", "few", "more",
            "most", "other", "some", "such", "no", "any", "this",
            "that", "these", "those", "what", "which", "who", "whom",
        }
        
        words = text.lower().split()
        topics = [
            word for word in words
            if word not in stop_words and len(word) > 3
        ]
        
        # Get unique, most frequent
        word_freq = {}
        for word in topics:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_topics = sorted(
            word_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [word for word, freq in sorted_topics[:5]]
    
    def _suggest_tasks(self, analysis: RequestAnalysis) -> List[Dict[str, Any]]:
        """Suggest tasks based on analysis."""
        tasks = []
        
        # Main task from request
        main_task = {
            "goal": analysis.original_input[:200],
            "priority": analysis.priority,
            "complexity": analysis.complexity.value,
            "intent": analysis.detected_intent.value,
        }
        tasks.append(main_task)
        
        # If complex, suggest decomposition
        if analysis.requires_decomposition:
            # Simple decomposition suggestion
            if analysis.detected_intent == RequestIntent.ANALYSIS:
                tasks.extend([
                    {"goal": "Gather relevant information", "type": "research"},
                    {"goal": "Perform analysis", "type": "analysis"},
                    {"goal": "Summarize findings", "type": "synthesis"},
                ])
            elif analysis.detected_intent == RequestIntent.CREATION:
                tasks.extend([
                    {"goal": "Understand requirements", "type": "analysis"},
                    {"goal": "Create draft", "type": "creation"},
                    {"goal": "Review and refine", "type": "review"},
                ])
        
        return tasks
    
    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints from text."""
        constraints = []
        
        # Time constraints
        time_patterns = [
            r'within (\d+) (minutes?|hours?|days?)',
            r'by (tomorrow|next week|monday|tuesday|wednesday|thursday|friday)',
            r'before (\d+)(am|pm)?',
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                constraints.append(f"time: {match}")
        
        # Quality constraints
        quality_patterns = [
            r'must (include|contain|have|be)',
            r'should (include|contain|have|be)',
            r'need to (include|contain|have|be)',
        ]
        
        for pattern in quality_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                constraints.append(f"quality: {match}")
        
        return constraints
    
    def _extract_priority(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Extract priority from text."""
        # Check metadata first
        if metadata and "priority" in metadata:
            return int(metadata["priority"])
        
        # Check for priority words
        high_priority_words = [
            "urgent", "critical", "important", "asap", "immediately",
            "emergency", "priority", "crucial", "essential",
        ]
        
        low_priority_words = [
            "whenever", "eventually", "someday", "when possible",
            "no rush", "low priority", "not urgent",
        ]
        
        text_lower = text.lower()
        
        for word in high_priority_words:
            if word in text_lower:
                return 8
        
        for word in low_priority_words:
            if word in text_lower:
                return 3
        
        return 5  # Default
    
    def _calculate_confidence(self, analysis: RequestAnalysis) -> float:
        """Calculate confidence in analysis."""
        confidence = 0.5
        
        # Intent detection confidence
        if analysis.detected_intent != RequestIntent.UNKNOWN:
            confidence += 0.2
        
        # Entity extraction confidence
        if analysis.extracted_entities:
            confidence += 0.1
        
        # Topic extraction confidence
        if analysis.key_topics:
            confidence += 0.1
        
        # Constraint detection confidence
        if analysis.constraints:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    # ========================================================================
    # EXTENSIBILITY
    # ========================================================================
    
    def add_analyzer(self, analyzer: Callable) -> None:
        """Add a custom analyzer function."""
        self._custom_analyzers.append(analyzer)
    
    def add_intent_pattern(
        self,
        intent: RequestIntent,
        patterns: List[str]
    ) -> None:
        """Add patterns for an intent."""
        if intent.value not in self.intent_patterns:
            self.intent_patterns[intent.value] = []
        self.intent_patterns[intent.value].extend(patterns)


# ============================================================================
# TASK GRAPH
# ============================================================================


@dataclass
class TaskNode:
    """
    A node in the task graph.
    
    Wraps TaskEntity with graph-specific information.
    """
    task: TaskEntity
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    dependents: List[str] = field(default_factory=list)    # Task IDs
    
    # Execution info
    assigned_agent: Optional[str] = None
    execution_order: int = 0
    
    @property
    def task_id(self) -> str:
        return self.task.task_id
    
    @property
    def is_ready(self) -> bool:
        """Check if all dependencies are satisfied."""
        # This needs to be checked against completed tasks
        return len(self.dependencies) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.task.goal[:100],
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "state": self.task.state.value,
            "execution_order": self.execution_order,
        }


@dataclass
class TaskGraph:
    """
    A graph of tasks with dependencies.
    
    This is the INTERNAL representation of work in Phoenix.
    Phoenix operates on TaskGraphs, not on requests.
    
    Features:
        - Dependency tracking
        - Execution ordering
        - Parallel task identification
        - Progress tracking
    """
    # Identity
    graph_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Nodes
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    root_task_id: Optional[str] = None
    
    # Ordering
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    
    # Status
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_task(
        self,
        task: TaskEntity,
        dependencies: List[str] = None
    ) -> str:
        """
        Add a task to the graph.
        
        Args:
            task: The task entity
            dependencies: List of task IDs this depends on
        
        Returns:
            The task ID
        """
        node = TaskNode(
            task=task,
            dependencies=dependencies or [],
        )
        
        self.nodes[task.task_id] = node
        
        # Update dependents
        for dep_id in (dependencies or []):
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.append(task.task_id)
        
        # Set root if first task
        if self.root_task_id is None:
            self.root_task_id = task.task_id
        
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[TaskEntity]:
        """Get a task by ID."""
        node = self.nodes.get(task_id)
        return node.task if node else None
    
    def get_ready_tasks(self, completed: Set[str]) -> List[TaskEntity]:
        """Get tasks that are ready to execute."""
        ready = []
        for node in self.nodes.values():
            if node.task.is_terminal:
                continue
            
            # Check all dependencies are completed
            all_deps_done = all(
                dep_id in completed
                for dep_id in node.dependencies
            )
            
            if all_deps_done:
                ready.append(node.task)
        
        return ready
    
    def get_blocking_tasks(self, task_id: str) -> List[str]:
        """Get tasks blocking a specific task."""
        node = self.nodes.get(task_id)
        if not node:
            return []
        
        return [
            dep_id for dep_id in node.dependencies
            if not self.nodes[dep_id].task.is_terminal
        ]
    
    def calculate_execution_order(self) -> List[str]:
        """
        Calculate topological execution order.
        
        Returns:
            List of task IDs in execution order
        """
        # Simple topological sort
        visited = set()
        order = []
        
        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            
            node = self.nodes.get(task_id)
            if node:
                for dep_id in node.dependencies:
                    visit(dep_id)
                order.append(task_id)
        
        for task_id in self.nodes:
            visit(task_id)
        
        self.execution_order = order
        return order
    
    def identify_parallel_groups(self) -> List[List[str]]:
        """
        Identify groups of tasks that can run in parallel.
        
        Returns:
            List of task ID groups
        """
        # Group by dependency depth
        depths = {}
        
        def get_depth(task_id: str) -> int:
            if task_id in depths:
                return depths[task_id]
            
            node = self.nodes.get(task_id)
            if not node or not node.dependencies:
                depths[task_id] = 0
                return 0
            
            max_dep_depth = max(
                get_depth(dep_id)
                for dep_id in node.dependencies
            )
            
            depths[task_id] = max_dep_depth + 1
            return depths[task_id]
        
        # Calculate depths
        for task_id in self.nodes:
            get_depth(task_id)
        
        # Group by depth
        groups = {}
        for task_id, depth in depths.items():
            if depth not in groups:
                groups[depth] = []
            groups[depth].append(task_id)
        
        # Convert to list of groups
        self.parallel_groups = [
            groups[d] for d in sorted(groups.keys())
        ]
        
        return self.parallel_groups
    
    @property
    def total_tasks(self) -> int:
        return len(self.nodes)
    
    @property
    def completed_tasks(self) -> int:
        return sum(
            1 for node in self.nodes.values()
            if node.task.is_terminal
        )
    
    @property
    def progress(self) -> float:
        if not self.nodes:
            return 0.0
        return self.completed_tasks / self.total_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "graph_id": self.graph_id,
            "correlation_id": self.correlation_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "progress": self.progress,
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "nodes": {tid: node.to_dict() for tid, node in self.nodes.items()},
        }


# ============================================================================
# TASK BUILDER
# ============================================================================


class TaskBuilder:
    """
    Build Task Entities and Task Graphs from Request Analysis.
    
    This is the BRIDGE between external requests and internal tasks.
    
    The builder:
        - Creates TaskEntity objects from RequestAnalysis
        - Builds TaskGraph with dependencies
        - Sets up identity and traceability
        - Assigns priorities and constraints
    """
    
    def __init__(
        self,
        default_priority: int = 5,
        default_timeout: float = 300.0,
        auto_decompose: bool = True,
    ):
        self.default_priority = default_priority
        self.default_timeout = default_timeout
        self.auto_decompose = auto_decompose
    
    def build_from_analysis(
        self,
        analysis: RequestAnalysis,
        parent_identity: TaskIdentity = None,
    ) -> TaskGraph:
        """
        Build a TaskGraph from RequestAnalysis.
        
        Args:
            analysis: The request analysis
            parent_identity: Optional parent identity for subtasks
        
        Returns:
            TaskGraph ready for execution
        """
        # Create graph
        graph = TaskGraph(
            correlation_id=analysis.trace_id,
            metadata={
                "request_id": analysis.request_id,
                "request_type": analysis.request_type.value,
                "intent": analysis.detected_intent.value,
            }
        )
        
        # Create root identity
        root_identity = parent_identity or create_task_identity(
            name=analysis.normalized_input[:50],
            correlation_id=analysis.trace_id,
            session_id=analysis.session_id,
        )
        
        # Create main task
        main_task = self._create_main_task(analysis, root_identity)
        graph.add_task(main_task)
        graph.root_task_id = main_task.task_id
        
        # Create subtasks if decomposition needed
        if analysis.requires_decomposition and self.auto_decompose:
            self._decompose_task(main_task, analysis, graph, root_identity)
        
        # Calculate execution order
        graph.calculate_execution_order()
        graph.identify_parallel_groups()
        
        return graph
    
    def _create_main_task(
        self,
        analysis: RequestAnalysis,
        identity: TaskIdentity,
    ) -> TaskEntity:
        """Create the main task from analysis."""
        task = TaskEntity(
            identity=identity,
            goal=analysis.original_input,
            description=f"Main task for request {analysis.request_id}",
            priority=analysis.priority,
            complexity=analysis.complexity.value,
            tags=analysis.key_topics,
            constraints=analysis.constraints,
            metadata={
                "request_id": analysis.request_id,
                "intent": analysis.detected_intent.value,
                "confidence": analysis.confidence,
            },
        )
        
        # Set deadline if present
        if analysis.deadline:
            task.deadline = analysis.deadline
        
        # Transition to validated
        task.lifecycle.transition(
            TaskLifecycleState.VALIDATED,
            "Task created from request analysis"
        )
        
        return task
    
    def _decompose_task(
        self,
        parent_task: TaskEntity,
        analysis: RequestAnalysis,
        graph: TaskGraph,
        parent_identity: TaskIdentity,
    ) -> None:
        """Decompose a task into subtasks."""
        # Get suggested tasks
        suggested = analysis.suggested_tasks[1:]  # Skip main task
        
        for i, suggestion in enumerate(suggested):
            # Create subtask identity
            sub_identity = parent_identity.create_child_identity(
                name=suggestion.get("goal", f"Subtask {i+1}")[:50]
            )
            
            # Create subtask
            subtask = TaskEntity(
                identity=sub_identity,
                goal=suggestion.get("goal", ""),
                description=f"Subtask {i+1} for {parent_task.task_id}",
                priority=parent_task.priority,
                complexity=suggestion.get("type", "moderate"),
                metadata={
                    "subtask_index": i,
                    "subtask_type": suggestion.get("type", "unknown"),
                },
            )
            
            # Add dependency on parent
            subtask.add_dependency(parent_task.task_id)
            
            # Transition to validated
            subtask.lifecycle.transition(
                TaskLifecycleState.VALIDATED,
                f"Subtask created from decomposition"
            )
            
            # Add to graph
            graph.add_task(subtask, dependencies=[parent_task.task_id])
    
    def build_single_task(
        self,
        goal: str,
        description: str = "",
        priority: int = None,
        metadata: Dict[str, Any] = None,
    ) -> TaskEntity:
        """
        Build a single task without a graph.
        
        Useful for simple operations.
        """
        task = create_task_entity(
            goal=goal,
            description=description,
            priority=priority or self.default_priority,
            metadata=metadata or {},
        )
        
        task.lifecycle.transition(
            TaskLifecycleState.VALIDATED,
            "Single task created"
        )
        
        return task
    
    def build_delegation_task(
        self,
        goal: str,
        target_agent: str,
        parent_task_id: str = None,
        identity: TaskIdentity = None,
    ) -> TaskEntity:
        """
        Build a task specifically for delegation.
        """
        task = TaskEntity(
            identity=identity or create_task_identity(name=goal[:50]),
            goal=goal,
            description=f"Delegation to {target_agent}",
            assigned_agent=target_agent,
            metadata={
                "delegation_target": target_agent,
                "parent_task_id": parent_task_id,
            },
        )
        
        if parent_task_id:
            task.add_dependency(parent_task_id)
        
        task.lifecycle.transition(
            TaskLifecycleState.VALIDATED,
            f"Delegation task created for {target_agent}"
        )
        
        return task


# ============================================================================
# FACTORIES
# ============================================================================


def create_request_parser() -> RequestParser:
    """Create a RequestParser with default configuration."""
    return RequestParser()


def create_task_builder(
    default_priority: int = 5,
    auto_decompose: bool = True,
) -> TaskBuilder:
    """Create a TaskBuilder with specified configuration."""
    return TaskBuilder(
        default_priority=default_priority,
        auto_decompose=auto_decompose,
    )
