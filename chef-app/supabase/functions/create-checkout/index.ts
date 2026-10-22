// =====================================================================
// Chef App v1 — Supabase Edge Function: create-checkout
// POST {order_ids, amount_cents, currency, success_url, cancel_url}
//   -> {url, id}  (Stripe Checkout Session URL to redirect the customer)
//
// Deploy: supabase functions deploy create-checkout
// Secrets: supabase secrets set STRIPE_SECRET_KEY=sk_live_...
// No Stripe SDK — plain fetch to the Stripe REST API (works in Deno).
// Never hardcode keys: STRIPE_SECRET_KEY comes from env only.
// =====================================================================
import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request): Promise<Response> => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  try {
    const body = await req.json();
    const orderIds: string[] = [].concat(body.order_ids || []).filter(Boolean);
    const amountCents: number = parseInt(body.amount_cents, 10);
    const currency: string = (body.currency || "cad").toLowerCase();
    const successUrl: string = body.success_url || "";
    const cancelUrl: string = body.cancel_url || "";

    const secretKey = Deno.env.get("STRIPE_SECRET_KEY") || "";
    if (!secretKey) throw new Error("STRIPE_SECRET_KEY is not set");
    if (!orderIds.length) throw new Error("order_ids is required");
    if (!Number.isFinite(amountCents) || amountCents < 50) {
      throw new Error("amount_cents must be >= 50");
    }
    if (!successUrl || !cancelUrl) {
      throw new Error("success_url and cancel_url are required");
    }

    const params = new URLSearchParams();
    params.append("mode", "payment");
    params.append("success_url", successUrl);
    params.append("cancel_url", cancelUrl);
    params.append("metadata[order_ids]", orderIds.join(","));
    params.append("line_items[0][price_data][currency]", currency);
    params.append(
      "line_items[0][price_data][product_data][name]",
      "Top 20 Chefs — pre-order"
    );
    params.append("line_items[0][price_data][unit_amount]", String(amountCents));
    params.append("line_items[0][quantity]", "1");

    const stripeRes = await fetch(
      "https://api.stripe.com/v1/checkout/sessions",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer " + secretKey,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      }
    );
    const data = await stripeRes.json();
    if (!stripeRes.ok) {
      throw new Error(
        (data && data.error && data.error.message) || "Stripe error"
      );
    }
    return new Response(JSON.stringify({ url: data.url, id: data.id }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return new Response(JSON.stringify({ error: msg }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
