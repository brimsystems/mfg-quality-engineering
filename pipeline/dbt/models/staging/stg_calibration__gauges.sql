select
    gauge_id,
    gauge_type,
    description,
    cast(range_min as double) as range_min,
    cast(range_max as double) as range_max,
    cast(resolution as double) as resolution,
    location,
    owner,
    cast(interval_months as integer) as interval_months,
    status,
    cast(status_date as date) as status_date,
    serial_no,
    export_batch_id
from {{ source('calibration', 'calibration__gauges') }}
