from __future__ import annotations

import importlib
import time

from fastapi.testclient import TestClient


def test_backpressure_failure(monkeypatch):
    """Configure tiny queue + fast ping to trigger backpressure quickly"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("SSE_BUFFER_SIZE", "1")
    monkeypatch.setenv("SSE_PING_INTERVAL_S", "0.01")
    # Sse fail timeout defaults to 2 * ping when unset
    import innerloop.settings as settings  # type: ignore

    importlib.reload(settings)
    import innerloop.main as main  # type: ignore

    importlib.reload(main)
    with TestClient(main.app) as client:
        headers = {"Authorization": "Bearer token"}
        job_id = client.post(
            "/v1/optimize",
            json={"prompt": "hi"},
            params={"iterations": 2},
            headers=headers,
        ).json()["job_id"]

        # Never open the SSE stream; queue fills and job should fail
        deadline = time.time() + 3
        state = {}
        while time.time() < deadline:
            state = client.get(f"/v1/optimize/{job_id}", headers=headers).json()
            if state.get("status") == "failed":
                break
            time.sleep(0.02)

    assert state.get("status") == "failed"
    assert state.get("result", {}).get("error") == "sse_backpressure"
