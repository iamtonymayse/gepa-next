import argparse
import asyncio
import statistics
import time
from typing import List

import anyio
import httpx

TERMINALS = {"finished", "failed", "cancelled", "shutdown"}


async def run_client(base_url: str, iterations: int, stats: List[float]) -> None:
    async with httpx.AsyncClient(base_url=base_url) as client:
        start = time.perf_counter()
        r = await client.post("/v1/optimize", json={"prompt": "hi"}, params={"iterations": iterations})
        job_id = r.json()["job_id"]
        async with client.stream("GET", f"/v1/optimize/{job_id}/events") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("event:") and line.split(":", 1)[1].strip() in TERMINALS:
                    break
        stats.append(time.perf_counter() - start)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=100)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    latencies: List[float] = []
    errors = 0

    async def worker_loop() -> None:
        nonlocal errors
        while True:
            try:
                await run_client(args.base_url, args.iterations, latencies)
            except Exception:
                errors += 1

    start = time.perf_counter()
    async with anyio.create_task_group() as tg:
        for _ in range(args.clients):
            tg.start_soon(worker_loop)
        while time.perf_counter() - start < args.duration:
            await anyio.sleep(0.1)
        tg.cancel_scope.cancel()

    if latencies:
        latencies.sort()
        p50 = statistics.quantiles(latencies, n=100)[49]
        p95 = statistics.quantiles(latencies, n=100)[94]
        p99 = statistics.quantiles(latencies, n=100)[98]
        print(f"p50={p50:.3f}s p95={p95:.3f}s p99={p99:.3f}s errors={errors}")
    else:
        print(f"no runs completed errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
