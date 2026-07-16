-- Pieces shipped and complaint quantity by customer and month; repeated complaint entries are left out.
with months as (select distinct period from {{ ref('int_cost_lines') }}),
shipped as (
    select strftime(ship_date, '%Y-%m') as period, customer_id, sum(quantity_good) as pieces_shipped
    from {{ ref('int_lot_outcomes') }} where ship_date is not null group by 1, 2
),
complaints as (
    select strftime(received_date, '%Y-%m') as period, customer_id, count(*) as complaints, sum(quantity) as complaint_quantity
    from {{ ref('mart_complaints') }} where not repeated_entry group by 1, 2
)
select m.period || ' ' || cu.customer_id as period_customer, m.period, cu.customer_id, cu.customer_name, cu.program,
    coalesce(s.pieces_shipped, 0) as pieces_shipped, coalesce(c.complaints, 0) as complaints, coalesce(c.complaint_quantity, 0) as complaint_quantity,
    case when coalesce(s.pieces_shipped, 0) > 0 then coalesce(c.complaint_quantity, 0) * 1e6 / s.pieces_shipped end as ppm,
    {{ batch_id() }} as export_batch_id
from months m
cross join {{ ref('stg_erp__customers') }} cu
left join shipped s on s.period = m.period and s.customer_id = cu.customer_id
left join complaints c on c.period = m.period and c.customer_id = cu.customer_id
