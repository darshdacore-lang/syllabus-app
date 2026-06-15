#!/usr/bin/env python3
"""
Quick test script to verify Python API server works correctly.
Run this independently to test the backend without Electron.
"""

import sys
import json
try:
    import requests
    _have_requests = True
except Exception:
    import urllib.request as _ur
    import urllib.error as _ue
    _have_requests = False
import time
from pathlib import Path
from subprocess import Popen
import signal

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

API_URL = "http://localhost:5555"

def test_api():
    """Test API endpoints."""
    
    print("🧪 Testing Python API Server\n")
    
    # Test 1: Health check
    print("1️⃣  Health check...")
    try:
        if _have_requests:
            resp = requests.get(f"{API_URL}/health", timeout=5)
            status = resp.status_code
            data = resp.json()
        else:
            with _ur.urlopen(f"{API_URL}/health") as r:
                status = r.getcode()
                data = json.loads(r.read().decode('utf-8'))
        print(f"   ✅ Status: {status}")
        print(f"   Response: {data}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 2: List commands
    print("2️⃣  List available commands...")
    try:
        if _have_requests:
            resp = requests.get(f"{API_URL}/commands", timeout=5)
            commands = resp.json()['commands']
        else:
            with _ur.urlopen(f"{API_URL}/commands") as r:
                commands = json.loads(r.read().decode('utf-8'))['commands']
        print(f"   ✅ Found {len(commands)} commands")
        print(f"   Commands: {', '.join(commands[:5])}...\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 3: Get active session (should be None initially)
    print("3️⃣  Get active session...")
    try:
        if _have_requests:
            resp = requests.post(
                f"{API_URL}/api",
                json={"command": "get_active"},
                timeout=5
            )
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            payload = json.dumps({"command": "get_active"}).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=payload, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        print(f"   ✅ Status: {result['success']}")
        print(f"   Active: {result['data']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 4: Start a focus session
    print("4️⃣  Start focus session (5 min)...")
    try:
        payload = {"command": "start_focus", "args": {"subject": "Testing", "minutes": 5}}
        if _have_requests:
            resp = requests.post(f"{API_URL}/api", json=payload, timeout=5)
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            body = json.dumps(payload).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=body, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        if result['success']:
            session = result['data']
            print(f"   ✅ Session started")
            print(f"   - Subject: {session.get('subject')}")
            print(f"   - Planned: {session.get('planned_minutes')} min")
            print(f"   - Remaining: {session.get('remaining_seconds')}s\n")
        else:
            print(f"   ❌ {result['error']}\n")
            return False
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 5: Tick session
    print("5️⃣  Tick session (simulate 1 sec passing)...")
    try:
        if _have_requests:
            resp = requests.post(f"{API_URL}/api", json={"command": "tick"}, timeout=5)
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            body = json.dumps({"command": "tick"}).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=body, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        if result['success']:
            remaining = result['data'].get('remaining_seconds', 0)
            print(f"   ✅ Ticked")
            print(f"   - Remaining: {remaining}s\n")
        else:
            print(f"   ❌ {result['error']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    # Test 6: Pause session
    print("6️⃣  Pause session...")
    try:
        if _have_requests:
            resp = requests.post(f"{API_URL}/api", json={"command": "pause"}, timeout=5)
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            body = json.dumps({"command": "pause"}).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=body, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        if result['success']:
            print(f"   ✅ Session paused\n")
        else:
            print(f"   ❌ {result['error']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    # Test 7: Add task
    print("7️⃣  Add task...")
    try:
        payload = {"command": "add_task", "args": {"title": "Test task", "subject": "Testing", "tags": ["test"]}}
        if _have_requests:
            resp = requests.post(f"{API_URL}/api", json=payload, timeout=5)
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            body = json.dumps(payload).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=body, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        if result['success']:
            task = result['data']
            print(f"   ✅ Task created")
            print(f"   - ID: {task.get('id')}")
            print(f"   - Title: {task.get('title')}\n")
        else:
            print(f"   ❌ {result['error']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    # Test 8: List tasks
    print("8️⃣  List tasks...")
    try:
        payload = {"command": "list_tasks", "args": {"include_done": False}}
        if _have_requests:
            resp = requests.post(f"{API_URL}/api", json=payload, timeout=5)
            result = resp.json()
        else:
            req = _ur.Request(f"{API_URL}/api", method='POST')
            body = json.dumps(payload).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            with _ur.urlopen(req, data=body, timeout=5) as r:
                result = json.loads(r.read().decode('utf-8'))
        if result['success']:
            tasks = result['data']
            print(f"   ✅ Found {len(tasks)} open tasks\n")
        else:
            print(f"   ❌ {result['error']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    print("✅ All tests completed!")
    return True

if __name__ == "__main__":
    # Start server if not running
    print("Starting Python API server...\n")
    
    server_process = Popen(
        [sys.executable, str(ROOT_DIR / "app/api_server.py")],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Run tests
        success = test_api()
        sys.exit(0 if success else 1)
    finally:
        # Cleanup
        print("\nShutting down server...")
        server_process.send_signal(signal.SIGTERM)
        server_process.wait(timeout=5)
