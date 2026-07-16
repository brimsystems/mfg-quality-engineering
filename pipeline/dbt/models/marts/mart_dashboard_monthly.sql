-- One row per month: revenue, cost of quality as booked by category, the scrap report, NCRs, complaints, S-017 receiving lots and F-14 lots.
with months as (
    select distinct period, cast(period || '-01' as date) as month_start, last_day(cast(period || '-01' as date)) as month_end
    from {{ ref('int_cost_lines') }}
),
cost as (
    select period,
        sum(case when cost_group = 'failure' then amount else 0 end) as failure_booked,
        sum(case when cost_group = 'appraisal' then amount else 0 end) as appraisal,
        sum(case when cost_group = 'prevention' then amount else 0 end) as prevention
    from {{ ref('int_cost_lines') }} group by 1
),
scrap as (
    select strftime(transaction_date, '%Y-%m') as period, sum(cost) as scrap_report
    from {{ ref('stg_erp__scrap_transactions') }} group by 1
),
shipped as (
    select strftime(ship_date, '%Y-%m') as period, sum(quantity_good * unit_price) as revenue, sum(quantity_good) as pieces_shipped
    from {{ ref('int_lot_outcomes') }} where ship_date is not null group by 1
),
ncr_opened as (
    select strftime(opened, '%Y-%m') as period, count(*) as ncrs_opened from {{ ref('stg_qms__ncrs') }} group by 1
),
ncr_mrb as (
    select strftime(mrb_date, '%Y-%m') as period,
        sum(case when disposition = 'rework' and job_id is not null then 1 else 0 end) as rework_ncrs,
        sum(case when disposition = 'rework' and job_id is not null and rework_hours_booked is null then 1 else 0 end) as rework_ncrs_without_booked_hours
    from {{ ref('stg_qms__ncrs') }} where mrb_date is not null group by 1
),
ncr_open as (
    select m.period, count(n.ncr_id) as ncrs_open_at_month_end
    from months m left join {{ ref('stg_qms__ncrs') }} n on n.opened <= m.month_end and (n.closed is null or n.closed > m.month_end)
    group by 1
),
complaints as (
    select strftime(received_date, '%Y-%m') as period, count(*) as complaints, sum(quantity) as complaint_quantity
    from {{ ref('mart_complaints') }} where not repeated_entry group by 1
),
s017 as (
    select strftime(received_at, '%Y-%m') as period, count(*) as s017_lots, sum(case when disposition = 'accept' then 1 else 0 end) as s017_lots_accepted
    from {{ ref('int_receiving_outcomes') }} where supplier_id = 'S-017' group by 1
),
f14 as (
    select strftime(end_time, '%Y-%m') as period, count(*) as f14_lots, sum(quantity) as f14_quantity, sum(scrap_quantity) as f14_scrap_quantity
    from {{ ref('int_lot_outcomes') }} where family_code = 'F-14' and end_time is not null group by 1
)
select m.period, m.month_start, m.month_end,
    coalesce(sh.revenue, 0) as revenue, coalesce(sh.pieces_shipped, 0) as pieces_shipped,
    c.failure_booked, c.appraisal, c.prevention, coalesce(s.scrap_report, 0) as scrap_report,
    coalesce(o.ncrs_opened, 0) as ncrs_opened, no.ncrs_open_at_month_end,
    coalesce(r.rework_ncrs, 0) as rework_ncrs, coalesce(r.rework_ncrs_without_booked_hours, 0) as rework_ncrs_without_booked_hours,
    coalesce(cp.complaints, 0) as complaints, coalesce(cp.complaint_quantity, 0) as complaint_quantity,
    coalesce(s17.s017_lots, 0) as s017_lots, coalesce(s17.s017_lots_accepted, 0) as s017_lots_accepted,
    coalesce(f.f14_lots, 0) as f14_lots, coalesce(f.f14_quantity, 0) as f14_quantity, coalesce(f.f14_scrap_quantity, 0) as f14_scrap_quantity,
    {{ batch_id() }} as export_batch_id
from months m
join cost c on c.period = m.period
left join scrap s on s.period = m.period
left join shipped sh on sh.period = m.period
left join ncr_opened o on o.period = m.period
left join ncr_mrb r on r.period = m.period
left join ncr_open no on no.period = m.period
left join complaints cp on cp.period = m.period
left join s017 s17 on s17.period = m.period
left join f14 f on f.period = m.period
