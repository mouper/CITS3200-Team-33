document.getElementById('open-dashboard')?.addEventListener('click', async () => {
  const url = chrome.runtime.getURL('ui/dashboard.html');
  await chrome.tabs.create({ url });
  window.close();
});

const toggleEl = document.getElementById('toggle-enabled');
const statusEl = document.getElementById('run-status');

const SERVER_BASE = 'http://127.0.0.1:5050';

async function api(path, opts = {}) {
  try {
    const res = await fetch(`${SERVER_BASE}${path}`, {
      method: opts.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { error: String(err) };
  }
}

async function getServerRunning() {
  const status = await api('/api/classifier/status');
  return Boolean(status && status.loop_running);
}

async function waitForServerState(targetRunning, timeoutMs = 1500, stepMs = 100) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const running = await getServerRunning();
    if (running === targetRunning) return running;
    await new Promise(r => setTimeout(r, stepMs));
  }
  return await getServerRunning();
}

async function readState() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['mellowEnabled'], (result) => {
      // Default to true if not set (first time usage)
      resolve(result.mellowEnabled !== undefined ? Boolean(result.mellowEnabled) : true);
    });
  });
}

async function writeState(enabled) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ mellowEnabled: enabled }, () => resolve());
  });
}

function renderStatus(enabled) {
  if (!statusEl) return;
  statusEl.textContent = enabled ? 'Running' : 'Stopped';
}

(async function init() {
  if (!toggleEl) return;
  // Ask server for actual status first
  let enabled = false;
  try {
    const status = await api('/api/classifier/status');
    enabled = Boolean(status && status.loop_running);
  } catch (_) {
    enabled = await readState();
  }
  toggleEl.checked = enabled;
  renderStatus(enabled);

  toggleEl.addEventListener('change', async () => {
    const next = toggleEl.checked;
    // Optimistic UI, but we'll immediately reconcile with server
    renderStatus(next);
    toggleEl.disabled = true;

    // Tell server to start/stop background worker
    const result = next
      ? await api('/api/classifier/start', { method: 'POST', body: {} })
      : await api('/api/classifier/stop', { method: 'POST' });

    let running;
    if (result && result.error) {
      running = !next; // failure -> revert to previous
    } else {
      // Wait briefly for background thread to flip state
      running = await waitForServerState(next);
    }

    toggleEl.checked = running;
    renderStatus(running);
    await writeState(running);
    toggleEl.disabled = false;
  });
})();

// Graph + category display (using shared graph module)
(async function initGraph() {
  try {
    const pill = document.getElementById('category-pill');
    if (!pill) return;

    // Read category selected in dashboard (if any). Fallback to 'Comedy' for demo
    const { selectedCategory } = await new Promise(resolve => chrome.storage?.local?.get(['selectedCategory'], resolve));
    const defaultCategory = selectedCategory || 'Comedy';
    console.log("🔍 Popup category selection:", { selectedCategory, defaultCategory });
    pill.textContent = defaultCategory;

    // Initialize shared graph
    let sharedGraph = null;

    async function initializeGraph() {
      if (typeof SharedGraph === 'undefined') {
        console.log("SharedGraph not ready, retrying in 100ms...");
        setTimeout(initializeGraph, 100);
        return;
      }

      sharedGraph = new SharedGraph('popupChart', 'category-pill', 4);
      await sharedGraph.initialize();
      await sharedGraph.updateChart(defaultCategory);
      
      console.log("✅ Popup graph initialized with shared module");
    }

    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeGraph);
    } else {
      initializeGraph();
    }

    // Listen for changes in selected category from dashboard
    chrome.storage.onChanged.addListener((changes, namespace) => {
      if (namespace === 'local' && changes.selectedCategory) {
        console.log("🔄 Category changed in dashboard, updating popup:", changes.selectedCategory.newValue);
        const newCategory = changes.selectedCategory.newValue || 'Comedy';
        pill.textContent = newCategory;
        if (sharedGraph) {
          sharedGraph.updateChart(newCategory);
        }
      }
    });

  } catch (error) {
    console.error("Error initializing popup graph:", error);
  }
})();


