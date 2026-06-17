-- CMM features by how they map to the characteristics master.
select map_method, count(*) as features, count(*) * 1.0 / sum(count(*)) over () as share, {{ batch_id() }} as export_batch_id
from {{ ref('int_cmm_features') }}
group by 1
