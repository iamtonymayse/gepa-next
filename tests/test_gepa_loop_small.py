import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.timeout(10)
def test_gepa_loop_sse(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        resp = client.post(
            "/optimize",
            json={
                "prompt": "answer:",
                "mode": "gepa",
                "dataset": {"name": "toy_qa"},
                "budget": {"max_generations": 2},
            },
        )
        job_id = resp.json()["job_id"]
        events = []
        with client.stream("GET", f"/optimize/{job_id}/events") as stream:
            for line in stream.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                if line.startswith("event: finished"):
                    break
        assert "generation_started" in events
        assert "candidate_scored" in events
        assert "frontier_updated" in events
        assert "finished" in events
        state = client.get(f"/optimize/{job_id}").json()
        assert "best_prompt" in state["result"]
