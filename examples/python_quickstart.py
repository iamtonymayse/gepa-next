import asyncio
import logging
from gepa_client import GepaClient

log = logging.getLogger("gepa.examples")
logging.basicConfig(level=logging.INFO)

async def main() -> None:
    async with GepaClient("http://localhost:8000", openrouter_key="dev") as client:
        job_id = await client.create_job("hello world", idempotency_key="demo")
        last = None
        async for env in client.stream(job_id):
            last = env
            if env.type in {"finished", "failed", "cancelled"}:
                break
        log.info("%s", last)

if __name__ == "__main__":
    asyncio.run(main())
