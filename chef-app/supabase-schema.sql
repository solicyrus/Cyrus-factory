-- =====================================================================
-- Chef App v1 — Supabase schema
-- Run ONCE in Supabase Dashboard -> SQL Editor -> New query -> Run.
-- Then paste your project URL + anon key into js/config.js.
--
-- Notes:
-- * IDs are TEXT (e.g. 'sch-1') to match js/data.js exactly, so the
--   demo seed and the live database stay interchangeable.
-- * The place_order() function is the atomic core from
--   supabase-backend-v2.py (adapted: uuid -> text ids). It locks the
--   schedule row, so concurrent orders can NEVER oversell.
-- * RLS is left OFF for v1 simplicity (anon key can read/write).
--   Before real customers: enable RLS + policies (see comment at end).
-- =====================================================================

create table if not exists chefs (
  id text primary key,
  name text not null,
  cuisine text not null,
  emoji text not null default '👨‍🍳',
  bio text not null default '',
  foodsafe boolean not null default false,
  island_health boolean not null default false,
  insurance boolean not null default false,
  tasting boolean not null default false
);

create table if not exists dishes (
  id text primary key,
  chef_id text not null references chefs(id) on delete cascade,
  name text not null,
  short_name text not null,
  description text not null default '',
  story text not null default '',
  price numeric not null,
  emoji text not null default '🍽️',
  gradient text not null default ''
);

create table if not exists daily_schedules (
  id text primary key,
  dish_id text not null references dishes(id) on delete cascade,
  weekday int not null check (weekday between 0 and 6),  -- 0=Sunday..6=Saturday
  label text not null,
  max_capacity int not null check (max_capacity >= 0),
  sold_count int not null default 0 check (sold_count >= 0)
);

