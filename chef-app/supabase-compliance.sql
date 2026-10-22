-- Top 20 Chefs — compliance checklist expansion (2026-10-22)
-- Run once in Supabase SQL Editor. Adds 3 legal checklist columns to chefs.
-- Legal basis: BC Food Premises Regulation (B.C. Reg. 210/99) via Island Health.

alter table chefs add column if not exists approved_kitchen boolean not null default false;
alter table chefs add column if not exists business_licence boolean not null default false;
alter table chefs add column if not exists labels boolean not null default false;
