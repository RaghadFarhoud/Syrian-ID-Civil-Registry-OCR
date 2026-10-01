// content-our.js — يعمل داخل صفحة التطبيق المحلي (localhost:8000)
// يلتقط حدث "نقل البيانات" من الصفحة ويرسله إلى الخلفية (background)
(function () {
  'use strict';

  function notifyPage(detail) {
    try {
      window.dispatchEvent(new CustomEvent('IDRELAY_RESPONSE', { detail: detail || {} }));
    } catch (e) { /* ignore */ }
  }

  window.addEventListener('IDRELAY_SEND', function (e) {
    var data = e.detail;
    var api = (typeof chrome !== 'undefined') ? chrome.runtime : null;

    if (!api || typeof api.sendMessage !== 'function') {
      // الوضع الآمن: لا يوجد chrome.runtime (كونتنت سكربت يعمل في عالم غير متوقع)
      notifyPage({ error: 'chromeUnavailable', errorText: 'إضافة ID Relay غير متاحة في هذا التاب.' });
      return;
    }

    try {
      api.sendMessage({ type: 'FILL', data: data, mode: 'prefix' }, function (res) {
        if (api.lastError) {
          res = { error: 'noReceiver', errorText: api.lastError.message };
        }
        notifyPage(res || {});
      });
    } catch (err) {
      notifyPage({ error: String(err && err.message || err) });
    }
  });
})();