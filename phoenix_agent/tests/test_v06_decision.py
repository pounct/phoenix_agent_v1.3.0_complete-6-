#!/usr/bin/env python3
"""
Phoenix Agent v0.6 - Cognitive Decision Layer Test Suite
========================================================

Tests de validation de la couche décisionnelle.

Architecture testée:
    Monitoring → DecisionEngine → DelegationPolicy → Action

Components testés:
    - DecisionEngine: Prend les décisions cognitives
    - DelegationPolicy: Map triggers → actions
    - AgentRole: Spécialisation des agents
    - ResultSynthesizer: Fusion multi-agents

Version: 0.6.0 (Decision Layer)
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ==========================================
# TEST 1: DECISION ENGINE
# ==========================================

def test_decision_engine():
    """Test le moteur de décision."""
    print_header("TEST 1: Decision Engine")
    
    from phoenix_agent.core.decision_engine import (
        DecisionEngine,
        CognitiveDecision,
        DecisionContext,
        DecisionResult,
    )
    from phoenix_agent.core.agent_profile import create_default_profile
    from phoenix_agent.core.capability_monitor import (
        CapabilityMonitor,
        MonitoringResult,
        MonitoringDecision,
        DelegationTrigger,
    )
    
    # Créer profil et monitor
    profile = create_default_profile("Test-Agent", max_tokens=1000, max_iterations=5)
    monitor = CapabilityMonitor(profile)
    
    # Créer engine
    engine = DecisionEngine(profile=profile, monitor=monitor)
    print(f"✓ DecisionEngine created")
    
    # Simuler un contexte de décision
    monitor_result = monitor.check()
    
    context = DecisionContext(
        profile=profile,
        monitor_result=monitor_result,
    )
    
    # Prendre une décision
    result = engine.decide(context)
    print(f"✓ Decision: {result.decision.value}")
    print(f"  reasoning: {result.reasoning}")
    print(f"  confidence: {result.confidence:.2f}")
    
    # Test avec différents triggers
    profile.state.update_tokens(950)  # 95% utilization
    monitor_result = monitor.check()
    
    context2 = DecisionContext(
        profile=profile,
        monitor_result=monitor_result,
    )
    
    result2 = engine.decide(context2)
    print(f"✓ Decision (high memory): {result2.decision.value}")
    
    # Vérifier les propriétés du résultat
    assert hasattr(result, 'should_delegate')
    assert hasattr(result, 'should_stop')
    
    print(f"✓ DecisionResult properties work")
    
    # Vérifier les stats
    stats = engine.get_stats()
    print(f"✓ Stats: {stats['total_decisions']} decisions")
    
    print("\n✅ Decision Engine test passed!")
    return True


# ==========================================
# TEST 2: DELEGATION POLICY
# ==========================================

def test_delegation_policy():
    """Test la politique de délégation."""
    print_header("TEST 2: Delegation Policy")
    
    from phoenix_agent.core.delegation_policy import (
        DelegationPolicy,
        DelegationStrategy,
        TargetAgentType,
        DelegationAction,
        DelegationTrigger,
        PolicyBuilder,
    )
    
    # Créer la politique
    policy = DelegationPolicy()
    print(f"✓ DelegationPolicy created")
    print(f"  default rules: {len(policy._rules)}")
    
    # Tester différentes résolutions
    triggers_to_test = [
        DelegationTrigger.MEMORY_OVERFLOW,
        DelegationTrigger.LOW_CONFIDENCE,
        DelegationTrigger.DOMAIN_MISMATCH,
        DelegationTrigger.MAX_ITERATIONS,
    ]
    
    for trigger in triggers_to_test:
        action = policy.get_action(trigger)
        print(f"✓ {trigger.value} → {action.strategy.value}")
        if action.target_agent_type:
            print(f"  target: {action.target_agent_type.value}")
    
    # Tester le builder fluent
    builder = PolicyBuilder()
    print(f"✓ PolicyBuilder created")
    
    # Tester la résolution de batch
    triggers_batch = [
        DelegationTrigger.MEMORY_PRESSURE,
        DelegationTrigger.LOW_CONFIDENCE,
    ]
    
    actions = policy.resolve_triggers(triggers_batch)
    print(f"✓ Batch resolution: {len(actions)} actions")
    
    # Stats
    stats = policy.get_stats()
    print(f"✓ Policy stats: {stats}")
    
    print("\n✅ Delegation Policy test passed!")
    return True


# ==========================================
# TEST 3: AGENT ROLE
# ==========================================

def test_agent_role():
    """Test les rôles d'agents."""
    print_header("TEST 3: Agent Role")
    
    from phoenix_agent.core.agent_role import (
        AgentRole,
        AgentRoleType,
        RoleCategory,
        RoleRegistry,
        get_predefined_roles,
    )
    from phoenix_agent.core.capability import Domain
    
    # Vérifier les rôles prédéfinis
    roles = get_predefined_roles()
    print(f"✓ Predefined roles: {len(roles)}")
    
    for role_type, role in list(roles.items())[:5]:
        print(f"  - {role_type.value}: {role.category.value}")
    
    # Tester un rôle
    coder_role = roles.get(AgentRoleType.CODER)
    if coder_role:
        print(f"✓ Coder role:")
        print(f"  domains: {[d.value for d in coder_role.domains]}")
        print(f"  skills: {coder_role.skills}")
        print(f"  can_delegate: {coder_role.can_delegate}")
        
        # Test de compatibilité
        assert coder_role.can_handle_domain(Domain.CODE) == True
        assert coder_role.has_skill("python") == True
        print(f"✓ Compatibility checks work")
    
    # Tester le RoleRegistry
    registry = RoleRegistry()
    print(f"✓ RoleRegistry created")
    
    best = registry.find_best_for_task(
        task_type="code",
        domain=Domain.CODE,
    )
    if best:
        print(f"  Best for 'code': {best.role_type.value}")
    
    # Lister par catégorie
    exec_roles = registry.list_by_category(RoleCategory.EXECUTION)
    print(f"✓ Execution roles: {len(exec_roles)}")
    
    print("\n✅ Agent Role test passed!")
    return True


