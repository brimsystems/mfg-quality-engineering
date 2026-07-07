select
    machine_id,
    cast(shop_machine_no as integer) as shop_machine_no,
    machine_type,
    machine_group,
    cast(model_year as integer) as model_year,
    cast(spindle_hours as integer) as spindle_hours,
    shift_pattern,
    export_batch_id
from {{ source('erp', 'erp__machines') }}
