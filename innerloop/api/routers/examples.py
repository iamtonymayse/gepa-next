from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request, Response

from ..models import ExampleIn, Example, APIError, ErrorCode, error_response
from ...domain.examples_store import ExampleStore

router = APIRouter()


@router.post("/examples", response_model=Example, status_code=201)
async def create_example(request: Request, body: ExampleIn) -> Example:
    store: ExampleStore = request.app.state.examples
    ex = await store.create(body.model_dump())
    return Example(**ex)


@router.get("/examples", response_model=List[Example])
async def list_examples(request: Request, limit: int = 100, offset: int = 0) -> List[Example]:
    store: ExampleStore = request.app.state.examples
    items = await store.list(limit, offset)
    return [Example(**ex) for ex in items]


@router.get("/examples/{ex_id}", response_model=Example)
async def get_example(request: Request, ex_id: str) -> Example | APIError:
    store: ExampleStore = request.app.state.examples
    ex = await store.get(ex_id)
    if not ex:
        return error_response(ErrorCode.not_found, "Example not found", 404, request_id=request.state.request_id)
    return Example(**ex)


@router.delete("/examples/{ex_id}", status_code=204, response_model=None)
async def delete_example(request: Request, ex_id: str) -> Response:
    store: ExampleStore = request.app.state.examples
    ok = await store.delete(ex_id)
    if not ok:
        return error_response(
            ErrorCode.not_found,
            "Example not found",
            404,
            request_id=request.state.request_id,
        )
    return Response(status_code=204)
