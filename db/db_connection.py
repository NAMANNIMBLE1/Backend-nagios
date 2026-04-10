"""
db_connection.py
~~~~~~~~~~~~~~~~
All database access for the Nagios prediction backend.

Public API
----------
get_hosts()                          → list[str]          distinct host aliases
get_services_for_host(host)          → list[str]          distinct service names for a host
get_sql_data(host, service, days)    → {"rows", "columns"} historical service-check rows
"""

import os
import logging
from typing import Optional
import mysql.connector
from config.get_config import get_config

logger = logging.getLogger(__name__)


# ── connection helper ─────────────────────────────────────────────────────────

def _get_connection():
    config = get_config()
    return mysql.connector.connect(
        host     = config["DB_HOST"],
        port     = int(config.get("DB_PORT", 3306)),
        user     = config["DB_USER"],
        password = config["DB_PASSWORD"],
        database = config["DB_NAME"],
    )


# ── hosts ─────────────────────────────────────────────────────────────────────

def get_hosts() -> list[str]:
    """
    Return every host alias that has at least one service check recorded.
    """
    sql = """
        SELECT DISTINCT h.alias
        FROM nagios_hosts h
        JOIN nagios_services s
            ON s.host_object_id = h.host_object_id
        JOIN nagios_servicechecks sc
            ON sc.service_object_id = s.service_object_id
        WHERE h.alias IS NOT NULL
          AND h.alias != ''
        ORDER BY h.alias ASC
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


# ── services for a host ───────────────────────────────────────────────────────

def get_services_for_host(host: str) -> list[str]:
    """
    Return every distinct service display_name that has check data for *host*.
    """
    sql = """
        SELECT DISTINCT s.display_name
        FROM nagios_services s
        JOIN nagios_hosts h
            ON h.host_object_id = s.host_object_id
        JOIN nagios_servicechecks sc
            ON sc.service_object_id = s.service_object_id
        WHERE h.alias = %s
          AND s.display_name IS NOT NULL
          AND s.display_name != ''
        ORDER BY s.display_name ASC
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, (host,))
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


# ── historical service-check data ─────────────────────────────────────────────

def get_sql_data(
    host: Optional[str]    = None,
    service: Optional[str] = None,
    days: int              = 30,
) -> dict:
    """
    Fetch historical service-check rows.

    Parameters
    ----------
    host    : filter to a single host alias  (None → all hosts)
    service : filter to a single service     (None → all services)
    days    : how many days of history to pull (default 30)

    Returns
    -------
    {"rows": list[tuple], "columns": list[str]}
    """
    params: list = []

    where_clauses = [
        "sc.start_time >= (SELECT MAX(start_time) FROM nagios_servicechecks) - INTERVAL %s DAY",
        "sc.early_timeout = 0",
    ]
    params.append(days)

    if host:
        where_clauses.append("h.alias = %s")
        params.append(host)

    if service:
        where_clauses.append("s.display_name = %s")
        params.append(service)

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            h.alias             AS host_name,
            s.display_name      AS service_name,
            sc.start_time       AS check_time,
            sc.state            AS check_state,
            sc.state_type       AS state_type,
            sc.output           AS check_output,
            sc.perfdata         AS perf_data,
            sc.execution_time   AS execution_time,
            sc.return_code      AS return_code
        FROM nagios_hosts h
        JOIN nagios_services s
            ON s.host_object_id = h.host_object_id
        JOIN nagios_servicechecks sc
            ON sc.service_object_id = s.service_object_id
        WHERE {where_sql}
        ORDER BY h.alias ASC, sc.start_time ASC
    """

    logger.info("[DB] Querying host=%s service=%s days=%d", host, service, days)

    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows    = cur.fetchall()
        columns = [d[0] for d in cur.description]
        logger.info("[DB] Fetched %d rows", len(rows))
        return {"rows": rows, "columns": columns}
    finally:
        conn.close()
