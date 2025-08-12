import importlib
import time

from fastapi.testclient import TestClient


def test_optimize_sse(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        resp = client.post("/optimize", params={"iterations": 1})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        with client.stream("GET", f"/optimize/{job_id}/events") as stream:
            line_iter = stream.iter_lines()
            first = next(line_iter)
            assert first.startswith("retry:")
            started = False
            finished = False
            start_time = time.time()
            for line in line_iter:
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    if event == "started":
                        started = True
                    if event == "finished":
                        finished = True
                if finished or time.time() - start_time > 5:
                    break
            assert started
            assert finished
