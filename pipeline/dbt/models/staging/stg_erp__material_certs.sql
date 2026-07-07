select
    material_cert_id,
    supplier_id,
    grade,
    heat_number,
    cast(bar_diameter_mm as double) as bar_diameter_mm,
    cast(hardness_hrc as double) as hardness_hrc,
    cast(receiving_hardness_hrc as double) as receiving_hardness_hrc,
    cast(tensile_mpa as integer) as tensile_mpa,
    cast(c_pct as double) as c_pct,
    cast(mn_pct as double) as mn_pct,
    cast(cr_pct as double) as cr_pct,
    cast(mo_pct as double) as mo_pct,
    cast(ni_pct as double) as ni_pct,
    cast(quantity_bars as integer) as quantity_bars,
    cast(received_date as date) as received_date,
    export_batch_id
from {{ source('erp', 'erp__material_certs') }}
