
# --- Query: All host services data for past 30 days (no alias filter, all services) ---
nagios_sql_query = """
SELECT
    h.host_object_id,
    h.display_name AS host_name,
    s.service_object_id,
    s.display_name AS service_name,
    sc.start_time AS check_time,
    sc.state AS check_state,
    sc.state_type AS state_type,
    sc.output AS check_output,
    sc.perfdata AS perf_data,
    sc.execution_time AS execution_time,
    sc.return_code AS return_code
FROM nagios_hosts h
JOIN nagios_services s
    ON s.host_object_id = h.host_object_id
JOIN nagios_servicechecks sc
    ON sc.service_object_id = s.service_object_id
WHERE
    sc.start_time >= NOW() - INTERVAL 30 DAY
ORDER BY
    h.host_object_id ASC,
    sc.start_time ASC;
"""

# --- Query: All services for a selected host (for UI dropdown) ---
host_services_query = """
SELECT
    s.service_object_id,
    s.display_name AS service_name
FROM nagios_services s
JOIN nagios_hosts h ON h.host_object_id = s.host_object_id
WHERE h.host_object_id = %s
ORDER BY s.display_name ASC;
"""

# --- Query: All hosts (for UI dropdown) ---
all_hosts_query = """
SELECT
    h.host_object_id,
    h.display_name AS host_name
FROM nagios_hosts h
ORDER BY h.display_name ASC;
"""

# --- Query: Historical host check data (host state over time) ---
host_check_history_query = """
SELECT
    hc.host_object_id,
    h.display_name AS host_name,
    hc.start_time AS check_time,
    hc.state AS check_state,
    hc.state_type AS state_type,
    hc.output AS check_output,
    hc.perfdata AS perf_data,
    hc.execution_time AS execution_time,
    hc.return_code AS return_code
FROM nagios_hostchecks hc
JOIN nagios_hosts h ON h.host_object_id = hc.host_object_id
WHERE hc.start_time >= NOW() - INTERVAL 30 DAY
ORDER BY hc.host_object_id ASC, hc.start_time ASC;
"""

# --- Query: nagios_objects for UI mapping (host/service names, etc) ---
objects_query = """
SELECT object_id, objecttype_id, name1, name2, is_active
FROM nagios_objects;
"""

