select r.*, {{ batch_id() }} as mart_export_batch_id
from {{ ref('stg_accounting__labor_rates') }} r
