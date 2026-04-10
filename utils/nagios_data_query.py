nagios_sql_query = """
SELECT
    h.alias AS host_name,
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
    h.alias IN (
        'DL-LCP-DX-01',
        'DL-LCP-DX-02',
        'DL-LCP-DX-03',
        'DL-LCP-DX-04'
    )
    AND s.display_name = 'LCP-DX_Cooling-Capacity'
     AND sc.start_time >= NOW() - INTERVAL 30 DAY
ORDER BY
    h.alias ASC,
    sc.start_time ASC;
"""


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