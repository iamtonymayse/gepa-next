from __future__ import annotations

from fastapi import APIRouter, Request
from ..models import ExampleIn, error_response, ErrorCode
import uuid

router = APIRouter()


@router.post("/examples/bulk", response_model=dict, status_code=200)
async def examples_bulk(request: Request, items: list[ExampleIn]):
    store = request.app.state.store
    payload = []
    for ex in items:
        payload.append(
            {
                "id": ex.id or str(uuid.uuid4()),
                "input": ex.input,
                "expected": ex.expected,
                "meta": ex.meta or {},
            }
        )
    n = await store.upsert_examples(payload)
    return {"upserted": n}


@router.get("/examples", response_model=dict, status_code=200)
async def examples_list(request: Request, limit: int = 50, offset: int = 0):
    store = request.app.state.store
    rows = await store.list_examples(limit=limit, offset=offset)
    return {"examples": rows, "limit": limit, "offset": offset}


@router.delete("/examples/{example_id}", status_code=204)
async def examples_delete(request: Request, example_id: str):
    store = request.app.state.store
    await store.delete_example(example_id)
    return {}
