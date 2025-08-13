import importlib
from fastapi.testclient import TestClient
import pytest


@pytest.mark.timeout(10)
def test_gepa_loop_roles_and_lessons_sse(monkeypatch):
    # Stubbed model path; no network
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        # Start GEPA-mode optimize job
        resp = client.post(
            "/optimize",
            headers={"Authorization": "Bearer token"},
            json={
                "mode": "gepa",
                "prompt": "Write a greeting",
                "dataset": {"name": "toy_qa"},
                "budget": {"max_generations": 1},
            },
        )
        job_id = resp.json()["job_id"]
        events = []
        with client.stream(
            "GET", f"/optimize/{job_id}/events", headers={"Authorization": "Bearer token"}
        ) as stream:
            for line in stream.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    evt = line.split(":", 1)[1].strip()
                    events.append(evt)
                if line.startswith("event: finished"):
                    break
        # Existing expectations must still hold
        assert "generation_started" in events
        assert "candidate_scored" in events
        assert "frontier_updated" in events
        assert "finished" in events
        # New goodness (non-breaking)
        assert "reflection_started" in events
        assert "lessons_updated" in events
        assert "reflection_finished" in events

