// fill.js — محرك تعبئة النموذج في تاب الموقع الحقيقي
// يدعم:
//   - حقول input / textarea / select و contentEditable
//   - قوائم Angular Material (mat-select) عبر فتح القائمة والضغط على الخيار
//   - التنقل بين خطوات mat-stepper (إلا إذا كان الخطي يمنعها)
//   - خطوات تحضيرية (ensure): مثل زر "إضافة بطاقة جديدة" قبل الرقم الوطني
// لا يضغط أي زر حفظ/إرسال — تعبئة فقط.
(function () {
  'use strict';

  const cfg = globalThis.RELAY_CONFIG || {};
  const RESULT = {
    done: false,
    docType: '',
    filled: [],
    missed: [],
    skipped: [],
    errors: [],
    notes: [],
    visited: []
  };
  globalThis.RELAY_RESULT = RESULT;

  // ---------- أدوات نصية ----------
  function norm(s) {
    s = String(s === null || s === undefined ? '' : s).toLowerCase();
    s = s.replace(/[\u064B-\u0652\u0640]/g, ''); // تشكيل وتطويل
    s = s.replace(/[أإآٱ]/g, 'ا');
    s = s.replace(/ة/g, 'ه');
    s = s.replace(/ى/g, 'ي');
    s = s.replace(/ؤ/g, 'و');
    s = s.replace(/ئ/g, 'ي');
    s = s.replace(/[^\w\s\u0600-\u06FF]/g, '');
    s = s.replace(/\s+/g, ' ').trim();
    return s;
  }

  // مطابقة متدرجة: تساوٍ تام > بادئة > احتواء. أدق من المقارنة المنطقية القديمة.
  function labelScore(text, value) {
    const a = norm(text);
    const b = norm(value);
    if (!a || !b) return 0;
    if (a === b) return 3;
    if (a.indexOf(b) === 0 || b.indexOf(a) === 0) return 2;
    if (a.indexOf(b) !== -1 || b.indexOf(a) !== -1) return 1;
    return 0;
  }

  function bestLabelScore(labels, value) {
    let best = 0;
    for (let i = 0; i < labels.length; i++) {
      const sc = labelScore(labels[i], value);
      if (sc > best) best = sc;
    }
    return best;
  }

  // ---------- نوع المستند المستخرج ----------
  // يوحّد شكل document_type ويقبل الأسماء الشائعة interchangeably
  const DOCTYPE_ALIASES = {
    nationalid: 'national_id', national: 'national_id', id: 'national_id',
    idcard: 'national_id', id_card: 'national_id', 'بطاقة هوية': 'national_id',
    'الهوية': 'national_id', 'هوية': 'national_id',
    civilregistry: 'civil_registry', civil: 'civil_registry', registry: 'civil_registry',
    record: 'civil_registry', 'سجل مدني': 'civil_registry', 'قيد مدني': 'civil_registry',
    'السجل': 'civil_registry', 'السجل المدني': 'civil_registry'
  };

  function normDocType(t) {
    let s = String(t === null || t === undefined ? '' : t).trim().toLowerCase();
    s = s.replace(/[\s\-/.]+/g, '_');
    if (!s) return '';
    return Object.prototype.hasOwnProperty.call(DOCTYPE_ALIASES, s) ? DOCTYPE_ALIASES[s] : s;
  }

  // ---------- أدوات ----------
  function note(msg) {
    RESULT.notes.push(msg);
  }

  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  async function waitFor(fn, timeout, step) {
    const t = timeout || 4000;
    const s = step || 80;
    const t0 = Date.now();
    for (;;) {
      let v = null;
      try { v = fn(); } catch (e) { v = null; }
      if (v) return v;
      if (Date.now() - t0 > t) return null;
      await sleep(s);
    }
  }

  function win() {
    return (document.defaultView) || window;
  }

  function isVisible(el) {
    if (!el || !el.isConnected) return false;
    if (typeof el.checkVisibility === 'function') {
      try {
        if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
      } catch (e) { /* fallback below */ }
    }
    try {
      const st = win().getComputedStyle(el);
      if (!st) return false;
      if (st.display === 'none' || st.visibility === 'hidden' || st.visibility === 'collapse') return false;
      if (parseFloat(st.opacity) === 0) return false;
    } catch (e) {
      return false;
    }
    // عنصر أب مخفي (مثل محتوى خطوة mat-stepper غير المحددة: visibility:hidden)
    let p = el.parentElement;
    let guard = 0;
    while (p && p.nodeType === 1 && guard++ < 40) {
      try {
        const st = win().getComputedStyle(p);
        if (!st) return false;
        if (st.display === 'none' || st.visibility === 'hidden' || st.visibility === 'collapse') return false;
        if (parseFloat(st.opacity) === 0) return false;
      } catch (e) {
        return false;
      }
      p = p.parentElement;
    }
    try {
      const b = el.getBoundingClientRect();
      if (b.width <= 0 || b.height <= 0) return false;
    } catch (e) { /* تجاهل */ }
    return true;
  }

  function safeClick(el) {
    if (!el) return false;
    try {
      el.click();
      return true;
    } catch (e) {
      try {
        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: win() }));
        return true;
      } catch (e2) {
        return false;
      }
    }
  }

  // ---------- الحقول القابلة للتعبئة ----------
  const SKIP_TYPES = {
    hidden: 1, submit: 1, button: 1, reset: 1, image: 1,
    file: 1, checkbox: 1, radio: 1
  };

  function tagOf(el) {
    return (el && el.tagName ? el.tagName : '').toLowerCase();
  }

  function isFillable(el) {
    if (!el || !el.isConnected) return false;
    if (el.disabled) return false;
    if (el.getAttribute && el.getAttribute('disabled') !== null) return false;
    if (el.getAttribute && el.getAttribute('aria-disabled') === 'true') return false;
    if (el.classList && el.classList.contains('mat-select-disabled')) return false;
    const tag = tagOf(el);
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      return !SKIP_TYPES[t];
    }
    return tag === 'textarea' || tag === 'select' || tag === 'mat-select' || !!el.isContentEditable;
  }

  const CANDIDATE_SELECTOR =
    'input, textarea, select, mat-select, [contenteditable="true"], [contenteditable=""]';

  function candidates() {
    return Array.prototype.slice.call(document.querySelectorAll(CANDIDATE_SELECTOR)).filter(isFillable);
  }

  // ---------- قراءة التسميات ----------
  function elementLabels(el) {
    const labels = [];
    const add = function (v) { if (v) labels.push(String(v)); };

    try {
      if (el.labels && el.labels.length) {
        for (let i = 0; i < el.labels.length; i++) add(el.labels[i].textContent);
      }
    } catch (e) { /* تجاهل */ }

    try {
      if (el.id) {
        const lab = el.ownerDocument.querySelector('label[for="' + CSS.escape(el.id) + '"]');
        if (lab) add(lab.textContent);
      }
    } catch (e) { /* تجاهل */ }

    // تسمية Angular Material داخل mat-form-field
    try {
      const ff = el.closest && el.closest('mat-form-field');
      if (ff) {
        const lab = ff.querySelector('mat-label, label.mat-form-field-label, .mat-form-field-label');
        if (lab) add(lab.textContent);
        const hint = ff.querySelector('mat-hint');
        if (hint) add(hint.textContent);
      }
    } catch (e) { /* تجاهل */ }

    try {
      if (el.parentElement && tagOf(el.parentElement) === 'label') add(el.parentElement.textContent);
    } catch (e) { /* تجاهل */ }

    try {
      const tr = el.closest && el.closest('tr');
      if (tr) {
        const th = tr.querySelector('th');
        if (th) add(th.textContent);
      }
    } catch (e) { /* تجاهل */ }

    const attrs = ['placeholder', 'data-placeholder', 'aria-label', 'name', 'id', 'title'];
    for (let i = 0; i < attrs.length; i++) {
      const v = el.getAttribute && el.getAttribute(attrs[i]);
      if (v) add(v);
    }

    try {
      const by = el.getAttribute('aria-labelledby');
      if (by) {
        const parts = by.split(/\s+/);
        for (let i = 0; i < parts.length; i++) {
          const ref = el.ownerDocument.getElementById(parts[i]);
          if (ref) add(ref.textContent);
        }
      }
    } catch (e) { /* تجاهل */ }

    return labels;
  }

  function elementScore(el, def) {
    if (!def.labels || !def.labels.length) return 0;
    return bestLabelScore(elementLabels(el), def.labels);
  }

  // ---------- mat-stepper ----------
  function stepHeaders() {
    return Array.prototype.slice.call(document.querySelectorAll('mat-step-header'));
  }

  function currentStep() {
    const hs = stepHeaders();
    for (let i = 0; i < hs.length; i++) {
      if (hs[i].getAttribute('aria-selected') === 'true') return i;
    }
    const cs = Array.prototype.slice.call(document.querySelectorAll('.mat-vertical-stepper-content'));
    for (let i = 0; i < cs.length; i++) {
      if (cs[i].getAttribute('aria-expanded') === 'true') return i;
    }
    return 0;
  }

  // زر "التالي" الظاهر داخل الخطوة الحالية
  function visibleNextButton() {
    const btns = Array.prototype.slice.call(document.querySelectorAll('button[matsteppernext]'));
    for (let i = 0; i < btns.length; i++) {
      if (isVisible(btns[i]) && !btns[i].disabled) return btns[i];
    }
    return null;
  }

  async function goToStep(target) {
    const hs = stepHeaders();
    if (!hs.length) return true;                 // لا يوجد stepper
    if (target >= hs.length) return false;
    if (currentStep() === target) return true;

    // 1) الضغط على رأس الخطوة (mat-stepper غير الخطي يسمح بذلك)
    const before = currentStep();
    safeClick(hs[target]);
    const moved = await waitFor(function () { return currentStep() !== before ? true : null; }, 1200, 80);
    if (currentStep() === target) return true;
    if (moved) {
      // تقدّم أكثر من المطلوب (نادر) — ارجع بالضغط على الرأس المطلوب مرة أخرى
      safeClick(hs[target]);
      await sleep(400);
      if (currentStep() === target) return true;
    }

    // 2) احتياطي: 반복 الضغط على "التالي" (لو الـ stepper خطي)
    for (let n = 0; n < 12 && currentStep() !== target; n++) {
      const btn = visibleNextButton();
      if (!btn) break;
      safeClick(btn);
      const advanced = await waitFor(function () { return currentStep() !== target - 1 ? true : null; }, 900, 80);
      await sleep(320);
      if (currentStep() === target) return true;
      if (!advanced && currentStep() !== before + (n + 1)) {
        note('الخطوة ' + (target + 1) + ' محجوبة: زر «التالي» معطّل — أكمل بيانات الخطوة ' + (currentStep() + 1) + ' أولاً.');
        return false;
      }
    }
    return currentStep() === target;
  }

  // ---------- ضبط القيم ----------
  function setNativeValue(el, value) {
    const tag = tagOf(el);
    const proto = tag === 'select' ? win().HTMLSelectElement.prototype
      : tag === 'textarea' ? win().HTMLTextAreaElement.prototype
        : win().HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value');
    if (setter && setter.set) setter.set.call(el, value);
    else el.value = value;
  }

  function setSelectValue(el, value) {
    const v = String(value).trim();
    setNativeValue(el, v);
    if (el.value !== v) {
      const opts = el.querySelectorAll('option');
      for (let i = 0; i < opts.length; i++) {
        if (labelScore(opts[i].textContent, v) === 3 || opts[i].value === v) {
          setNativeValue(el, opts[i].value);
          break;
        }
      }
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function setContentEditable(el, value) {
    try { el.focus(); } catch (e) { /* تجاهل */ }
    el.innerText = value;
    try {
      el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
    } catch (e) {
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function applyValue(el, value) {
    const tag = tagOf(el);
    if (el.isContentEditable) return setContentEditable(el, value);
    if (tag === 'select') return setSelectValue(el, value);
    if (tag === 'mat-select') throw new Error('mat-select requires opening the panel');
    setNativeValue(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: false }));
    try { if (el.ownerDocument.activeElement === el) el.blur(); } catch (e) { /* تجاهل */ }
  }

  // ---------- قوائم mat-select ----------
  function readMatSelectValue(el) {
    const t = el.querySelector('.mat-select-value-text');
    return t ? String(t.textContent || '').trim() : '';
  }

  function openOptions() {
    return Array.prototype.slice
      .call(document.querySelectorAll('mat-option'))
      .filter(function (o) {
        return isVisible(o) &&
          o.getAttribute('aria-disabled') !== 'true' &&
          !(o.classList && (o.classList.contains('cdk-option-disabled') || o.classList.contains('mat-option-disabled')));
      });
  }

  function closeOverlay() {
    const panes = document.querySelectorAll('.cdk-overlay-pane, .cdk-overlay-container');
    for (let i = 0; i < panes.length; i++) {
      try {
        panes[i].dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
      } catch (e) { /* تجاهل */ }
    }
  }

  // الخيارات التي كانت معروضة فعلاً في آخر قائمة لم يُطابقها الطلب (للتشخيص)
  let MATSELECT_AVAILABLE = null;

  async function fillMatSelect(el, value) {
    const desired = String(value).trim();
    MATSELECT_AVAILABLE = null;
    if (labelScore(readMatSelectValue(el), desired) === 3) return true; // مضبوط أصلاً

    const opened = safeClick(el);
    const opts = await waitFor(function () {
      const o = openOptions();
      return o.length ? o : null;
    }, opened ? 3500 : 800);
    if (!opts) {
      closeOverlay();
      return false;
    }

    let target = null;
    let best = 0;
    for (let i = 0; i < opts.length; i++) {
      const sc = labelScore(opts[i].textContent, desired);
      if (sc > best) { best = sc; target = opts[i]; }
    }
    if (!target) {
      MATSELECT_AVAILABLE = opts.map(function (o) { return String(o.textContent || '').trim(); });
      closeOverlay();
      return false;
    }
    try { target.scrollIntoView({ block: 'nearest' }); } catch (e) { /* تجاهل */ }
    await sleep(80);
    safeClick(target);
    await waitFor(function () { return document.querySelector('mat-option') ? null : true; }, 2500);
    await sleep(150);
    return labelScore(readMatSelectValue(el), desired) > 0;
  }

  // ---------- البحث عن العنصر ----------
  function resolveElement(def) {
    if (def.selectors && def.selectors.length) {
      for (let i = 0; i < def.selectors.length; i++) {
        let node = null;
        try { node = document.querySelector(def.selectors[i]); } catch (e) { node = null; }
        if (node) return node;
      }
    }
    if (cfg.autodetectLabels !== false && def.labels && def.labels.length) {
      let bestEl = null;
      let bestScore = 0;
      candidates().forEach(function (el) {
        const sc = elementScore(el, def);
        if (sc > bestScore) { bestScore = sc; bestEl = el; }
      });
      if (bestEl) return bestEl;
    }
    return null;
  }

  // يبحث عن العنصر، وإن لم يجده ينفّذ خطوات ensure (أزرار تحضيرية) ثم يعيد البحث
  async function locate(def) {
    let el = resolveElement(def);
    if (el) return el;
    if (def.ensure && def.ensure.length) {
      for (let i = 0; i < def.ensure.length; i++) {
        let btn = null;
        try { btn = document.querySelector(def.ensure[i]); } catch (e) { btn = null; }
        if (!btn) continue;
        if (!safeClick(btn)) continue;
        el = await waitFor(function () { return resolveElement(def); }, 3000, 100);
        if (el) return el;
      }
    }
    return null;
  }

  // قيمة الحقل: قد تكون ثابتة، أو تعتمد على نوع المستند المستخرج، أو تأتي من الاستخراج
  function valueFor(def, ctx) {
    if (def.valueByDocumentType && typeof def.valueByDocumentType === 'object') {
      const map = def.valueByDocumentType;
      const dt = normDocType(ctx.docType);
      const mapped = dt ? map[dt] : undefined;
      if (mapped !== undefined && String(mapped).trim() !== '') return String(mapped);
    }
    if (def.value !== undefined && def.value !== null && String(def.value).trim() !== '') {
      return String(def.value);
    }
    return ctx.fields[def.key];
  }

  // ---------- تعبئة حقل واحد ----------
  async function fillOne(def, ctx) {
    const key = def.key;
    if (RESULT.filled.indexOf(key) !== -1) return;
    if (Array.isArray(def.exclude) && def.exclude.indexOf(key) !== -1) return;

    const raw = valueFor(def, ctx);
    if (raw === undefined || raw === null || String(raw).trim() === '') {
      RESULT.skipped.push(key);
      return;
    }
    const textValue = String(raw).trim();

    const el = await locate(def);
    if (!el) { RESULT.missed.push(key); return; }

    const tag = tagOf(el);
    try {
      if (tag === 'mat-select') {
        if (!isVisible(el)) return;                       // نحاول لاحقاً/في المسح
        const done = await fillMatSelect(el, textValue);
        if (done) {
          RESULT.filled.push(key);
        } else {
          RESULT.missed.push(key);
          if (MATSELECT_AVAILABLE) {
            RESULT.notes.push('القيمة "' + textValue + '" غير موجودة في قائمة "' + key +
              '". المتاح: ' + MATSELECT_AVAILABLE.slice(0, 12).join(' | '));
          }
        }
        return;
      }
      applyValue(el, textValue);
      RESULT.filled.push(key);
    } catch (e) {
      RESULT.missed.push(key);
      RESULT.errors.push(key + ': ' + String((e && e.message) || e));
    }
  }

  // مسح أخير: يملأ حقول input/textarea حتى لو كانت داخل خطوة مخفية
  // (Angular يحدّث النموذج من حدث input حتى لو كان العنصر غير مرئي)
  async function sweep(defs, ctx) {
    if (cfg.sweepHidden === false) return;
    for (let i = 0; i < defs.length; i++) {
      const def = defs[i];
      const key = def.key;
      if (RESULT.filled.indexOf(key) !== -1) continue;
      if (Array.isArray(def.exclude) && def.exclude.indexOf(key) !== -1) continue;
      const raw = valueFor(def, ctx);
      if (raw === undefined || raw === null || String(raw).trim() === '') continue;
      const textValue = String(raw).trim();

      const el = await locate(def);
      if (!el) continue;
      const tag = tagOf(el);
      if (tag === 'mat-select') {
        // القوائم تحتاج فتح اللوح، ولا يمكن فتحها داخل خطوة مخفية → أبلغ المستخدم
        if (RESULT.missed.indexOf(key) === -1) {
          RESULT.missed.push(key);
          RESULT.notes.push('القائمة "' + key + '" داخل خطوة لم نتمكن من فتحها — افتح الخطوة يدوياً ثم أعد النقل.');
        }
        continue;
      }
      if (!isFillable(el)) continue;
      try {
        applyValue(el, textValue);
        RESULT.filled.push(key);
        RESULT.notes.push('حقل "' + key + '" مملوء داخل خطوة مخفية (بدون فتح قائمة) — سيظهر عند تنقلك لتلك الخطوة.');
      } catch (e) {
        RESULT.errors.push('sweep ' + key + ': ' + String((e && e.message) || e));
      }
    }
  }

  // ---------- التشغيل ----------
  async function run() {
    let data = null;
    try {
      const base = (cfg.baseUrl || 'http://localhost:8000').replace(/\/+$/, '');
      const r = await fetch(base + '/relay/last', { cache: 'no-store' });
      data = await r.json();
    } catch (e) {
      RESULT.errors.push('تعذر جلب البيانات من ' + (cfg.baseUrl || 'http://localhost:8000'));
      RESULT.errors.push(String((e && e.message) || e));
    }

    const ctx = {
      fields: (data && data.fields) || {},
      docType: (data && data.document_type) || ''
    };
    RESULT.docType = normDocType(ctx.docType);
    const defs = cfg.fields || [];
    const hs = stepHeaders();

    if (!hs.length) {
      for (let i = 0; i < defs.length; i++) await fillOne(defs[i], ctx);
    } else {
      for (let s = 0; s < hs.length; s++) {
        const ok = await goToStep(s);
        if (!ok) {
          note('توقّفنا عند الخطوة ' + (s + 1) + ' من ' + hs.length + '.');
          break;
        }
        RESULT.visited.push(s + 1);
        for (let i = 0; i < defs.length; i++) await fillOne(defs[i], ctx);
      }
    }

    await sweep(defs, ctx);
    RESULT.done = true;
  }

  run().catch(function (e) {
    RESULT.errors.push('خطأ عام: ' + String((e && e.message) || e));
    RESULT.done = true;
  });
})();
