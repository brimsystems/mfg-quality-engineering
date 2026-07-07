-- CMM program features mapped to the characteristics master: by the id where the report carries it, otherwise by the name the
-- program uses (type prefix and order on the part), confirmed by nominal and tolerance.
with features as (
    select distinct r.part_id, f.feature_name, f.characteristic_id, f.nominal, f.upper_tol, f.lower_tol
    from {{ ref('stg_cmm__cmm_features') }} f
    join {{ ref('stg_cmm__cmm_reports') }} r on r.report_id = f.report_id
),
named as (
    select *,
        case split_part(feature_name, '_', 1)
            when 'DIA' then 'diameter' when 'LEN' then 'length' when 'BORE' then 'bore' when 'RUN' then 'runout' when 'TP' then 'true position' when 'FLT' then 'flatness'
        end as characteristic_type,
        try_cast(split_part(feature_name, '_', 2) as integer) as type_order
    from features
    where characteristic_id is null and regexp_matches(feature_name, '^(DIA|LEN|BORE|RUN|TP|FLT)_[0-9]+$')
),
master as (
    select characteristic_id, part_id, characteristic_type, nominal, usl, lsl,
        row_number() over (partition by part_id, characteristic_type order by characteristic_id) as type_order
    from {{ ref('stg_qms__characteristics') }}
)
select f.part_id, f.feature_name, f.characteristic_id, 'id in the report' as map_method
from features f
where f.characteristic_id is not null
union all
select n.part_id, n.feature_name, m.characteristic_id, 'mapping table' as map_method
from named n
join master m
  on m.part_id = n.part_id and m.characteristic_type = n.characteristic_type and m.type_order = n.type_order
 and abs(m.nominal - n.nominal) < 1e-6 and abs((m.usl - m.nominal) - n.upper_tol) < 1e-6
