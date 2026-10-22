# Platform Commission — 10% default, per chef, per order

## The model (simple)

Every order gives the platform a cut and the chef the rest:

- **Dish price $35** → customer pays **$35.00**
- Platform fee (10%) → **$3.50**
- Chef payout → **$31.50**

The split is **recorded on each order row at order time** (`total_cents`,
`platform_fee_cents`, `chef_payout_cents` — integer cents, so
`fee + payout` always equals `total` exactly). Each chef has their own
`commission_rate` (default `0.10` = 10%).

**Rate changes are history-safe:** if the admin raises Chef Sara from 10%
to 15%, her old orders keep the 10% fee they were recorded with — only
NEW orders use 15%.

## Setup (one SQL file)

In Supabase Dashboard → SQL Editor → New query → paste → Run:

```
supabase-commission.sql
```

It adds `chefs.commission_rate`, the three money columns on `orders`,
and replaces `place_order()` with the commission-aware version
(same signature — no app code changes needed for live mode).

## Where it shows

- **Customer app** — the confirmation screen shows "Total charged: $X".
- **Chef Hub** — new **Earnings** card: gross sales, platform fee (their
  rate %), payout, order count, per-dish breakdown.
- **Admin** — new **Platform revenue** section: total commission collected,
  total gross, total payouts, per-chef table (rate · gross · fee · payout),
  plus a **Commission rates** form to change any chef's rate (0–50%).
  Changes apply to new orders only.

## Notes

- Demo mode computes the identical split client-side, so demo and live
  always agree (verified by automated tests).
- Money columns on orders placed *before* this update are NULL and count
  as $0 in earnings — that's correct, no fee was recorded then.
- RLS hardening (before real customers) should add policies that let chefs
  read only their own payout rows; see the comment at the end of
  `supabase-schema.sql`.
