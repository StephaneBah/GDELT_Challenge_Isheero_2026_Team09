"""
Cache in-memory par hash(message + sector).
Même question + même secteur → zéro appel LLM.
"""
import hashlib
import time
from typing import Any

_store: dict[str, dict] = {}
TTL = 3600  # 1h


def _key(message: str, sector: str) -> str:
    raw = f"{message.strip().lower()}|{sector.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def get(message: str, sector: str) -> Any | None:
    k = _key(message, sector)
    entry = _store.get(k)
    if entry and (time.time() - entry["ts"]) < TTL:
        return entry["data"]
    return None


def set(message: str, sector: str, data: Any) -> None:
    _store[_key(message, sector)] = {"data": data, "ts": time.time()}


def stats() -> dict:
    return {"entries": len(_store), "keys": list(_store.keys())[:5]}
