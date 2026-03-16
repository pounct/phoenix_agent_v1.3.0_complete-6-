#!/usr/bin/env python3
"""
Phoenix Agent v0.3 - Kernel Test Suite
=====================================

Tests de validation du kernel Phoenix.

Architecture validée:
    Phoenix → GatewayAdapter → LLM Gateway

Components testés:
    - Contract: Schemas, Events, Session
    - Gateway: Adapter (Mock)
    - Core: State, AgentLoop, Orchestrator
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
# TEST 1: CONTRACT SCHEMAS
# ==========================================

def test_contract_schemas():
    """Test les schémas de contrat."""
    print_header("TEST 1: Contract Schemas")
    
    from phoenix_agent.contract.schemas import (
        GenerateRequest,
        GenerateResponse,
        DEFAULT_MODEL,
        FALLBACK_PROVIDERS,
        POPULAR_MODELS,
    )
    
    # GenerateRequest
    req = GenerateRequest(prompt="Explain quantum computing")
    print(f"✓ GenerateRequest: model={req.model}, prompt='{req.prompt[:30]}...'")
    
    # GenerateResponse
    resp = GenerateResponse(
        response="Quantum computing uses qubits...",
        latency_ms=123.45,
        cached=False,
        model="llama3.2:latest"
    )
    print(f"✓ GenerateResponse: response='{resp.response[:30]}...'")
    print(f"  is_empty={resp.is_empty}, latency={resp.latency_ms}ms")
    
    # Constants
    print(f"✓ DEFAULT_MODEL: {DEFAULT_MODEL}")
    print(f"✓ FALLBACK_PROVIDERS: {FALLBACK_PROVIDERS}")
    print(f"✓ POPULAR_MODELS keys: {list(POPULAR_MODELS.keys())}")
    
    print("\n✅ Contract Schemas test passed!")
    return True


# ==========================================
# TEST 2: CONTRACT EVENTS
# ==========================================

def test_contract_events():
    """Test les événements du contrat."""
    print_header("TEST 2: Contract Events")
    
    from phoenix_agent.contract.events import (
        ThinkEvent,
        ActEvent,
        ObserveEvent,
        CompleteEvent,
        ErrorEvent,
        EventType,
    )
    
    # ThinkEvent
    think = ThinkEvent.create(
        session_id="test-session",
        iteration=1,
        reasoning="Processing request...",
        context_summary="Empty context"
    )
    print(f"✓ ThinkEvent: type={think.event_type}, session={think.session_id[:8]}...")
    
    # ActEvent
    act = ActEvent.create_llm_call(
        session_id="test-session",
        iteration=1,
        model="llama3.2:latest",
        prompt_length=100
    )
    print(f"✓ ActEvent: action_type={act.data.get('action_type')}")
    
    # ObserveEvent
    observe = ObserveEvent.create_llm_response(
        session_id="test-session",
        iteration=1,
        response="Hello!",
        latency_ms=100.0
    )
    print(f"✓ ObserveEvent: obs_type={observe.data.get('observation_type')}")
    
    # CompleteEvent
    complete = CompleteEvent.create(
        session_id="test-session",
        status="completed",
        final_response="Done!",
        total_iterations=1
    )
    print(f"✓ CompleteEvent: status={complete.data.get('status')}")
    
    # ErrorEvent
    error = ErrorEvent.create(
        session_id="test-session",
        iteration=1,
        error_code="TEST_ERROR",
        error_message="Test error"
    )
    print(f"✓ ErrorEvent: code={error.data.get('error_code')}")
    
    print("\n✅ Contract Events test passed!")
    return True


# ==========================================
# TEST 3: CONTRACT SESSION
# ==========================================

def test_contract_session():
    """Test les types de session."""
    print_header("TEST 3: Contract Session")
    
    from phoenix_agent.contract.session import (
        Message,
        Session,
        SessionStatus,
    )
    
    # Message
    msg = Message.user("Hello!")
    print(f"✓ Message: role={msg.role}, content='{msg.content}'")
    
    # Session
    session = Session(model="llama3.2:latest")
    session.add_system("You are helpful.")
    session.add_user("Hello!")
    session.add_assistant("Hi there!")
    
    print(f"✓ Session: id={session.session_id[:8]}...")
    print(f"  messages={session.message_count}, status={session.status}")
    
    # Session lifecycle
    session.start()
    print(f"✓ Session.start(): status={session.status}")
    
    session.complete()
    print(f"✓ Session.complete(): status={session.status}")
    
    # Context
    context = session.get_context()
    print(f"✓ get_context(): {len(context)} chars")
    
    print("\n✅ Contract Session test passed!")
    return True


# ==========================================
# TEST 4: GATEWAY ADAPTER (Mock)
# ==========================================

async def test_gateway_adapter():
    """Test le gateway adapter."""
    print_header("TEST 4: Gateway Adapter (Mock)")
    
    from phoenix_agent.gateway.adapter import (
        MockGatewayAdapter,
        create_gateway_adapter,
    )
    
    # Create via factory
    adapter = create_gateway_adapter(mock=True, mock_response="Hello from Phoenix!")
    print(f"✓ Created MockGatewayAdapter via factory")
    
    # Generate
    response = await adapter.generate(
        prompt="Say hello",
        model="llama3.2:latest"
    )
    print(f"✓ generate(): response='{response.response}'")
    print(f"  latency={response.latency_ms}ms, provider={response.provider}")
    
    # Health check
    health = await adapter.health_check()
    print(f"✓ health_check(): {health}")
    
    # Stats
    if hasattr(adapter, 'call_count'):
        print(f"✓ call_count: {adapter.call_count}")
    
    print("\n✅ Gateway Adapter test passed!")
    return True


# ==========================================
# TEST 5: CORE STATE
# ==========================================

def test_core_state():
    """Test le state management."""
    print_header("TEST 5: Core State")
    
    from phoenix_agent.core.state import (
        SessionState,
        SessionManager,
    )
    
    # SessionState
    state = SessionState(model="llama3.2:latest", max_iterations=5)
    print(f"✓ SessionState: id={state.session_id[:8]}...")
    
    state.add_system("You are helpful.")
    state.add_user("Hello!")
    print(f"✓ Messages added: count={state.session.message_count}")
    
    # Lifecycle
    state.start()
    state.increment_iteration()
    print(f"✓ iteration={state.iteration}, status={state.status}")
    print(f"  can_continue={state.can_continue()}")
    
    # SessionManager
    manager = SessionManager()
    s1 = manager.create(model="llama3.2:latest")
    s2 = manager.create(model="mistral:latest")
    print(f"✓ SessionManager: created 2 sessions")
    print(f"  list_all: {manager.list_all()}")
    
    print("\n✅ Core State test passed!")
    return True


# ==========================================
# TEST 6: AGENT LOOP
# ==========================================

async def test_agent_loop():
    """Test l'agent loop."""
    print_header("TEST 6: Agent Loop")
    
    from phoenix_agent.gateway.adapter import MockGatewayAdapter
    from phoenix_agent.core.agent_loop import AgentLoop
    
    # Setup
    adapter = MockGatewayAdapter(
        response_content="I am Phoenix, your AI assistant!"
    )
    loop = AgentLoop(
        adapter=adapter,
        max_iterations=5,
        enable_thinking=True
    )
    print(f"✓ AgentLoop created")
    
    # Run
    result = await loop.run(
        user_input="Who are you?",
        model="llama3.2:latest"
    )
    
    print(f"✓ run() result:")
    print(f"  status={result.status}")
    print(f"  response='{result.response[:50]}...'")
    print(f"  iterations={result.iterations}")
    print(f"  is_success={result.is_success}")
    
    print("\n✅ Agent Loop test passed!")
    return True


