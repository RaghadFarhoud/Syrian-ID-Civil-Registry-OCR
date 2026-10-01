// background.js — نقطة توجيه ناقل البيانات
// config.js (مولّد من .env) = القيم الأساسية،
// إعدادات chrome.storage التي يحفظها المستخدم من النافذة المنبثقة = تتجاوزها.
importScripts('config.js');

function log(msg) {
  console.log('[IDRelay]', msg);
}

// الإعدادات الفعلية = الأساس + ما حفظه المستخدم في المتصفح
async function resolveConfig() {
  const baked = (typeof self !== 'undefined' && self.RELAY_CONFIG) || {};
  try {
    const got = await chrome.storage.local.get('relaySettings');
    const saved = got && got.relaySettings ? got.relaySettings : {};
    return {
      baseUrl: saved.baseUrl || baked.baseUrl || 'http://localhost:8000',
      targetTabPrefix: (saved.targetTabPrefix !== undefined ? saved.targetTabPrefix : baked.targetTabPrefix) || '',
      openTabIfMissing: saved.openTabIfMissing !== undefined ? saved.openTabIfMissing : !!baked.openTabIfMissing,
      openUrlIfMissing: saved.openUrlIfMissing || baked.openUrlIfMissing || '',
      fillOnly: baked.fillOnly !== false,
      autodetectLabels: baked.autodetectLabels !== false,
      fillWhenVisible: baked.fillWhenVisible !== false,
      scanFrames: baked.scanFrames !== false,
      skipEmptyValues: baked.skipEmptyValues !== false,
      sweepHidden: baked.sweepHidden !== false,
      fields: baked.fields || [],
    };
  } catch (e) {
    return baked;
  }
}

function findTabByPrefix(prefix) {
  return new Promise(function (resolve) {
    if (!prefix) return resolve(null);
    chrome.tabs.query({}, function (tabs) {
      const found = (tabs || []).filter((t) => t.url && t.url.indexOf(prefix) === 0);
      found.sort((a, b) => ((b.active ? 1 : 0) - (a.active ? 1 : 0)));
      resolve(found.length ? found[0] : null);
    });
  });
}

function getActiveTab() {
  return new Promise(function (resolve) {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      resolve(tabs && tabs.length ? tabs[0] : null);
    });
  });
}

function openUrl(url) {
  return new Promise(function (resolve) {
    chrome.tabs.create({ url: url, active: true }, function (tab) {
      const timeout = setTimeout(() => resolve(tab), 20000);
      chrome.tabs.onUpdated.addListener(function listener(tabId, change) {
        if (tabId === tab.id && change.status === 'complete') {
          clearTimeout(timeout);
          chrome.tabs.onUpdated.removeListener(listener);
          resolve(tab);
        }
      });
    });
  });
}

function focusTab(tabId) {
  chrome.tabs.update(tabId, { active: true });
}

function injectAndWait(tabId, cfg) {
  const target = { tabId: tabId, allFrames: !!cfg.scanFrames };

  return chrome.scripting
    .executeScript({ target: target, files: ['config.js', 'fill.js'] })
    .then(function (results) {
      const frameIds = (results || []).map((r) => r.frameId);
      if (!frameIds.length) frameIds.push(0);
      return pollResults(tabId, frameIds);
    });
}

function pollResults(tabId, frameIds) {
  return new Promise(function (resolve, reject) {
    // التعبئة قد تتنقل بين خطوات mat-stepper وتفتح قوائم، sozّع المهلة.
    const attempts = 400;
    const interval = 150;
    let count = 0;

    const poll = function () {
      chrome.scripting
        .executeScript({
          target: { tabId: tabId, frameIds: frameIds },
          func: function () {
            var r = globalThis.RELAY_RESULT;
            return r ? JSON.stringify(r) : null;
          },
        })
        .then(function (res) {
          const got = [];
          let allDone = (res || []).length > 0;
          (res || []).forEach(function (frame) {
            if (frame.result) {
              try {
                const parsed = JSON.parse(frame.result);
                got.push(parsed);
                if (!parsed.done) allDone = false;
              } catch (e) { /* تجاهل */ }
            } else {
              allDone = false;
            }
          });
          if (allDone || ++count >= attempts) {
            resolve(mergeResults(got));
          } else {
            setTimeout(poll, interval);
          }
        })
        .catch(reject);
    };

    poll();
  });
}

function mergeResults(frames) {
  const out = { docType: '', filled: [], missed: [], skipped: [], notes: [], errors: [], visited: [] };
  const seen = {};
  const add = function (bucket, name) {
    if (!name) return;
    if (seen[bucket + '::' + name]) return;
    seen[bucket + '::' + name] = true;
    out[bucket].push(name);
  };
  frames.forEach(function (f) {
    if (!out.docType && f.docType) out.docType = f.docType;
    ['filled', 'missed', 'skipped', 'notes', 'errors', 'visited'].forEach(function (key) {
      (f[key] || []).forEach(function (name) { add(key, name); });
    });
  });
  out.visited.sort(function (a, b) { return a - b; });
  return out;
}

async function handleFill(data, mode) {
  const cfg = await resolveConfig();
  let tab = null;

  if (mode === 'active') {
    tab = await getActiveTab();
    if (!tab) {
      return { ok: false, error: 'noActiveTab', errorText: 'لا يوجد تاب نشط.' };
    }
  } else {
    const prefix = cfg.targetTabPrefix;
    tab = await findTabByPrefix(prefix);
    if (!tab) {
      if (cfg.openTabIfMissing) {
        tab = await openUrl(cfg.openUrlIfMissing || prefix);
      } else {
        return {
          ok: false,
          error: 'tabNotFound',
          errorText:
            'لم يُعثر على تاب يبدأ عنوانه بالـ "' + prefix +
            '". افتح صفحة الإدخال، أو فعّل "فتح عند الغياب"، أو استخدم زر "أرسل إلى التاب النشط".',
        };
      }
    }
  }

  focusTab(tab.id);

  try {
    const result = await injectAndWait(tab.id, cfg);
    return {
      ok: true,
      docType: result.docType || '',
      filled: result.filled,
      missed: result.missed,
      skipped: result.skipped,
      notes: result.notes,
      errors: result.errors,
      visited: result.visited,
      tabId: tab.id,
      tabUrl: tab.url || '',
    };
  } catch (e) {
    log('inject failed', e);
    return {
      ok: false,
      error: String(e && e.message ? e.message : e),
      errorText:
        'تعذّر حقن التعبئة في «' + (tab.url || '') + '». تأكد أن الصفحة محمّلة وأنك في وضع Chrome.',
    };
  }
}

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (msg && msg.type === 'FILL') {
    handleFill(msg.data, msg.mode || 'prefix')
      .then(sendResponse)
      .catch(function (err) {
        sendResponse({ ok: false, error: String((err && err.message) || err) });
      });
    return true; // استجابة غير متزامنة
  }
  return false;
});