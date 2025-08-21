// Placeholder for dashboard interactivity. Hook charts / data here.
console.log('Dashboard loaded');

// Placeholder for dashboard interactivity. Hook charts / data here.
console.log('Dashboard loaded');

// Dashboard bootstrap
(async () => {
  try {
    const nameEl = document.getElementById('user-first-name');
    if (!nameEl || !chrome?.identity) return;

    // Try cached name first
    const cached = await new Promise(resolve => chrome.storage?.local?.get(['userProfile'], resolve));
    if (cached?.userProfile?.given_name) {
      nameEl.textContent = cached.userProfile.given_name;
      return;
    }

    // Try OAuth userinfo
    chrome.identity.getAuthToken({ interactive: true }, async (token) => {
      if (!chrome.runtime.lastError && token) {
        try {
          const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const profile = await res.json();
            const firstName = profile?.given_name || profile?.name?.split(' ')[0] || 'User';
            nameEl.textContent = firstName;
            chrome.storage?.local?.set({ userProfile: profile });
            return;
          }
        } catch (_) { /* fall through */ }
      }

      // Fallback: derive name from profile email (requires identity.email)
      chrome.identity.getProfileUserInfo({ accountStatus: 'ANY' }, (info) => {
        if (chrome.runtime.lastError) return;
        const email = info?.email || '';
        const localPart = email.split('@')[0] || '';
        const firstGuess = localPart.split(/[._-]/)[0] || '';
        const pretty = firstGuess ? firstGuess.charAt(0).toUpperCase() + firstGuess.slice(1) : 'User';
        if (pretty) nameEl.textContent = pretty;
      });
    });
  } catch (_) { /* no-op */ }
})();