# ==========================================
# TEST 4: RESULT SYNTHESIZER
# ==========================================

def test_result_synthesizer():
    """Test le synthétiseur de résultats."""
    print_header("TEST 4: Result Synthesizer")
    
    from phoenix_agent.core.result_synthesizer import (
        ResultSynthesizer,
        SynthesisStrategy,
        AgentResult,
        synthesize_results,
    )
    from phoenix_agent.core.agent_role import AgentRoleType
    from phoenix_agent.core.task import Task
    
    # Créer des résultats simulés
    results = [
        AgentResult(
            agent_id="agent-1",
            agent_role=AgentRoleType.REASONER,
            task_id="task-1",
            content="First analysis: The data shows significant trends.",
            confidence=0.85,
            quality_score=0.9,
        ),
        AgentResult(
            agent_id="agent-2",
            agent_role=AgentRoleType.ANALYST,
            task_id="task-1",
            content="Second analysis: Additional insights found.",
            confidence=0.75,
            quality_score=0.8,
        ),
        AgentResult(
            agent_id="agent-3",
            agent_role=AgentRoleType.WRITER,
            task_id="task-1",
            content="Summary: Combined results.",
            confidence=0.9,
            quality_score=0.85,
        ),
    ]
    print(f"✓ Created {len(results)} test results")
    
    # Créer le synthétiseur
    synthesizer = ResultSynthesizer(
        default_strategy=SynthesisStrategy.SEQUENTIAL_MERGE
    )
    print(f"✓ ResultSynthesizer created")
    
    # Ajouter les résultats
    synthesizer.add_results(results)
    
    # Créer une tâche
    task = Task(task_id="task-1", goal="Analyze data")
    
    # Synthétiser
    final = synthesizer.synthesize(task)
    
    print(f"✓ Synthesis result:")
    print(f"  strategy: {final.synthesis_strategy.value}")
    print(f"  confidence: {final.confidence:.2f}")
    print(f"  quality: {final.quality_score:.2f}")
    print(f"  sources: {final.source_agents}")
    print(f"  content length: {len(final.content)} chars")
    
    assert final.is_success == True
    assert len(final.source_agents) == 3
    
    # Tester la stratégie BEST_SINGLE
    synthesizer.clear()
    synthesizer.add_results(results)
    
    final_best = synthesizer.synthesize(
        task,
        strategy=SynthesisStrategy.BEST_SINGLE
    )
    print(f"✓ Best single strategy: confidence={final_best.confidence:.2f}")
    
    # Tester la fonction utilitaire
    final_util = synthesize_results(
        results=results,
        task=task,
        strategy=SynthesisStrategy.PARALLEL_VOTE
    )
    print(f"✓ Utility function works: {final_util.synthesis_strategy.value}")
    
    print("\n✅ Result Synthesizer test passed!")
    return True


# ==========================================
# TEST 5: INTEGRATION FLOW
# ==========================================

