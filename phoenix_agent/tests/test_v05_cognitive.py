#!/usr/bin/env python3
"""
Phoenix Agent v0.5 - Cognitive Capability Test Suite
====================================================

Tests de validation du modèle de capacités cognitives.

Architecture testée:
    AgentProfile → CapabilityMonitor → Delegation Decision

Components testés:
    - AgentCapability: Capacités avec limites
    - AgentProfile: Profil avec self-model
    - CapabilityMonitor: Surveillance et décisions
    - DelegationTrigger: Triggers cognitifs

Version: 0.5.0 (Cognitive Self-Awareness)
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
# TEST 1: CAPABILITY LIMITS
# ==========================================

def test_capability_limits():
    """Test les limites de capacité."""
    print_header("TEST 1: Capability Limits")
    
    from phoenix_agent.core.capability import (
        CapabilityLimits,
        Domain,
    )
    
    # Créer des limites
    limits = CapabilityLimits(
        max_context_tokens=4000,
        max_iterations=10,
        max_reasoning_depth=5,
        min_confidence_threshold=0.6,
    )
    print(f"✓ CapabilityLimits created:")
    print(f"  max_tokens={limits.max_context_tokens}")
    print(f"  max_iterations={limits.max_iterations}")
    print(f"  max_depth={limits.max_reasoning_depth}")
    
    # Test is_exceeded
    assert limits.is_exceeded(current_tokens=5000) == True
    assert limits.is_exceeded(current_tokens=3000) == False
    print(f"✓ is_exceeded(5000 tokens) = True")
    print(f"✓ is_exceeded(3000 tokens) = False")
    
    # Test get_exceeded_limits
    exceeded = limits.get_exceeded_limits(
        current_tokens=5000,
        current_iterations=12,
        current_confidence=0.5
    )
    print(f"✓ Exceeded limits: {exceeded}")
    assert "CONTEXT_TOKENS" in exceeded
    assert "ITERATIONS" in exceeded
    assert "CONFIDENCE" in exceeded
    
    print("\n✅ Capability Limits test passed!")
    return True


# ==========================================
# TEST 2: AGENT CAPABILITY
# ==========================================

def test_agent_capability():
    """Test la capacité d'agent."""
    print_header("TEST 2: Agent Capability")
    
    from phoenix_agent.core.capability import (
        AgentCapability,
        CapabilityLimits,
        CapabilityResources,
        Domain,
    )
    
    # Créer une capacité
    capability = AgentCapability(
        name="code_expert",
        domain=Domain.CODE,
        proficiency=0.9,
        limits=CapabilityLimits(
            max_context_tokens=8000,
            max_iterations=15,
        ),
        resources=CapabilityResources(
            token_budget=100000,
            available_tools=["python_repl", "file_read"],
        )
    )
    print(f"✓ AgentCapability created: {capability.name}")
    print(f"  domain={capability.domain.value}")
    print(f"  proficiency={capability.proficiency}")
    
    # Test assess
    assessment = capability.assess(
        task_complexity="moderate",
        estimated_tokens=3000,
        estimated_iterations=5,
        required_domain=Domain.CODE
    )
    print(f"✓ Assessment:")
    print(f"  can_execute={assessment.can_execute}")
    print(f"  confidence={assessment.confidence:.2f}")
    print(f"  should_delegate={assessment.should_delegate}")
    
    assert assessment.can_execute == True
    
    # Test avec tâche trop complexe
    assessment2 = capability.assess(
        task_complexity="expert",
        estimated_tokens=10000,  # Dépasse la limite
        required_domain=Domain.CODE
    )
    print(f"✓ Assessment (complex task):")
    print(f"  can_execute={assessment2.can_execute}")
    print(f"  reasons={assessment2.reasons}")
    
    assert assessment2.can_execute == False
    
    print("\n✅ Agent Capability test passed!")
    return True


# ==========================================
# TEST 3: AGENT PROFILE
# ==========================================

