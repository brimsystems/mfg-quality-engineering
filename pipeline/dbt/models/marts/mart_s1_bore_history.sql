-- Subgroups on the critical bore of family F-21 taken with the two-point bore gauge.
select h.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_process_history') }} h
where h.gauge_id = '{{ var("bore_gauge_id") }}' and h.subgroup_size = 5
