select
    supplier_id,
    supplier_name,
    commodity,
    approved_status,
    cast(approval_date as date) as approval_date,
    cast(lots_per_year as integer) as lots_per_year,
    cast(scorecard_lot_acceptance_pct as double) as scorecard_lot_acceptance_pct,
    cast(scorecard_on_time_pct as double) as scorecard_on_time_pct,
    cast(scorecard_rank_as_published as integer) as scorecard_rank_as_published,
    export_batch_id
from {{ source('qms', 'qms__suppliers') }}
