select r.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_receiving_outcomes') }} r
