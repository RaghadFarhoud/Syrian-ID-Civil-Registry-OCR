(function () {
  'use strict';

  const baked = globalThis.RELAY_CONFIG || {};

  const status = document.getElementById('status');
  const sendBtn = document.getElementById('sendBtn');
  const sendPrefixBtn = document.getElementById('sendPrefixBtn');
  const saveBtn = document.getElementById('saveBtn');
  const savedMsg = document.getElementById('savedMsg');
  const sBase = document.getElementById('sBase');
  const sPrefix = document.getElementById('sPrefix');
  const sOpen = document.getElementById('sOpen');
  const sOpenUrl = document.getElementById('sOpenUrl');

  let saved = {};

  function setStatus(html, cls) {
    status.className = 'status ' + cls;
    status.innerHTML = html;
    status.style.display = 'block';
  }

  function currentConfig() {
    return {
      baseUrl: sBase.value.trim() || baked.baseUrl || 'http://localhost:8000',
      targetTabPrefix: sPrefix.value.trim(),
      openTabIfMissing: sOpen.checked,
      openUrlIfMissing: sOpenUrl.value.trim(),
      fields: baked.fields || [],
    };
  }

  function saveSettings() {
    saved = {
      baseUrl: sBase.value.trim(),
      targetTabPrefix: sPrefix.value.trim(),
      openTabIfMissing: sOpen.checked,
      openUrlIfMissing: sOpenUrl.value.trim(),
    };
    return new Promise(function (resolve) {
      chrome.storage.local.set({ relaySettings: saved }, function () {
        const err = chrome.runtime.lastError;
        savedMsg.style.display = err ? 'block' : 'block';
        savedMsg.style.color = err ? '#dc2626' : '#16a34a';
        savedMsg.textContent = err ? 'خطأ في الحفظ: ' + err.message : '✓ تم الحفظ. الإعدادات تسري الآن.';
        resolve(!err);
      });
    });
  }

  function loadSettings() {
    return new Promise(function (resolve) {
      chrome.storage.local.get('relaySettings', function (got) {
        saved = (got && got.relaySettings) || {};
        sBase.value = saved.baseUrl || baked.baseUrl || 'http://localhost:8000';
        sPrefix.value = saved.targetTabPrefix !== undefined ? saved.targetTabPrefix : (baked.targetTabPrefix || '');
        sOpen.checked = saved.openTabIfMissing !== undefined ? saved.openTabIfMissing : !!baked.openTabIfMissing;
        sOpenUrl.value = saved.openUrlIfMissing || baked.openUrlIfMissing || '';
        resolve();
      });
    });
  }

  function send(mode) {
    const cfg = currentConfig();
    return fetch(cfg.baseUrl.replace(/\/+$/, '') + '/relay/last', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        const hasData = data && data.fields && Object.keys(data.fields).length > 0;
        if (!hasData) throw new Error('لا توجد نتيجة استخراج محفوظة بعد.');
        return new Promise(function (resolve) {
          chrome.runtime.sendMessage({ type: 'FILL', data: data, mode: mode }, function (res) {
            if (chrome.runtime.lastError) {
              res = { ok: false, error: chrome.runtime.lastError.message };
            }
            resolve(res || {});
          });
        });
      });
  }

  function renderResult(res, cfg) {
    if (!res.ok) {
      setStatus('فشل: ' + (res.errorText || res.error || 'خطأ غير معروف'), 'bad');
      return;
    }
    const filled = (res.filled || []).length;
    const missed = res.missed || [];
    const skipped = res.skipped || [];
    let html = 'تم ملء <b>' + filled + '</b>/' + (cfg.fields || []).length + ' حقل في «' + (res.tabUrl || '') + '».';
    if (skipped.length) html += '<br>فارغ/متجاهل: <b>' + skipped.join('، ') + '</b>';
    if (missed.length) html += '<br>لم يُملأ: <b>' + missed.join('، ') + '</b>';
    else if (!skipped.length) html += '<br>اكتمل التعبئة بنجاح.';
    setStatus(html, missed.length ? 'warn' : 'ok');
  }

  function wireButton(btn, mode) {
    btn.addEventListener('click', function () {
      btn.disabled = true;
      status.style.display = 'none';
      setStatus('جاري الإرسال...', 'warn');
      const cfg = currentConfig();
      send(mode)
        .then(function (res) { renderResult(res, cfg); })
        .catch(function (e) { setStatus('فشل الجلب: ' + (e && e.message || e), 'bad'); })
        .then(function () { btn.disabled = false; });
    });
  }

  saveBtn.addEventListener('click', function () {
    saveSettings();
  });

  loadSettings().then(function () {
    sendBtn.textContent = 'أرسل آخر استخراج إلى التاب النشط الآن ⇦';
    sendPrefixBtn.textContent = 'أرسل حسب إعداد "عنوان الموقع" أدناه';
    wireButton(sendBtn, 'active');
    wireButton(sendPrefixBtn, 'prefix');
  });
})();