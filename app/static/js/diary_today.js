// app/static/js/diary_today.js
(function () {
  const fmt = (n) => (Math.round((n ?? 0) * 10) / 10).toString();

  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('todayDate').textContent = today;

  const els = {
    btnUseBreakfast: document.getElementById('btnUseBreakfast'),
    btnReload: document.getElementById('btnReload'),
    breakfastList: document.getElementById('breakfastList'),
    breakfastEmpty: document.getElementById('breakfastEmpty'),
    breakfastTotals: document.getElementById('breakfastTotals'),
    dayTotals: document.getElementById('dayTotals'),
    // modal
    subModal: document.getElementById('subModal'),
    subForm: document.getElementById('subForm'),
    subSlotId: document.getElementById('subSlotId'),
    subName: document.getElementById('subName'),
    subQty: document.getElementById('subQty'),
    subUnit: document.getElementById('subUnit'),
    subKcal: document.getElementById('subKcal'),
    subCho: document.getElementById('subCho'),
    subPro: document.getElementById('subPro'),
    subFat: document.getElementById('subFat'),
  };

  const bsModal = new bootstrap.Modal(els.subModal);

  async function loadDay() {
    const res = await fetch(`/api/diary/day?date=${today}`);
    const json = await res.json();

    const meals = json?.data?.meals || {};
    const breakfast = meals['desayuno'] || { items: [], totals: { kcal: 0, cho_g: 0, pro_g: 0, fat_g: 0 } };

    els.breakfastList.innerHTML = '';
    if (!breakfast.items.length) {
      els.breakfastEmpty.classList.remove('d-none');
    } else {
      els.breakfastEmpty.classList.add('d-none');
      breakfast.items.forEach(it => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
          <div>
            <div class="fw-semibold">${it.food_name}</div>
            <div class="text-muted small">${fmt(it.serving_qty)} ${it.unit} · ${fmt(it.kcal)} kcal 
              — C:${fmt(it.cho_g)}g P:${fmt(it.pro_g)}g G:${fmt(it.fat_g)}g
            </div>
          </div>
          <div>
            ${it.slot_id ? `<button class="btn btn-sm btn-outline-primary" data-sub slot="${it.slot_id}">Sustituir</button>` : ''}
          </div>
        `;
        // botón sustituir
        const btn = li.querySelector('[data-sub]');
        if (btn) {
          btn.addEventListener('click', () => {
            els.subSlotId.value = it.slot_id;
            els.subName.value = '';
            els.subQty.value = it.serving_qty;
            els.subUnit.value = it.unit || 'g';
            els.subKcal.value = it.kcal;
            els.subCho.value = it.cho_g;
            els.subPro.value = it.pro_g;
            els.subFat.value = it.fat_g;
            bsModal.show();
          });
        }
        els.breakfastList.appendChild(li);
      });
    }

    els.breakfastTotals.textContent =
      `Kcal ${fmt(breakfast.totals.kcal)} · C ${fmt(breakfast.totals.cho_g)}g · P ${fmt(breakfast.totals.pro_g)}g · G ${fmt(breakfast.totals.fat_g)}g`;

    const dt = json?.data?.day_totals || { kcal: 0, cho_g: 0, pro_g: 0, fat_g: 0 };
    els.dayTotals.textContent =
      `Kcal ${fmt(dt.kcal)} · Carbs ${fmt(dt.cho_g)}g · Proteínas ${fmt(dt.pro_g)}g · Grasas ${fmt(dt.fat_g)}g`;
  }

  // Usar desayuno base → aplica y recarga
  els.btnUseBreakfast.addEventListener('click', async () => {
    await fetch('/api/diary/apply-base', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meal_type: 'desayuno', date: today })
    }).then(r => r.json());
    loadDay();
  });

  els.btnReload.addEventListener('click', loadDay);

  // Envío del modal de sustitución
  els.subForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      food_name: els.subName.value || 'Alimento',
      unit: els.subUnit.value || 'g',
      serving_qty: Number(els.subQty.value || 0),
      kcal: Number(els.subKcal.value || 0),
      cho_g: Number(els.subCho.value || 0),
      pro_g: Number(els.subPro.value || 0),
      fat_g: Number(els.subFat.value || 0),
      meal_type: 'desayuno',
      date: today
    };
    const slotId = els.subSlotId.value;
    await fetch(`/api/diary/slot/${slotId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());
    bsModal.hide();
    loadDay();
  });

  // Primera carga
  loadDay();
})();
