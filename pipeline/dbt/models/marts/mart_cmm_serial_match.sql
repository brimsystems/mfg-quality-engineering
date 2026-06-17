select m.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_cmm_serial_match') }} m
