import threading
from datetime import datetime
from typing import Any

_lock  = threading.Lock()
_store: dict[str, Any] = {}


def set_cache(payload: dict) -> None:
    with _lock:                                          # ← _lock not payload
        _store.clear()
        _store.update(payload)
        _store["cached_at"] = datetime.utcnow().isoformat()


def get_cache() -> dict:
    with _lock:
        return dict(_store)


def is_ready() -> bool:
    with _lock:
        return bool(_store)


def get_cached_at() -> str | None:
    with _lock:
        return _store.get("cached_at")