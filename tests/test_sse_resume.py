import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.timeout(5)
def test_sse_resume(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        resp = client.post("/v1/optimize", json={"prompt": "hi"}, params={"iterations": 3})
        job_id = resp.json()["job_id"]

        with client.stream("GET", f"/v1/optimize/{job_id}/events") as stream:
            lines = stream.iter_lines()
            next(lines)  # retry prelude
            events = []
            last_id = 0
            while len(events) < 2:
                line = next(lines)
                if line.startswith("id:"):
                    last_id = int(line.split(":", 1)[1])
                if line.startswith("event:"):
                    ev = line.split(":", 1)[1].strip()
                    if ev not in {"mutation", "selected"}:
                        events.append(ev)
                    next(lines)

        headers = {"Last-Event-ID": str(last_id)}
        with client.stream(
            "GET", f"/v1/optimize/{job_id}/events", headers=headers
        ) as stream:
            lines = stream.iter_lines()
            next(lines)
            received = []
            ids = []
            current_id = None
            for line in lines:
                if line.startswith("id:"):
                    current_id = int(line.split(":", 1)[1])
                elif line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_id is not None:
                    if event not in {"mutation", "selected"}:
                        received.append(event)
                        ids.append(current_id)
                    if event == "finished":
                        break
            assert received == ["progress", "progress", "finished"]
            assert ids[0] >= last_id + 1
            assert ids == sorted(ids)
