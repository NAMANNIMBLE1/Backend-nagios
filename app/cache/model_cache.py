"""
cache.py
~~~~~~~~
Thread-safe in-memory cache keyed on (host_name, service_name) tuples.

Each entry stores:
    model, scaler, data, metrics, forecast_df, days_ahead,
    y_test, y_pred, cached_at
"""

import threading
from datetime import datetime, timezone
from typing import Optional


class ModelCache:
    """
    Multi-key cache: key = (host: str | None, service: str | None)
    Using None means "all hosts / all services" — the legacy default.
    """

    def __init__(self):
        self._lock:  threading.RLock     = threading.RLock()
        self._store: dict[tuple, dict]   = {}

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _key(host: Optional[str], service: Optional[str]) -> tuple:
        return (host, service)

    # ── write ─────────────────────────────────────────────────────────────────

    def set_cache(
        self,
        host:        Optional[str],
        service:     Optional[str],
        model,
        scaler,
        data:        dict,
        metrics:     dict,
        forecast_df,
        days_ahead:  int,
        y_test,
        y_pred,
    ) -> None:
        key = self._key(host, service)
        entry = {
            "model":       model,
            "scaler":      scaler,
            "data":        data,
            "metrics":     metrics,
            "forecast_df": forecast_df,
            "days_ahead":  days_ahead,
            "y_test":      y_test,
            "y_pred":      y_pred,
            "cached_at":   datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._store[key] = entry

    # ── read ──────────────────────────────────────────────────────────────────

    def is_ready(self, host: Optional[str] = None, service: Optional[str] = None) -> bool:
        with self._lock:
            return self._key(host, service) in self._store

    def get_cache(self, host: Optional[str] = None, service: Optional[str] = None) -> Optional[dict]:
        with self._lock:
            return self._store.get(self._key(host, service))

    def get_cached_at(self, host: Optional[str] = None, service: Optional[str] = None) -> Optional[str]:
        entry = self.get_cache(host, service)
        return entry["cached_at"] if entry else None

    # ── introspection ─────────────────────────────────────────────────────────

    def cached_keys(self) -> list[dict]:
        """Return list of {host, service, cached_at} for all warm entries."""
        with self._lock:
            return [
                {"host": k[0], "service": k[1], "cached_at": v["cached_at"]}
                for k, v in self._store.items()
            ]

    def invalidate(self, host: Optional[str] = None, service: Optional[str] = None) -> bool:
        key = self._key(host, service)
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear_all(self) -> None:
        with self._lock:
            self._store.clear()


# ── singleton ─────────────────────────────────────────────────────────────────
model_cache = ModelCache()
