// app/static/js/home_index.js
(function () {
  const today = new Date().toISOString().slice(0,10);
  const $ = (id) => document.getElementById(id);

  $('todayDate') && ($('todayDate').textContent = today);

  // ---------------- Utils ----------------
  const toNum = (x) => { const n = Number(x); return isFinite(n) ? n : 0; };
  function cap(s){ s = s || ''; return s.charAt(0).toUpperCase() + s.slice(1); }
  function clamp01(x){ return Math.max(0, Math.min(1, x)); }

  // ---------------- Semáforo helpers ----------------
  function ratio(a, b) { return (b > 0) ? (a / b) : 0; }
  function statusKey(value, target, bands) {
    if (!target || target <= 0) return 'secondary';
    const r = ratio(value, target);
    const g = bands.green, a = bands.amber;
    if (r >= g[0] && r <= g[1]) return 'success';
    if (r >= a[0] && r <= a[1]) return 'warning';
    return 'danger';
  }
  function setBarColored(barEl, textEl, value, target, unit, bands) {
    if (!barEl || !textEl) return;
    const pct = target > 0 ? Math.max(0, Math.min(100, (value / target) * 100)) : 0;
    barEl.style.width = pct + '%';
    textEl.textContent = `${Math.round(value)}${unit||''} / ${Math.round(target)}${unit||''}`;
    barEl.classList.remove('bg-success','bg-warning','bg-danger','bg-secondary');
    barEl.classList.add('bg-' + statusKey(value, target, bands));
  }
  function setDot(dotEl, status) {
    if (!dotEl) return;
    dotEl.className = 'badge rounded-pill bg-' + status;
    dotEl.textContent = '●';
  }

  // ---------------- UI entrenos ----------------
  function iconFor(sport){
    const map = { bike:'🚴', run:'🏃', swim:'🏊', row:'🚣', hike:'🥾', walk:'🚶' };
    return map[sport] || '🏋️';
  }
  function renderTrainings(sessions) {
    const ul = $('trainList');
    if (!ul) return;
    ul.innerHTML = '';
    if (!sessions || sessions.length === 0) {
      ul.innerHTML = `
        <li class="list-group-item text-muted d-flex align-items-center justify-content-between">
          <span>No hay entrenos hoy.</span>
          <button class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#addTrainModal">Añadir entreno</button>
        </li>`;
      return;
    }
    sessions.forEach(s => {
      const hhmm = s.started_at ? `${s.started_at}` : '(sin hora)';
      const kcal = (s.kcal ?? 0);
      const li = document.createElement('li');
      li.className = 'list-group-item d-flex justify-content-between align-items-center';
      li.innerHTML = `
        <div class="d-flex flex-column">
          <div class="fw-semibold">${iconFor(s.type)} ${cap(s.type)} · ${hhmm}</div>
          <div class="text-muted small">${s.duration_min || 0}’ · ${Math.round(kcal)} kcal</div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-danger" data-action="del-train" data-id="${s.id}">Eliminar</button>
        </div>
      `;
      ul.appendChild(li);
    });
  }

  // ---------------- Objetivos por comida (desde overview) ----------------
  function computeByMealFromOverview(ovData) {
    // Prioridad 1: backend ya trae el reparto dinámico exacto
    const dyn = ovData?.by_meal_dynamic;
    if (dyn && typeof dyn === "object") {
      const out = {};
      for (const k of Object.keys(dyn)) {
        const v = dyn[k] || {};
        out[k.toLowerCase()] = {
          kcal:  toNum(v.kcal),
          cho_g: toNum(v.cho_g ?? v.carbs),
          pro_g: toNum(v.pro_g ?? v.protein),
          fat_g: toNum(v.fat_g ?? v.fats),
        };
      }
      return out;
    }
    // Prioridad 2: repartir por pesos (comportamiento actual)
    const t = ovData?.rings?.target || {};
    const weights = ovData?.weights || {};
    const daily = {
      kcal: toNum(t.kcal), cho_g: toNum(t.cho_g),
      pro_g: toNum(t.pro_g), fat_g: toNum(t.fat_g),
    };
    const MEALS = ["desayuno","almuerzo","comida","merienda","cena","snack"];
    const byMeal = {};
    for (const m of MEALS) {
      const w = toNum(weights[m] ?? 0);
      byMeal[m] = {
        kcal: daily.kcal*w,
        cho_g: daily.cho_g*w,
        pro_g: daily.pro_g*w,
        fat_g: daily.fat_g*w,
      };
    }
    return byMeal;
  }

  // ---------------- UI comidas (agregadas por tipo) ----------------
  function weightMap(hasSnack, base) {
    if (!hasSnack) return base;
    const total = (base.desayuno||0) + (base.comida||0) + (base.cena||0) + (base.snack||0);
    return {
      desayuno: (base.desayuno||0) / total,
      comida:   (base.comida||0)   / total,
      cena:     (base.cena||0)     / total,
      snack:    (base.snack||0)    / total,
    };
  }

  function renderMealTypeRow(ul, type, consumed, target, bands) {
    const li = document.createElement('li');
    li.className = 'list-group-item';

    const id = `meal-${type}-${Math.random().toString(36).slice(2,8)}`;
    li.innerHTML = `
      <div class="d-flex flex-column gap-2">
        <div class="d-flex justify-content-between align-items-center">
          <div class="d-flex align-items-center gap-2">
            <span id="${id}-dot" class="badge rounded-pill bg-secondary" aria-label="estado"></span>
            <div class="fw-semibold mb-0">${cap(type)}</div>
          </div>
          <a class="btn btn-sm btn-outline-secondary" href="/diary/today">Editar</a>
        </div>

        <div>
          <div class="d-flex justify-content-between small"><span>Kcal</span><span id="${id}-kcal-text">—</span></div>
          <div class="progress"><div id="${id}-kcal-bar" class="progress-bar" style="width:0%"></div></div>
        </div>

        <div class="row g-2">
          <div class="col-12 col-md-4">
            <div class="d-flex justify-content-between small"><span>Carbs</span><span id="${id}-cho-text">—</span></div>
            <div class="progress"><div id="${id}-cho-bar" class="progress-bar" style="width:0%"></div></div>
          </div>
          <div class="col-12 col-md-4">
            <div class="d-flex justify-content-between small"><span>Proteínas</span><span id="${id}-pro-text">—</span></div>
            <div class="progress"><div id="${id}-pro-bar" class="progress-bar" style="width:0%"></div></div>
          </div>
          <div class="col-12 col-md-4">
            <div class="d-flex justify-content-between small"><span>Grasas</span><span id="${id}-fat-text">—</span></div>
            <div class="progress"><div id="${id}-fat-bar" class="progress-bar" style="width:0%"></div></div>
          </div>
        </div>
      </div>
    `;
    ul.appendChild(li);

    setBarColored(li.querySelector(`#${id}-kcal-bar`), li.querySelector(`#${id}-kcal-text`), consumed.kcal||0, target.kcal||0, '', bands.kcal);
    setBarColored(li.querySelector(`#${id}-cho-bar`),  li.querySelector(`#${id}-cho-text`),  consumed.cho_g||0, target.cho_g||0, ' g', bands.cho_g);
    setBarColored(li.querySelector(`#${id}-pro-bar`),  li.querySelector(`#${id}-pro-text`),  consumed.pro_g||0, target.pro_g||0, ' g', bands.pro_g);
    setBarColored(li.querySelector(`#${id}-fat-bar`),  li.querySelector(`#${id}-fat-text`),  consumed.fat_g||0, target.fat_g||0, ' g', bands.fat_g);

    const dotStatus = statusKey(consumed.kcal||0, target.kcal||0, bands.kcal);
    setDot(li.querySelector(`#${id}-dot`), dotStatus);
  }

  function renderMealsAggregated(meals, dailyTarget, bands, baseWeights, byMealTargets){
    const ul = $('mealList');
    if (!ul) return;
    ul.innerHTML = '';

    // Sumas consumidas por tipo
    const sums = {};
    (meals || []).forEach(m => {
      const t = (m.meal_type || 'comida').toLowerCase();
      if (!sums[t]) sums[t] = { kcal:0, cho_g:0, pro_g:0, fat_g:0 };
      sums[t].kcal += +m.kcal || 0;
      sums[t].cho_g += +m.cho_g || 0;
      sums[t].pro_g += +m.pro_g || 0;
      sums[t].fat_g += +m.fat_g || 0;
    });

    const hasSnack = !!sums.snack;
    const W = weightMap(hasSnack, baseWeights || {desayuno:0.25, comida:0.45, cena:0.30, snack:0.15});
    const types = ['desayuno','comida','cena'].concat(hasSnack ? ['snack'] : []);

    // Targets por tipo:
    const tgtByType = {};
    types.forEach(t => {
      if (byMealTargets && byMealTargets[t]) {
        tgtByType[t] = {
          kcal:  toNum(byMealTargets[t].kcal),
          cho_g: toNum(byMealTargets[t].cho_g),
          pro_g: toNum(byMealTargets[t].pro_g),
          fat_g: toNum(byMealTargets[t].fat_g),
        };
      } else {
        const w = clamp01(W[t] || 0);
        tgtByType[t] = {
          kcal: (dailyTarget.kcal||0) * w,
          cho_g: (dailyTarget.cho_g||0) * w,
          pro_g: (dailyTarget.pro_g||0) * w,
          fat_g: (dailyTarget.fat_g||0) * w,
        };
      }
    });

    types.forEach(t => {
      renderMealTypeRow(ul, t, sums[t] || {kcal:0,cho_g:0,pro_g:0,fat_g:0}, tgtByType[t], bands);
    });

    if ((meals||[]).length === 0) {
      const li = document.createElement('li');
      li.className = 'list-group-item text-muted d-flex align-items-center justify-content-between';
      li.innerHTML = `<span>No has añadido comidas hoy.</span>
                      <div class="d-flex gap-2">
                        <div class="btn-group">
                          <button class="btn btn-sm btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown">Usar base</button>
                          <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="#" data-apply-base="desayuno">Desayuno</a></li>
                            <li><a class="dropdown-item" href="#" data-apply-base="comida">Comida</a></li>
                            <li><a class="dropdown-item" href="#" data-apply-base="cena">Cena</a></li>
                          </ul>
                        </div>
                        <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#addMealModal">Añadir comida</button>
                      </div>`;
      ul.prepend(li);
    }
  }

  // ---------------- Carga de overview + barras del header ----------------
  async function loadOverview() {
    const res = await fetch(`/api/day/overview?date=${today}`);
    if (!res.ok) return;
    const j = await res.json();
    const data = j?.data || {};

    const rings = data.rings || {};
    const tgt = rings.target || {kcal:0,cho_g:0,pro_g:0,fat_g:0};
    const con = rings.consumed || {kcal:0,cho_g:0,pro_g:0,fat_g:0};
    const bands = data.bands || {
      kcal:{green:[0.9,1.1],amber:[0.85,1.15]},
      cho_g:{green:[0.85,1.15],amber:[0.75,1.25]},
      pro_g:{green:[0.9,1.1],amber:[0.8,1.2]},
      fat_g:{green:[0.9,1.2],amber:[0.8,1.3]}
    };
    const weights = data.weights || {desayuno:0.25, comida:0.45, cena:0.30, snack:0.15};

    // Header totals
    setBarColored($('kcalBar'), $('kcalText'), con.kcal||0, tgt.kcal||0, '', bands.kcal);
    setBarColored($('choBar'),  $('choText'),  con.cho_g||0, tgt.cho_g||0, ' g', bands.cho_g);
    setBarColored($('proBar'),  $('proText'),  con.pro_g||0, tgt.pro_g||0, ' g', bands.pro_g);
    setBarColored($('fatBar'),  $('fatText'),  con.fat_g||0, tgt.fat_g||0, ' g', bands.fat_g);

    // Objetivos por comida (dinámicos si existen)
    const byMealTargets = computeByMealFromOverview(data);
    window.__BY_MEAL_GOALS__ = byMealTargets; // para inspección rápida

    renderTrainings((data.training && data.training.sessions) || []);
    renderMealsAggregated(data.meals || [], tgt, bands, weights, byMealTargets);
  }

  // ---------------- Eventos globales ----------------
  document.addEventListener('click', async (e) => {
    const delTrain = e.target.closest('button[data-action="del-train"]');
    if (delTrain) {
      const id = delTrain.getAttribute('data-id');
      if (!confirm('¿Eliminar este entreno?')) return;
      const r = await fetch(`/api/training/actual/${id}`, { method:'DELETE' });
      if (r.ok) loadOverview(); else alert('No se pudo eliminar el entreno.');
      return;
    }

    const apply = e.target.closest('[data-apply-base]');
    if (apply) {
      e.preventDefault();
      const meal_type = apply.getAttribute('data-apply-base');
      try {
        const chk = await fetch(`/api/base-meals/${meal_type}`);
        if (chk.status === 404) { alert(`No tienes una base de "${meal_type}" creada aún.`); return; }
        if (!chk.ok) { alert('No se pudo verificar la base.'); return; }
        const j = await chk.json();
        const slots = j?.data?.slots || [];
        if (!Array.isArray(slots) || slots.length === 0) { alert(`Tu base de "${meal_type}" no tiene ingredientes.`); return; }

        const r = await fetch('/api/diary/apply-base', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ meal_type, date: today })
        });
        if (!r.ok) { alert('No se pudo aplicar la base.'); return; }
        await loadOverview();
      } catch (err) {
        console.error(err);
        alert('Error inesperado aplicando la base.');
      }
    }
  });

  // ---------- Guardar entreno ----------
  $('addTrainForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      date: today,
      type: $('trainType')?.value,
      duration_min: parseInt(($('trainDur')?.value || '0'), 10),
    };
    if ($('trainDist')?.value) body.distance_km = parseFloat($('trainDist').value);
    if ($('trainElev')?.value) body.elevation_m = parseInt($('trainElev').value, 10);
    if ($('trainPower')?.value) body.avg_power_w = parseInt($('trainPower').value, 10);
    if ($('trainHr')?.value) body.avg_hr = parseInt($('trainHr').value, 10);
    if ($('trainStart')?.value) body.started_at = $('trainStart').value;

    const res = await fetch('/api/training/actual', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    if (res.ok) {
      const modalEl = $('#addTrainModal');
      if (modalEl) (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).hide?.();
      ['trainDur','trainDist','trainElev','trainPower','trainHr','trainStart'].forEach(id => { const el=$(id); if (el) el.value=''; });
      await loadOverview();
    } else {
      alert('No se pudo guardar el entreno.');
    }
  });

  // ---------- Guardar comida manual ----------
  $('addMealForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      date: today,
      meal_type: $('mealType')?.value,
      name: $('mealName')?.value,
      kcal: parseFloat(($('mealKcal')?.value || '0')),
      cho_g: parseFloat(($('mealCho')?.value || '0')),
      pro_g: parseFloat(($('mealPro')?.value || '0')),
      fat_g: parseFloat(($('mealFat')?.value || '0')),
    };
    if ($('mealTime')?.value) body.time = $('mealTime').value;
    if ($('mealQty')?.value) body.quantity = parseFloat($('mealQty').value);
    if ($('mealUnit')?.value) body.unit = $('mealUnit').value;

    const res = await fetch('/api/diary/add-item', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    if (res.ok) {
      const modalEl = $('#addMealModal');
      if (modalEl) (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).hide?.();
      ['mealName','mealKcal','mealCho','mealPro','mealFat','mealTime','mealQty','mealUnit'].forEach(id => { const el=$(id); if (el) el.value=''; });
      await loadOverview();
    } else {
      alert('No se pudo guardar la comida.');
    }
  });

  // ---------------- Autocompletado robusto de alimentos ----------------
  (function setupFoodAutocomplete(){
    const input = $('mealName');
    if (!input) return;

    const box = document.createElement('div');
    box.className = 'list-group position-absolute w-100 shadow-sm';
    box.style.zIndex = '1080';
    box.style.maxHeight = '220px';
    box.style.overflowY = 'auto';
    box.hidden = true;

    const parent = input.parentElement;
    if (parent && getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }
    parent.appendChild(box);

    let idx = -1;
    let items = [];
    let last = '';
    let t = null;

    function clearBox(){ box.innerHTML=''; box.hidden = true; idx = -1; items = []; }
    function fillInputsFrom(item){
      input.value = item.name || '';
      const m = item.macros || item.macros_per_100g || null;
      if (m) {
        if ($('mealKcal')) $('mealKcal').value = toNum(m.kcal);
        if ($('mealCho'))  $('mealCho').value  = toNum(m.cho_g ?? m.carbs);
        if ($('mealPro'))  $('mealPro').value  = toNum(m.pro_g ?? m.protein);
        if ($('mealFat'))  $('mealFat').value  = toNum(m.fat_g ?? m.fat);
      } else {
        if ($('mealKcal') && item.kcal != null) $('mealKcal').value = toNum(item.kcal);
        if ($('mealCho')  && item.cho_g != null) $('mealCho').value = toNum(item.cho_g);
        if ($('mealPro')  && item.pro_g != null) $('mealPro').value = toNum(item.pro_g);
        if ($('mealFat')  && item.fat_g != null) $('mealFat').value = toNum(item.fat_g);
      }
      clearBox();
    }

    function normalizeList(j){
      // acepta {foods:[]}, {suggestions:[]}, {items:[]}, lista directa, o {data:{foods:[]}}
      if (!j) return [];
      const d = j.data || j;
      const arr = d.foods || d.suggestions || d.items || (Array.isArray(d) ? d : []);
      return (arr || []).map(x => {
        const name = x.name || x.product_name || x.food_name || '';
        const macros = x.macros_per_100g || x.macros || (
          (x.kcal!=null || x.cho_g!=null || x.pro_g!=null || x.fat_g!=null)
            ? { kcal:x.kcal, cho_g:x.cho_g, pro_g:x.pro_g, fat_g:x.fat_g }
            : null
        );
        return { name, macros, ...x };
      }).filter(x => x.name);
    }

    async function query(term){
      const enc = encodeURIComponent(term);
      const candidates = [
        `/api/foods/search?q=${enc}`,   // nuevo blueprint
        `/api/foods?search=${enc}`,     // API legacy que usa "search"
        `/api/foods?q=${enc}`           // API legacy que acepta "q"
      ];
      for (const url of candidates) {
        try{
          const res = await fetch(url);
          if (!res.ok) continue;
          const j = await res.json();
          const list = normalizeList(j);
          if (list.length) {
            items = list;
            render();
            return;
          }
        } catch(_) { /* intenta el siguiente */ }
      }
      // si nada devolvió contenido:
      clearBox();
    }

    function render(){
      box.innerHTML = '';
      if (!items.length){ clearBox(); return; }
      box.hidden = false;
      items.forEach((it, i) => {
        const kcalVal = (it.macros?.kcal ?? it.kcal);
        const kcalTxt = (kcalVal != null && isFinite(+kcalVal)) ? ` · ${Math.round(+kcalVal)} kcal/100g` : '';
        const a = document.createElement('button');
        a.type = 'button';
        a.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        a.innerHTML = `<span>${it.name}</span><small class="text-muted">${kcalTxt}</small>`;
        a.addEventListener('click', () => fillInputsFrom(it));
        a.addEventListener('mousemove', () => { setActive(i); });
        box.appendChild(a);
      });
      setActive(-1);
    }

    function setActive(newIdx){
      idx = newIdx;
      [...box.children].forEach((el, i) => {
        el.classList.toggle('active', i === idx);
      });
    }

    function onInput(){
      const term = (input.value || '').trim();
      if (term.length < 2){ clearBox(); return; }
      if (term === last) return;
      last = term;
      if (t) clearTimeout(t);
      t = setTimeout(() => query(term), 200);
    }

    function onKey(e){
      if (box.hidden) return;
      if (e.key === 'ArrowDown'){ e.preventDefault(); setActive(Math.min(idx + 1, items.length - 1)); }
      else if (e.key === 'ArrowUp'){ e.preventDefault(); setActive(Math.max(idx - 1, -1)); }
      else if (e.key === 'Enter'){
        if (idx >= 0 && items[idx]){ e.preventDefault(); fillInputsFrom(items[idx]); }
      } else if (e.key === 'Escape'){ clearBox(); }
    }

    document.addEventListener('click', (e) => {
      if (e.target !== input && !box.contains(e.target)) clearBox();
    });

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKey);
  })();

  // Carga inicial
  loadOverview();
})();
