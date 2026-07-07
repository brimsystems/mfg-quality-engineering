-- Receiving lots with the Z1.4 table values for the lot size beside the sample as taken.
select
    r.receiving_id,
    r.supplier_id,
    s.commodity,
    r.item_type,
    r.part_or_material,
    r.job_id,
    r.material_cert_id,
    r.lot_quantity,
    r.po_due_date,
    r.code_letter,
    r.sample_size,
    r.defects_found,
    r.defect_codes,
    r.disposition,
    r.received_at,
    r.inspected_at,
    r.inspector,
    z.code_letter as table_code_letter,
    least(z.sample_size, r.lot_quantity) as table_sample_size,
    z.acceptance_number,
    r.sample_size < least(z.sample_size, r.lot_quantity) as sample_below_table,
    r.defects_found > z.acceptance_number as above_acceptance_number,
    r.defects_found > z.acceptance_number and r.disposition = 'accept' as accepted_above_acceptance_number,
    cast(r.received_at as date) <= r.po_due_date as on_time
from {{ ref('stg_qms__receiving_inspection') }} r
join {{ ref('stg_qms__suppliers') }} s on s.supplier_id = r.supplier_id
join {{ ref('z14_single_normal_aql_1_0') }} z on r.lot_quantity between z.lot_size_from and z.lot_size_to
