select h.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_process_history') }} h
