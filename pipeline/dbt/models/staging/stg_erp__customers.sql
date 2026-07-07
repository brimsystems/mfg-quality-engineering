select
    customer_id,
    customer_name,
    program,
    cast(ppap_level as integer) as ppap_level,
    cast(as9102_required as boolean) as as9102_required,
    cast(validated_process as boolean) as validated_process,
    cast(source_inspection as boolean) as source_inspection,
    cast(cpk_required as double) as cpk_required,
    cast(created_at as date) as created_at,
    status,
    export_batch_id
from {{ source('erp', 'erp__customers') }}
