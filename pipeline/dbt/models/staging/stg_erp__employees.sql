select
    employee_id,
    name,
    role,
    cast(shift as integer) as shift,
    cast(hire_date as date) as hire_date,
    cast(certification_level as integer) as certification_level,
    home_machine,
    "position",
    export_batch_id
from {{ source('erp', 'erp__employees') }}
