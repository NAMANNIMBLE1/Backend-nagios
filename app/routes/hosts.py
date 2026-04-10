"""
routes/hosts.py
~~~~~~~~~~~~~~~
Endpoints for host + service discovery and cache introspection.

GET /hosts/                          → list all hosts with service-check data
GET /hosts/{host_name}/services      → list services for a host
GET /hosts/cache                     → show which (host,service) pairs are trained
DELETE /hosts/cache                  → invalidate a specific cache entry
POST  /hosts/{host_name}/services/{service_name}/train
                                     → trigger training for a (host,service) pair
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.cache.model_cache import model_cache
from app.schemas.response import HostsResponse, ServicesResponse, CacheStatusResponse, CacheEntryInfo
import time
from db.db_connection import get_hosts, get_services_for_host

# Simple in-memory cache for /hosts and /hosts/{host_name}/services
_hosts_cache = {"data": None, "timestamp": 0}
_HOSTS_TTL = 300  # seconds (5 minutes)
_services_cache = {}
_SERVICES_TTL = 300  # seconds (5 minutes)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hosts", tags=["Hosts"])


# ── GET /hosts/ ───────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model = HostsResponse,
    summary        = "List all hosts that have service-check data",
)
def list_hosts():
    now = time.time()
    if _hosts_cache["data"] is not None and now - _hosts_cache["timestamp"] < _HOSTS_TTL:
        hosts = _hosts_cache["data"]
    else:
        try:
            hosts = get_hosts()
            _hosts_cache["data"] = hosts
            _hosts_cache["timestamp"] = now
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DB error: {exc}")
    return HostsResponse(total=len(hosts), hosts=hosts)


# ── GET /hosts/{host_name}/services ──────────────────────────────────────────

@router.get(
    "/{host_name}/services",
    response_model = ServicesResponse,
    summary        = "List all services for a specific host",
)
def list_services(host_name: str):
    now = time.time()
    cache_key = host_name
    if cache_key in _services_cache and now - _services_cache[cache_key]["timestamp"] < _SERVICES_TTL:
        services = _services_cache[cache_key]["data"]
    else:
        try:
            services = get_services_for_host(host_name)
            _services_cache[cache_key] = {"data": services, "timestamp": now}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    if not services:
        raise HTTPException(
            status_code=404,
            detail=f"No services found for host '{host_name}'. "
                   "Verify the host name matches nagios_hosts.alias exactly.",
        )

    return ServicesResponse(host=host_name, total=len(services), services=services)


# ── GET /hosts/cache ──────────────────────────────────────────────────────────

@router.get(
    "/cache",
    response_model = CacheStatusResponse,
    summary        = "Show which (host, service) pairs have a trained model cached",
)
def get_cache_status():
    entries = model_cache.cached_keys()
    return CacheStatusResponse(
        total_cached = len(entries),
        entries      = [CacheEntryInfo(**e) for e in entries],
    )


# ── DELETE /hosts/cache ───────────────────────────────────────────────────────

@router.delete(
    "/cache",
    summary = "Invalidate a cached (host, service) model — forces retrain on next request",
)
def invalidate_cache(
    host:    Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    removed = model_cache.invalidate(host, service)
    return {
        "invalidated": removed,
        "host":        host,
        "service":     service,
        "message":     "Cache entry removed. Next API call will trigger retraining."
                       if removed else "No cache entry found for this (host, service) pair.",
    }


# ── POST /hosts/{host_name}/services/{service_name}/train ─────────────────────

@router.post(
    "/{host_name}/services/{service_name}/train",
    summary = "Trigger training for a specific (host, service) pair",
)
def trigger_training(
    host_name:    str,
    service_name: str,
    force: bool = Query(default=False, description="Force retrain even if cache is warm"),
):
    """
    Kicks off training synchronously.
    Returns immediately if cache is already warm (unless force=True).
    """
    from app.services.training_service import run_training_pipeline

    if not force and model_cache.is_ready(host_name, service_name):
        cached_at = model_cache.get_cached_at(host_name, service_name)
        return {
            "status":    "already_cached",
            "host":      host_name,
            "service":   service_name,
            "cached_at": cached_at,
            "message":   "Model already trained. Pass ?force=true to retrain.",
        }

    try:
        run_training_pipeline(host=host_name, service=service_name, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Training failed for host=%s service=%s", host_name, service_name)
        raise HTTPException(status_code=500, detail=f"Training error: {exc}")

    return {
        "status":    "trained",
        "host":      host_name,
        "service":   service_name,
        "cached_at": model_cache.get_cached_at(host_name, service_name),
        "message":   "Model trained and cached successfully.",
    }
