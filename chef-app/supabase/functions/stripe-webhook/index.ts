// =====================================================================
// Chef App v1 — Supabase Edge Function: stripe-webhook
// Receives Stripe events. On checkout.session.completed it marks the
// matching Orders rows as Confirmed + paid (via the service role key).
//
// Stripe Dashboard -> Developers -> Webhooks -> Add endpoint:
//   https://<project-ref>.supabase.co/functions/v1/stripe-webhook
//   Events: checkout.session.completed
// Then: supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
//
// Signature is verified with Web Crypto (HMAC-SHA256) — no SDK needed.
// Never hardcode secrets: all from env.
// =====================================================================
import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const TOLERANCE_SECS = 300; // reject webhooks older than 5 minutes

async function verifyStripeSignature(
  payload: string,
  header: string,
  secret: string
): Promise<boolean> {
  // Stripe header looks like: t=1492774577,v1=5257a869...,v0=...
  const parts: Record<string, string> = {};
  for (const kv of header.split(",")) {
    const i = kv.indexOf("=");
    if (i > 0) parts[kv.slice(0, i).trim()] = kv.slice(i + 1).trim();
  }
  const t = parts["t"];
  const v1 = parts["v1"];
  if (!t || !v1 || !secret) return false;

  const ts = parseInt(t, 10);
  if (!Number.isFinite(ts)) return false;
  if (Math.abs(Date.now() / 1000 - ts) > TOLERANCE_SECS) return false;

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sigBuf = await crypto.subtle.sign(
    "HMAC",
    key,
    enc.encode(t + "." + payload)
  );
  const hex = Array.from(new Uint8Array(sigBuf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  // constant-time compare
  if (hex.length !== v1.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) {
    diff |= hex.charCodeAt(i) ^ v1.charCodeAt(i);
  }
  return diff === 0;
}

serve(async (req: Request): Promise<Response> => {
  try {
    const signature = req.headers.get("stripe-signature") || "";
    const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET") || "";
    const payload = await req.text();

    if (!(await verifyStripeSignature(payload, signature, webhookSecret))) {
      return new Response("bad signature", { status: 400 });
    }

    const event = JSON.parse(payload);

    if (event.type === "checkout.session.completed") {
      const session = event.data.object || {};
      const orderIds: string[] = String(
        (session.metadata && session.metadata.order_ids) || ""
      )
        .split(",")
        .map((s: string) => s.trim())
        .filter(Boolean);

      if (orderIds.length > 0) {
        const supabase = createClient(
          Deno.env.get("SUPABASE_URL") || "",
          Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
        );
        const { error } = await supabase
          .from("orders")
          .update({
            status: "Confirmed",
            payment_status: "paid",
            stripe_session_id: session.id || null,
          })
          .in("id", orderIds);
        if (error) {
          console.error("orders update failed:", error.message);
          return new Response("db update failed", { status: 500 });
        }
      }
    }

    return new Response(JSON.stringify({ received: true }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error("webhook error:", msg);
    return new Response("webhook error", { status: 400 });
  }
});
