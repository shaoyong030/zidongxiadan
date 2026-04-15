import requests
OPENCLAW_BASE = "http://127.0.0.1:18789"
paths = ["/api/chat", "/chat", "/api/v1/chat", "/message"]
for path in paths:
    print(f"Testing {path}...")
    try:
        payload = {"message": "hello", "query": "hello", "session_id": "test", "agent_id": "test"}
        res = requests.post(f"{OPENCLAW_BASE}{path}", json=payload, timeout=5)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
