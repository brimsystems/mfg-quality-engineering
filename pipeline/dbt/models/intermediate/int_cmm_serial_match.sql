-- Pieces measured both in process and on the CMM. The serial on the CMM report is the piece number in the lot; the in-process
-- reading of that piece is the last reading of the subgroup ending at it (the only reading where every piece is measured).
select
    f.report_id,
    f.feature_no,
    f.characteristic_id,
    f.job_id,
    f.piece_no,
    f.measured_at,
    f.cmm_machine,
    f.actual as cmm_actual,
    h.subgroup_id,
    h.recorded_at,
    h.recorded_date,
    h.recorded_year,
    h.operator_id,
    h.gauge_id,
    h.gauge_type,
    case when h.subgroup_size = 5 then h.r5 else h.r1 end as gauge_reading,
    case when h.subgroup_size = 5 then h.r5 else h.r1 end - f.actual as gauge_minus_cmm
from {{ ref('int_cmm_features') }} f
join {{ ref('int_process_history') }} h
  on h.job_id = f.job_id and h.characteristic_id = f.characteristic_id and h.piece_no = f.piece_no
where f.characteristic_id is not null and f.piece_no is not null