create table if not exists orders (
  id text primary key,
  user_id text not null,
  schedule_id text not null references daily_schedules(id),
  delivery_type text not null default 'Delivery'
    check (delivery_type in ('Pickup', 'Delivery')),
  status text not null default 'Pending Kitchen Approval',
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Atomic order placement: row lock -> capacity check -> insert -> bump.
-- Called from js/customer.js as POST /rest/v1/rpc/place_order
-- ---------------------------------------------------------------------
create or replace function place_order(
  p_user_id text,
  p_schedule_id text,
  p_delivery_type text
)
returns jsonb
language plpgsql
as $$
declare
  v_max int;
  v_sold int;
  v_left int;
begin
  select max_capacity, sold_count
    into v_max, v_sold
    from daily_schedules
   where id = p_schedule_id
   for update;  -- locks the row: concurrent orders queue here

  if not found then
    return jsonb_build_object('status', 'error',
      'message', 'Menu not found for this day.');
  end if;

  if v_sold >= v_max then
    return jsonb_build_object('status', 'failed',
      'message', 'Sorry — this dish is fully sold out for the day.');
  end if;

  insert into orders(id, user_id, schedule_id, delivery_type, status)
  values ('ord-' || substr(md5(random()::text), 1, 10),
          p_user_id, p_schedule_id, p_delivery_type,
          'Pending Kitchen Approval');

  update daily_schedules
     set sold_count = v_sold + 1
   where id = p_schedule_id;

  v_left := v_max - v_sold - 1;

  return jsonb_build_object('status', 'success',
    'message', 'Order placed!', 'portions_left', v_left);
end;
$$;

-- =====================================================================
-- Seed rows — identical to js/data.js (demo mode uses the same data)
-- =====================================================================

insert into chefs (id, name, cuisine, emoji, bio,
  foodsafe, island_health, insurance, tasting) values
('chef-sara',   'Chef Sara',   'Persian',  '👩‍🍳', 'Third-generation home cook from Tehran. Every stew starts before sunrise.', true, true, true, true),
('chef-arjun',  'Chef Arjun',  'Indian',   '👨‍🍳', 'Tandoor master from Old Delhi. His marinades rest a full 24 hours.', true, true, false, true),
('chef-fatima', 'Chef Fatima', 'Moroccan', '👩‍🍳', 'Cooks the way Fez taught her — clay tagines, saffron, patience.', true, false, false, true),
('chef-marco',  'Chef Marco',  'Italian',  '👨‍🍳', 'Umbrian risotto obsessive. Eighteen minutes of stirring, never less.', true, true, true, false),
('chef-yuki',   'Chef Yuki',   'Japanese', '🧑‍🍳', 'Ten years in Osaka sushi counters before Victoria. Fish first, always.', true, false, false, false),
('chef-diego',  'Chef Diego',  'Mexican',  '👨‍🍳', 'Ensenada street-cart roots. Charred lime and chipotle crema on everything.', true, true, false, true)
on conflict (id) do nothing;

insert into dishes (id, chef_id, name, short_name, description, story, price, emoji, gradient) values
('dish-ghormeh', 'chef-sara',
 'Authentic Persian Ghormeh Sabzi', 'Ghormeh Sabzi Dish',
 'Slow-simmered herb stew with dried lime, kidney beans and lamb.',
 'From Sara''s grandmother''s kitchen in Tehran — dried limes, kidney beans and lamb, simmered low for hours exactly as it has been made for three generations.',
 35, '🍲',
 'radial-gradient(circle at 25% 20%, rgba(45,106,62,.55), transparent 60%), radial-gradient(circle at 80% 90%, rgba(212,175,55,.18), transparent 55%), linear-gradient(140deg, #0e1f12 0%, #090d09 70%)'),
('dish-fesenjan', 'chef-sara',
 'Royal Chicken Fesenjan', 'Fesenjan',
 'Walnuts and pomegranate molasses, chicken, saffron rice.',
 'Walnuts ground by hand every Saturday morning — the dish Sara''s family serves at Nowruz, sweet, dark and unforgettable.',
 38, '🍗',
 'radial-gradient(circle at 70% 15%, rgba(120,50,60,.5), transparent 60%), radial-gradient(circle at 20% 85%, rgba(212,175,55,.16), transparent 55%), linear-gradient(140deg, #1c0e12 0%, #0c0708 70%)'),
('dish-tikka', 'chef-arjun',
 'Old Delhi Chicken Tikka Masala', 'Tikka Masala',
 '24-hour marinated chicken, tandoor-charred, creamy tomato sauce.',
 'Hung curd, Kashmiri chilies and a blazing tandoor — Arjun''s father''s recipe from the lanes of Chandni Chowk.',
 28, '🍛',
 'radial-gradient(circle at 70% 15%, rgba(196,90,20,.5), transparent 60%), radial-gradient(circle at 20% 85%, rgba(212,175,55,.15), transparent 55%), linear-gradient(140deg, #221006 0%, #0d0805 70%)'),
('dish-butter', 'chef-arjun',
 'Midnight Butter Chicken', 'Butter Chicken',
 'Silky makhani sauce, charcoal-kissed chicken, basmati.',
 'The late-night Delhi classic — tomatoes and butter simmered down until the sauce coats the spoon like velvet.',
 30, '🫕',
 'radial-gradient(circle at 30% 20%, rgba(200,110,30,.5), transparent 60%), linear-gradient(140deg, #201005 0%, #0d0704 70%)'),
('dish-tagine', 'chef-fatima',
 'Atlas Mountain Lamb Tagine', 'Lamb Tagine',
 'Preserved lemon, green olives, saffron, clay-pot steamed lamb.',
 'Preserved lemon and saffron, steamed slowly in the clay tagine Fatima carried with her from Fez.',
 32, '🥘',
 'radial-gradient(circle at 30% 25%, rgba(178,74,32,.5), transparent 60%), radial-gradient(circle at 75% 80%, rgba(212,175,55,.14), transparent 55%), linear-gradient(140deg, #241009 0%, #0e0705 70%)'),
('dish-risotto', 'chef-marco',
 'Black Truffle Risotto', 'Truffle Risotto',
 'Carnaroli rice, Umbrian black truffle, 24-month Parmigiano.',
 'Stirred for exactly eighteen minutes, finished with Umbrian black truffle shaved tableside-thin. Marco accepts no shortcuts.',
 38, '🍝',
 'radial-gradient(circle at 75% 20%, rgba(122,60,32,.5), transparent 60%), radial-gradient(circle at 15% 80%, rgba(90,110,50,.25), transparent 55%), linear-gradient(140deg, #1d1208 0%, #0c0705 70%)'),
('dish-omakase', 'chef-yuki',
 'Victoria Omakase Box', 'Omakase Box',
 'Eight pieces from the morning''s best catch, seasoned rice.',
 'Eight pieces chosen each dawn from the day''s best catch — Yuki trained ten years in Osaka before bringing omakase to Victoria.',
 45, '🍱',
 'radial-gradient(circle at 25% 20%, rgba(40,70,120,.55), transparent 60%), radial-gradient(circle at 80% 80%, rgba(180,50,50,.22), transparent 55%), linear-gradient(140deg, #0a1220 0%, #060809 70%)'),
('dish-tacos', 'chef-diego',
 'Baja Fish Tacos (4 pc)', 'Fish Tacos',
 'Crispy lingcod, chipotle crema, charred lime, corn tortillas.',
 'Diego''s Ensenada street-cart recipe — crispy lingcod, chipotle crema and a squeeze of charred lime, exactly like the malecón at midnight.',
 24, '🌮',
 'radial-gradient(circle at 70% 25%, rgba(210,110,30,.5), transparent 60%), radial-gradient(circle at 20% 80%, rgba(160,40,40,.28), transparent 55%), linear-gradient(140deg, #200f06 0%, #0d0704 70%)')
on conflict (id) do nothing;

insert into daily_schedules (id, dish_id, weekday, label, max_capacity, sold_count) values
('sch-1', 'dish-ghormeh', 5, 'FRIDAY MENU',    10, 7),
('sch-2', 'dish-fesenjan', 6, 'SATURDAY MENU',  8, 0),
('sch-3', 'dish-tikka',   2, 'TUESDAY MENU',   12, 3),
('sch-4', 'dish-butter',  5, 'FRIDAY MENU',    10, 1),
('sch-5', 'dish-tagine',  6, 'SATURDAY MENU',   8, 0),
('sch-6', 'dish-risotto', 4, 'THURSDAY MENU',  10, 4),
('sch-7', 'dish-omakase', 3, 'WEDNESDAY MENU',  6, 6),
('sch-8', 'dish-tacos',   0, 'SUNDAY MENU',    15, 5)
on conflict (id) do nothing;

-- =====================================================================
-- PRODUCTION HARDENING (do before real customers):
--   alter table chefs enable row level security;
--   alter table dishes enable row level security;
--   alter table daily_schedules enable row level security;
--   alter table orders enable row level security;
-- then add policies: public read on chefs/dishes/daily_schedules,
-- orders insert for anon + select own (user_id), chef/admin via
-- service key or authenticated roles. Never expose the service key
-- in js/config.js — the anon key is the only browser-safe one.
-- =====================================================================
