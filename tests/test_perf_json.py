from innerloop.api.sse import format_sse

def test_format_sse_compact_json():
    env = {"id": 1, "job_id": "j", "ts": 0.0, "data": {"x": 1}}
    text = format_sse("progress", env)
    assert "data: {" in text and '":1' in text
