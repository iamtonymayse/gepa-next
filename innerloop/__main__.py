from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable developer mode (auth bypass allowed).",
    )
    # Default to loopback to avoid accidental exposure; override via HOST env or --host.
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() == "true",
    )
    args = parser.parse_args()
    if args.dev:
        os.environ.setdefault("REQUIRE_AUTH", "false")
    uvicorn.run("innerloop.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
