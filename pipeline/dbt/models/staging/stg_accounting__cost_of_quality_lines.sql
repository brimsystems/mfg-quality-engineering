select
    line_id,
    period,
    category,
    source_type,
    source_record,
    cast(amount as double) as amount,
    cast("hours" as double) as "hours",
    gl_account,
    export_batch_id
from {{ source('accounting', 'accounting__cost_of_quality_lines') }}
