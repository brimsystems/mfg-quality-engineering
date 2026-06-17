select l.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_cost_lines') }} l
