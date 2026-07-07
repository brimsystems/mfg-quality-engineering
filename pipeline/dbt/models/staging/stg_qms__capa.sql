select
    capa_id,
    source_type,
    source_id,
    cast(opened as date) as opened,
    owner,
    actions_text,
    verification,
    cast(closed as date) as closed,
    export_batch_id
from {{ source('qms', 'qms__capa') }}
