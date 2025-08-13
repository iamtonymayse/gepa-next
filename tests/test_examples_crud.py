import importlib
from fastapi.testclient import TestClient


def app_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_examples_bulk_list_delete(monkeypatch):
    c = app_client(monkeypatch)
    with c:
        up = c.post(
            "/v1/examples/bulk",
            json=[
                {"input": "I love it", "expected": "pos"},
                {"input": "I hate it", "expected": "neg"},
            ],
        )
        assert up.status_code == 200 and up.json()["upserted"] == 2
        ls = c.get("/v1/examples").json()["examples"]
        assert len(ls) >= 2
        ex_id = ls[0]["id"]
        assert c.delete(f"/v1/examples/{ex_id}").status_code in (200, 204)
