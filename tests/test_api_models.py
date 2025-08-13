from innerloop.api.models import JobState, OptimizeResponse, SSEEnvelope


def test_model_schemas():
    opt_schema = OptimizeResponse.model_json_schema()
    assert "job_id" in opt_schema["properties"]

    job_schema = JobState.model_json_schema()
    for key in ["job_id", "status", "created_at", "updated_at", "result"]:
        assert key in job_schema["properties"]

    env_schema = SSEEnvelope.model_json_schema()
    for key in ["type", "schema_version", "job_id", "ts", "data"]:
        assert key in env_schema["properties"]