def test_agent_profile():
    """Test le profil d'agent."""
    print_header("TEST 3: Agent Profile")
    
    from phoenix_agent.core.agent_profile import (
        AgentProfile,
        AgentState,
        AgentType,
        create_default_profile,
    )
    from phoenix_agent.core.capability import Domain
    
    # Créer un profil par défaut
    profile = create_default_profile(
        name="Phoenix-Main",
        agent_type=AgentType.ORCHESTRATOR,
        max_tokens=4000,
        max_iterations=10,
    )
    print(f"✓ AgentProfile created: {profile.name}")
    print(f"  agent_id={profile.agent_id[:8]}...")
    print(f"  type={profile.agent_type.value}")
    
    # Tester les domaines
    print(f"✓ Primary domains: {[d.value for d in profile.primary_domains]}")
    assert profile.can_handle_domain(Domain.GENERAL) == True
    
    # Tester l'état
    state = profile.state
    print(f"✓ Initial state:")
    print(f"  tokens={state.current_tokens_used}")
    print(f"  iterations={state.current_iterations}")
    print(f"  confidence={state.current_confidence}")
    
    # Simuler l'utilisation
    state.update_tokens(2000)
    state.increment_iteration()
    state.update_confidence(0.8)
    print(f"✓ After usage:")
    print(f"  tokens={state.current_tokens_used}")
    print(f"  iterations={state.current_iterations}")
    print(f"  confidence={state.current_confidence}")
    
    # Tester can_continue
    assert profile.can_continue() == True
    print(f"✓ can_continue() = True")
    
    print("\n✅ Agent Profile test passed!")
    return True


# ==========================================
# TEST 4: CAPABILITY MONITOR
# ==========================================

def test_capability_monitor():
    """Test le moniteur de capacités."""
    print_header("TEST 4: Capability Monitor")
    
    from phoenix_agent.core.agent_profile import (
        AgentProfile,
        create_default_profile,
    )
    from phoenix_agent.core.capability_monitor import (
        CapabilityMonitor,
        MonitoringConfig,
        MonitoringDecision,
        DelegationTrigger,
    )
    
    # Créer profil et monitor
    profile = create_default_profile(
        name="Test-Agent",
        max_tokens=1000,  # Low for testing
        max_iterations=5,
    )
    
    monitor = CapabilityMonitor(profile)
    print(f"✓ CapabilityMonitor created")
    
    # Check initial state
    result = monitor.check()
    print(f"✓ Initial check:")
    print(f"  decision={result.decision.value}")
    print(f"  token_util={result.token_utilization:.1%}")
    assert result.decision == MonitoringDecision.CONTINUE
    
    # Simuler utilisation élevée
    profile.state.update_tokens(900)  # 90% de 1000
    profile.state.increment_iteration()
    profile.state.increment_iteration()
    profile.state.increment_iteration()
    profile.state.increment_iteration()  # 4/5 iterations
    
    result2 = monitor.check()
    print(f"✓ After high usage:")
    print(f"  decision={result2.decision.value}")
    print(f"  token_util={result2.token_utilization:.1%}")
    print(f"  iter_util={result2.iteration_utilization:.1%}")
    
    # Devrait être en warning ou delegate
    assert result2.decision in [MonitoringDecision.WARNING, MonitoringDecision.DELEGATE]
    
    # Test avec limites dépassées
    profile.state.update_tokens(1100)  # > 1000
    profile.state.increment_iteration()  # 5/5 iterations
    
    result3 = monitor.check()
    print(f"✓ After limits exceeded:")
    print(f"  decision={result3.decision.value}")
    print(f"  triggers={[t.value for t in result3.triggers]}")
    
    assert result3.should_delegate == True
    assert DelegationTrigger.MEMORY_OVERFLOW in result3.triggers or DelegationTrigger.MAX_ITERATIONS in result3.triggers
    
    print("\n✅ Capability Monitor test passed!")
    return True


# ==========================================
# TEST 5: DELEGATION TRIGGERS
# ==========================================

def test_delegation_triggers():
    """Test les triggers de délégation."""
    print_header("TEST 5: Delegation Triggers")
    
    from phoenix_agent.core.capability_monitor import DelegationTrigger
    from phoenix_agent.core.agent_profile import AgentProfile, create_default_profile
    
    # Créer profil avec différents états
    profile = create_default_profile("Test-Agent", max_tokens=1000, max_iterations=5)
    
    # Test 1: Memory pressure
    profile.state.update_tokens(800)  # 80%
    profile.state.current_iterations = 0
    profile.state.current_reasoning_depth = 0
    profile.state.current_confidence = 1.0
    profile.state.cognitive_fatigue = 0.0
    
    triggers = profile.get_delegation_triggers()
    print(f"✓ At 80% memory: triggers={triggers}")
    
    # Test 2: Low confidence
    profile.state.update_tokens(100)
    profile.state.update_confidence(0.4)
    
    triggers = profile.get_delegation_triggers()
    print(f"✓ With low confidence: triggers={triggers}")
    assert "LOW_CONFIDENCE" in triggers
    
    # Test 3: Cognitive fatigue
    profile.state.cognitive_fatigue = 0.8
    triggers = profile.get_delegation_triggers()
    print(f"✓ With fatigue: triggers={triggers}")
    assert "COGNITIVE_FATIGUE" in triggers
    
    # Test 4: Multiple triggers
    profile.state.update_tokens(900)
    profile.state.current_iterations = 5
    profile.state.update_confidence(0.3)
    profile.state.cognitive_fatigue = 0.9
    
    triggers = profile.get_delegation_triggers()
    print(f"✓ Multiple triggers: {triggers}")
    assert len(triggers) >= 3
    
    print("\n✅ Delegation Triggers test passed!")
    return True


