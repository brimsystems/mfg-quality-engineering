select
    transaction_id,
    job_id,
    cast(quantity as integer) as quantity,
    cast(cost as double) as cost,
    reason_code,
    cast(transaction_date as date) as transaction_date,
    ncr_id,
    export_batch_id
from {{ source('erp', 'erp__scrap_transactions') }}
