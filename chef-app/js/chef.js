/* =====================================================================
   Chef App v1 — CHEF backend (second of two API surfaces)
   window.ChefAPI: weekly schedule + per-dish capacity, incoming
   orders (view/confirm), chef verification checklist.
   admin.html reuses this module (listAllOrders / listAllChefs).
   Shares ONE database with js/customer.js:
     - demo mode  -> same localStorage blob (see js/config.js keys)
     - live mode  -> same Supabase tables + atomic place_order RPC
   All methods are async (uniform in both modes). No DOM access here.
   ===================================================================== */

window.ChefAPI = (function () {
  var S = window.CHEFAPP;

  /* ---------------- demo store (shared with customer.js) ---------------- */
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
  function enrichDish(st, sch) {
    var dish = st.dishes.find(function (d) { return d.id === sch.dish_id; }) || {};
    var out = Object.assign({}, sch);
    out.dish = dish;
    out.portions_left = Math.max(0, sch.max_capacity - sch.sold_count);
    return out;
  }
  function demoId(prefix) {
    return prefix + "-" + Date.now().toString(36) +
      Math.random().toString(36).slice(2, 7);
  }

  /* ---------------- supabase helpers ---------------- */
  async function sbGet(table, query) {
    var rows = await S.rest("/" + table + (query ? "?" + query : ""),
      { prefer: "return=representation" });
    return rows || [];
  }

  /* ---------------- public API ---------------- */
  return {
    mode: function () { return S.isSupabaseMode() ? "supabase" : "demo"; },

    /* --- chefs --- */
    listChefs: async function () {
      if (S.isSupabaseMode()) return sbGet("chefs", "order=name");
      return loadStore().chefs;
    },
    getChef: async function (chefId) {
      if (S.isSupabaseMode()) {
        var rows = await sbGet("chefs", "id=eq." + encodeURIComponent(chefId));
        return rows[0] || null;
      }
      return loadStore().chefs.find(function (c) { return c.id === chefId; }) || null;
    },

    /* --- schedule & capacity --- */
    myDishes: async function (chefId) {
      if (S.isSupabaseMode())
        return sbGet("dishes", "chef_id=eq." + encodeURIComponent(chefId) + "&order=name");
      return loadStore().dishes.filter(function (d) { return d.chef_id === chefId; });
    },
    mySchedules: async function (chefId) {
      /* enriched with dish + portions_left, sorted by weekday */
      if (S.isSupabaseMode()) {
        var dishes = await this.myDishes(chefId);
        var ids = dishes.map(function (d) { return d.id; });
        if (!ids.length) return [];
        var rows = await sbGet("daily_schedules",
          "dish_id=in.(" + ids.map(encodeURIComponent).join(",") + ")&order=weekday");
        return rows.map(function (r) {
          var out = Object.assign({}, r);
          out.dish = dishes.find(function (d) { return d.id === r.dish_id; }) || {};
          out.portions_left = Math.max(0, r.max_capacity - r.sold_count);
          return out;
        });
      }
      var st = loadStore();
      var myDishIds = {};
      st.dishes.forEach(function (d) {
        if (d.chef_id === chefId) myDishIds[d.id] = true;
      });
      return st.schedules
        .filter(function (s) { return myDishIds[s.dish_id]; })
        .map(function (s) { return enrichDish(st, s); })
        .sort(function (a, b) { return a.weekday - b.weekday; });
    },
    setCapacity: async function (scheduleId, maxCapacity) {
      var cap = Math.max(0, parseInt(maxCapacity, 10) || 0);
      if (S.isSupabaseMode()) {
        await S.rest("/daily_schedules?id=eq." + encodeURIComponent(scheduleId), {
          method: "PATCH", body: { max_capacity: cap }, prefer: "return=minimal"
        });
        return { ok: true };
      }
      var st = loadStore();
      var sch = st.schedules.find(function (s) { return s.id === scheduleId; });
      if (!sch) return { ok: false, reason: "not_found" };
      /* never silently drop already-sold portions: floor capacity at sold */
      if (cap < sch.sold_count) {
        return { ok: false, reason: "below_sold", sold: sch.sold_count };
      }
      sch.max_capacity = cap;
      saveStore(st);
      return { ok: true };
    },
    addSchedule: async function (opts) {
      /* opts: {dish_id, weekday 0-6, label, max_capacity} */
      var wd = parseInt(opts.weekday, 10);
      if (isNaN(wd) || wd < 0 || wd > 6) return { ok: false, reason: "bad_weekday" };
      var cap = Math.max(1, parseInt(opts.max_capacity, 10) || 1);
      if (S.isSupabaseMode()) {
        var rows = await S.rest("/daily_schedules", {
          method: "POST",
          body: {
            id: demoId("sch"), dish_id: opts.dish_id, weekday: wd,
            label: opts.label || (S.WEEKDAYS[wd] + " MENU").toUpperCase(),
            max_capacity: cap, sold_count: 0
          },
          prefer: "return=representation"
        });
        return { ok: true, schedule: rows[0] };
      }
      var st = loadStore();
      var rec = {
        id: demoId("sch"), dish_id: opts.dish_id, weekday: wd,
        label: opts.label || (S.WEEKDAYS[wd] + " MENU").toUpperCase(),
        max_capacity: cap, sold_count: 0
      };
      st.schedules.push(rec);
      saveStore(st);
      return { ok: true, schedule: rec };
    },

    /* --- orders --- */
    incomingOrders: async function (chefId) {
      /* all orders for this chef's dishes, newest first, with dish/day info */
      if (S.isSupabaseMode()) {
        var dishes = await this.myDishes(chefId);
        var ids = dishes.map(function (d) { return d.id; });
        if (!ids.length) return [];
        var schs = await sbGet("daily_schedules",
          "dish_id=in.(" + ids.map(encodeURIComponent).join(",") + ")");
        var schIds = schs.map(function (s) { return s.id; });
        if (!schIds.length) return [];
        var orders = await sbGet("orders",
          "schedule_id=in.(" + schIds.map(encodeURIComponent).join(",") +
          ")&order=created_at.desc");
        var dishById = {};
        dishes.forEach(function (d) { dishById[d.id] = d; });
        var schById = {};
        schs.forEach(function (s) { schById[s.id] = s; });
        return orders.map(function (o) {
          var s = schById[o.schedule_id] || {};
          o.dish = dishById[s.dish_id] || {};
          o.day = S.WEEKDAYS[s.weekday] || "";
          return o;
        });
      }
      var st = loadStore();
      var myDishIds = {};
      st.dishes.forEach(function (d) {
        if (d.chef_id === chefId) myDishIds[d.id] = d;
      });
      var mySchIds = {};
      st.schedules.forEach(function (s) {
        if (myDishIds[s.dish_id]) mySchIds[s.id] = s;
      });
      return st.orders
        .filter(function (o) { return mySchIds[o.schedule_id]; })
        .map(function (o) {
          var c = Object.assign({}, o);
          var s = mySchIds[o.schedule_id];
          c.dish = myDishIds[s.dish_id];
          c.day = S.WEEKDAYS[s.weekday];
          return c;
        })
        .sort(function (a, b) { return b.created_at.localeCompare(a.created_at); });
    },
    confirmOrder: async function (orderId) {
      if (S.isSupabaseMode()) {
        await S.rest("/orders?id=eq." + encodeURIComponent(orderId), {
          method: "PATCH", body: { status: "Confirmed" }, prefer: "return=minimal"
        });
        return { ok: true };
      }
      var st = loadStore();
      var o = st.orders.find(function (x) { return x.id === orderId; });
      if (!o) return { ok: false, reason: "not_found" };
      o.status = "Confirmed";
      saveStore(st);
      return { ok: true };
    },

    /* --- verification checklist (FoodSafe / Island Health / Insurance / Tasting) --- */
    getChecks: async function (chefId) {
      var chef = await this.getChef(chefId);
      return (chef && chef.checks) || {};
    },
    setCheck: async function (chefId, key, value) {
      var allowed = ["foodsafe", "island_health", "insurance", "tasting"];
      if (allowed.indexOf(key) === -1) return { ok: false, reason: "bad_key" };
      var v = !!value;
      if (S.isSupabaseMode()) {
        var body = {};
        body[key] = v;
        await S.rest("/chefs?id=eq." + encodeURIComponent(chefId), {
          method: "PATCH", body: body, prefer: "return=minimal"
        });
        return { ok: true };
      }
      var st = loadStore();
      var chef = st.chefs.find(function (c) { return c.id === chefId; });
      if (!chef) return { ok: false, reason: "not_found" };
      chef.checks = chef.checks || {};
      chef.checks[key] = v;
      saveStore(st);
      return { ok: true };
    },

    /* --- commission & earnings ---
       Money is recorded per order row at order time (total_cents /
       platform_fee_cents / chef_payout_cents), so rate changes only
       affect NEW orders. Sums treat missing columns as 0. */
    _moneyData: async function () {
      /* orders (money columns) + schedules + dishes, joined client-side */
      if (S.isSupabaseMode()) {
        var orders = await sbGet("orders",
          "select=id,schedule_id,total_cents,platform_fee_cents,chef_payout_cents,created_at&order=created_at.desc");
        var schs = await sbGet("daily_schedules", "select=id,dish_id");
        var dishes = await sbGet("dishes", "select=id,chef_id,short_name,name");
        return { orders: orders, schedules: schs, dishes: dishes };
      }
      var st = loadStore();
      return { orders: st.orders, schedules: st.schedules, dishes: st.dishes };
    },
    _sumForChef: function (data, chefId) {
      var dishChef = {};
      data.dishes.forEach(function (d) { dishChef[d.id] = d.chef_id; });
      var schDish = {};
      data.schedules.forEach(function (s) { schDish[s.id] = s.dish_id; });
      var nameById = {};
      data.dishes.forEach(function (d) {
        nameById[d.id] = d.short_name || d.name || "Dish";
      });
      var out = { gross_cents: 0, fee_cents: 0, payout_cents: 0,
                  order_count: 0, by_dish: {} };
      data.orders.forEach(function (o) {
        if (dishChef[schDish[o.schedule_id]] !== chefId) return;
        out.gross_cents += Number(o.total_cents) || 0;
        out.fee_cents += Number(o.platform_fee_cents) || 0;
        out.payout_cents += Number(o.chef_payout_cents) || 0;
        out.order_count += 1;
        var b = out.by_dish[schDish[o.schedule_id]] ||
          (out.by_dish[schDish[o.schedule_id]] =
            { dish_id: schDish[o.schedule_id], count: 0,
              gross_cents: 0, payout_cents: 0 });
        b.count += 1;
        b.gross_cents += Number(o.total_cents) || 0;
        b.payout_cents += Number(o.chef_payout_cents) || 0;
      });
      out.by_dish = Object.keys(out.by_dish).map(function (id) {
        var b = out.by_dish[id];
        b.name = nameById[id] || "Dish";
        return b;
      }).sort(function (a, b) { return b.payout_cents - a.payout_cents; });
      return out;
    },
    getEarnings: async function (chefId) {
      var data = await this._moneyData();
      return this._sumForChef(data, chefId);
    },
    getCommissionRate: async function (chefId) {
      var chef = await this.getChef(chefId);
      return (chef && chef.commission_rate != null)
        ? Number(chef.commission_rate) : 0.10;
    },
    setCommissionRate: async function (chefId, rate) {
      /* clamp to 0–50%; applies to NEW orders only */
      var r = Math.min(0.50, Math.max(0, Number(rate) || 0));
      if (S.isSupabaseMode()) {
        await S.rest("/chefs?id=eq." + encodeURIComponent(chefId), {
          method: "PATCH", body: { commission_rate: r },
          prefer: "return=minimal"
        });
        return { ok: true, rate: r };
      }
      var st = loadStore();
      var chef = st.chefs.find(function (c) { return c.id === chefId; });
      if (!chef) return { ok: false, reason: "not_found" };
      chef.commission_rate = r;
      saveStore(st);
      return { ok: true, rate: r };
    },
    platformTotals: async function () {
      /* whole-marketplace revenue + per-chef breakdown, one fetch */
      var data = await this._moneyData();
      var chefs = S.isSupabaseMode()
        ? await sbGet("chefs", "select=id,name,commission_rate&order=name")
        : loadStore().chefs;
      var self = this;
      var perChef = chefs.map(function (c) {
        var e = self._sumForChef(data, c.id);
        e.chef_id = c.id;
        e.chef_name = c.name;
        e.rate = (c.commission_rate != null)
          ? Number(c.commission_rate) : 0.10;
        return e;
      });
      var t = { total_gross_cents: 0, total_fee_cents: 0,
                total_payout_cents: 0, order_count: 0 };
      perChef.forEach(function (e) {
        t.total_gross_cents += e.gross_cents;
        t.total_fee_cents += e.fee_cents;
        t.total_payout_cents += e.payout_cents;
        t.order_count += e.order_count;
      });
      t.per_chef = perChef;
      return t;
    },

    /* --- admin views (same tables, wider lens) --- */
    listAllOrders: async function (status) {
      if (S.isSupabaseMode()) {
        var q = "order=created_at.desc";
        if (status && status !== "all")
          q = "status=eq." + encodeURIComponent(status) + "&" + q;
        var rows = await sbGet("orders", q);
        for (var i = 0; i < rows.length; i++) {
          var schs = await sbGet("daily_schedules",
            "id=eq." + encodeURIComponent(rows[i].schedule_id));
          var dishes = schs[0]
            ? await sbGet("dishes", "id=eq." + encodeURIComponent(schs[0].dish_id)) : [];
          rows[i].dish = dishes[0] || {};
          rows[i].day = schs[0] ? (S.WEEKDAYS[schs[0].weekday] || "") : "";
        }
        return rows;
      }
      var st = loadStore();
      return st.orders
        .filter(function (o) { return !status || status === "all" || o.status === status; })
        .map(function (o) {
          var c = Object.assign({}, o);
          var s = st.schedules.find(function (x) { return x.id === o.schedule_id; }) || {};
          var d = st.dishes.find(function (x) { return x.id === s.dish_id; }) || {};
          var ch = st.chefs.find(function (x) { return x.id === d.chef_id; }) || {};
          c.dish = d; c.chef = ch; c.day = S.WEEKDAYS[s.weekday] || "";
          return c;
        })
        .sort(function (a, b) { return b.created_at.localeCompare(a.created_at); });
    },
    listAllChefs: async function () { return this.listChefs(); }
  };
})();
