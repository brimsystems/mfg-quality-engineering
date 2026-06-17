select l.*, {{ batch_id() }} as export_batch_id
from {{ ref('int_lot_outcomes') }} l
