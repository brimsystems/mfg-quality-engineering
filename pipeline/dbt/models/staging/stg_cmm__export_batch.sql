select
    export_batch_id,
    cast(exported_at as timestamp) as exported_at,
    source_system,
    table_name,
    cast("rows" as integer) as "rows"
from {{ source('cmm', 'cmm__export_batch') }}
