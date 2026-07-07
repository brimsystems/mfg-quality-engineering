select
    report_id,
    cast(feature_no as integer) as feature_no,
    feature_name,
    characteristic_id,
    cast(nominal as double) as nominal,
    cast(upper_tol as double) as upper_tol,
    cast(lower_tol as double) as lower_tol,
    cast(actual as double) as actual,
    cast(deviation as double) as deviation,
    cast(out_of_tolerance as boolean) as out_of_tolerance,
    export_batch_id
from {{ source('cmm', 'cmm__cmm_features') }}
