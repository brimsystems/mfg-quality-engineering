-- CMM reports by machine and month.
select strftime(measured_at, '%Y-%m') as period, machine, count(*) as reports, {{ batch_id() }} as export_batch_id
from {{ ref('stg_cmm__cmm_reports') }}
group by 1, 2
