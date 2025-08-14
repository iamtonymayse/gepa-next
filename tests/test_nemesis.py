import importlib
import json
import time

from fastapi.testclient import TestClient
import pytest


@pytest.mark.timeout(5)
def test_slow_consumer_completes(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("SSE_PING_INTERVAL_S", "0.05")
    monkeypatch.setenv("SSE_BACKPRESSURE_FAIL_TIMEOUT_S", "1.0")
    monkeypatch.setenv("GEPA_DETERMINISTIC", "true")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        job_id = client.post(
            "/v1/optimize",
            json={"prompt": "x"},
            params={"iterations": 2},
            headers={"Authorization": "Bearer token"},
        ).json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            it = stream.iter_lines()
            assert next(it).startswith("retry:")
            seen_finished = False
            for line in it:
                time.sleep(0.03)  # slow drain
                if line.startswith("event: finished"):
                    seen_finished = True
                    break
            assert seen_finished


@pytest.mark.timeout(5)
def test_stalled_consumer_triggers_backpressure(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("SSE_BUFFER_SIZE", "2")
    monkeypatch.setenv("SSE_PING_INTERVAL_S", "0.05")
    monkeypatch.setenv("SSE_BACKPRESSURE_FAIL_TIMEOUT_S", "0.001")
    monkeypatch.setenv("GEPA_DETERMINISTIC", "true")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        job_id = client.post(
            "/v1/optimize",
            json={"prompt": "x"},
            params={"iterations": 10},
            headers={"Authorization": "Bearer token"},
        ).json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            time.sleep(0.7)  # stall reading to overflow queue
            lines = [ln for ln in stream.iter_lines() if ln.startswith("data:")]
    terminals = [json.loads(ln[5:].strip()) for ln in lines]
    assert any(
        env["type"] == "failed" and env["data"].get("error") == "sse_backpressure"
        for env in terminals
    )
