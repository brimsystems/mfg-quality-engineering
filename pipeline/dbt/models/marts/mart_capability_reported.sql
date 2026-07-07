-- Capability as reported: the module's figures on each report, with the latest report of each year marked.
select
    r.report_id,
    r.characteristic_id,
    c.part_id,
    c.characteristic_name,
    c.characteristic_type,
    c.critical_flag,
    c.subgroup_size,
    r.run_date,
    cast(extract(year from r.run_date) as integer) as run_year,
    r.report_type,
    r.subgroups_used,
    r.first_subgroup_id,
    r.last_subgroup_id,
    r.subgroup_ids,
    r.method_flag,
    r.cp, r.cpk, r.pp, r.ppk,
    case when r.cpk >= 1.33 then 'capable' when r.cpk >= 1.0 then 'marginal' else 'not capable' end as reported_category,
    row_number() over (partition by r.characteristic_id, extract(year from r.run_date) order by r.run_date desc) = 1 as latest_in_year,
    r.issued_to,
    r.issued_date,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__capability_reports') }} r
join {{ ref('stg_qms__characteristics') }} c on c.characteristic_id = r.characteristic_id
