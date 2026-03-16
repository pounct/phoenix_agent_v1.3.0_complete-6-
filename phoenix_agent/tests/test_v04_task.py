#!/usr/bin/env python3
"""
Phoenix Agent v0.4 - Task Abstraction Test Suite
================================================

Tests de validation de l'abstraction Task.

Architecture validée:
    UserInput → Task → TaskManager → Execution Plan

Components testés:
    - Task: Création, états, hiérarchie
    - TaskManager: Analyse, classification, décomposition
    - DelegationEngine: Structure (v0.4)
    - MemoryManager: Structure (v0.4)
    - SubAgent: Structure (v0.4)
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ==========================================
# TEST 1: TASK CREATION
# ==========================================

def test_task_creation():
    """Test la création de tâches."""
    print_header("TEST 1: Task Creation")
    
    from phoenix_agent.core.task import (
        Task,
        TaskType,
        TaskComplexity,
        TaskPriority,
        TaskStatus,
    )
    
    # Créer une tâche simple
    task = Task.create(
        goal="Explain quantum computing",
        task_type=TaskType.QUERY,
        complexity=TaskComplexity.MODERATE
    )
    print(f"✓ Task created: id={task.task_id[:8]}...")
    print(f"  goal='{task.goal[:30]}...'")
    print(f"  type={task.task_type.value}, complexity={task.complexity.value}")
    
    # Créer depuis input utilisateur
    task2 = Task.from_user_input("What is machine learning?")
    print(f"✓ Task from user input: id={task2.task_id[:8]}...")
    print(f"  is_root={task2.is_root}, status={task2.status.value}")
    
    # Vérifier les propriétés
    assert task.is_root == True
    assert task.is_terminal == False
    assert task.is_active == True
    
    print("\n✅ Task Creation test passed!")
    return True


# ==========================================
# TEST 2: TASK LIFECYCLE
# ==========================================

def test_task_lifecycle():
    """Test le cycle de vie d'une tâche."""
    print_header("TEST 2: Task Lifecycle")
    
    from phoenix_agent.core.task import Task, TaskStatus
    
    task = Task.from_user_input("Test task")
    
    # États initiaux
    print(f"✓ Initial status: {task.status.value}")
    assert task.status == TaskStatus.PENDING
    
    # Démarrer
    task.start()
    print(f"✓ After start(): {task.status.value}")
    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None
    
    # Compléter
    task.complete("Task completed successfully!")
    print(f"✓ After complete(): {task.status.value}")
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "Task completed successfully!"
    assert task.is_terminal == True
    
    # Vérifier durée
    print(f"✓ Duration: {task.duration_ms:.2f}ms")
    
    print("\n✅ Task Lifecycle test passed!")
    return True


# ==========================================
# TEST 3: TASK HIERARCHY
# ==========================================

def test_task_hierarchy():
    """Test la hiérarchie des tâches."""
    print_header("TEST 3: Task Hierarchy")
    
    from phoenix_agent.core.task import Task, TaskType
    
    # Tâche racine
    root = Task.from_user_input("Build a web application")
    print(f"✓ Root task: id={root.task_id[:8]}..., depth={root.depth}")
    
    # Créer des sous-tâches
    subtask1 = root.create_subtask(
        goal="Design the architecture",
        task_type=TaskType.ANALYSIS
    )
    print(f"✓ Subtask 1: id={subtask1.task_id[:8]}..., depth={subtask1.depth}")
    assert subtask1.parent_task_id == root.task_id
    assert subtask1.depth == 1
    
    subtask2 = root.create_subtask(
        goal="Implement the backend",
        task_type=TaskType.CODE
    )
    print(f"✓ Subtask 2: id={subtask2.task_id[:8]}..., depth={subtask2.depth}")
    
    # Vérifier la hiérarchie
    print(f"✓ Root has {len(root.child_task_ids)} children")
    assert len(root.child_task_ids) == 2
    assert root.has_children == True
    
    # Créer une sous-sous-tâche
    subsubtask = subtask1.create_subtask(
        goal="Define API endpoints"
    )
    print(f"✓ Sub-subtask: depth={subsubtask.depth}")
    assert subsubtask.depth == 2
    
    print("\n✅ Task Hierarchy test passed!")
    return True


# ==========================================
# TEST 4: TASK ANALYSIS
# ==========================================

