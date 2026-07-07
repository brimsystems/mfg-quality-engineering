select
    job_id,
    inspector,
    sampling_plan_code,
    cast(sample_size as integer) as sample_size,
    result,
    defect_codes,
    cast(defects_found as integer) as defects_found,
    cast(inspected_at as timestamp) as inspected_at,
    export_batch_id
from {{ source('qms', 'qms__final_inspection') }}
