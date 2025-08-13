from __future__ import annotations

from typing import Dict, List
from uuid import uuid4


class ExampleStore:
    def __init__(self) -> None:
        self._examples: Dict[str, Dict] = {}

    async def create(self, ex: Dict) -> Dict:
        ex = dict(ex)
        ex_id = ex.get("id")
        if not ex_id:
            ex_id = str(uuid4())
        ex["id"] = ex_id
        self._examples[ex_id] = ex
        return ex

    async def get(self, ex_id: str) -> Dict | None:
        return self._examples.get(ex_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        items = list(self._examples.values())
        return items[offset : offset + limit]

    async def delete(self, ex_id: str) -> bool:
        return self._examples.pop(ex_id, None) is not None
