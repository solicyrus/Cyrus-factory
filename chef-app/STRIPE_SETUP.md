# Chef App — Stripe Setup (5 steps)

Real card payments for the Top 20 Chefs app. Do these once, in order.
No keys ever go into the code — everything lives in Supabase secrets.

## Step 1 — Get your Stripe secret key
1. Go to [dashboard.stripe.com](https://dashboard.stripe.com) and log in
   (create a free account if you don't have one).
2. Turn on **Test mode** (top-right toggle) while you try things out.
3. Go to **Developers → API keys**.
4. Copy the **Secret key** (starts with `sk_test_...`).

## Step 2 — Save secrets in Supabase
1. Open your Supabase project → **Edge Functions** → **Manage secrets**.
2. Add two secrets:
   - `STRIPE_SECRET_KEY` = the `sk_test_...` key from Step 1
   - `STRIPE_WEBHOOK_SECRET` = leave empty for now (comes from Step 4)

## Step 3 — Deploy the two functions
Install the Supabase CLI once on your laptop
([supabase.com/docs/guides/cli](https://supabase.com/docs/guides/cli)),
then in the `chef-app` folder:

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy create-checkout
supabase functions deploy stripe-webhook
```

## Step 4 — Connect the webhook
1. In Stripe Dashboard → **Developers → Webhooks** → **Add endpoint**.
2. URL: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/stripe-webhook`
3. Select event: `checkout.session.completed` → **Add endpoint**.
4. Click the new endpoint → **Signing secret** → **Reveal** → copy
   the value (starts with `whsec_...`).
5. Back in Supabase → Edge Functions → Manage secrets → set
   `STRIPE_WEBHOOK_SECRET` to that value.

## Step 5 — Run the SQL + paste keys into the app
1. In Supabase **SQL Editor**, run `supabase-schema.sql` once,
   then `supabase-stripe.sql` once.
2. In `js/config.js`, paste your project URL and **anon** key
   (NOT the service key — that one never touches the browser).
3. Reload `index.html` — the Pay button now opens real Stripe Checkout.

## How money flows
1. Customer taps **Pay $X with card** → portions are reserved first
   (the atomic `place_order` — never oversells).
2. `create-checkout` makes a Stripe Checkout Session → customer
   pays on Stripe's secure page.
3. Stripe calls `stripe-webhook` → orders become **Confirmed + paid**.
4. Cancel → customer returns, nothing is charged, portions stay
   reserved as "Pending Kitchen Approval" (the chef dashboard shows them).

## Test cards (test mode only)
- `4242 4242 4242 4242` — payment succeeds
- `4000 0000 0000 0002` — card declined

## Demo mode
Leave `SUPABASE_URL` empty in `js/config.js` and the Pay button shows
a clearly-labeled **DEMO** checkout page — no keys, no network, no charge.