def test_task_analysis():
    """Test l'analyse de tâches."""
    print_header("TEST 4: Task Analysis")
    
    from phoenix_agent.core.task import Task
    from phoenix_agent.core.task_manager import TaskManager, ComplexityAnalyzer, TaskTypeClassifier
    
    # Analyseur de complexité
    analyzer = ComplexityAnalyzer()
    
    simple = analyzer.analyze("What is AI?")
    print(f"✓ 'What is AI?' → complexity={simple.value}")
    
    complex_task = analyzer.analyze("Design and implement a distributed system for real-time data processing")
    print(f"✓ 'Design distributed system...' → complexity={complex_task.value}")
    
    # Classificateur de type
    classifier = TaskTypeClassifier()
    
    query_type = classifier.classify("What is machine learning?")
    print(f"✓ 'What is ML?' → type={query_type.value}")
    
    code_type = classifier.classify("Write a function to sort a list")
    print(f"✓ 'Write a function...' → type={code_type.value}")
    
    # TaskManager analyse
    manager = TaskManager()
    
    task = Task.from_user_input("Analyze the performance of this algorithm")
    analysis = manager.analyze(task)
    
    print(f"✓ TaskAnalysis:")
    print(f"  complexity={analysis.complexity.value}")
    print(f"  task_type={analysis.task_type.value}")
    print(f"  should_decompose={analysis.should_decompose}")
    print(f"  recommended_strategy={analysis.recommended_strategy}")
    
    print("\n✅ Task Analysis test passed!")
    return True


# ==========================================
# TEST 5: TASK DECOMPOSITION
# ==========================================

async def test_task_decomposition():
    """Test la décomposition de tâches."""
    print_header("TEST 5: Task Decomposition")
    
    from phoenix_agent.core.task import Task, TaskComplexity, TaskType
    from phoenix_agent.core.task_manager import TaskManager
    
    manager = TaskManager()
    
    # Tâche complexe
    task = Task.create(
        goal="Implement a user authentication system",
        task_type=TaskType.CODE,
        complexity=TaskComplexity.COMPLEX
    )
    
    print(f"✓ Complex task: '{task.goal[:40]}...'")
    
    # Décomposer
    plan = await manager.decompose(task)
    
    print(f"✓ Decomposition plan created:")
    print(f"  root_task_id={plan.root_task_id[:8]}...")
    print(f"  total_subtasks={plan.total_subtasks}")
    
    for i, subtask in enumerate(plan.subtasks):
        print(f"  [{i+1}] {subtask.goal[:50]}... (type={subtask.task_type.value})")
    
    # Vérifier l'ordre d'exécution
    print(f"✓ Execution order: {len(plan.execution_order)} tasks")
    
    print("\n✅ Task Decomposition test passed!")
    return True


# ==========================================
# TEST 6: DELEGATION ENGINE (Structure)
# ==========================================

async def test_delegation_engine():
    """Test le moteur de délégation (structure)."""
    print_header("TEST 6: Delegation Engine (Structure)")
    
    from phoenix_agent.core.delegation import (
        DelegationEngine,
        DelegationRequest,
        AgentRole,
        AgentCapability,
        SubAgentInfo,
    )
    from phoenix_agent.core.task import Task
    
    engine = DelegationEngine()
    
    # Enregistrer des agents
    coder_agent = SubAgentInfo(
        agent_id="coder-1",
        role=AgentRole.CODER,
        capabilities=[
            AgentCapability(
                name="python",
                description="Python development",
                supported_task_types=["code"]
            )
        ]
    )
    engine.register_agent(coder_agent)
    print(f"✓ Registered agent: {coder_agent.agent_id} ({coder_agent.role.value})")
    
    # Lister les agents
    agents = engine.list_agents()
    print(f"✓ Agents count: {len(agents)}")
    
    # Créer une requête de délégation
    task = Task.from_user_input("Write a Python function")
    request = DelegationRequest(
        task=task,
        required_role=AgentRole.CODER
    )
    
    # Trouver le meilleur agent
    best_agent = engine.find_best_agent(request)
    if best_agent:
        print(f"✓ Best agent found: {best_agent.agent_id}")
    
    # Stats
    stats = engine.get_stats()
    print(f"✓ Stats: agents_count={stats['agents_count']}")
    
    print("\n✅ Delegation Engine test passed!")
    return True


# ==========================================
# TEST 7: MEMORY MANAGER (Structure)
# ==========================================

