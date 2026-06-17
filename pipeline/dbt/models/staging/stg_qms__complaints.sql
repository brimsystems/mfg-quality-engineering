select
    complaint_id,
    customer_id,
    part_id,
    job_id,
    cast(quantity as integer) as quantity,
    defect_code,
    cast(received_date as date) as received_date,
    cast(ppm_impact_recorded as double) as ppm_impact_recorded,
    cast(containment_cost as double) as containment_cost,
    cast(sorting_hours as double) as sorting_hours,
    cast(credit_issued as double) as credit_issued,
    cast(returned_quantity as integer) as returned_quantity,
    cast(return_freight_cost as double) as return_freight_cost,
    status,
    export_batch_id
from {{ source('qms', 'qms__complaints') }}
