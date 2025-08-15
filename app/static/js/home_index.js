// app/static/js/home_index.js
(function () {
  const today = new Date().toISOString().slice(0,10);
  const $ = (id) => document.getElementById(id);

  $('todayDate').textContent = today;

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
    const pct = target > 0 ? Math.max(0, Math.min(100, (value / target) * 100)) : 0;
    barEl.style.width = pct + '%';
    textEl.textContent = `${Math.round(value)}${unit||''} / ${Math.round(target)}${unit||''}`;
    // limpia clases y aplica color
    barEl.classList.remove('bg-success','bg-warning','bg-danger','bg-secondary');
    barEl.classList.add('bg-' + statusKey(value, target, bands));
  }
  function setDot(dotEl, status) {
    dotEl.className = 'badge rounded-pill bg-' + status;
    dotEl.textContent = '●';
  }
  function cap(s){ s = s || ''; return s.charAt(0).toUpperCase() + s.slice(1); }
  function clamp01(x){ return Math.max(0, Math.min(1, x)); }

  // ---------------- UI entrenos ----------------
  function iconFor(sport){
    const map = { bike:'🚴', run:'🏃', swim:'🏊', row:'🚣', hike:'🥾', walk:'🚶' };
    return map[sport] || '🏋️';
  }
  function renderTrainings(sessions) {
    const ul = $('trainList');
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

  // ---------------- UI comidas (agregadas por tipo) ----------------
  function weightMap(hasSnack, base) {
    // normaliza a 1 si hay snack; si no, usa base tal cual
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
            <span id="${id}-dot" class="badge rounded-pill bg-secondary">●</span>
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

    // Pintar barras
    setBarColored(li.querySelector(`#${id}-kcal-bar`), li.querySelector(`#${id}-kcal-text`), consumed.kcal||0, target.kcal||0, '', bands.kcal);
    setBarColored(li.querySelector(`#${id}-cho-bar`),  li.querySelector(`#${id}-cho-text`),  consumed.cho_g||0, target.cho_g||0, ' g', bands.cho_g);
    setBarColored(li.querySelector(`#${id}-pro-bar`),  li.querySelector(`#${id}-pro-text`),  consumed.pro_g||0, target.pro_g||0, ' g', bands.pro_g);
    setBarColored(li.querySelector(`#${id}-fat-bar`),  li.querySelector(`#${id}-fat-text`),  consumed.fat_g||0, target.fat_g||0, ' g', bands.fat_g);

    // Dot global (usamos kcal como resumen)
    const dotStatus = statusKey(consumed.kcal||0, target.kcal||0, bands.kcal);
    setDot(li.querySelector(`#${id}-dot`), dotStatus);
  }

  function renderMealsAggregated(meals, dailyTarget, bands, baseWeights){
    const ul = $('mealList');
    ul.innerHTML = '';

    // Sumar por tipo
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

    // Objetivos por tipo
    const tgtByType = {};
    types.forEach(t => {
      const w = clamp01(W[t] || 0);
      tgtByType[t] = {
        kcal: (dailyTarget.kcal||0) * w,
        cho_g: (dailyTarget.cho_g||0) * w,
        pro_g: (dailyTarget.pro_g||0) * w,
        fat_g: (dailyTarget.fat_g||0) * w,
      };
    });

    // Render
    types.forEach(t => {
      renderMealTypeRow(ul, t, sums[t] || {kcal:0,cho_g:0,pro_g:0,fat_g:0}, tgtByType[t], bands);
    });

    // CTA si vacío
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

    // Top bars con color
    setBarColored($('kcalBar'), $('kcalText'), con.kcal||0, tgt.kcal||0, '', bands.kcal);
    setBarColored($('choBar'),  $('choText'),  con.cho_g||0, tgt.cho_g||0, ' g', bands.cho_g);
    setBarColored($('proBar'),  $('proText'),  con.pro_g||0, tgt.pro_g||0, ' g', bands.pro_g);
    setBarColored($('fatBar'),  $('fatText'),  con.fat_g||0, tgt.fat_g||0, ' g', bands.fat_g);

    // Entrenamientos
    renderTrainings((data.training && data.training.sessions) || []);

    // Comidas agregadas por tipo con semáforo
    renderMealsAggregated(data.meals || [], tgt, bands, weights);
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

  // Modal: Añadir entreno
  $('addTrainForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      date: today,
      type: $('trainType').value,
      duration_min: parseInt($('trainDur').value || '0', 10),
    };
    if ($('trainDist').value) body.distance_km = parseFloat($('trainDist').value);
    if ($('trainElev').value) body.elevation_m = parseInt($('trainElev').value, 10);
    if ($('trainPower').value) body.avg_power_w = parseInt($('trainPower').value, 10);
    if ($('trainHr').value) body.avg_hr = parseInt($('trainHr').value, 10);
    if ($('trainStart').value) body.started_at = $('trainStart').value;

    const res = await fetch('/api/training/actual', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    if (res.ok) {
      (bootstrap.Modal.getInstance($('#addTrainModal')) || new bootstrap.Modal($('#addTrainModal'))).hide?.();
      ['trainDur','trainDist','trainElev','trainPower','trainHr','trainStart'].forEach(id => { const el=$(id); if (el) el.value=''; });
      await loadOverview();
    } else {
      alert('No se pudo guardar el entreno.');
    }
  });

  // Modal: Añadir comida
  $('addMealForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      date: today,
      meal_type: $('mealType').value,
      name: $('mealName').value,
      kcal: parseFloat($('mealKcal').value || '0'),
      cho_g: parseFloat($('mealCho').value || '0'),
      pro_g: parseFloat($('mealPro').value || '0'),
      fat_g: parseFloat($('mealFat').value || '0'),
    };
    if ($('mealTime').value) body.time = $('mealTime').value;
    if ($('mealQty').value) body.quantity = parseFloat($('mealQty').value);
    if ($('mealUnit').value) body.unit = $('mealUnit').value;

    const res = await fetch('/api/diary/add-item', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    if (res.ok) {
      (bootstrap.Modal.getInstance($('#addMealModal')) || new bootstrap.Modal($('#addMealModal'))).hide?.();
      ['mealName','mealKcal','mealCho','mealPro','mealFat','mealTime','mealQty','mealUnit'].forEach(id => { const el=$(id); if (el) el.value=''; });
      await loadOverview();
    } else {
      alert('No se pudo guardar la comida.');
    }
  });

  // Carga inicial
  loadOverview();
})();
