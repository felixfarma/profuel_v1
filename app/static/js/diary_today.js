(function () {
  // ---------- Utils ----------
  const fmt0 = (n) => (Math.round(Number(n || 0))).toString();
  const fmt1 = (n) => (Math.round(Number(n || 0) * 10) / 10).toString();
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const $ = (id) => document.getElementById(id);
  const unwrap = (x) => (x && typeof x === "object" && "data" in x ? x.data : x);
  const toNum = (x) => { const n = Number(x); return isFinite(n) ? n : 0; };
  const show = (el, v) => { if (!el) return; el.classList.toggle("d-none", !v); el.style.display = v ? "" : "none"; };

  // ---------- Fecha (?date=YYYY-MM-DD opcional) ----------
  const urlDate = new URLSearchParams(location.search).get("date");
  const today = (urlDate && /^\d{4}-\d{2}-\d{2}$/.test(urlDate))
    ? urlDate : new Date().toISOString().slice(0, 10);

  const todaySpan = $("todayDate");
  if (todaySpan) {
    const d = new Date(today + "T00:00:00");
    todaySpan.textContent = d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
  }

  // ---------- Estado ----------
  let currentMeal = (location.hash?.replace("#", "") || "desayuno").toLowerCase();
  const MEAL_NAMES = { desayuno: "Desayuno", almuerzo: "Almuerzo", comida: "Comida", merienda: "Merienda", cena: "Cena" };
  const MEALS = Object.keys(MEAL_NAMES);

  // ---------- Elementos ----------
  const els = {
    btnReload: $("btnReload"),
    tabs: document.querySelectorAll("#mealTabs .nav-link"),
    goalMealName: $("goalMealName"),
    goalMini: $("goalMini"),
    goalBars: $("goalBars"),
    mealListTitle: $("mealListTitle"),
    mealEmpty: $("mealEmpty"),
    mealList: $("mealList"),
    mealTotals: $("mealTotals"),
    btnAddItem: $("btnAddItem"),
    // modal
    editModalEl: $("editModal"),
    editForm: $("editForm"),
    editMealId: $("editMealId"),
    editFoodName: $("editFoodName"),
    editQty: $("editQty"),
    editUnit: $("editUnit"),
    // estrategia (badge + copy)
    strategyBadge: $("strategyBadge"),
    badgePre: $("badgePre"),
    badgePost: $("badgePost"),
    badgeTime: $("badgeTime"),
    strategyCopy: $("strategyCopy"),
  };
  const bsModal = els.editModalEl ? new bootstrap.Modal(els.editModalEl) : null;

  // ---------- Normalizadores ----------
  function normMacros(x) {
    if (!x || typeof x !== "object") return { kcal: 0, carbs: 0, protein: 0, fats: 0 };
    x = unwrap(x);
    const kcalField = x.kcal ?? x.calories ?? x.kcals ?? x.kcal_total ?? x.energy_kcal ?? 0;
    const kcal = typeof kcalField === "object" ? toNum(kcalField.total ?? kcalField.target ?? 0) : toNum(kcalField);
    const carbs   = toNum(x.carbs ?? x.cho_g ?? x.carbohydrates_g);
    const protein = toNum(x.protein ?? x.pro_g ?? x.proteins_g);
    const fats    = toNum(x.fats ?? x.fat ?? x.fat_g ?? x.lipids_g);
    return { kcal, carbs, protein, fats };
  }

  function normMealItem(m) {
    m = unwrap(m);
    const kcal    = toNum(m.calories ?? m.kcal);
    const carbs   = toNum(m.carbs ?? m.cho_g);
    const protein = toNum(m.protein ?? m.pro_g);
    const fats    = toNum(m.fats ?? m.fat_g ?? m.fat);
    return {
      id: m.id,
      meal_type: (m.meal_type || m.type || "").toLowerCase(),
      quantity: m.quantity ?? m.qty ?? 0,
      unit: (m.unit || "g"),
      calories: kcal,
      carbs, protein, fats,
      food: m.food || (m.food_name ? { name: m.food_name } : null),
    };
  }

  // ---------- Objetivos por comida desde OVERVIEW ----------
  function computeByMealFromOverview(ovData) {
    // 1) Prioridad: dinámico
    const dyn = ovData?.by_meal_dynamic;
    if (dyn && typeof dyn === "object") {
      const byMeal = {};
      for (const k of Object.keys(dyn)) {
        const v = dyn[k] || {};
        byMeal[k.toLowerCase()] = {
          kcal:    toNum(v.kcal),
          carbs:   toNum(v.cho_g ?? v.carbs),
          protein: toNum(v.pro_g ?? v.protein),
          fats:    toNum(v.fat_g ?? v.fats),
        };
      }
      return { byMeal, tolerance: { per_meal: { lower: -0.08, upper: 0.08 } } };
    }

    // 2) Fallback: reparto por pesos
    const t = ovData?.rings?.target || {};
    const weights = ovData?.weights || {};
    const daily = {
      kcal:    toNum(t.kcal),
      carbs:   toNum(t.cho_g),
      protein: toNum(t.pro_g),
      fats:    toNum(t.fat_g),
    };
    const byMeal = {};
    for (const m of MEALS) {
      const w = toNum(weights[m] ?? 0);
      byMeal[m] = {
        kcal: daily.kcal * w,
        carbs: daily.carbs * w,
        protein: daily.protein * w,
        fats: daily.fats * w,
      };
    }
    return { byMeal, tolerance: { per_meal: { lower: -0.08, upper: 0.08 } } };
  }

  // ---------- Estrategia (badge) ----------
  function renderStrategyBadge(strategy) {
    if (!strategy) { show(els.strategyBadge, false); show(els.strategyCopy, false); return; }
    if (els.badgePre)  els.badgePre.textContent  = `pre: ${String(strategy.pre_meal || "—")}`;
    if (els.badgePost) els.badgePost.textContent = `post: ${String(strategy.post_meal || "—")}`;
    if (els.badgeTime) els.badgeTime.textContent = `entreno ${String(strategy.primary_session_time || "—")}`;
    show(els.strategyBadge, true);
    show(els.strategyCopy, true);
  }

  // ---------- Barras ----------
  function renderBars(container, goal, actual, tolerance) {
    if (!container) return;
    container.innerHTML = "";

    const tol = (tolerance?.per_meal) ? tolerance.per_meal : { lower: -0.08, upper: 0.08 };
    const within = (g, a) => {
      const lo = (g || 0) * (1 + Number(tol.lower || 0));
      const hi = (g || 0) * (1 + Number(tol.upper || 0));
      return a >= lo && a <= hi;
    };
    const color = (g, a) => {
      if (!g) return "bg-secondary";
      if (within(g, a)) return "bg-success";
      const r = g > 0 ? a / g : 0;
      if (r > 0.85 && r < 1.15) return "bg-warning text-dark";
      return "bg-danger";
    };
    const row = (label, g, a) => {
      const pct = g > 0 ? clamp((a / g) * 100, 0, 200) : 0;
      const div = document.createElement("div");
      div.className = "mb-2";
      div.innerHTML = `
        <div class="d-flex justify-content-between small">
          <span>${label}</span>
          <span>${fmt0(a)} / ${fmt0(g)}</span>
        </div>
        <div class="progress" style="height: 10px;">
          <div class="progress-bar ${color(g, a)}" style="width:${pct}%;" role="progressbar"
               aria-valuenow="${fmt0(a)}" aria-valuemin="0" aria-valuemax="${fmt0(g)}"></div>
        </div>`;
      return div;
    };

    container.append(
      row("Kcal", Number(goal.kcal || 0), Number(actual.kcal || 0)),
      row("Carbs (g)", Number(goal.carbs || 0), Number(actual.carbs || 0)),
      row("Proteínas (g)", Number(goal.protein || 0), Number(actual.protein || 0)),
      row("Grasas (g)", Number(goal.fats || 0), Number(actual.fats || 0)),
    );
  }

  // ---------- Fetch ----------
  async function fetchOverview() {
    const r = await fetch(`/api/day/overview?date=${encodeURIComponent(today)}`);
    if (!r.ok) throw new Error("overview error");
    return unwrap(await r.json());
  }

  async function fetchMealsOfDay() {
    const r = await fetch(`/api/meals?date=${today}`);
    if (!r.ok) throw new Error("meals error");
    const j = unwrap(await r.json());
    const raw = Array.isArray(j) ? j : (Array.isArray(j.meals) ? j.meals : (Array.isArray(j.items) ? j.items : []));
    return raw.map(normMealItem);
  }

  // ---------- Totales ----------
  function totalsOf(items) {
    const tk = items.reduce((a, m) => a + (m.calories || 0), 0);
    const tc = items.reduce((a, m) => a + (m.carbs || 0), 0);
    const tp = items.reduce((a, m) => a + (m.protein || 0), 0);
    const tf = items.reduce((a, m) => a + (m.fats || 0), 0);
    return { kcal: tk, carbs: tc, protein: tp, fats: tf };
  }

  // ---------- Render lista ----------
  function renderMealList(listEl, emptyEl, items) {
    listEl.innerHTML = "";
    if (!items.length) { emptyEl.classList.remove("d-none"); return; }
    emptyEl.classList.add("d-none");

    for (const it of items) {
      const li = document.createElement("li");
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      li.innerHTML = `
        <div class="me-3">
          <div class="fw-semibold">${it.food?.name || "Alimento"}</div>
          <div class="text-muted small">
            ${fmt1(it.quantity)} ${it.unit || "g"} · ${fmt0(it.calories)} kcal
            — C:${fmt1(it.carbs)}g · P:${fmt1(it.protein)}g · G:${fmt1(it.fats)}g
          </div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-secondary" data-edit="${it.id}">Editar</button>
          <button class="btn btn-sm btn-outline-danger" data-del="${it.id}">Eliminar</button>
        </div>`;

      // abrir modal edición
      li.querySelector(`[data-edit="${it.id}"]`).addEventListener("click", () => {
        els.editMealId.value = String(it.id);
        els.editFoodName.value = it.food?.name || "Alimento";
        els.editQty.value = it.quantity ?? 0;
        els.editUnit.value = it.unit || "g";
        bsModal?.show();
      });

      // eliminar
      li.querySelector(`[data-del="${it.id}"]`).addEventListener("click", async () => {
        if (!confirm("¿Eliminar este alimento?")) return;
        const r = await fetch(`/api/meals/${it.id}`, { method: "DELETE" });
        if (!r.ok) { alert("No se pudo eliminar."); return; }
        await loadAll();
      });

      listEl.appendChild(li);
    }
  }

  // ---------- Carga completa ----------
  async function loadAll() {
    try {
      // pestañas y textos
      els.tabs.forEach(btn => {
        const m = btn.getAttribute("data-meal");
        const active = (m === currentMeal);
        btn.classList.toggle("active", active);
        btn.setAttribute("aria-selected", active ? "true" : "false");
      });
      els.goalMealName.textContent = MEAL_NAMES[currentMeal] || "Comida";
      els.mealListTitle.textContent = MEAL_NAMES[currentMeal] || "Comida";

      // 1) Overview (y estrategia si existe)
      const ov = await fetchOverview();
      renderStrategyBadge(ov?.strategy || null);

      // 2) Objetivos por comida (dinámico → fallback weights)
      const goalsData = computeByMealFromOverview(ov);
      const goal = goalsData.byMeal[currentMeal] || { kcal: 0, carbs: 0, protein: 0, fats: 0 };
      els.goalMini.textContent = `K:${fmt0(goal.kcal)} · C:${fmt0(goal.carbs)}g · P:${fmt0(goal.protein)}g · G:${fmt0(goal.fats)}g`;

      // 3) Items y totales
      const allMeals = await fetchMealsOfDay();
      const mealsOfType = allMeals.filter(m => (m.meal_type || "").toLowerCase() === currentMeal);
      renderMealList(els.mealList, els.mealEmpty, mealsOfType);

      const tot = totalsOf(mealsOfType);
      els.mealTotals.textContent = `Kcal ${fmt0(tot.kcal)} · C ${fmt1(tot.carbs)}g · P ${fmt1(tot.protein)}g · G ${fmt1(tot.fats)}g`;

      renderBars(els.goalBars, goal, tot, goalsData.tolerance);
    } catch (e) {
      console.error(e);
      alert("No se pudieron cargar los datos del día.");
    }
  }

  // ---------- Eventos ----------
  els.btnReload?.addEventListener("click", loadAll);
  els.tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const m = btn.getAttribute("data-meal");
      if (!m) return;
      currentMeal = m.toLowerCase();
      location.hash = currentMeal;
      loadAll();
    });
  });

  // Añadir alimento (con prechequeo opcional de macros del alimento)
  els.btnAddItem?.addEventListener("click", async () => {
    try {
      const foodId = Number(prompt("ID del alimento (food_id):", "")) || 0;
      if (!foodId) return;

      // Prechequear macros del alimento (opcional)
      try {
        const rf = await fetch(`/api/foods/${foodId}`);
        if (rf.ok) {
          const jf = unwrap(await rf.json());
          const mm = normMacros(jf);
          if ((mm.kcal + mm.carbs + mm.protein + mm.fats) <= 0) {
            alert("Este alimento no tiene macros en la base. No se puede añadir.");
            return;
          }
        }
      } catch {}

      const quantity = Number(prompt("Cantidad (p.ej. 100):", "100")) || 0;
      if (!quantity || quantity <= 0) return;
      let unit = (prompt('Unidad ("g", "ml" o "unidad"):', "g") || "g").toLowerCase().trim();
      if (!["g", "ml", "unidad"].includes(unit)) unit = "g";

      const payload = { food_id: foodId, quantity, unit, meal_type: currentMeal, date: today };
      const r = await fetch(`/api/meals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        alert(j?.message || "No se pudo añadir el alimento.");
        return;
      }
      await loadAll();
    } catch (e) {
      console.error(e);
      alert("Error inesperado al añadir alimento.");
    }
  });

  // ---------- Primera carga ----------
  loadAll();
})();
