-- Calibration check points of the bore gauge and the air gauge, one row per event and point.
{% set points = [1, 2, 3, 4, 5] %}
with c as (
    select * from {{ ref('stg_calibration__calibrations') }}
    where gauge_id in ('{{ var("bore_gauge_id") }}', '{{ var("air_gauge_id") }}') and done_date is not null
)
{% for i in points %}
select
    c.calibration_id || '-' || '{{ i }}' as checkpoint_key,
    c.calibration_id, c.gauge_id, g.gauge_type, c.due_date, c.done_date, c.result, c.tolerance,
    {{ i }} as point_no,
    c.check_point_{{ i }} as reference_value,
    c.as_found_error_{{ i }} as as_found_error,
    c.as_left_error_{{ i }} as as_left_error,
    c.done_date > c.due_date as done_past_due,
    {{ batch_id() }} as export_batch_id
from c
join {{ ref('stg_calibration__gauges') }} g on g.gauge_id = c.gauge_id
where c.check_point_{{ i }} is not null
{% if not loop.last %}union all{% endif %}
{% endfor %}
