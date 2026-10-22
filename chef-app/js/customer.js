/* =====================================================================
   Chef App v1 — CUSTOMER backend (one of two API surfaces)
   window.CustomerAPI: browse chefs/menus, read capacity, cart,
   place orders (atomic), order status.
   Shares ONE database with js/chef.js:
     - demo mode  -> same localStorage blob (see js/config.js keys)
     - live mode  -> same Supabase tables (Chefs, Dishes, DailySchedules,
                     Orders) + the atomic place_order RPC
   All methods are async (uniform in both modes). No DOM access here.
   ===================================================================== */

window.CustomerAPI = (function () {
  var S = window.CHEFAPP;

  /* ---------------- demo store (localStorage) ---------------- */
  function loadStore() {
    try {
      var raw = localStorage.getItem(S.STORE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* corrupted -> reseed below */ }
    var seed = JSON.parse(JSON.stringify(S.seed));
    seed.orders = [];
    saveStore(seed);
    return seed;
  }
  function saveStore(s) {
    localStorage.setItem(S.STORE_KEY, JSON.stringify(s));
  }
  function enrich(st, sch) {
    var dish = st.dishes.find(function (d) { return d.id === sch.dish_id; }) || {};
    var chef = st.chefs.find(function (c) { return c.id === dish.chef_id; }) || {};
    var out = Object.assign({}, sch);
    out.dish = dish; out.chef = chef;
    out.portions_left = Math.max(0, sch.max_capacity - sch.sold_count);
    return out;
  }
  function demoId(prefix) {
    return prefix + "-" + Date.now().toString(36) +
      Math.random().toString(36).slice(2, 7);
  }

  /* Integer-cents money split, identical to the place_order RPC:
     total = round(price*100), fee = round(total*rate), payout = total-fee.
     Rate is read at order time so later changes never rewrite history. */
  function splitCents(priceDollars, rate) {
    var total = Math.round(Number(priceDollars) * 100);
    var fee = Math.round(total * (rate == null ? 0.10 : Number(rate)));
    return { total_cents: total,
             platform_fee_cents: fee,
             chef_payout_cents: total - fee };
  }

  /* ---------------- supabase helpers ---------------- */
  async function sbGet(table, query) {
    var rows = await S.rest("/" + table + (query ? "?" + query : ""),
      { prefer: "return=representation" });
    return rows || [];
  }
  async function enrichLive(sch) {
    var dishes = await sbGet("dishes", "id=eq." + encodeURIComponent(sch.dish_id));
    var dish = dishes[0] || {};
    var chefs = dish.chef_id
      ? await sbGet("chefs", "id=eq." + encodeURIComponent(dish.chef_id)) : [];
    var out = Object.assign({}, sch);
    out.dish = dish; out.chef = chefs[0] || {};
    out.portions_left = Math.max(0, sch.max_capacity - sch.sold_count);
    return out;
  }

  /* ---------------- public API ---------------- */
  return {
    mode: function () { return S.isSupabaseMode() ? "supabase" : "demo"; },

    /* --- browse --- */
    listChefs: async function () {
      if (S.isSupabaseMode()) return sbGet("chefs", "order=name");
      return loadStore().chefs;
    },
    listDishes: async function (chefId) {
      if (S.isSupabaseMode()) {
        var q = chefId ? "chef_id=eq." + encodeURIComponent(chefId) : "order=name";
        return sbGet("dishes", q);
      }
      var ds = loadStore().dishes;
      return chefId ? ds.filter(function (d) { return d.chef_id === chefId; }) : ds;
    },
    /* all scheduled menus, enriched with dish + chef + portions_left */
    listSchedules: async function () {
      if (S.isSupabaseMode()) {
        var rows = await sbGet("daily_schedules", "order=weekday");
        var out = [];
        for (var i = 0; i < rows.length; i++) out.push(await enrichLive(rows[i]));
        return out;
      }
      var st = loadStore();
      return st.schedules.map(function (s) { return enrich(st, s); });
    },
    getSchedule: async function (id) {
      if (S.isSupabaseMode()) {
        var rows = await sbGet("daily_schedules",
          "id=eq." + encodeURIComponent(id));
        return rows[0] ? enrichLive(rows[0]) : null;
      }
      var st = loadStore();
      var sch = st.schedules.find(function (s) { return s.id === id; });
      return sch ? enrich(st, sch) : null;
    },
    portionsLeft: async function (scheduleId) {
      var sch = await this.getSchedule(scheduleId);
      return sch ? sch.portions_left : 0;
    },

    /* --- ordering (atomic: never oversells) ---
       qty: number of portions. Returns
       {ok:true, order_ids:[...], portions_left:n} or
       {ok:false, reason:'sold_out'|'not_found'|'error'} */
    placeOrder: async function (opts) {
      var qty = Math.max(1, parseInt(opts.qty || 1, 10));
      var userId = opts.user_id || "guest";
      var dtype = opts.delivery_type === "Pickup" ? "Pickup" : "Delivery";

      if (S.isSupabaseMode()) {
        /* atomic RPC — single call, server handles the full quantity */
        var ids = [];
        try {
          var r = await S.rest("/rpc/place_order", {
            method: "POST",
            body: {
              p_user_id: userId,
              p_schedule_id: opts.schedule_id,
              p_delivery_type: dtype,
              p_qty: qty
            }
          });
          if (!r || r.status === "failed") return { ok: false, reason: "sold_out" };
          if (r.status === "error") return { ok: false, reason: "not_found" };
          /* fetch the rows we just created for their ids */
          var mine = await sbGet("orders",
            "user_id=eq." + encodeURIComponent(userId) +
            "&schedule_id=eq." + encodeURIComponent(opts.schedule_id) +
            "&order=created_at.desc&limit=" + qty);
          mine.forEach(function (o) { ids.push(o.id); });
          var left = await this.portionsLeft(opts.schedule_id);
          /* server-computed money split, for the confirmation screen */
          return { ok: true, order_ids: ids, portions_left: left,
            receipt: {
              total_cents: Number(r.total_cents) || 0,
              platform_fee_cents: Number(r.platform_fee_cents) || 0,
              chef_payout_cents: Number(r.chef_payout_cents) || 0
            } };
        } catch (e) {
          return { ok: false, reason: "error", message: String(e).slice(0, 120) };
        }
      }

      /* demo: single synchronous block = atomic in one thread.
         Computes the same per-portion money split as the RPC. */
      var st = loadStore();
      var sch = st.schedules.find(function (s) { return s.id === opts.schedule_id; });
      if (!sch) return { ok: false, reason: "not_found" };
      if (sch.sold_count + qty > sch.max_capacity) {
        return { ok: false, reason: "sold_out" };
      }
      var dish = st.dishes.find(function (d) { return d.id === sch.dish_id; }) || {};
      var chef = st.chefs.find(function (c) { return c.id === dish.chef_id; }) || {};
      var split = splitCents(dish.price || 0,
        chef.commission_rate == null ? 0.10 : chef.commission_rate);
      var group = demoId("grp");
      var orderIds = [];
      for (var j = 0; j < qty; j++) {
        var oid = demoId("ord");
        st.orders.push({
          id: oid, group_id: group, user_id: userId,
          schedule_id: sch.id, delivery_type: dtype, qty: 1,
          status: "Pending Kitchen Approval",
          total_cents: split.total_cents,
          platform_fee_cents: split.platform_fee_cents,
          chef_payout_cents: split.chef_payout_cents,
          created_at: new Date().toISOString()
        });
        orderIds.push(oid);
      }
      sch.sold_count += qty;
      saveStore(st);
      return { ok: true, order_ids: orderIds,
               portions_left: Math.max(0, sch.max_capacity - sch.sold_count),
               receipt: {
                 total_cents: split.total_cents * qty,
                 platform_fee_cents: split.platform_fee_cents * qty,
                 chef_payout_cents: split.chef_payout_cents * qty
               } };
    },

    myOrders: async function (userId) {
      if (S.isSupabaseMode()) {
        var rows = await sbGet("orders",
          "user_id=eq." + encodeURIComponent(userId) + "&order=created_at.desc");
        for (var i = 0; i < rows.length; i++) {
          var sch = await this.getSchedule(rows[i].schedule_id);
          rows[i].schedule = sch;
        }
        return rows;
      }
      var st = loadStore();
      return st.orders
        .filter(function (o) { return o.user_id === userId; })
        .map(function (o) {
          var c = Object.assign({}, o);
          var sch = st.schedules.find(function (s) { return s.id === o.schedule_id; });
          c.schedule = sch ? enrich(st, sch) : null;
          return c;
        })
        .sort(function (a, b) { return b.created_at.localeCompare(a.created_at); });
    },

    /* --- cart (always local; keyed by schedule+delivery) --- */
    getCart: function () {
      try {
        return JSON.parse(localStorage.getItem(S.CART_KEY) || "[]");
      } catch (e) { return []; }
    },
    saveCart: function (cart) {
      localStorage.setItem(S.CART_KEY, JSON.stringify(cart));
    },
    addToCart: function (item) {
      /* item: {schedule_id, qty, delivery_type} */
      var cart = this.getCart();
      var key = item.schedule_id + "|" + item.delivery_type;
      var found = cart.find(function (c) { return c.key === key; });
      if (found) found.qty += Math.max(1, parseInt(item.qty || 1, 10));
      else cart.push({ key: key, schedule_id: item.schedule_id,
        qty: Math.max(1, parseInt(item.qty || 1, 10)),
        delivery_type: item.delivery_type === "Pickup" ? "Pickup" : "Delivery" });
      this.saveCart(cart);
      return cart;
    },
    updateCartQty: function (key, qty) {
      var cart = this.getCart();
      var it = cart.find(function (c) { return c.key === key; });
      if (it) { it.qty = Math.max(1, parseInt(qty || 1, 10)); this.saveCart(cart); }
      return cart;
    },
    removeFromCart: function (key) {
      var cart = this.getCart().filter(function (c) { return c.key !== key; });
      this.saveCart(cart);
      return cart;
    },
    clearCart: function () { this.saveCart([]); return []; },
    cartCount: function () {
      return this.getCart().reduce(function (n, c) { return n + c.qty; }, 0);
    },

    /* --- Stripe checkout ---
       startCheckout({order_ids, amount_cents, currency, success_url, cancel_url})
       Live mode: calls the create-checkout edge function -> {url, id}.
                  Redirect the browser to url (Stripe's hosted page).
       Demo mode: returns {demo:true} — the UI renders the simulated
                  checkout page instead (no network, no keys needed). */
    startCheckout: async function (opts) {
      var ids = opts.order_ids || [];
      var cents = Math.round(Number(opts.amount_cents) || 0);
      if (S.isSupabaseMode()) {
        var fn = S.config.SUPABASE_URL.replace(/\/$/, "") +
          "/functions/v1/create-checkout";
        var res = await fetch(fn, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "apikey": S.config.SUPABASE_ANON_KEY,
            "Authorization": "Bearer " + S.config.SUPABASE_ANON_KEY
          },
          body: JSON.stringify({
            order_ids: ids,
            amount_cents: cents,
            currency: opts.currency || "cad",
            success_url: opts.success_url,
            cancel_url: opts.cancel_url
          })
        });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) throw new Error(data.error || ("checkout failed: " + res.status));
        return data; // {url, id}
      }
      return { demo: true };
    },

    /* Called on page boot: if the customer just returned from Stripe
       (?paid=1&session_id=...), report it so the UI can show success.
       Live mode: the stripe-webhook already marked orders Confirmed.
       The ?paid params are stripped from the URL. */
    confirmOrderFromSession: async function () {
      var q = new URLSearchParams(window.location.search);
      if (q.get("canceled") === "1") {
        window.history.replaceState({}, "", window.location.pathname);
        return { canceled: true };
      }
      var sid = q.get("session_id");
      if (q.get("paid") !== "1" || !sid) return null;
      window.history.replaceState({}, "", window.location.pathname);
      return { ok: true, session_id: sid, demo: q.get("demo") === "1" };
    },

    /* Demo mode only: mark orders Confirmed after the simulated payment. */
    demoConfirmPayment: function (orderIds) {
      if (S.isSupabaseMode()) return false;
      var st = loadStore();
      st.orders.forEach(function (o) {
        if (orderIds.indexOf(o.id) !== -1) {
          o.status = "Confirmed";
          o.payment_status = "paid";
        }
      });
      saveStore(st);
      return true;
    }
  };
})();
