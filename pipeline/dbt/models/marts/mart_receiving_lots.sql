-- Receiving lots with the Z1.4 table values and the zero-acceptance plan's sample size for the lot size.
select r.*, case when c.sample_size = 0 then r.lot_quantity else least(c.sample_size, r.lot_quantity) end as c0_sample_size, {{ batch_id() }} as export_batch_id
from {{ ref('int_receiving_outcomes') }} r
join {{ ref('c0_plan_aql_1_0') }} c on r.lot_quantity between c.lot_size_from and c.lot_size_to
