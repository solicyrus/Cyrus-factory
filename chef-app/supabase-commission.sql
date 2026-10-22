-- =====================================================================
-- Chef App v1 — platform commission (10% default, per chef, per order)
-- Run ONCE in Supabase Dashboard -> SQL Editor -> New query -> Run.
-- Safe to run twice (IF NOT EXISTS guards + CREATE OR REPLACE).
--
-- MODEL (standard marketplace split, recorded at order time):
--   * chefs.commission_rate — numeric, default 0.10 (10%), admin can
--     change it per chef any time. Changes apply ONLY to new orders;
--     old rows keep the fee they were recorded with (history is safe).
--   * orders.total_cents / platform_fee_cents / chef_payout_cents — int
--     cents recorded per portion row at order time. Money math is in
--     INTEGER cents: total = round(price*100), fee = round(total*rate),
--     payout = total - fee (so fee + payout always equals total).
-- =====================================================================

alter table chefs
  add column if not exists commission_rate numeric not null default 0.10;

alter table orders
  add column if not exists total_cents int;

alter table orders
  add column if not exists platform_fee_cents int;

alter table orders
  add column if not exists chef_payout_cents int;

-- ---------------------------------------------------------------------
-- Atomic order placement with commission split.
-- Same signature as before (p_user_id, p_schedule_id, p_delivery_type,
-- p_qty default 1): row lock -> capacity check -> price+rate lookup ->
-- per-portion money split -> insert -> bump sold_count.
-- ---------------------------------------------------------------------
create or replace function place_order(
  p_user_id text,
  p_schedule_id text,
  p_delivery_type text,
  p_qty int default 1
)
returns jsonb
language plpgsql
as $$
declare
  v_max int;
  v_sold int;
  v_left int;
  v_qty int;
  v_price numeric;
  v_rate numeric;
  v_total int;
  v_fee int;
  v_payout int;
  i int;
begin
  -- sanitize quantity: 1..20
  v_qty := greatest(1, least(coalesce(p_qty, 1), 20));

  select max_capacity, sold_count
    into v_max, v_sold
    from daily_schedules
   where id = p_schedule_id
   for update;  -- locks the row: concurrent orders queue here

  if not found then
    return jsonb_build_object('status', 'error',
      'message', 'Menu not found for this day.');
  end if;

  if v_sold + v_qty > v_max then
    return jsonb_build_object('status', 'failed',
      'message', 'Sorry — not enough portions left for this day.');
  end if;

  -- dish price + the chef's CURRENT commission rate, locked in now
  select d.price, coalesce(c.commission_rate, 0.10)
    into v_price, v_rate
    from dishes d
    join chefs c on c.id = d.chef_id
   where d.id = (select dish_id from daily_schedules
                  where id = p_schedule_id);

  if v_price is null then
    return jsonb_build_object('status', 'error',
      'message', 'Menu not found for this day.');
  end if;

  -- integer-cents money split (per portion)
  v_total  := round(v_price * 100)::int;
  v_fee    := round(v_total * v_rate)::int;
  v_payout := v_total - v_fee;

  -- one order row per portion (orders table has no quantity column)
  for i in 1..v_qty loop
    insert into orders(id, user_id, schedule_id, delivery_type, status,
                       total_cents, platform_fee_cents, chef_payout_cents)
    values ('ord-' || substr(md5(random()::text || i::text), 1, 10),
            p_user_id, p_schedule_id, p_delivery_type,
            'Pending Kitchen Approval',
            v_total, v_fee, v_payout);
  end loop;

  update daily_schedules
     set sold_count = v_sold + v_qty
   where id = p_schedule_id;

  v_left := v_max - v_sold - v_qty;

  return jsonb_build_object('status', 'success',
    'message', 'Order placed!', 'portions_left', v_left,
    'qty', v_qty,
    'total_cents', v_total * v_qty,
    'platform_fee_cents', v_fee * v_qty,
    'chef_payout_cents', v_payout * v_qty);
end;
$$;
