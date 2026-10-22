# Top 20 Chefs — Luxury Home-Chef Marketplace (Victoria, BC)

Curated marketplace: 20 hand-picked chefs, customers order by the portion,
chefs manage their weekly menu, the platform takes a 10% commission.

## Structure

| Path | What |
|---|---|
| `index.html` | Customer app (browse, cart, checkout) |
| `chef.html` | Chef dashboard (schedule, capacity, orders, earnings) |
| `admin.html` | Admin panel (orders, verification, revenue, commission rates) |
| `js/config.js` | Supabase URL + publishable key (public by design) |
| `js/customer.js` | Customer API — browse, cart, atomic `place_order` |
| `js/chef.js` | Chef API — schedule, orders, verification, earnings |
| `js/data.js` | Demo seed data (6 chefs) |
| `css/app.css` | Dark + gold luxury theme |
| `supabase-*.sql` | Database migrations (run in order in SQL Editor) |
| `supabase/functions/` | Stripe Checkout + webhook edge functions (Deno) |

## Database setup (Supabase SQL Editor, in order)

1. `supabase-schema.sql` — tables + `place_order()` + seed data
2. `supabase-stripe.sql` — payment columns
3. `supabase-commission.sql` — commission columns + commission-aware `place_order()`

(`supabase-seed.sql` and `supabase-fix-qty.sql` were one-time fixes, already folded in.)

## Live deploy

Static site — deploy on Vercel (root = this folder). No build step.
Backend = Supabase (Postgres + Edge Functions). Payments = Stripe Checkout.
