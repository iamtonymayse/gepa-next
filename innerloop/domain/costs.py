from __future__ import annotations

from typing import cast

from ..settings import get_settings


class CostTracker:
    def __init__(self):
        self.toks = {"input": 0, "output": 0}

    def add(self, input_toks: int = 0, output_toks: int = 0):
        self.toks["input"] += input_toks
        self.toks["output"] += output_toks

    def usd(self, model: str) -> float:
        s = get_settings()
        prices = cast(dict[str, dict[str, float]], s.MODEL_PRICES)
        price = prices.get(model, {"input": 0.0, "output": 0.0})
        return (
            self.toks["input"] * price["input"] / 1e6
            + self.toks["output"] * price["output"] / 1e6
        )
