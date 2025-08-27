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

// Graph + category display (placeholder chart)
(async function initGraph() {
  try {
    const pill = document.getElementById('category-pill');
    const canvas = document.getElementById('popupChart');
    if (!canvas || !pill) return;

    // Read category selected in dashboard (if any). Fallback to 'All'
    const { selectedCategory } = await new Promise(resolve => chrome.storage?.local?.get(['selectedCategory'], resolve));
    pill.textContent = selectedCategory || 'All';

    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Axes grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
      const y = (h / 5) * i;
      ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(w - 10, y); ctx.stroke();
    }

    // Placeholder data (smooth-ish)
    const points = [
      [40, 120],[80,60],[120,90],[160,50],[200,120],[240,30],[280,110],[320,90],[360,100],[400,80],[440,30],[480,100],[520,150]
    ];

    // Gradient stroke similar to accent
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, 'rgba(232,103,90,0.8)');
    grad.addColorStop(1, 'rgba(255,255,255,0.9)');

    ctx.lineWidth = 3;
    ctx.strokeStyle = grad;
    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
      const [x, y] = points[i];
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Soft fill under curve
    const fillGrad = ctx.createLinearGradient(0, 0, 0, h);
    fillGrad.addColorStop(0, 'rgba(232,103,90,0.12)');
    fillGrad.addColorStop(1, 'rgba(232,103,90,0.02)');
    ctx.fillStyle = fillGrad;
    ctx.lineTo(points[points.length - 1][0], h - 10);
    ctx.lineTo(points[0][0], h - 10);
    ctx.closePath();
    ctx.fill();
  } catch (_) { /* no-op for placeholder */ }
})();


