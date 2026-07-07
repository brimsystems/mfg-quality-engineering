select
    report_id,
    characteristic_id,
    cast(run_date as timestamp) as run_date,
    report_type,
    cast(subgroups_used as integer) as subgroups_used,
    first_subgroup_id,
    last_subgroup_id,
    subgroup_ids,
    method_flag,
    cast(cp as double) as cp,
    cast(cpk as double) as cpk,
    cast(pp as double) as pp,
    cast(ppk as double) as ppk,
    issued_to,
    cast(issued_date as date) as issued_date,
    created_by,
    export_batch_id
from {{ source('qms', 'qms__capability_reports') }}