def test_memory_manager():
    """Test le gestionnaire de mémoire (structure)."""
    print_header("TEST 7: Memory Manager (Structure)")
    
    from phoenix_agent.core.memory_manager import (
        MemoryManager,
        MemoryManagerConfig,
        MemoryStrategy,
    )
    from phoenix_agent.contract.session import Session
    
    config = MemoryManagerConfig(
        max_tokens=1000,
        window_size=5
    )
    manager = MemoryManager(config)
    
    # Créer une session avec des messages
    session = Session()
    session.add_system("You are helpful.")
    for i in range(10):
        session.add_user(f"Message {i}")
        session.add_assistant(f"Response {i}")
    
    print(f"✓ Session created: {session.message_count} messages")
    
    # Analyser
    analysis = manager.analyze(session)
    print(f"✓ Analysis:")
    print(f"  total_messages={analysis.total_messages}")
    print(f"  estimated_tokens={analysis.estimated_tokens}")
    print(f"  utilization={analysis.utilization:.2%}")
    print(f"  should_compress={analysis.should_compress}")
    
    # Compresser
    window = manager.compress(session)
    print(f"✓ Compression:")
    print(f"  original={window.original_message_count} → compressed={len(window.messages)}")
    print(f"  is_compressed={window.is_compressed}")
    
    # Stats
    stats = manager.get_stats(session)
    print(f"✓ Stats: compression_ratio={stats.compression_ratio:.2f}")
    
    print("\n✅ Memory Manager test passed!")
    return True


# ==========================================
# TEST 8: SUB-AGENT (Structure)
# ==========================================

async def test_subagent():
    """Test les sub-agents (structure)."""
    print_header("TEST 8: Sub-Agent (Structure)")
    
    from phoenix_agent.core.subagent import (
        SubAgent,
        SubAgentConfig,
        SubAgentPool,
        SubAgentStatus,
    )
    from phoenix_agent.core.delegation import AgentRole
    from phoenix_agent.core.task import Task
    from phoenix_agent.gateway.adapter import MockGatewayAdapter
    
    # Créer un adapter mock
    adapter = MockGatewayAdapter(response_content="Sub-agent response!")
    
    # Créer un pool
    pool = SubAgentPool(adapter)
    
    # Créer des agents
    coder = pool.create_agent(
        role=AgentRole.CODER,
        system_prompt="You are a Python expert."
    )
    print(f"✓ Created sub-agent: {coder.config.agent_id}")
    
    researcher = pool.create_agent(
        role=AgentRole.RESEARCHER,
        system_prompt="You are a research specialist."
    )
    print(f"✓ Created sub-agent: {researcher.config.agent_id}")
    
    # Lister les agents
    available = pool.list_available()
    print(f"✓ Available agents: {len(available)}")
    
    # Stats du pool
    stats = pool.get_stats()
    print(f"✓ Pool stats: total={stats['total_agents']}, idle={stats['idle_agents']}")
    
    # Exécuter une tâche avec un sub-agent
    task = Task.from_user_input("Write a hello world in Python")
    result = await coder.execute(task)
    
    print(f"✓ Sub-agent execution:")
    print(f"  success={result.success}")
    print(f"  result='{result.result[:40]}...'")
    print(f"  iterations={result.iterations}")
    
    # Info de l'agent
    info = coder.get_info()
    print(f"✓ Agent info: tasks_completed={info['tasks_completed']}")
    
    print("\n✅ Sub-Agent test passed!")
    return True


# ==========================================
# RUN ALL TESTS
# ==========================================

async def run_all_tests():
    """Run all tests."""
    print("\n" + "🐦" * 30)
    print("  PHOENIX AGENT v0.4 - TASK ABSTRACTION TEST SUITE")
    print("🐦" * 30)
    
    tests = [
        ("Task Creation", test_task_creation, False),
        ("Task Lifecycle", test_task_lifecycle, False),
        ("Task Hierarchy", test_task_hierarchy, False),
        ("Task Analysis", test_task_analysis, False),
        ("Task Decomposition", test_task_decomposition, True),
        ("Delegation Engine", test_delegation_engine, True),
        ("Memory Manager", test_memory_manager, False),
        ("Sub-Agent", test_subagent, True),
    ]
    
    results = []
    
    for name, test_func, is_async in tests:
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ Test '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, r, _ in results if r)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if error:
            print(f"         Error: {error}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed! Phoenix v0.4 Task Abstraction ready! 🐦")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
