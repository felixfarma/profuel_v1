// app/static/js/diary_meal_bars.js
(function () {
  const DATE_ISO = new Date().toISOString().slice(0, 10);
  const MEAL_KEY = "desayuno"; // de momento solo desayuno (podemos generalizar luego)

  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const pct = (v, t) => (t > 0 ? (v / t) * 100 : 0);
  const fmt0 = (x) => (Number.isFinite(+x) ? (+x).toFixed(0) : "0");

  // colores Bootstrap: info (carbs), success (pro), warning (fat)
  const splitDefault = 0.25; // objetivo desayuno = 25% del día cuando no venga especificado

  const el = (id) => document.getElementById(id);

  function macroKcal({ carbs = 0, protein = 0, fats = 0, calories = 0 }) {
    const kc = Number(carbs) * 4;
    const kp = Number(protein) * 4;
    const kf = Number(fats) * 9;
    const total = calories > 0 ? calories : kc + kp + kf;
    return { kc, kp, kf, total: total || 0.0001 };
  }

  function stackedBar(item) {
    const { kc, kp, kf, total } = macroKcal(item);
    const pc = clamp((kc / total) * 100, 0, 100);
    const pp = clamp((kp / total) * 100, 0, 100);
    const pf = clamp((kf / total) * 100, 0, 100);

    return `
      <div class="d-flex align-items-center justify-content-between small">
        <span class="text-truncate me-2" title="${item.name || ""}">${item.name || ""}</span>
        <span class="text-muted">${fmt0(item.calories)} kcal</span>
      </div>
      <div class="d-flex w-100" style="height:10px;border-radius:6px;overflow:hidden;">
        <div class="bg-info" style="width:${pc}%"></div>
        <div class="bg-success" style="width:${pp}%"></div>
        <div class="bg-warning" style="width:${pf}%"></div>
      </div>
      <div class="small text-muted mb-2">
        C ${fmt0(item.carbs)} g · P ${fmt0(item.protein)} g · G ${fmt0(item.fats)} g
      </div>
    `;
  }

  function barLine(label, val, tgt, unit) {
    const p = clamp(pct(val, tgt), 0, 200);
    const cls = p <= 105 ? "bg-success" : p <= 120 ? "bg-warning" : "bg-danger";
    return `
      <div class="mb-2">
        <div class="d-flex justify-content-between small">
          <span>${label}</span>
          <span>${fmt0(val)}${unit} / ${fmt0(tgt)}${unit}</span>
        </div>
        <div class="progress" style="height:10px">
          <div class="progress-bar ${cls}" role="progressbar" style="width:${clamp(p,0,100)}%"></div>
        </div>
      </div>
    `;
  }

  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) return null;
    try { return await r.json(); } catch { return null; }
  }

  // Normaliza una entrada de comida de /api/diary/day
  function normalizeMeal(m) {
    return {
      meal_type: (m.meal_type || m.type || "").toLowerCase(),
      name: m.food?.name || m.name || "",
      calories: Number(m.calories || m.kcal || 0),
      carbs: Number(m.carbs || m.cho_g || 0),
      protein: Number(m.protein || m.pro_g || 0),
      fats: Number(m.fats || m.fat_g || 0),
    };
  }

  function sumMeals(items) {
    return items.reduce((acc, it) => {
      acc.calories += it.calories;
      acc.carbs += it.carbs;
      acc.protein += it.protein;
      acc.fats += it.fats;
      return acc;
    }, { calories: 0, carbs: 0, protein: 0, fats: 0 });
  }

  function pickTargetsForBreakfast(overview) {
    // 1) si viene objetivo específico por desayuno
    const ms = overview?.meals_summary || overview?.meals || null;
    if (ms && ms[MEAL_KEY]?.targets) return ms[MEAL_KEY].targets;

    // 2) si viene un targets_day, repartir 25%
    const td = overview?.targets_day || overview?.targets || null;
    if (td) {
      return {
        kcal: td.kcal * splitDefault,
        carbs: td.carbs * splitDefault,
        protein: td.protein * splitDefault,
        fats: td.fats * splitDefault,
      };
    }
    // 3) fallback vacío
    return { kcal: 0, carbs: 0, protein: 0, fats: 0 };
  }

  function renderMealBars(actual, targets) {
    const wrap = el("meal-bars");
    const hdr = el("mealHeaderTotals");
    if (!wrap) return;

    hdr.textContent = `${fmt0(actual.calories)} / ${fmt0(targets.kcal)} kcal`;

    wrap.innerHTML = [
      barLine("Kcal", actual.calories, targets.kcal, ""),
      barLine("Carbs", actual.carbs,    targets.carbs,   " g"),
      barLine("Proteínas", actual.protein, targets.protein, " g"),
      barLine("Grasas", actual.fats,    targets.fats,    " g"),
    ].join("");
  }

  function renderIngredientComposition(list) {
    const box = el("meal-ingredients");
    if (!box) return;

    if (!list.length) {
      box.innerHTML = `<div class="text-muted">Sin ingredientes.</div>`;
      return;
    }
    box.innerHTML = list.map(stackedBar).join("");
  }

  async function refreshBars() {
    const [overview, diary] = await Promise.all([
      fetchJSON(`/api/day/overview?date=${DATE_ISO}`),
      fetchJSON(`/api/diary/day?date=${DATE_ISO}`),
    ]);

    const meals = (diary?.meals || diary?.items || []).map(normalizeMeal);
    const breakfast = meals.filter(m => m.meal_type === MEAL_KEY);

    // Pintar composición por ingrediente
    renderIngredientComposition(breakfast);

    // Totales del desayuno + objetivos
    const actual = sumMeals(breakfast);
    const targets = pickTargetsForBreakfast(overview?.data || overview);

    renderMealBars(actual, targets);
  }

  // Refrescos cuando el diario cambia
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === "string" ? args[0] : (args[0]?.url || "");
    const method = (args[1]?.method || "GET").toUpperCase();
    const mut = url.startsWith("/api/diary/") && method !== "GET";
    const resp = await origFetch.apply(this, args);
    if (mut) setTimeout(refreshBars, 100);
    return resp;
  };
  window.addEventListener("diary:changed", () => setTimeout(refreshBars, 50));

  document.addEventListener("DOMContentLoaded", refreshBars);
})();
