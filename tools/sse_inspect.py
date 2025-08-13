#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

import anyio
import httpx

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--last-id", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()
    headers = {"Last-Event-ID": str(args.last_id)} if args.last_id else {}
    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout) as client:
        async with client.stream("GET", f"/v1/optimize/{args.job_id}/events", headers=headers) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("id:") or line.startswith("event:"):
                    print(line)
                elif line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                        print("data:", json.dumps(payload, indent=2))
                    except Exception:
                        print(line)
                elif line == ":":
                    print("(ping)")
                sys.stdout.flush()

if __name__ == "__main__":
    anyio.run(main)
