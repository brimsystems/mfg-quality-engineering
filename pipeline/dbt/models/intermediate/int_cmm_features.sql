-- CMM features with the report header and the characteristic each maps to.
select
    f.report_id,
    f.feature_no,
    f.feature_name,
    coalesce(f.characteristic_id, m.characteristic_id) as characteristic_id,
    case when f.characteristic_id is not null then 'id in the report' else coalesce(m.map_method, 'not in the master') end as map_method,
    f.nominal,
    f.upper_tol,
    f.lower_tol,
    f.actual,
    f.deviation,
    f.out_of_tolerance,
    r.machine as cmm_machine,
    r.job_id,
    r.part_id,
    r.serial_no,
    try_cast(r.serial_no as integer) as piece_no,
    r.measured_at,
    r.operator_id as cmm_operator_id
from {{ ref('stg_cmm__cmm_features') }} f
join {{ ref('stg_cmm__cmm_reports') }} r on r.report_id = f.report_id
left join {{ ref('int_cmm_characteristic_map') }} m
  on f.characteristic_id is null and m.map_method = 'mapping table' and m.part_id = r.part_id and m.feature_name = f.feature_name
