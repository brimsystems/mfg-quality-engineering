select
    part_id,
    cast(op_no as integer) as op_no,
    operation,
    machine_type,
    cast(cycle_time_min as double) as cycle_time_min,
    outside_process,
    inspection_plan_id,
    export_batch_id
from {{ source('erp', 'erp__routings') }}
