import importlib
from fastapi.testclient import TestClient


def test_retrieval_influences_context(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.post(
            "/v1/optimize",
            json={
                "prompt": "classify sentiment",
                "examples": [
                    {"input": "I love it", "expected": "positive"},
                    {"input": "I hate it", "expected": "negative"},
                ],
            },
        )
        assert r.status_code == 200