# ==========================================
# TEST 7: ORCHESTRATOR
# ==========================================

async def test_orchestrator():
    """Test l'orchestrator."""
    print_header("TEST 7: Orchestrator")
    
    from phoenix_agent.core.orchestrator import (
        PhoenixOrchestrator,
        create_orchestrator,
    )
    
    # Create via factory
    orchestrator = create_orchestrator(
        mock=True,
        mock_response="Hello! I'm Phoenix, ready to help!"
    )
    print(f"✓ Orchestrator created via factory")
    
    # Run
    result = await orchestrator.run(
        user_input="Hello Phoenix!",
        model="llama3.2:latest"
    )
    
    print(f"✓ run() result:")
    print(f"  session_id={result.session_id[:8]}...")
    print(f"  status={result.status}")
    print(f"  response='{result.response}'")
    print(f"  iterations={result.iterations}")
    
    # Session management
    sessions = orchestrator.list_sessions()
    print(f"✓ list_sessions: {sessions}")
    
    print("\n✅ Orchestrator test passed!")
    return True


# ==========================================
# TEST 8: STREAMING
# ==========================================

async def test_streaming():
    """Test le streaming."""
    print_header("TEST 8: Streaming")
    
    from phoenix_agent.core.orchestrator import create_orchestrator
    
    orchestrator = create_orchestrator(
        mock=True,
        mock_response="Streaming response from Phoenix!"
    )
    
    events = []
    async for event in orchestrator.run_stream(
        user_input="Stream me a response",
        model="llama3.2:latest"
    ):
        events.append(event)
        print(f"  → {event.event_type}")
    
    print(f"✓ Received {len(events)} events")
    
    # Verify event types
    event_types = [e.event_type for e in events]
    print(f"✓ Event types: {event_types}")
    
    print("\n✅ Streaming test passed!")
    return True


# ==========================================
# RUN ALL TESTS
# ==========================================

async def run_all_tests():
    """Run all tests."""
    print("\n" + "🐦" * 30)
    print("  PHOENIX AGENT v0.3 - KERNEL TEST SUITE")
    print("🐦" * 30)
    
    tests = [
        ("Contract Schemas", test_contract_schemas, False),
        ("Contract Events", test_contract_events, False),
        ("Contract Session", test_contract_session, False),
        ("Gateway Adapter", test_gateway_adapter, True),
        ("Core State", test_core_state, False),
        ("Agent Loop", test_agent_loop, True),
        ("Orchestrator", test_orchestrator, True),
        ("Streaming", test_streaming, True),
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
        print("\n  🎉 All tests passed! Phoenix v0.3 is ready! 🐦")
        print("\n  Architecture: Phoenix → GatewayAdapter → LLM Gateway")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
