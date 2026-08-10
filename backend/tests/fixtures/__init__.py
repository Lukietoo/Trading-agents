# Loader for the recorded API responses. See README.md for provenance.

import json
from functools import cache
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent


@cache
def _read(name: str) -> str:
    path = FIXTURE_DIR / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in FIXTURE_DIR.glob("*.json"))
        raise FileNotFoundError(f"No fixture {name!r}. Available: {', '.join(available)}")
    return path.read_text(encoding="utf-8")


def load(name: str) -> Any:
    """The recorded response body, decoded.

    Returns a fresh object each call — a test that mutates a fixture must not
    be able to affect the next one.
    """
    return json.loads(_read(name))
