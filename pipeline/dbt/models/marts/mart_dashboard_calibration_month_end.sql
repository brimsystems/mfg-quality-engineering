-- Gauge calibration status at each month end by gauge type: in the program, due in the month and done, due in the following month, overdue, out of service, lost.
with months as (
    select distinct period, cast(period || '-01' as date) as month_start, last_day(cast(period || '-01' as date)) as month_end from {{ ref('int_cost_lines') }}
),
gauges as (
    select m.period, m.month_start, m.month_end, g.gauge_id, g.gauge_type,
        case when g.status <> 'active' and g.status_date <= m.month_end then g.status else 'active' end as status_at_month_end
    from months m cross join {{ ref('stg_calibration__gauges') }} g
),
events as (
    select g.period, g.gauge_id,
        max(case when c.due_date < g.month_end and (c.done_date is null or c.done_date > g.month_end) then 1 else 0 end) as overdue,
        max(case when c.due_date >= g.month_start and c.due_date <= g.month_end then 1 else 0 end) as due_in_month,
        max(case when c.due_date > g.month_end and c.due_date <= last_day(g.month_end + interval 1 day) and (c.done_date is null or c.done_date > g.month_end) then 1 else 0 end) as due_next_month,
        max(case when c.due_date >= g.month_start and c.due_date <= g.month_end and c.done_date <= g.month_end then 1 else 0 end) as due_in_month_done
    from gauges g join {{ ref('stg_calibration__calibrations') }} c on c.gauge_id = g.gauge_id
    group by 1, 2
)
select g.period || ' ' || g.gauge_type as period_gauge_type, g.period, g.month_end, g.gauge_type,
    sum(case when g.status_at_month_end = 'active' then 1 else 0 end) as gauges_active,
    sum(case when g.status_at_month_end = 'active' then coalesce(e.overdue, 0) else 0 end) as gauges_overdue,
    sum(case when g.status_at_month_end = 'active' then coalesce(e.due_in_month, 0) else 0 end) as gauges_due_in_month,
    sum(case when g.status_at_month_end = 'active' then coalesce(e.due_next_month, 0) else 0 end) as gauges_due_next_month,
    sum(case when g.status_at_month_end = 'active' then coalesce(e.due_in_month_done, 0) else 0 end) as gauges_due_in_month_done,
    sum(case when g.status_at_month_end = 'out of service' then 1 else 0 end) as gauges_out_of_service,
    sum(case when g.status_at_month_end = 'lost' then 1 else 0 end) as gauges_lost,
    {{ batch_id() }} as export_batch_id
from gauges g left join events e on e.period = g.period and e.gauge_id = g.gauge_id
group by 1, 2, 3, 4