# ==========================================
# TEST 6: COGNITIVE DECISION FLOW
# ==========================================

def test_cognitive_decision_flow():
    """Test le flow de décision cognitive complet."""
    print_header("TEST 6: Cognitive Decision Flow")
    
    from phoenix_agent.core.agent_profile import create_default_profile
    from phoenix_agent.core.capability_monitor import (
        CapabilityMonitor,
        MonitoringDecision,
    )
    
    # Simuler un agent qui travaille
    profile = create_default_profile(
        name="Working-Agent",
        max_tokens=2000,
        max_iterations=10,
    )
    
    monitor = CapabilityMonitor(profile)
    
    print("✓ Simulating agent work cycle:")
    
    decisions = []
    for i in range(15):
        # Simuler le travail
        profile.state.update_tokens(200 * (i + 1))
        profile.state.increment_iteration()
        
        # Vérifier l'état
        result = monitor.check()
        decisions.append(result.decision)
        
        status = "✓" if result.can_continue else "⚠"
        print(f"  {status} Iteration {i+1}: decision={result.decision.value}, tokens={profile.state.current_tokens_used}")
        
        # Si doit déléguer, arrêter
        if result.should_delegate:
            print(f"  → Delegation triggered at iteration {i+1}")
            break
    
    # Vérifier qu'on a eu différents états
    assert MonitoringDecision.CONTINUE in decisions
    assert MonitoringDecision.DELEGATE in decisions or MonitoringDecision.ABORT in decisions
    
    print(f"✓ Decision flow captured: {set(d.value for d in decisions)}")
    
    # Vérifier les métriques finales
    metrics = monitor.get_metrics()
    print(f"✓ Final metrics:")
    print(f"  token utilization: {metrics['tokens']['utilization']:.1%}")
    print(f"  iteration utilization: {metrics['iterations']['utilization']:.1%}")
    print(f"  cognitive state: confidence={metrics['cognitive']['confidence']}, fatigue={metrics['cognitive']['fatigue']}")
    
    print("\n✅ Cognitive Decision Flow test passed!")
    return True


# ==========================================
# TEST 7: PROFILE SERIALIZATION
# ==========================================

def test_profile_serialization():
    """Test la sérialisation du profil."""
    print_header("TEST 7: Profile Serialization")
    
    from phoenix_agent.core.agent_profile import create_default_profile
    
    profile = create_default_profile("Test-Agent")
    
    # Utiliser le profil
    profile.state.update_tokens(1500)
    profile.state.increment_iteration()
    profile.state.update_confidence(0.85)
    
    # Sérialiser
    data = profile.to_dict()
    print(f"✓ Serialized profile:")
    print(f"  agent_id={data['agent_id'][:8]}...")
    print(f"  name={data['name']}")
    print(f"  type={data['type']}")
    print(f"  state={data['state']}")
    print(f"  limits={data['limits']}")
    
    # Vérifier les champs
    assert "agent_id" in data
    assert "state" in data
    assert "limits" in data
    assert data["state"]["current_tokens"] == 1500
    
    print("\n✅ Profile Serialization test passed!")
    return True


# ==========================================
# RUN ALL TESTS
# ==========================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "🐦" * 30)
    print("  PHOENIX AGENT v0.5 - COGNITIVE CAPABILITY TEST SUITE")
    print("🐦" * 30)
    
    tests = [
        ("Capability Limits", test_capability_limits, False),
        ("Agent Capability", test_agent_capability, False),
        ("Agent Profile", test_agent_profile, False),
        ("Capability Monitor", test_capability_monitor, False),
        ("Delegation Triggers", test_delegation_triggers, False),
        ("Cognitive Decision Flow", test_cognitive_decision_flow, False),
        ("Profile Serialization", test_profile_serialization, False),
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
        print("\n  🎉 All tests passed! Phoenix v0.5 Cognitive Model ready! 🐦")
        print("\n  Architecture: AgentProfile → CapabilityMonitor → Delegation Decision")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
