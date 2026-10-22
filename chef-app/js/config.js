/* =====================================================================
   Chef App v1 — backend configuration
   ---------------------------------------------------------------------
   ONE database, TWO API surfaces:
     js/customer.js  -> window.CustomerAPI  (browse chefs/menus, cart,
                                             place orders, order status)
     js/chef.js      -> window.ChefAPI      (weekly schedule + capacity,
                                             incoming orders, verification)
   admin.html reuses ChefAPI.

   BACKEND MODES:
   - DEMO mode (default): SUPABASE_URL / SUPABASE_ANON_KEY left empty.
     All data lives in the browser's localStorage, seeded from js/data.js.
     Works by just opening index.html — no server, no internet needed.
   - SUPABASE mode: paste your Supabase project URL + anon key below,
     then run supabase-schema.sql once in the Supabase SQL Editor.
     Both API modules then talk to the same live tables.
   ===================================================================== */

window.CHEFAPP = window.CHEFAPP || {};

window.CHEFAPP.config = {
  SUPABASE_URL: "https://yuryjcjwiyhbdquatbpg.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_5JWkatqtSuczvpMaKgzkbQ_iXsD416V"   // publishable key — safe in frontend code
};

window.CHEFAPP.isSupabaseMode = function () {
  var c = window.CHEFAPP.config;
  return !!(
    c.SUPABASE_URL &&
    c.SUPABASE_ANON_KEY &&
    c.SUPABASE_URL.indexOf("your-project") === -1 &&
    c.SUPABASE_URL.indexOf("http") === 0
  );
};

/* Minimal PostgREST client — no dependencies, so demo mode stays offline-safe.
   Only used when isSupabaseMode() is true. */
window.CHEFAPP.rest = async function (path, options) {
  options = options || {};
  var c = window.CHEFAPP.config;
  var url = c.SUPABASE_URL.replace(/\/$/, "") + "/rest/v1" + path;
  var headers = {
    "apikey": c.SUPABASE_ANON_KEY,
    "Authorization": "Bearer " + c.SUPABASE_ANON_KEY,
    "Content-Type": "application/json"
  };
  if (options.prefer) headers["Prefer"] = options.prefer;
  var res = await fetch(url, {
    method: options.method || "GET",
    headers: headers,
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  if (!res.ok) {
    var txt = await res.text().catch(function () { return ""; });
    throw new Error("Supabase " + res.status + ": " + txt.slice(0, 200));
  }
  if (res.status === 204) return null;
  var ct = res.headers.get("content-type") || "";
  return ct.indexOf("json") !== -1 ? res.json() : res.text();
};

/* Shared localStorage keys — BOTH modules read/write the same keys,
   so a chef's capacity edit instantly shows in the customer app. */
window.CHEFAPP.STORE_KEY = "chefapp_v1_store";
window.CHEFAPP.CART_KEY = "chefapp_v1_cart";
