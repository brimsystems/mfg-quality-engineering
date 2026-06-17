select
    role,
    cast("year" as integer) as "year",
    cast(loaded_rate as double) as loaded_rate,
    export_batch_id
from {{ source('accounting', 'accounting__labor_rates') }}
