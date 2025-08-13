#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from innerloop.main import app

SNAP_PATH = Path("docs/openapi.snap.json")


def canonical(obj: dict) -> str:
    """Stable dump for reproducible diffs"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI snapshot check / update")
    parser.add_argument("--update", action="store_true", help="rewrite the snapshot")
    args = parser.parse_args()

    schema = app.openapi()
    data = canonical(schema)

    if not SNAP_PATH.exists():
        SNAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAP_PATH.write_text(data, encoding="utf-8")
        print(f"[snapshot-openapi] created {SNAP_PATH}")
        return 0

    if args.update:
        SNAP_PATH.write_text(data, encoding="utf-8")
        print(f"[snapshot-openapi] updated {SNAP_PATH}")
        return 0

    old = SNAP_PATH.read_text(encoding="utf-8")
    if old != data:
        print("[snapshot-openapi] OpenAPI drift detected. Run with --update to refresh snapshot.")
        return 1

    print("[snapshot-openapi] snapshot OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
