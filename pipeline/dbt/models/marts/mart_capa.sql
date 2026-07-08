-- Corrective actions with the lot, part and family of the source NCR or complaint.
select
    c.capa_id, c.source_type, c.source_id, c.opened, c.owner, c.actions_text, c.verification, c.closed,
    coalesce(n.job_id, k.job_id) as job_id,
    coalesce(l.part_id, k.part_id) as part_id,
    l.family_code,
    {{ batch_id() }} as mart_export_batch_id
from {{ ref('stg_qms__capa') }} c
left join {{ ref('stg_qms__ncrs') }} n on c.source_type = 'NCR' and n.ncr_id = c.source_id
left join {{ ref('stg_qms__complaints') }} k on c.source_type = 'complaint' and k.complaint_id = c.source_id
left join {{ ref('int_lot_outcomes') }} l on l.job_id = coalesce(n.job_id, k.job_id)
