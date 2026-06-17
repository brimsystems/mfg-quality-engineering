-- Bore gauge readings against the CMM on the pieces measured by both.
select m.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_cmm_serial_match') }} m
where m.gauge_id = '{{ var("bore_gauge_id") }}'
