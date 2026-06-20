-- Calibration events with the gauge type and whether each was done past its due date.
select c.calibration_id, c.gauge_id, g.gauge_type, g.status as gauge_status, g.status_date, g.interval_months, c.due_date, c.pulled_date, c.done_date, c.returned_date, c.result,
    c.performed_by, c.certificate_no, c.done_date > c.due_date as done_past_due, {{ batch_id() }} as mart_export_batch_id
from {{ ref('stg_calibration__calibrations') }} c
join {{ ref('stg_calibration__gauges') }} g on g.gauge_id = c.gauge_id
