-- Complaints with the lot where the complaint names one that is in the job records, and a flag on repeated entries.
select
    c.*,
    l.job_id is not null as lot_found,
    l.family_code,
    l.program,
    l.ship_date,
    l.quantity_good,
    row_number() over (partition by c.customer_id, c.part_id, coalesce(c.job_id, ''), c.defect_code, c.quantity order by c.received_date, c.complaint_id) > 1 as repeated_entry,
    {{ batch_id() }} as mart_export_batch_id
from {{ ref('stg_qms__complaints') }} c
left join {{ ref('int_lot_outcomes') }} l on l.job_id = c.job_id
