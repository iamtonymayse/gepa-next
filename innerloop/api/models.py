from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None

