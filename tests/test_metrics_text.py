import importlib

from fastapi.testclient import TestClient


def test_metrics_text_endpoint(monkeypatch):
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        resp = client.get("/v1/metrics")
        assert resp.status_code == 200
        # FastAPI includes charset; accept either exact or startswith
        assert resp.headers["content-type"].startswith("text/plain")
        body = resp.text
        assert len(body) > 0
        # Heuristic: Prometheus format often includes HELP/TYPE or metric name
        assert any(
            token in body.lower() for token in ["help", "type", "requests_total", "judge_stub_used"]
        )
