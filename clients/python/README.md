# GEPA Python Client

```python
import asyncio
from gepa_client import GepaClient

async def main():
    async with GepaClient("http://localhost:8000", openrouter_key="dev") as client:
        job_id = await client.create_job("hello world", idempotency_key="demo")
        async for env in client.stream(job_id):
            print(env.type)
            if env.type in {"finished", "failed", "cancelled"}:
                break

asyncio.run(main())
```
