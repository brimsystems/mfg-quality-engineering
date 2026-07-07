-- Subgroups with the job, the machine, the operator, the gauge, the bar lot and the calibration status of the gauge on the day.
with s as (
    select *, cast(recorded_at as date) as recorded_date from {{ ref('stg_qms__spc_subgroups') }}
),
cal as (
    select gauge_id, due_date, pulled_date, returned_date from {{ ref('stg_calibration__calibrations') }}
),
in_calibration as (
    select distinct s.subgroup_id
    from s
    join cal c on c.gauge_id = s.gauge_id and c.pulled_date is not null and s.recorded_date between c.pulled_date and c.returned_date
),
past_due as (
    select distinct s.subgroup_id
    from s
    join cal c on c.gauge_id = s.gauge_id and s.recorded_date > c.due_date and (c.pulled_date is null or s.recorded_date < c.pulled_date)
)
select
    s.subgroup_id,
    s.job_id,
    s.characteristic_id,
    s.subgroup_no,
    s.piece_no,
    s.recorded_at,
    s.recorded_date,
    cast(extract(year from s.recorded_at) as integer) as recorded_year,
    s.operator_id,
    s.gauge_id,
    s.machine_id,
    s.r1, s.r2, s.r3, s.r4, s.r5,
    s."mean" as subgroup_mean,
    s."range" as subgroup_range,
    s.alarm_rule_1,
    s.alarm_rule_2,
    s.acknowledged,
    s.acknowledgement_text,
    j.part_id,
    p.family_code,
    p.program,
    j.bar_lot,
    j.insert_grade,
    j.start_time as job_start,
    j.end_time as job_end,
    j.quantity as job_quantity,
    c.characteristic_name,
    c.characteristic_type,
    c.nominal,
    c.usl,
    c.lsl,
    c.critical_flag,
    c.subgroup_size,
    c.chart_centre,
    c.chart_ucl,
    c.chart_lcl,
    g.gauge_type,
    g.resolution,
    g.gauge_type in ('bore gauge', 'micrometer', 'caliper', 'dial indicator') as hand_gauge,
    ic.subgroup_id is not null as gauge_in_calibration,
    coalesce(g.status <> 'active' and s.recorded_date >= g.status_date, false) as gauge_out_of_service_or_lost,
    pd.subgroup_id is not null and ic.subgroup_id is null
        and not coalesce(g.status <> 'active' and s.recorded_date >= g.status_date, false) as gauge_past_due
from s
join {{ ref('stg_erp__jobs') }} j on j.job_id = s.job_id
join {{ ref('stg_erp__parts') }} p on p.part_id = j.part_id
join {{ ref('stg_qms__characteristics') }} c on c.characteristic_id = s.characteristic_id
join {{ ref('stg_calibration__gauges') }} g on g.gauge_id = s.gauge_id
left join in_calibration ic on ic.subgroup_id = s.subgroup_id
left join past_due pd on pd.subgroup_id = s.subgroup_id
