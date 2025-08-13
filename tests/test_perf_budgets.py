import importlib, json
from fastapi.testclient import TestClient


def test_perf_budgets(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("GEPA_DETERMINISTIC", "true")
    import innerloop.settings as settings
    importlib.reload(settings)
    s = settings.get_settings()
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        job_id = client.post("/v1/optimize", json={"prompt":"x"}, params={"iterations":2}).json()["job_id"]
        with client.stream("GET", f"/v1/optimize/{job_id}/events") as stream:
            for line in stream.iter_lines():
                if line.startswith("event: finished"):
                    break
        metrics = client.get("/v1/metricsz").json()
        job_p95 = metrics["histograms"].get("job_total_ms", {}).get("p95", 0)
        ev_p95 = metrics["histograms"].get("sse_put_ms", {}).get("p95", 0)
        assert job_p95 <= s.PERF_BUDGET_P95_JOB_MS
        assert ev_p95 <= s.PERF_BUDGET_P95_EVENT_MS
