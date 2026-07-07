-- NCRs with the lot, the part and the family.
select
    n.*,
    l.part_id,
    l.family_code,
    l.program,
    l.machine_id,
    l.shop_machine_no,
    {{ batch_id() }} as mart_export_batch_id
from {{ ref('stg_qms__ncrs') }} n
left join {{ ref('int_lot_outcomes') }} l on l.job_id = n.job_id
