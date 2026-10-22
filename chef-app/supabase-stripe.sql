-- =====================================================================
-- Chef App v1 — Stripe payment columns (run AFTER supabase-schema.sql)
-- Supabase Dashboard -> SQL Editor -> New query -> paste -> Run.
-- Safe to run twice (IF NOT EXISTS guards).
-- =====================================================================

alter table orders
  add column if not exists payment_status text not null default 'unpaid'
  check (payment_status in ('unpaid', 'paid', 'refunded'));

alter table orders
  add column if not exists stripe_session_id text;

create index if not exists orders_stripe_session_idx
  on orders (stripe_session_id);

-- The stripe-webhook edge function sets:
--   status='Confirmed', payment_status='paid',
--   stripe_session_id='<cs_...>'
-- when Stripe reports checkout.session.completed.
