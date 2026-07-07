-- One row per lot: the part, the bar lot and its hardness, scrap, the final inspection result and the nonconformances.
with scrap as (
    select job_id, sum(quantity) as scrap_quantity, sum(cost) as scrap_cost,
        sum(case when reason_code = 'NCR' then quantity else 0 end) as scrap_quantity_ncr
    from {{ ref('stg_erp__scrap_transactions') }}
    group by 1
),
ncr as (
    select job_id, count(*) as ncrs,
        sum(case when disposition = 'rework' then 1 else 0 end) as rework_ncrs,
        sum(case when disposition = 'rework' and rework_hours_booked is null then 1 else 0 end) as rework_ncrs_without_booked_hours,
        sum(coalesce(rework_hours_booked, 0)) as rework_hours_booked,
        sum(coalesce(sorting_hours, 0)) as sorting_hours,
        sum(coalesce(reinspection_hours, 0)) as reinspection_hours
    from {{ ref('stg_qms__ncrs') }}
    where job_id is not null
    group by 1
)
select
    j.job_id,
    j.part_id,
    p.family_code,
    p.program,
    p.customer_id,
    p.unit_price,
    p.standard_cost,
    j.quantity,
    j.machine_id,
    m.shop_machine_no,
    j.primary_operator,
    j.start_time,
    j.end_time,
    j.start_time < timestamp '2024-01-01' as started_before_export,
    j.bar_lot,
    c.grade as material_grade,
    c.hardness_hrc,
    c.receiving_hardness_hrc,
    c.supplier_id as bar_supplier_id,
    j.insert_grade,
    j.status,
    j.standard_hours,
    j.actual_hours,
    j.quantity_good,
    j.ship_date,
    coalesce(s.scrap_quantity, 0) as scrap_quantity,
    coalesce(s.scrap_quantity_ncr, 0) as scrap_quantity_ncr,
    coalesce(s.scrap_cost, 0) as scrap_cost,
    f.result as final_result,
    f.sample_size as final_sample_size,
    f.defects_found as final_defects_found,
    f.inspected_at as final_inspected_at,
    coalesce(n.ncrs, 0) as ncrs,
    coalesce(n.rework_ncrs, 0) as rework_ncrs,
    coalesce(n.rework_ncrs_without_booked_hours, 0) as rework_ncrs_without_booked_hours,
    coalesce(n.rework_hours_booked, 0) as rework_hours_booked,
    coalesce(n.sorting_hours, 0) as sorting_hours,
    coalesce(n.reinspection_hours, 0) as reinspection_hours
from {{ ref('stg_erp__jobs') }} j
join {{ ref('stg_erp__parts') }} p on p.part_id = j.part_id
join {{ ref('stg_erp__machines') }} m on m.machine_id = j.machine_id
left join {{ ref('stg_erp__material_certs') }} c on c.material_cert_id = j.bar_lot
left join scrap s on s.job_id = j.job_id
left join {{ ref('stg_qms__final_inspection') }} f on f.job_id = j.job_id
left join ncr n on n.job_id = j.job_id
