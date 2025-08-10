// app/static/js/diario.js
// Diario nutricional — UX fluida + edición inline

document.addEventListener('DOMContentLoaded', () => {
  const todayISO = new Date().toISOString().slice(0,10);
  const $  = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  // Elementos base (si no existen, el script no revienta)
  const searchInput    = $('#food-search');
  const suggestionsBox = $('#suggestions') || $('#food-suggestions');
  const foodIdInput    = $('#food-id');
  const mealsList      = $('#today-meals-list');
  const totals = {
    kcal:   $('#total-kcal'),
    prot:   $('#total-protein'),
    carbs:  $('#total-carbs'),
    fats:   $('#total-fats'),
  };

  // Modales (si existen)
  const modalFoodEl = document.getElementById('foodModal') || document.getElementById('modalFood');
  const modalMealEl = document.getElementById('modalMeal'); // opcional
  const modalFood = modalFoodEl ? new bootstrap.Modal(modalFoodEl) : null;
  const modalMeal = modalMealEl ? new bootstrap.Modal(modalMealEl) : null;

  // CSRF opcional
  // const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // --- Helpers HTTP ----------------------------------------------------------
  const GET = async (url) => {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  };

  const jsonFetch = async (url, opts = {}) => {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        // ...(csrf ? { 'X-CSRFToken': csrf } : {}),
        ...(opts.headers || {})
      },
      ...opts
    });
    let data = null;
    try { data = await res.json(); } catch (_) { data = {}; }
    if (!res.ok) {
      const msg = data?.message || data?.error || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  };

  const escapeHtml = (s) => String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

  // --- Totales: por API con fallback a DOM -----------------------------------
  async function refreshTotals() {
    // Intento por API
    try {
      const data = await GET(`/api/meals/stats?date=${todayISO}`);
      totals.kcal && (totals.kcal.textContent = data.total?.kcal ?? 0);
      totals.prot && (totals.prot.textContent = data.total?.protein ?? 0);
      totals.carbs && (totals.carbs.textContent = data.total?.carbs ?? 0);
      totals.fats && (totals.fats.textContent = data.total?.fat ?? 0);
      return;
    } catch (_) {
      // Fallback: suma lo que hay pintado
      let tk=0,tp=0,tc=0,tf=0;
      $$('.meal-row', mealsList || document).forEach(r => {
        tk += toNum(r.querySelector('.meal-calories')?.textContent);
        tp += toNum(r.querySelector('.meal-protein')?.textContent);
        tc += toNum(r.querySelector('.meal-carbs')?.textContent);
        tf += toNum(r.querySelector('.meal-fats')?.textContent);
      });
      totals.kcal && (totals.kcal.textContent = Math.round(tk));
      totals.prot && (totals.prot.textContent = Math.round(tp));
      totals.carbs && (totals.carbs.textContent = Math.round(tc));
      totals.fats && (totals.fats.textContent = Math.round(tf));
    }
  }

  function toNum(v){ const x = parseFloat(v); return isNaN(x) ? 0 : x; }

  // --- Carga de comidas del día (si existe endpoint) -------------------------
  async function loadMeals() {
    if (!mealsList) return;
    try {
      const data = await GET(`/api/meals?date=${todayISO}`);
      const list = data?.meals || [];
      mealsList.innerHTML = '';
      if (!list.length) {
        mealsList.innerHTML = '<div class="list-group-item text-center text-muted">Aún no hay comidas hoy.</div>';
        return;
      }
      list.forEach(m => appendMealRow(m));
    } catch (_) {
      // Si no existe el endpoint, no tocamos la UI server-side.
    }
  }

  // --- Render fila de comida -------------------------------------------------
  function appendMealRow(m) {
    if (!mealsList) return;
    const row = document.createElement('div');
    row.className = 'd-flex justify-content-between align-items-center py-1 border-bottom meal-row';
    row.dataset.mealId = m.id;
    if (m.protein !== undefined) row.dataset.protein = m.protein;
    if (m.carbs   !== undefined) row.dataset.carbs   = m.carbs;
    if (m.fats    !== undefined) row.dataset.fats    = m.fats;
    if (m.calories!== undefined) row.dataset.kcal    = m.calories;
    if (m.food_default_unit || m.food?.default_unit) {
      row.dataset.unit = m.food_default_unit || m.food.default_unit;
    }

    const unit = escapeHtml(m.food_default_unit || m.food?.default_unit || '');
    const macrosHtml = (['protein','carbs','fats'].every(k => m[k] !== undefined))
      ? `<small class="text-muted d-inline-block ms-2">
           <span class="meal-protein">${m.protein}</span>P ·
           <span class="meal-carbs">${m.carbs}</span>C ·
           <span class="meal-fats">${m.fats}</span>G
         </small>` : '';

    row.innerHTML = `
      <div class="me-3 flex-grow-1">
        <div class="fw-semibold">
          <span class="badge text-bg-secondary me-1">${escapeHtml(m.meal_type || '')}</span>
          ${escapeHtml(m.food?.name || m.food_name || '')}
        </div>
        <div class="text-muted small">
          <span class="meal-quantity">${m.quantity}</span> ${unit} — 
          <span class="meal-calories">${m.calories}</span> kcal
          ${macrosHtml}
        </div>
      </div>
      <div class="d-flex align-items-center">
        <div class="btn-group btn-group-sm me-2" role="group" aria-label="Ajustes cantidad">
          <button class="btn btn-outline-secondary dec-qty" title="-">−</button>
          <button class="btn btn-outline-secondary inc-qty" title="+">+</button>
          <button class="btn btn-outline-secondary edit-meal" title="Editar">✏️</button>
        </div>
        <button class="btn btn-sm btn-outline-danger delete-meal" title="Eliminar">🗑️</button>
      </div>
    `;
    mealsList.appendChild(row);
  }

  // --- Autocomplete de alimentos --------------------------------------------
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
            li.innerHTML = `<strong>${escapeHtml(item.name)}</strong> <small class="text-muted">(${kcal100} kcal/100g)</small>`;
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
          suggestionsBox.innerHTML = `<li class="list-group-item text-danger">Error: ${escapeHtml(e.message)}</li>`;
        }
      }, 250);
    });

    document.addEventListener('click', e => {
      if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
        suggestionsBox.innerHTML = '';
      }
    });
  }

  // --- Crear alimento desde modal -------------------------------------------
  const formCreateFood = document.getElementById('create-food-form');
  if (formCreateFood) {
    formCreateFood.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: $('#food-name')?.value.trim(),
        default_unit: $('#food-unit')?.value,
        default_quantity: parseFloat($('#food-quantity')?.value || '0'),
        kcal_per_100g:   numOrZero($('#food-kcal100')?.value),
        protein_per_100g:numOrZero($('#food-prot100')?.value),
        carbs_per_100g:  numOrZero($('#food-carbs100')?.value),
        fat_per_100g:    numOrZero($('#food-fat100')?.value),
        kcal_per_unit:   numOrNull($('#food-kcal1')?.value),
        protein_per_unit:numOrNull($('#food-prot1')?.value),
        carbs_per_unit:  numOrNull($('#food-carbs1')?.value),
        fat_per_unit:    numOrNull($('#food-fat1')?.value),
      };
      try {
        const data = await jsonFetch('/api/foods', { method:'POST', body: JSON.stringify(payload) });
        if (searchInput) searchInput.value = data.food.name;
        if (foodIdInput) foodIdInput.value = data.food.id;
        modalFood && modalFood.hide();
        $('#quantity')?.focus();
      } catch (e) {
        alert(e.message || 'Error al crear el alimento');
      }
    });
  }
  function numOrZero(v){ const x=parseFloat(v); return isNaN(x)?0:x; }
  function numOrNull(v){ const x=parseFloat(v); return isNaN(x)?null:x; }

  // --- Añadir comida ---------------------------------------------------------
  const formAddMeal = document.getElementById('add-meal-form');
  if (formAddMeal) {
    formAddMeal.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        food_id:  parseInt(foodIdInput?.value || '0'),
        quantity: parseFloat($('#quantity')?.value || '0'),
        meal_type: $('#meal_type')?.value
      };
      if (!payload.food_id) return alert('Elige un alimento de la lista.');
      if (!payload.quantity || payload.quantity <= 0) return alert('Cantidad inválida.');

      try {
        const resp = await jsonFetch('/api/meals', { method: 'POST', body: JSON.stringify(payload) });
        const m = resp.meal || resp; // compatibilidad
        appendMealRow(m);
        await refreshTotals();
        // reset
        if (searchInput) searchInput.value = '';
        if (foodIdInput) foodIdInput.value = '';
        $('#quantity') && ( $('#quantity').value = '' );
        suggestionsBox && (suggestionsBox.innerHTML = '');
      } catch (e) {
        alert(e.message || 'Error al añadir comida');
      }
    });
  }

  // --- Delegación: borrar / editar inline / botones ± ------------------------
  if (mealsList) {
    mealsList.addEventListener('click', async (e) => {
      const row = e.target.closest('.meal-row');
      if (!row) return;
      const id = row.dataset.mealId;

      // borrar
      if (e.target.matches('.delete-meal')) {
        if (!confirm('¿Eliminar esta comida?')) return;
        try {
          await jsonFetch(`/api/meals/${id}`, { method: 'DELETE' });
          row.remove();
          await refreshTotals();
        } catch (err) {
          alert(err.message || 'Error al borrar');
        }
        return;
      }

      // editar inline
      if (e.target.matches('.edit-meal')) {
        activateInlineEdit(row, id);
        return;
      }

      // botones ±
      if (e.target.matches('.inc-qty') || e.target.matches('.dec-qty')) {
        const qtySpan = row.querySelector('.meal-quantity');
        if (!qtySpan) return;
        const current = toNum(qtySpan.textContent) || 0;
        const step = (row.dataset.unit || '').toLowerCase() === 'unidad' ? 1 : 5;
        const next = Math.max(0.01, current + (e.target.matches('.inc-qty') ? step : -step));
        previewRowScaling(row, current, next);
        qtySpan.textContent = next;
        try {
          const { meal } = await jsonFetch(`/api/meals/${id}`, {
            method:'PUT',
            body: JSON.stringify({ quantity: next })
          });
          syncRowWithServer(row, meal);
          await refreshTotals();
        } catch (err) {
          alert('No se pudo actualizar la cantidad');
          // revert totals para evitar drift
          await refreshTotals();
        }
      }
    });
  }

  // --- Edición inline --------------------------------------------------------
  function activateInlineEdit(row, id){
    const qtySpan = row.querySelector('.meal-quantity');
    const btnEdit = row.querySelector('.edit-meal');
    if (!qtySpan || !btnEdit) return;
    if (row.dataset.editing === '1') return;
    row.dataset.editing = '1';

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

    let debounceTimer; let lastSent = null; let saving = false;

    input.addEventListener('input', () => {
      const v = parseFloat(input.value);
      if (isNaN(v) || v <= 0) return;
      previewRowScaling(row, oldQty, v);
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        if (lastSent === v) return;
        lastSent = v;
        persist(v);
      }, 500);
    });

    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        const v = parseFloat(input.value);
        if (!isNaN(v) && v > 0) { clearTimeout(debounceTimer); lastSent = v; persist(v); }
        else alert('Cantidad inválida');
      }
      if (ev.key === 'Escape') {
        replaceInputWithSpan(input, oldQty);
        row.dataset.editing = '0';
        refreshTotals();
      }
    });

    input.addEventListener('blur', () => {
      const v = parseFloat(input.value);
      if (!isNaN(v) && v > 0) {
        clearTimeout(debounceTimer);
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
      btnEdit.disabled = true;
      const oldText = btnEdit.textContent;
      btnEdit.textContent = '…';

      try{
        const { meal } = await jsonFetch(`/api/meals/${id}`, {
          method: 'PUT',
          body: JSON.stringify({ quantity: newQty })
        });
        replaceInputWithSpan(input, meal.quantity);
        syncRowWithServer(row, meal);
        await refreshTotals();
      }catch(err){
        alert(err.message || 'No se pudo guardar la nueva cantidad');
        replaceInputWithSpan(input, oldQty);
        await refreshTotals();
      }finally{
        btnEdit.disabled = false;
        btnEdit.textContent = oldText;
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

  // --- Utilidades de UI para edición ----------------------------------------
  function previewRowScaling(row, baseQty, newQty){
    const ratio = (newQty / Math.max(0.01, baseQty || 1));
    const kcalEl = row.querySelector('.meal-calories');
    const pEl = row.querySelector('.meal-protein');
    const cEl = row.querySelector('.meal-carbs');
    const fEl = row.querySelector('.meal-fats');

    if (kcalEl) kcalEl.textContent = Math.max(0, Math.round(toNum(kcalEl.textContent) * ratio));
    if (pEl) pEl.textContent = Math.max(0, Math.round(toNum(pEl.textContent) * ratio));
    if (cEl) cEl.textContent = Math.max(0, Math.round(toNum(cEl.textContent) * ratio));
    if (fEl) fEl.textContent = Math.max(0, Math.round(toNum(fEl.textContent) * ratio));
  }

  function syncRowWithServer(row, meal){
    // cantidad
    const q = row.querySelector('.meal-quantity'); if (q) q.textContent = meal.quantity;
    // kcal
    const kcalEl = row.querySelector('.meal-calories'); if (kcalEl) kcalEl.textContent = meal.calories;
    // macros si llegan
    const pEl = row.querySelector('.meal-protein');
    const cEl = row.querySelector('.meal-carbs');
    const fEl = row.querySelector('.meal-fats');
    if (meal.protein !== undefined) { pEl ? (pEl.textContent = meal.protein) : null; row.dataset.protein = meal.protein; }
    if (meal.carbs   !== undefined) { cEl ? (cEl.textContent = meal.carbs)   : null; row.dataset.carbs   = meal.carbs; }
    if (meal.fats    !== undefined) { fEl ? (fEl.textContent = meal.fats)    : null; row.dataset.fats    = meal.fats; }
    // unidad (por si backend la envía)
    if (meal.food_default_unit || meal.food?.default_unit) {
      row.dataset.unit = meal.food_default_unit || meal.food.default_unit;
    }
  }

  // --- Primera carga ---------------------------------------------------------
  loadMeals();       // si no existe el endpoint, no rompe
  refreshTotals();   // intenta API; si no, suma lo pintado
});
