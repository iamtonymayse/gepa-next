from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import List

import yaml  # type: ignore[import-untyped]


@dataclass
class Example:
    id: str
    input: str
    output: str
    meta: dict = field(default_factory=dict)


@dataclass
class ExamplePack:
    name: str
    metrics: List[str]
    examples: List[Example]


_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "gepa_next" / "examples"
_MANIFEST_PATH = _EXAMPLES_DIR / "manifest.yaml"
_EXCLUDED_KEYS = {"id", "question", "answer", "text", "label", "input", "output"}


def load_pack(name: str) -> ExamplePack:
    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    pack_info = manifest.get("packs", {}).get(name)
    if not pack_info:
        raise ValueError(f"Unknown example pack: {name}")
    data_path = _EXAMPLES_DIR / pack_info["path"]
    examples: List[Example] = []
    with data_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if "question" in rec:
                inp = rec.get("question", "")
                out = rec.get("answer", "")
            elif "text" in rec:
                inp = rec.get("text", "")
                out = rec.get("label", "")
            else:
                inp = rec.get("input", "")
                out = rec.get("output", "")
            meta = {k: v for k, v in rec.items() if k not in _EXCLUDED_KEYS}
            examples.append(Example(str(rec.get("id")), inp, out, meta))
    return ExamplePack(
        name=name, metrics=pack_info.get("metrics", []), examples=examples
    )
