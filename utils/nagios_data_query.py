
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

# --- Notes ---
# Use host_object_id and service_object_id for all filtering and selection in APIs and UI.
# Use nagios_objects to map object IDs to display names for UI.
# For host selection: query all_hosts_query, then for a selected host, query host_services_query.
# For historical host state: use host_check_history_query.
# For service state history: use nagios_sql_query with host/service filters as needed.



# SELECT
#         h.alias                 AS host_name,
#         s.display_name          AS service_name,
#         sc.start_time           AS check_time,
#         sc.state                AS check_state,
#         sc.state_type           AS state_type,
#         sc.output               AS check_output,
#         sc.perfdata             AS perf_data,
#         sc.execution_time       AS execution_time,
#         sc.return_code          AS return_code
#     FROM nagios_hosts h
#     INNER JOIN nagios_services s
#         ON s.host_object_id = h.host_object_id
#     INNER JOIN nagios_servicechecks sc
#         ON sc.service_object_id = s.service_object_id
#     WHERE
#         h.alias IN (
#             'DL-LCP-DX-01',
#             'DL-LCP-DX-02',
#             'DL-LCP-DX-03',
#             'DL-LCP-DX-04'
#         )
#         AND s.display_name = 'LCP-DX_Cooling-Capacity'
#         AND sc.start_time BETWEEN '2026-02-01' AND '2026-02-28'
#     ORDER BY
#         h.alias ASC,
#         sc.start_time ASC


# SELECT sc.service_object_id, COUNT(*) as total, MAX(sc.start_time) as latest
# FROM nagios_servicechecks sc
# WHERE sc.service_object_id IN (
#     SELECT s.service_object_id
#     FROM nagios_services s
#     INNER JOIN nagios_hosts h ON h.host_object_id = s.host_object_id
#     WHERE h.alias LIKE '%DL-LCP%'
# )
# GROUP BY sc.service_object_id;


# SELECT DISTINCT display_name
# FROM nagios_services
# WHERE host_object_id IN (
#     SELECT host_object_id FROM nagios_hosts WHERE alias LIKE '%DL-LCP%'
# );

# SELECT service_id, service_object_id, host_object_id, display_name
# FROM nagios_services
# WHERE host_object_id IN (
#     SELECT host_object_id FROM nagios_hosts WHERE alias LIKE '%DL-LCP%'
# );
# SELECT host_id, host_object_id, alias
# FROM nagios_hosts
# WHERE alias LIKE '%DL-LCP%';



# SELECT *
# FROM nagios_hosts h
# JOIN nagios_services s
#   ON s.host_object_id = h.host_object_id
# JOIN nagios_servicechecks sc
#   ON sc.service_object_id = s.service_object_id
# LIMIT 10;

# SELECT
#         h.alias                 AS host_name,
#         s.display_name          AS service_name,
#         sc.start_time           AS check_time,
#         sc.state                AS check_state,
#         sc.state_type           AS state_type,
#         sc.output               AS check_output,
#         sc.perfdata             AS perf_data,
#         sc.execution_time       AS execution_time,
#         sc.return_code          AS return_code
#     FROM nagios_hosts h
#     INNER JOIN nagios_services s
#         ON s.host_object_id = h.host_object_id
#     INNER JOIN nagios_servicechecks sc
#         ON sc.service_object_id = s.service_object_id
#     WHERE
#         h.alias IN (
#             'DL-LCP-DX-01',
#             'DL-LCP-DX-02',
#             'DL-LCP-DX-03',
#             'DL-LCP-DX-04'
#         )
#         AND s.display_name = 'LCP-DX_Cooling-Capacity'
#         AND sc.start_time >= NOW() - INTERVAL 30 DAY
#         AND sc.early_timeout = 0
#     ORDER BY
#         h.alias ASC,
#         sc.start_time ASC