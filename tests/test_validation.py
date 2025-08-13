import importlib
from fastapi.testclient import TestClient

def test_iterations_min(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.post("/v1/optimize", json={"prompt":"hi"}, params={"iterations":0})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
