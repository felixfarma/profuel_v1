// app/static/js/home_index.js
(function () {
  const today = new Date().toISOString().slice(0,10);
  const $ = (id) => document.getElementById(id);
  const clamp = (n) => Math.max(0, Math.min(100, n));

  $('todayDate').textContent = today;

  function setBar(barId, textId, value, target, unit = '') {
    const pct = target > 0 ? clamp((value / target) * 100) : 0;
    $(barId).style.width = pct + '%';
    $(textId).textContent = `${Math.round(value)}${unit} / ${Math.round(target)}${unit}`;
  }

  async function loadOverview() {
    const res = await fetch(`/api/day/overview?date=${today}`);
    if (!res.ok) return;
    const j = await res.json();
    const data = j?.data || {};

    const rings = data.rings || {};
    const tgt = rings.target || {kcal:0,cho_g:0,pro_g:0,fat_g:0};
    const con = rings.consumed || {kcal:0,cho_g:0,pro_g:0,fat_g:0};

    setBar('kcalBar', 'kcalText', con.kcal||0, tgt.kcal||0, '');
    setBar('choBar',  'choText',  con.cho_g||0, tgt.cho_g||0, ' g');
    setBar('proBar',  'proText',  con.pro_g||0, tgt.pro_g||0, ' g');
    setBar('fatBar',  'fatText',  con.fat_g||0, tgt.fat_g||0, ' g');

    // Contexto de entreno
    const ctx = data.training_context || {phase:'neutral', basis:'none'};
    const phaseMap = { pre: 'Preentreno', post: 'Postentreno', neutral: 'Comida estándar' };
    $('trainContext').textContent = `${phaseMap[ctx.phase] || 'Comida estándar'}`;

    // Top recomendación
    const top = data.recommendations?.top;
    if (top) {
      $('topRecBlock').classList.remove('d-none');
      $('noRecBlock').classList.add('d-none');
      $('topRecTitle').textContent = `${capitalize(top.meal_type)} · ${top.title} (${top.fit_score}/100)`;
      $('topRecWhy').textContent = (top.reasons || []).join(' · ');
      $('btnUseTop').onclick = async () => {
        await fetch('/api/diary/apply-base', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ meal_type: top.meal_type, date: today })
        });
        // Pequeña confirmación y refresco
        $('btnUseTop').disabled = true;
        $('btnUseTop').textContent = 'Añadido ✓';
        setTimeout(() => { $('btnUseTop').disabled = false; $('btnUseTop').textContent = 'Usar ahora'; }, 1500);
        loadOverview();
      };
    } else {
      $('topRecBlock').classList.add('d-none');
      $('noRecBlock').classList.remove('d-none');
    }
  }

  function capitalize(s){ return (s||'').charAt(0).toUpperCase()+ (s||'').slice(1); }

  loadOverview();
})();
