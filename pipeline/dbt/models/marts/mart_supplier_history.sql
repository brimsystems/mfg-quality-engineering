-- Receiving history by supplier beside the scorecard as published.
select
    s.supplier_id,
    s.supplier_name,
    s.commodity,
    s.scorecard_rank_as_published,
    s.scorecard_lot_acceptance_pct,
    s.scorecard_on_time_pct,
    count(r.receiving_id) as lots,
    sum(r.sample_size) as pieces_sampled,
    sum(r.defects_found) as defects_found,
    sum(case when r.disposition = 'accept' then 1 else 0 end) as lots_accepted,
    sum(case when r.on_time then 1 else 0 end) as lots_on_time,
    sum(case when r.sample_below_table then 1 else 0 end) as lots_sample_below_table,
    sum(case when r.accepted_above_acceptance_number then 1 else 0 end) as lots_accepted_above_acceptance_number,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__suppliers') }} s
left join {{ ref('int_receiving_outcomes') }} r on r.supplier_id = s.supplier_id
group by all
