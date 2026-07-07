select
    export_batch_id,
    cast(exported_at as timestamp) as exported_at,
    source_system,
    table_name,
    cast("rows" as integer) as "rows"
from {{ source('calibration', 'calibration__export_batch') }}
