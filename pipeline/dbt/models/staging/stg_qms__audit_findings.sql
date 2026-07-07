select
    finding_id,
    audit_type,
    clause,
    finding_text,
    severity,
    cast(opened as date) as opened,
    cast(closed as date) as closed,
    export_batch_id
from {{ source('qms', 'qms__audit_findings') }}
