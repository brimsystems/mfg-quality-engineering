select
    part_id,
    customer_id,
    program,
    revision,
    material_grade,
    process_route,
    cast(annual_volume as integer) as annual_volume,
    cast(lot_size as integer) as lot_size,
    drawing_units,
    cast(ppap_level as integer) as ppap_level,
    family_code,
    cast(unit_price as double) as unit_price,
    cast(standard_cost as double) as standard_cost,
    status,
    export_batch_id
from {{ source('erp', 'erp__parts') }}
