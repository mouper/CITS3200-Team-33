document.getElementById('open-dashboard')?.addEventListener('click', async () => {
  const url = chrome.runtime.getURL('ui/dashboard.html');
  await chrome.tabs.create({ url });
  window.close();
});


