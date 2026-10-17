"""Versioned settings, stored as JSON to avoid a YAML runtime dependency."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def load_config(name: str) -> dict | list:
    if name not in {"lexicon", "settings", "zones", "profiles"}:
        raise ValueError(f"Unknown config: {name}")
    return json.loads((Path(__file__).parent / "config" / f"{name}.json").read_text())
