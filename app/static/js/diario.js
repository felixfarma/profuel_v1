// app/static/js/diario.js
// Diario nutricional — edición fluida con botones ± y totales en vivo

document.addEventListener('DOMContentLoaded', () => {
  const todayISO = new Date().toISOString().slice(0,10);
  const $  = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  // ----- Anchors del DOM (opcionales: el script no revienta si falta algo)
  const searchInput    = $('#food-search');
  const suggestionsBox = $('#suggestions') || $('#food-suggestions');
  const foodIdInput    = $('#food-id');
  const mealsList      = $('#today-meals-list');
  const totals = {
    kcal:  $('#total-kcal'),
    prot:  $('#total-protein'),
    carbs: $('#total-carbs'),
    fats:  $('#total-fats'),
  };

  // ----- HTTP helpers
  const GET = async (url) => {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  };

  const jsonFetch = async (url, opts = {}) => {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) {
      const msg = data?.message || data?.error || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  };

  const esc = (s) => String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

  const toNum = (v) => {
    const x = parseFloat(String(v).replace(',', '.'));
    return Number.isFinite(x) ? x : 0;
  };

  // ========== TOTALES ==========
  async function refreshTotals() {
    try {
      const data = await GET(`/api/meals/stats?date=${todayISO}`);
      totals.kcal  && (totals.kcal.textContent  = data.total?.kcal    ?? 0);
      totals.prot  && (totals.prot.textContent  = data.total?.protein ?? 0);
      totals.carbs && (totals.carbs.textContent = data.total?.carbs   ?? 0);
      totals.fats  && (totals.fats.textContent  = data.total?.fat     ?? 0);
    } catch {
      // Fallback: sumar lo que hay en DOM
      let tk=0,tp=0,tc=0,tf=0;
      $$('.meal-row', mealsList || document).forEach(r => {
        tk += toNum(r.querySelector('.meal-calories')?.textContent);
        tp += toNum(r.querySelector('.meal-protein')?.textContent);
        tc += toNum(r.querySelector('.meal-carbs')?.textContent);
        tf += toNum(r.querySelector('.meal-fats')?.textContent);
      });
      totals.kcal  && (totals.kcal.textContent  = Math.round(tk));
      totals.prot  && (totals.prot.textContent  = Math.round(tp));
      totals.carbs && (totals.carbs.textContent = Math.round(tc));
      totals.fats  && (totals.fats.textContent  = Math.round(tf));
    }
  }

  // ========== CARGA INICIAL ==========
  async function loadMeals() {
    if (!mealsList) return;
    try {
      const data = await GET(`/api/meals?date=${todayISO}`);
      const list = data?.meals || [];
      mealsList.innerHTML = '';
      if (!list.length) {
        mealsList.innerHTML = '<div class="text-muted">Aún no hay comidas hoy.</div>';
        return;
      }
      list.forEach(m => appendMealRow(m)); // crea filas con botones ±
    } catch {
      // Si la página ya trae filas renderizadas por el servidor, las rehidratamos:
      $$('.meal-row', mealsList).forEach(row => hydrateExistingRow(row));
    }
  }

  // ========== UI: crear fila ==========
  function appendMealRow(m) {
    if (!mealsList) return;

    // Datos base
    const qty   = toNum(m.quantity);
    const kcal  = toNum(m.calories);
    const prot  = toNum(m.protein);
    const carbs = toNum(m.carbs);
    const fats  = toNum(m.fats);
    const unit  = m.food?.default_unit || m.food_default_unit || '';

    // Cálculo "por unidad" (para evitar acumulación al editar)
    const per = perUnitFrom(qty, { kcal, prot, carbs, fats });

    const row = document.createElement('div');
    row.className = 'd-flex justify-content-between align-items-center py-1 border-bottom meal-row';
    row.dataset.mealId = m.id;
    row.dataset.unit = unit.toLowerCase();

    // Guarda per-unit en data-*
    setPerUnit(row, per);

    const macrosHtml = Number.isFinite(prot) && Number.isFinite(carbs) && Number.isFinite(fats)
      ? `<small class="text-muted d-inline-block ms-2">
           <span class="meal-protein">${prot}</span>P ·
           <span class="meal-carbs">${carbs}</span>C ·
           <span class="meal-fats">${fats}</span>G
         </small>` : '';

    row.innerHTML = `
      <div class="me-3 flex-grow-1">
        <div class="fw-semibold">
          <span class="badge text-bg-secondary me-1">${esc(m.meal_type || '')}</span>
          ${esc(m.food?.name || m.food_name || '')}
        </div>
        <div class="text-muted small">
          <span class="meal-quantity">${qty}</span> ${esc(unit)} —
          <span class="meal-calories">${kcal}</span> kcal
          ${macrosHtml}
        </div>
      </div>
      <div class="d-flex align-items-center">
        <div class="btn-group btn-group-sm me-2" role="group" aria-label="Ajustes cantidad">
          <button class="btn btn-outline-secondary dec-qty" title="-">−</button>
          <button class="btn btn-outline-secondary inc-qty" title="+">+</button>
          <button class="btn btn-outline-secondary edit-meal"  title="Editar">✏️</button>
        </div>
        <button class="btn btn-sm btn-outline-danger delete-meal" title="Eliminar">🗑️</button>
      </div>
    `;
    mealsList.appendChild(row);
  }

  // Rehidrata filas renderizadas por servidor (añade botones ± y per-unit)
  function hydrateExistingRow(row) {
    // Si ya tiene botones, solo asegúrate del per-unit
    const hasBtns = row.querySelector('.inc-qty');
    if (!hasBtns) {
      const rightBox = row.querySelector('.d-flex.align-items-center');
      if (rightBox) {
        const group = document.createElement('div');
        group.className = 'btn-group btn-group-sm me-2';
        group.setAttribute('role','group');
        group.innerHTML = `
          <button class="btn btn-outline-secondary dec-qty" title="-">−</button>
          <button class="btn btn-outline-secondary inc-qty" title="+">+</button>
          <button class="btn btn-outline-secondary edit-meal"  title="Editar">✏️</button>`;
        rightBox.prepend(group);
      }
    }

    // Construir per-unit desde lo visible
    const qty   = toNum(row.querySelector('.meal-quantity')?.textContent);
    const kcal  = toNum(row.querySelector('.meal-calories')?.textContent);
    const prot  = toNum(row.querySelector('.meal-protein')?.textContent);
    const carbs = toNum(row.querySelector('.meal-carbs')?.textContent);
    const fats  = toNum(row.querySelector('.meal-fats')?.textContent);
    const per   = perUnitFrom(qty, { kcal, prot, carbs, fats });
    setPerUnit(row, per);

    // Asegura data-unit
    const unitText = (row.textContent || '').toLowerCase();
    if (!row.dataset.unit) {
      if (unitText.includes('unidad')) row.dataset.unit = 'unidad';
      else if (unitText.includes(' ml')) row.dataset.unit = 'ml';
      else row.dataset.unit = 'g';
    }
  }

  function perUnitFrom(qty, vals) {
    const q = Math.max(0.0001, qty || 0);
    return {
      kcalPer:  Math.max(0, Math.round(vals.kcal  / q)),
      protPer:  Math.max(0, Math.round(vals.prot  / q)),
      carbsPer: Math.max(0, Math.round(vals.carbs / q)),
      fatsPer:  Math.max(0, Math.round(vals.fats  / q)),
    };
  }

  function setPerUnit(row, per) {
    row.dataset.kcalPer  = per.kcalPer;
    row.dataset.protPer  = per.protPer;
    row.dataset.carbsPer = per.carbsPer;
    row.dataset.fatsPer  = per.fatsPer;
  }

  function computeFromPer(row, qty) {
    const q = Math.max(0, qty);
    const kcal  = Math.round(toNum(row.dataset.kcalPer)  * q);
    const prot  = Math.round(toNum(row.dataset.protPer)  * q);
    const carbs = Math.round(toNum(row.dataset.carbsPer) * q);
    const fats  = Math.round(toNum(row.dataset.fatsPer)  * q);
    return { qty: q, kcal, prot, carbs, fats };
  }

  function stepForUnit(row, ev) {
    const unit = (row.dataset.unit || '').toLowerCase();
    // Modificadores: Alt=1, Shift=50
    if (ev?.altKey) return 1;
    if (ev?.shiftKey) return 50;
    if (unit === 'unidad') return 1;
    return 10; // g/ml por defecto
    // Si prefieres 5, cambia a return 5;
  }

  // ========== AUTOCOMPLETE (crear/añadir) ==========
  if (searchInput && suggestionsBox && foodIdInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const q = searchInput.value.trim();
      if (q.length < 2) {
        suggestionsBox.innerHTML = '';
        foodIdInput.value = '';
        return;
      }
      debounceTimer = setTimeout(async () => {
        try {
          const data = await GET(`/api/foods?search=${encodeURIComponent(q)}`);
          const foods = data.foods || [];
          suggestionsBox.innerHTML = '';
          if (!foods.length) {
            suggestionsBox.innerHTML = '<li class="list-group-item text-muted">No se encontraron alimentos.</li>';
            return;
          }
          foods.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action';
            const kcal100 = item?.macros_per_100g?.kcal ?? 0;
            li.innerHTML = `<strong>${esc(item.name)}</strong> <small class="text-muted">(${kcal100} kcal/100g)</small>`;
            li.style.cursor = 'pointer';
            li.addEventListener('click', () => {
              searchInput.value = item.name;
              foodIdInput.value = item.id;
              suggestionsBox.innerHTML = '';
              $('#quantity')?.focus();
            });
            suggestionsBox.appendChild(li);
          });
        } catch (e) {
          suggestionsBox.innerHTML = `<li class="list-group-item text-danger">Error: ${esc(e.message)}</li>`;
        }
      }, 250);
    });

    document.addEventListener('click', e => {
      if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
        suggestionsBox.innerHTML = '';
      }
    });
  }

  // Crear alimento (modal)
  const formCreateFood = document.getElementById('create-food-form');
  if (formCreateFood) {
    formCreateFood.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: $('#food-name')?.value.trim(),
        default_unit: $('#food-unit')?.value,
        default_quantity: toNum($('#food-quantity')?.value),
        kcal_per_100g:    toNum($('#food-kcal100')?.value),
        protein_per_100g: toNum($('#food-prot100')?.value),
        carbs_per_100g:   toNum($('#food-carbs100')?.value),
        fat_per_100g:     toNum($('#food-fat100')?.value),
        kcal_per_unit:    valueOrNull($('#food-kcal1')?.value),
        protein_per_unit: valueOrNull($('#food-prot1')?.value),
        carbs_per_unit:   valueOrNull($('#food-carbs1')?.value),
        fat_per_unit:     valueOrNull($('#food-fat1')?.value),
      };
      try {
        const data = await jsonFetch('/api/foods', { method:'POST', body: JSON.stringify(payload) });
        if (searchInput) searchInput.value = data.food.name;
        if (foodIdInput) foodIdInput.value = data.food.id;
        const modalEl = document.getElementById('foodModal');
        if (modalEl && window.bootstrap?.Modal) {
          window.bootstrap.Modal.getInstance(modalEl)?.hide();
        }
        $('#quantity')?.focus();
      } catch (e2) {
        alert(e2.message || 'Error al crear el alimento');
      }
    });
  }
  function valueOrNull(v){ const x = toNum(v); return x ? x : null; }

  // Añadir comida
  const formAddMeal = document.getElementById('add-meal-form');
  if (formAddMeal) {
    formAddMeal.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        food_id:  parseInt(foodIdInput?.value || '0', 10),
        quantity: toNum($('#quantity')?.value),
        meal_type: ($('#meal_type')?.value || '').toLowerCase()
      };
      if (!payload.food_id) return alert('Elige un alimento de la lista.');
      if (!payload.quantity || payload.quantity <= 0) return alert('Cantidad inválida.');

      try {
        const resp = await jsonFetch('/api/meals', { method:'POST', body: JSON.stringify(payload) });
        const m = resp.meal || resp;
        appendMealRow(m);
        await refreshTotals();
        // reset
        if (searchInput) searchInput.value = '';
        if (foodIdInput) foodIdInput.value = '';
        const q = $('#quantity'); if (q) q.value = '';
        if (suggestionsBox) suggestionsBox.innerHTML = '';
      } catch (e2) {
        alert(e2.message || 'Error al añadir comida');
      }
    });
  }

  // ========== Delegación: borrar / editar / ± ==========
  if (mealsList) {
    mealsList.addEventListener('click', async (e) => {
      const row = e.target.closest('.meal-row');
      if (!row) return;
      const id = row.dataset.mealId;

      // Borrar
      if (e.target.matches('.delete-meal')) {
        if (!confirm('¿Eliminar esta comida?')) return;
        try {
          await jsonFetch(`/api/meals/${id}`, { method:'DELETE' });
          row.remove();
          await refreshTotals();
        } catch (err) {
          alert(err.message || 'Error al borrar');
        }
        return;
      }

      // Editar inline (input)
      if (e.target.matches('.edit-meal')) {
        activateInlineEdit(row, id);
        return;
      }

      // Botones ±
      if (e.target.matches('.inc-qty') || e.target.matches('.dec-qty')) {
        const qtyEl = row.querySelector('.meal-quantity');
        if (!qtyEl) return;

        const current = toNum(qtyEl.textContent);
        const delta   = stepForUnit(row, e) * (e.target.matches('.inc-qty') ? 1 : -1);
        const next    = Math.max(0.01, roundSmart(current + delta));

        // Previsualiza con per-unit (no acumulativo)
        paintRowFromComputed(row, computeFromPer(row, next));

        // Persistir
        try {
          const { meal } = await jsonFetch(`/api/meals/${id}`, {
            method:'PUT',
            body: JSON.stringify({ quantity: next })
          });
          syncRowWithServer(row, meal); // recalibra per-unit con respuesta real
          await refreshTotals();
        } catch (err) {
          alert('No se pudo actualizar la cantidad');
          // Recalcular desde servidor para evitar drift
          await refreshTotals();
        }
      }
    });
  }

  function roundSmart(x) {
    // Evita colas de decimales feos
    return Math.round(x * 100) / 100;
  }

  // Edición inline con input number y guardado diferido
  function activateInlineEdit(row, id) {
    if (row.dataset.editing === '1') return;
    row.dataset.editing = '1';

    const qtySpan = row.querySelector('.meal-quantity');
    if (!qtySpan) return;
    const oldQty = toNum(qtySpan.textContent) || 1;

    const input = document.createElement('input');
    input.type  = 'number';
    input.min   = '0.01';
    input.step  = 'any';
    input.value = String(oldQty);
    input.className = 'form-control form-control-sm d-inline-block';
    input.style.width = '90px';

    qtySpan.replaceWith(input);
    input.focus(); input.select();

    let timer, lastSent=null, saving=false;

    input.addEventListener('input', () => {
      const v = toNum(input.value);
      if (v <= 0) return;
      // Previsualiza
      paintRowFromComputed(row, computeFromPer(row, v));
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (lastSent === v) return;
        lastSent = v; persist(v);
      }, 500);
    });

    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        const v = toNum(input.value);
        if (v > 0) { clearTimeout(timer); lastSent = v; persist(v); }
        else alert('Cantidad inválida');
      }
      if (ev.key === 'Escape') {
        replaceInputWithSpan(input, oldQty);
        row.dataset.editing = '0';
        refreshTotals();
      }
    });

    input.addEventListener('blur', () => {
      const v = toNum(input.value);
      if (v > 0) {
        clearTimeout(timer);
        if (lastSent !== v) persist(v);
      } else {
        replaceInputWithSpan(input, oldQty);
        row.dataset.editing = '0';
        refreshTotals();
      }
    });

    async function persist(newQty){
      if (saving) return;
      saving = true;
      try {
        const { meal } = await jsonFetch(`/api/meals/${id}`, {
          method:'PUT',
          body: JSON.stringify({ quantity: newQty })
        });
        replaceInputWithSpan(input, meal.quantity);
        syncRowWithServer(row, meal);
        await refreshTotals();
      } catch (err) {
        alert(err.message || 'No se pudo guardar la nueva cantidad');
        replaceInputWithSpan(input, oldQty);
        await refreshTotals();
      } finally {
        row.dataset.editing = '0';
        saving = false;
      }
    }

    function replaceInputWithSpan(inputEl, value){
      const span = document.createElement('span');
      span.className = 'meal-quantity';
      span.textContent = value;
      inputEl.replaceWith(span);
    }
  }

  // Pintar fila desde valores computados (sin tocar per-unit)
  function paintRowFromComputed(row, comp) {
    const qtyEl  = row.querySelector('.meal-quantity');
    const kcalEl = row.querySelector('.meal-calories');
    const pEl    = row.querySelector('.meal-protein');
    const cEl    = row.querySelector('.meal-carbs');
    const fEl    = row.querySelector('.meal-fats');

    if (qtyEl)  qtyEl.textContent  = comp.qty;
    if (kcalEl) kcalEl.textContent = comp.kcal;
    if (pEl)    pEl.textContent    = comp.prot;
    if (cEl)    cEl.textContent    = comp.carbs;
    if (fEl)    fEl.textContent    = comp.fats;
  }

  // Sincroniza fila con respuesta real del backend y recalibra per-unit
  function syncRowWithServer(row, meal) {
    const qtyEl  = row.querySelector('.meal-quantity');
    const kcalEl = row.querySelector('.meal-calories');
    const pEl    = row.querySelector('.meal-protein');
    const cEl    = row.querySelector('.meal-carbs');
    const fEl    = row.querySelector('.meal-fats');

    if (qtyEl)  qtyEl.textContent  = meal.quantity;
    if (kcalEl) kcalEl.textContent = meal.calories;
    if (pEl && meal.protein !== undefined) pEl.textContent = meal.protein;
    if (cEl && meal.carbs   !== undefined) cEl.textContent = meal.carbs;
    if (fEl && meal.fats    !== undefined) fEl.textContent = meal.fats;

    // Recalibrar per-unit a partir de la respuesta
    const per = perUnitFrom(toNum(meal.quantity), {
      kcal:  toNum(meal.calories),
      prot:  toNum(meal.protein),
      carbs: toNum(meal.carbs),
      fats:  toNum(meal.fats)
    });
    setPerUnit(row, per);

    // Guardar unidad si llega
    if (meal.food_default_unit || meal.food?.default_unit) {
      row.dataset.unit = (meal.food_default_unit || meal.food.default_unit || '').toLowerCase();
    }
  }

  // ========== Inicio ==========
  loadMeals();     // intenta API; si no, rehidrata
  refreshTotals(); // intenta API; si no, suma DOM
});
