import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.timeout(5)
def test_optimize_sse(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        resp = client.post("/optimize", json={"prompt": "hi"}, params={"iterations": 1})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        with client.stream(
            "GET", f"/optimize/{job_id}/events", headers={"Authorization": "Bearer token"}
        ) as stream:
            line_iter = stream.iter_lines()
            first = next(line_iter)
            assert first.startswith("retry:")
            started = False
            finished = False
            for line in line_iter:
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    if event == "started":
                        started = True
                    if event == "finished":
                        finished = True
                        break
            assert started
            assert finished
