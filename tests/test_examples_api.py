import importlib

from fastapi.testclient import TestClient


def create_client(monkeypatch):
    monkeypatch.setenv("API_BEARER_TOKENS", '["dev"]')
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_examples_crud(monkeypatch):
    client = create_client(monkeypatch)
    with client:
        # auth required
        resp = client.post("/v1/examples", json={"input": "hi"})
        assert resp.status_code == 401
        headers = {"Authorization": "Bearer dev"}
        resp = client.post("/v1/examples", json={"input": "hi"}, headers=headers)
        assert resp.status_code == 201
        ex = resp.json()
        ex_id = ex["id"]
        resp = client.get("/v1/examples", headers=headers)
        assert any(item["id"] == ex_id for item in resp.json())
        resp = client.get(f"/v1/examples/{ex_id}", headers=headers)
        assert resp.status_code == 200
        resp = client.delete(f"/v1/examples/{ex_id}", headers=headers)
        assert resp.status_code == 204
        resp = client.get(f"/v1/examples/{ex_id}", headers=headers)
        assert resp.status_code == 404