def test_decision_flow():
    """Test le flow de décision complet."""
    print_header("TEST 5: Integration Decision Flow")
    
    from phoenix_agent.core.agent_profile import create_default_profile
    from phoenix_agent.core.capability_monitor import CapabilityMonitor, DelegationTrigger
    from phoenix_agent.core.decision_engine import DecisionEngine, DecisionContext
    from phoenix_agent.core.delegation_policy import DelegationPolicy
    from phoenix_agent.core.agent_role import RoleRegistry
    from phoenix_agent.core.task import Task
    
    # Setup
    profile = create_default_profile("Test-Agent", max_tokens=2000, max_iterations=10)
    monitor = CapabilityMonitor(profile)
    engine = DecisionEngine(profile=profile, monitor=monitor)
    policy = DelegationPolicy()
    registry = RoleRegistry()
    
    print(f"✓ All components initialized")
    
    # Simuler un cycle de travail
    task = Task.from_user_input("Analyze complex data")
    
    print(f"\n✓ Simulating work cycle:")
    
    for i in range(12):
        # Simuler le travail
        profile.state.update_tokens(300 * (i + 1))
        profile.state.increment_iteration()
        
        # Monitor check
        monitor_result = monitor.check()
        
        # Decision context
        context = DecisionContext(
            profile=profile,
            monitor_result=monitor_result,
            current_task=task,
        )
        
        # Decision
        result = engine.decide(context)
        
        status = "✓" if result.decision.value == "continue" else "⚠"
        print(f"  {status} Iteration {i+1}: {result.decision.value}")
        
        # Check if should stop
        if result.should_stop or result.should_delegate:
            # Get policy action
            if monitor_result.triggers:
                action = policy.get_action(monitor_result.triggers[0])
                print(f"    → Policy action: {action.strategy.value}")
                
                # Find best role
                if action.target_agent_type:
                    best_role = registry.get(action.target_agent_type)
                    if best_role:
                        print(f"    → Target role: {best_role.role_type.value}")
            
            print(f"  → Stopping at iteration {i+1}")
            break
    
    # Stats
    stats = engine.get_stats()
    print(f"\n✓ Decision stats:")
    print(f"  total decisions: {stats['total_decisions']}")
    if 'delegation_rate' in stats:
        print(f"  delegation rate: {stats['delegation_rate']:.1%}")
    
    print("\n✅ Integration Decision Flow test passed!")
    return True


# ==========================================
# TEST 6: ROLE SPECIALIZATION
# ==========================================

def test_role_specialization():
    """Test la spécialisation des rôles."""
    print_header("TEST 6: Role Specialization")
    
    from phoenix_agent.core.agent_role import (
        AgentRole,
        AgentRoleType,
        RoleCategory,
        RoleRegistry,
        Domain,
    )
    
    registry = RoleRegistry()
    
    # Test finding best role for different task types
    test_cases = [
        {
            "task_type": "code",
            "domain": Domain.CODE,
            "skills": ["python"],
        },
        {
            "task_type": "research",
            "domain": Domain.RESEARCH,
            "skills": ["search"],
        },
        {
            "task_type": "analysis",
            "domain": Domain.ANALYSIS,
            "skills": ["statistics"],
        },
        {
            "task_type": "planning",
            "domain": Domain.PLANNING,
            "skills": ["decomposition"],
        },
    ]
    
    print("✓ Testing role matching:")
    for case in test_cases:
        best = registry.find_best_for_task(
            task_type=case["task_type"],
            domain=case["domain"],
            required_skills=case["skills"],
        )
        if best:
            print(f"  {case['task_type']:12} → {best.role_type.value:20} ({best.category.value})")
        else:
            print(f"  {case['task_type']:12} → No match found")
    
    # Test category listing
    print(f"\n✓ Roles by category:")
    for category in RoleCategory:
        roles = registry.list_by_category(category)
        print(f"  {category.value}: {len(roles)} roles")
    
    print("\n✅ Role Specialization test passed!")
    return True


# ==========================================
# RUN ALL TESTS
# ==========================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "🐦" * 30)
    print("  PHOENIX AGENT v0.6 - DECISION LAYER TEST SUITE")
    print("🐦" * 30)
    
    tests = [
        ("Decision Engine", test_decision_engine, False),
        ("Delegation Policy", test_delegation_policy, False),
        ("Agent Role", test_agent_role, False),
        ("Result Synthesizer", test_result_synthesizer, False),
        ("Integration Flow", test_decision_flow, False),
        ("Role Specialization", test_role_specialization, False),
    ]
    
    results = []
    
    for name, test_func, is_async in tests:
        try:
            if is_async:
                import asyncio
                result = asyncio.run(test_func())
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
        print("\n  🎉 All tests passed! Phoenix v0.6 Decision Layer ready! 🐦")
        print("\n  Architecture: Monitor → DecisionEngine → Policy → Action")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
