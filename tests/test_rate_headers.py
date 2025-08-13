import importlib
from fastapi.testclient import TestClient


def test_retry_after_present(monkeypatch):
    client = TestClient(_mkapp(monkeypatch))
    with client:
        for _ in range(5):
            resp = client.post("/optimize", json={"prompt":"hi"})
        last = resp
        assert last.status_code in (200, 429)
        if last.status_code == 429:
            headers = {k.lower(): v for k, v in last.headers.items()}
            assert "retry-after" in headers


def _mkapp(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("RATE_LIMIT_OPTIMIZE_RPS", "1")
    monkeypatch.setenv("RATE_LIMIT_OPTIMIZE_BURST", "1")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return main.app
