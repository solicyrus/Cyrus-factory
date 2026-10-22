/* =====================================================================
   Chef App v1 — sample data (DEMO seed + Supabase seed rows)
   6 curated Victoria chefs. Prices/capacities here are the single
   source of truth in demo mode; the same rows live in
   supabase-schema.sql for live mode. No fake numbers: sold_count
   values below are opening state, updated for real on every order.
   ===================================================================== */

window.CHEFAPP = window.CHEFAPP || {};

window.CHEFAPP.WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday",
  "Thursday", "Friday", "Saturday"];

window.CHEFAPP.seed = {
  chefs: [
    {
      id: "chef-sara", name: "Chef Sara", cuisine: "Persian", emoji: "👩‍🍳",
      bio: "Third-generation home cook from Tehran. Every stew starts before sunrise.",
      checks: { foodsafe: true, island_health: true, insurance: true, tasting: true },
      commission_rate: 0.10
    },
    {
      id: "chef-arjun", name: "Chef Arjun", cuisine: "Indian", emoji: "👨‍🍳",
      bio: "Tandoor master from Old Delhi. His marinades rest a full 24 hours.",
      checks: { foodsafe: true, island_health: true, insurance: false, tasting: true },
      commission_rate: 0.10
    },
    {
      id: "chef-fatima", name: "Chef Fatima", cuisine: "Moroccan", emoji: "👩‍🍳",
      bio: "Cooks the way Fez taught her — clay tagines, saffron, patience.",
      checks: { foodsafe: true, island_health: false, insurance: false, tasting: true },
      commission_rate: 0.10
    },
    {
      id: "chef-marco", name: "Chef Marco", cuisine: "Italian", emoji: "👨‍🍳",
      bio: "Umbrian risotto obsessive. Eighteen minutes of stirring, never less.",
      checks: { foodsafe: true, island_health: true, insurance: true, tasting: false },
      commission_rate: 0.10
    },
    {
      id: "chef-yuki", name: "Chef Yuki", cuisine: "Japanese", emoji: "🧑‍🍳",
      bio: "Ten years in Osaka sushi counters before Victoria. Fish first, always.",
      checks: { foodsafe: true, island_health: false, insurance: false, tasting: false },
      commission_rate: 0.10
    },
    {
      id: "chef-diego", name: "Chef Diego", cuisine: "Mexican", emoji: "👨‍🍳",
      bio: "Ensenada street-cart roots. Charred lime and chipotle crema on everything.",
      checks: { foodsafe: true, island_health: true, insurance: false, tasting: true },
      commission_rate: 0.10
    }
  ],

  dishes: [
    {
      id: "dish-ghormeh", chef_id: "chef-sara",
      name: "Authentic Persian Ghormeh Sabzi", short_name: "Ghormeh Sabzi Dish",
      description: "Slow-simmered herb stew with dried lime, kidney beans and lamb.",
      story: "From Sara's grandmother's kitchen in Tehran — dried limes, kidney beans and lamb, simmered low for hours exactly as it has been made for three generations.",
      price: 35, emoji: "🍲",
      gradient: "radial-gradient(circle at 25% 20%, rgba(45,106,62,.55), transparent 60%), radial-gradient(circle at 80% 90%, rgba(212,175,55,.18), transparent 55%), linear-gradient(140deg, #0e1f12 0%, #090d09 70%)"
    },
    {
      id: "dish-fesenjan", chef_id: "chef-sara",
      name: "Royal Chicken Fesenjan", short_name: "Fesenjan",
      description: "Walnuts and pomegranate molasses, chicken, saffron rice.",
      story: "Walnuts ground by hand every Saturday morning — the dish Sara's family serves at Nowruz, sweet, dark and unforgettable.",
      price: 38, emoji: "🍗",
      gradient: "radial-gradient(circle at 70% 15%, rgba(120,50,60,.5), transparent 60%), radial-gradient(circle at 20% 85%, rgba(212,175,55,.16), transparent 55%), linear-gradient(140deg, #1c0e12 0%, #0c0708 70%)"
    },
    {
      id: "dish-tikka", chef_id: "chef-arjun",
      name: "Old Delhi Chicken Tikka Masala", short_name: "Tikka Masala",
      description: "24-hour marinated chicken, tandoor-charred, creamy tomato sauce.",
      story: "Hung curd, Kashmiri chilies and a blazing tandoor — Arjun's father's recipe from the lanes of Chandni Chowk.",
      price: 28, emoji: "🍛",
      gradient: "radial-gradient(circle at 70% 15%, rgba(196,90,20,.5), transparent 60%), radial-gradient(circle at 20% 85%, rgba(212,175,55,.15), transparent 55%), linear-gradient(140deg, #221006 0%, #0d0805 70%)"
    },
    {
      id: "dish-butter", chef_id: "chef-arjun",
      name: "Midnight Butter Chicken", short_name: "Butter Chicken",
      description: "Silky makhani sauce, charcoal-kissed chicken, basmati.",
      story: "The late-night Delhi classic — tomatoes and butter simmered down until the sauce coats the spoon like velvet.",
      price: 30, emoji: "🫕",
      gradient: "radial-gradient(circle at 30% 20%, rgba(200,110,30,.5), transparent 60%), linear-gradient(140deg, #201005 0%, #0d0704 70%)"
    },
    {
      id: "dish-tagine", chef_id: "chef-fatima",
      name: "Atlas Mountain Lamb Tagine", short_name: "Lamb Tagine",
      description: "Preserved lemon, green olives, saffron, clay-pot steamed lamb.",
      story: "Preserved lemon and saffron, steamed slowly in the clay tagine Fatima carried with her from Fez.",
      price: 32, emoji: "🥘",
      gradient: "radial-gradient(circle at 30% 25%, rgba(178,74,32,.5), transparent 60%), radial-gradient(circle at 75% 80%, rgba(212,175,55,.14), transparent 55%), linear-gradient(140deg, #241009 0%, #0e0705 70%)"
    },
    {
      id: "dish-risotto", chef_id: "chef-marco",
      name: "Black Truffle Risotto", short_name: "Truffle Risotto",
      description: "Carnaroli rice, Umbrian black truffle, 24-month Parmigiano.",
      story: "Stirred for exactly eighteen minutes, finished with Umbrian black truffle shaved tableside-thin. Marco accepts no shortcuts.",
      price: 38, emoji: "🍝",
      gradient: "radial-gradient(circle at 75% 20%, rgba(122,60,32,.5), transparent 60%), radial-gradient(circle at 15% 80%, rgba(90,110,50,.25), transparent 55%), linear-gradient(140deg, #1d1208 0%, #0c0705 70%)"
    },
    {
      id: "dish-omakase", chef_id: "chef-yuki",
      name: "Victoria Omakase Box", short_name: "Omakase Box",
      description: "Eight pieces from the morning's best catch, seasoned rice.",
      story: "Eight pieces chosen each dawn from the day's best catch — Yuki trained ten years in Osaka before bringing omakase to Victoria.",
      price: 45, emoji: "🍱",
      gradient: "radial-gradient(circle at 25% 20%, rgba(40,70,120,.55), transparent 60%), radial-gradient(circle at 80% 80%, rgba(180,50,50,.22), transparent 55%), linear-gradient(140deg, #0a1220 0%, #060809 70%)"
    },
    {
      id: "dish-tacos", chef_id: "chef-diego",
      name: "Baja Fish Tacos (4 pc)", short_name: "Fish Tacos",
      description: "Crispy lingcod, chipotle crema, charred lime, corn tortillas.",
      story: "Diego's Ensenada street-cart recipe — crispy lingcod, chipotle crema and a squeeze of charred lime, exactly like the malecón at midnight.",
      price: 24, emoji: "🌮",
      gradient: "radial-gradient(circle at 70% 25%, rgba(210,110,30,.5), transparent 60%), radial-gradient(circle at 20% 80%, rgba(160,40,40,.28), transparent 55%), linear-gradient(140deg, #200f06 0%, #0d0704 70%)"
    }
  ],

  /* weekday: 0=Sunday..6=Saturday. sold_count = opening state (demo). */
  schedules: [
    { id: "sch-1", dish_id: "dish-ghormeh", weekday: 5, label: "FRIDAY MENU",    max_capacity: 10, sold_count: 7 },
    { id: "sch-2", dish_id: "dish-fesenjan", weekday: 6, label: "SATURDAY MENU",  max_capacity: 8,  sold_count: 0 },
    { id: "sch-3", dish_id: "dish-tikka",   weekday: 2, label: "TUESDAY MENU",   max_capacity: 12, sold_count: 3 },
    { id: "sch-4", dish_id: "dish-butter",  weekday: 5, label: "FRIDAY MENU",    max_capacity: 10, sold_count: 1 },
    { id: "sch-5", dish_id: "dish-tagine",  weekday: 6, label: "SATURDAY MENU",  max_capacity: 8,  sold_count: 0 },
    { id: "sch-6", dish_id: "dish-risotto", weekday: 4, label: "THURSDAY MENU",  max_capacity: 10, sold_count: 4 },
    { id: "sch-7", dish_id: "dish-omakase", weekday: 3, label: "WEDNESDAY MENU", max_capacity: 6,  sold_count: 6 },
    { id: "sch-8", dish_id: "dish-tacos",   weekday: 0, label: "SUNDAY MENU",    max_capacity: 15, sold_count: 5 }
  ]
};

window.CHEFAPP.CHECK_LABELS = {
  foodsafe: "FoodSafe Level 1",
  approved_kitchen: "Approved commercial/commissary kitchen (no home kitchens)",
  island_health: "Island Health operating permit",
  business_licence: "City of Victoria business licence",
  insurance: "Liability insurance",
  labels: "CFIA-compliant labels (allergens, bilingual)",
  tasting: "Tasting session with Cyrus"
};
