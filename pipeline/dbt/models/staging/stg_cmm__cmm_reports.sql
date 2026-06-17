select
    report_id,
    machine,
    job_id,
    part_id,
    revision,
    program_name,
    program_revision,
    serial_no,
    cast(measured_at as timestamp) as measured_at,
    operator_id,
    export_batch_id
from {{ source('cmm', 'cmm__cmm_reports') }}
