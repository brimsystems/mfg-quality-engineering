-- Cost of quality lines with their category group and whether the source record is found in its table.
select
    l.line_id,
    l.period,
    cast(substr(l.period, 1, 4) as integer) as period_year,
    l.category,
    l.source_type,
    l.source_record,
    l.amount,
    l."hours" as line_hours,
    case
        when l.category in ('scrap', 'rework labor', 'sorting and containment', 'customer credit', 'return freight') then 'failure'
        when l.category = 'inspection labor' and l.source_type = 'NCR' then 'failure'
        when l.category in ('inspection labor', 'CMM time', 'calibration') then 'appraisal'
        else 'prevention'
    end as cost_group,
    case when l.category = 'inspection labor' and l.source_type = 'NCR' then 're-inspection' else l.category end as cost_line,
    n.job_id as ncr_job_id,
    c.job_id as complaint_job_id,
    case
        when l.source_type = 'NCR' then n.ncr_id is not null
        when l.source_type = 'complaint' then c.complaint_id is not null
    end as source_found
from {{ ref('stg_accounting__cost_of_quality_lines') }} l
left join {{ ref('stg_qms__ncrs') }} n on l.source_type = 'NCR' and n.ncr_id = l.source_record
left join {{ ref('stg_qms__complaints') }} c on l.source_type = 'complaint' and c.complaint_id = l.source_record
