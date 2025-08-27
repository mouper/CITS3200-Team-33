document.getElementById('open-dashboard')?.addEventListener('click', async () => {
  const url = chrome.runtime.getURL('ui/dashboard.html');
  await chrome.tabs.create({ url });
  window.close();
});

const toggleEl = document.getElementById('toggle-enabled');
const statusEl = document.getElementById('run-status');

async function readState() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['mellowEnabled'], (result) => {
      resolve(Boolean(result.mellowEnabled));
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
  const enabled = await readState();
  toggleEl.checked = enabled;
  renderStatus(enabled);

  toggleEl.addEventListener('change', async () => {
    const next = toggleEl.checked;
    await writeState(next);
    renderStatus(next);
  });
})();


