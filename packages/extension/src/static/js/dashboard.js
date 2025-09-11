// Placeholder for dashboard interactivity. Hook charts / data here.
console.log("Dashboard loaded");

// Placeholder for dashboard interactivity. Hook charts / data here.
console.log("Dashboard loaded");

// Dashboard bootstrap
(async () => {
  try {
    // Backend readiness ping
    try {
      const res = await fetch("http://127.0.0.1:5050/health", {
        method: "GET",
      });
      const ok = res?.ok;
      const wrap = document.getElementById("backend-health");
      const textEl = document.getElementById("backend-health-text");
      if (wrap && textEl) {
        wrap.classList.remove("status-online", "status-offline");
        wrap.classList.add(ok ? "status-online" : "status-offline");
        textEl.textContent = ok ? "Backend: Online" : "Backend: Offline";
      }
    } catch (_) {
      const wrap = document.getElementById("backend-health");
      const textEl = document.getElementById("backend-health-text");
      if (wrap && textEl) {
        wrap.classList.remove("status-online");
        wrap.classList.add("status-offline");
        textEl.textContent = "Backend: Offline";
      }
    }

    const nameEl = document.getElementById("user-first-name");
    if (!nameEl || !chrome?.identity) return;

    // Try cached name first
    const cached = await new Promise((resolve) =>
      chrome.storage?.local?.get(["userProfile"], resolve)
    );
    if (cached?.userProfile?.given_name) {
      nameEl.textContent = cached.userProfile.given_name;
      return;
    }

    // Try OAuth userinfo
    chrome.identity.getAuthToken({ interactive: true }, async (token) => {
      if (!chrome.runtime.lastError && token) {
        try {
          const res = await fetch(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            {
              headers: { Authorization: `Bearer ${token}` },
            }
          );
          if (res.ok) {
            const profile = await res.json();
            const firstName =
              profile?.given_name || profile?.name?.split(" ")[0] || "User";
            nameEl.textContent = firstName;
            chrome.storage?.local?.set({ userProfile: profile });
            return;
          }
        } catch (_) {
          /* fall through */
        }
      }

      // Fallback: derive name from profile email (requires identity.email)
      chrome.identity.getProfileUserInfo({ accountStatus: "ANY" }, (info) => {
        if (chrome.runtime.lastError) return;
        const email = info?.email || "";
        const localPart = email.split("@")[0] || "";
        const firstGuess = localPart.split(/[._-]/)[0] || "";
        const pretty = firstGuess
          ? firstGuess.charAt(0).toUpperCase() + firstGuess.slice(1)
          : "User";
        if (pretty) nameEl.textContent = pretty;
      });
    });
  } catch (_) {
    /* no-op */
  }
})();

// Settings API client
const SERVER_BASE = "http://127.0.0.1:5050";
async function api(path, opts = {}) {
  try {
    const res = await fetch(`${SERVER_BASE}${path}`, {
      method: opts.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn("API error", path, e);
    return null;
  }
}

// Utility to sync slider fill percent
function setSliderFill(sliderEl) {
  const min = parseInt(sliderEl.min || "0", 10);
  const max = parseInt(sliderEl.max || "100", 10);
  const val = parseInt(sliderEl.value || String(min), 10);
  const pct = ((val - min) * 100) / (max - min);
  sliderEl.style.setProperty("--fill", pct + "%");
}

// Helpers to wire behaviors for a settings card by category key
function wireCardBehaviorsByCategory(category) {
  const esc = CSS.escape(category);
  // Toggle body
  const toggle = document.querySelector(`[data-category="${esc}"] .settings-toggle`);
  const body = document.querySelector(`[data-category="${esc}"] .settings-body`);
  if (toggle && body) {
    const apply = () => body.classList.toggle("hidden", !toggle.checked);
    apply();
    toggle.addEventListener("change", async () => {
      apply();
      // Persist toggle state
      const currentStrength = getStrengthLabelByCategory(category);
      await api(`/api/settings/${encodeURIComponent(category)}`, {
        method: "POST",
        body: { filter_strength: currentStrength, is_active: toggle.checked },
      });
    });
  }

  // Slider behavior
  const slider = document.querySelector(`[data-category="${esc}"] .strength-slider`);
  const label = document.querySelector(`[data-category="${esc}"] .strength-label`);
  const group = document.querySelector(`[data-category="${esc}"] .strength-group`);
  const yesRadio = document.querySelector(`[data-category="${esc}"] .radio-yes`);
  const noRadio = document.querySelector(`[data-category="${esc}"] .radio-no`);
  if (!slider || !label || !group || !yesRadio || !noRadio) return;

  const showGroup = () => group.classList.remove("hidden");
  const hideGroup = () => group.classList.add("hidden");

  const applyState = (val) => {
    showGroup();
    label.classList.remove("is-weak", "is-moderate", "is-strong");

    if (val === 1) {
      label.textContent = "Weak";
      label.classList.add("is-weak");
      noRadio.checked = true;
    } else if (val === 2) {
      label.textContent = "Moderate";
      label.classList.add("is-moderate");
      noRadio.checked = true;
    } else if (val === 3) {
      label.textContent = "Strong";
      label.classList.add("is-strong");
      noRadio.checked = true;
    } else if (val === 4) {
      yesRadio.checked = true;
      hideGroup();
    }

    setSliderFill(slider);
  };

  // Init
  setSliderFill(slider);
  applyState(parseInt(slider.value, 10));

  slider.addEventListener("input", (e) => {
    const v = parseInt(e.target.value, 10);
    applyState(v);
  });
  slider.addEventListener("change", async (e) => {
    // Persist strength change
    const strength = getStrengthLabelByCategory(category);
    const isActive = Boolean(toggle?.checked);
    await api(`/api/settings/${encodeURIComponent(category)}`, {
      method: "POST",
      body: { filter_strength: strength, is_active: isActive },
    });
  });
  yesRadio.addEventListener("change", () => {
    if (yesRadio.checked) {
      slider.value = "4";
      applyState(4);
      // Persist Extra Strong when blocking all
      api(`/api/settings/${encodeURIComponent(category)}`, {
        method: "POST",
        body: { filter_strength: "Extra Strong", is_active: true },
      });
    }
  });
  noRadio.addEventListener("change", () => {
    if (noRadio.checked) {
      if (parseInt(slider.value, 10) === 4) slider.value = "3";
      applyState(parseInt(slider.value, 10));
      // Persist current strength when unblocking all
      api(`/api/settings/${encodeURIComponent(category)}`, {
        method: "POST",
        body: { filter_strength: getStrengthLabelByCategory(category), is_active: true },
      });
    }
  });
}

// Render settings cards dynamically
async function renderSettingsCards() {
  const container = document.getElementById("cards-categories");
  if (!container) return;

  const data = await api("/api/settings");
  const items = (data?.items || []).filter((i) => i.is_active);
  container.innerHTML = "";

  for (const row of items) {
    const slug = slugify(row.category);
    const card = document.createElement("article");
    card.className = "card settings-card";
    card.setAttribute("data-category", row.category);
    card.innerHTML = `
      <div class="card-header">
        <div class="header-left">
          <div class="icon-box"><img class="icon-svg" src="../static/assets/category.svg" alt="" /></div>
          <div class="header-text">
            <div class="category-header">${row.category}</div>
            <p class="category-desc"></p>
          </div>
        </div>
        <div class="toggle-switch">
          <input type="checkbox" id="toggle-${slug}" class="settings-toggle" ${row.is_active ? "checked" : ""} />
          <label for="toggle-${slug}"></label>
        </div>
      </div>
      <div class="settings-body">
        <div class="setting-group">
          <div class="setting-row">
            <label class="setting-label">Block All Content</label>
            <div class="button-group">
              <input type="radio" id="yes-${slug}" name="block-${slug}" class="radio-input radio-yes" ${row.filter_strength === 'Extra Strong' ? "checked" : ""} />
              <label for="yes-${slug}" class="setting-btn">Yes</label>
              <input type="radio" id="no-${slug}" name="block-${slug}" class="radio-input radio-no" ${row.filter_strength !== 'Extra Strong' ? "checked" : ""} />
              <label for="no-${slug}" class="setting-btn active">No</label>
            </div>
          </div>
        </div>

        <div class="setting-group strength-group">
          <div class="strength-header">
            <label class="setting-label">Filter Strength</label>
            <span class="strength-label">${row.filter_strength || 'Weak'}</span>
          </div>
          <div class="slider-container">
            <input type="range" id="strength-${slug}" class="strength-slider" min="1" max="4" value="${mapStrengthToValue(row.filter_strength)}" />
          </div>
        </div>
      </div>
    `;

    container.appendChild(card);
    // Wire behaviors for this category
    wireCardBehaviorsByCategory(row.category);
    // Ensure slider fill is correct
    const slider = card.querySelector(".strength-slider");
    if (slider) setSliderFill(slider);
  }
}

function mapStrengthToValue(str) {
  return str === "Moderate" ? 2 : str === "Strong" ? 3 : str === "Extra Strong" ? 4 : 1;
}

function slugify(str) {
  return (str || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

// Helpers
function getStrengthLabelByCategory(category) {
  const label = document.querySelector(`[data-category="${CSS.escape(category)}"] .strength-label`);
  const text = (label?.textContent || "").trim();
  if (["Weak", "Moderate", "Strong", "Extra Strong"].includes(text)) return text;
  // Map slider value to label if label text not yet updated
  const slider = document.querySelector(`[data-category="${CSS.escape(category)}"] .strength-slider`);
  const val = parseInt(slider?.value || "1", 10);
  return val === 1 ? "Weak" : val === 2 ? "Moderate" : val === 3 ? "Strong" : "Extra Strong";
}

// Load initial settings from backend and apply to UI
renderSettingsCards();

// Edit Categories modal logic
(function setupEditCategoriesModal() {
  const btn = document.getElementById("edit-categories-btn");
  const modal = document.getElementById("edit-categories-modal");
  if (!btn || !modal) return;
  const closeBtn = modal.querySelector(".modal-close");
  const cancelBtn = modal.querySelector(".modal-cancel");
  const saveBtn = modal.querySelector(".modal-save");
  const list = document.getElementById("edit-categories-list");

  const open = async () => {
    modal.classList.remove("hidden");
    // Populate list
    const data = await api("/api/settings");
    const items = data?.items || [];
    list.innerHTML = items
      .map((row) => {
        const slug = slugify(row.category);
        return `
          <div class="edit-cat-name">${row.category}</div>
          <div class="edit-cat-toggle">
            <label class="toggle-switch">
              <input type="checkbox" id="edit-toggle-${slug}" ${row.is_active ? "checked" : ""}>
              <label for="edit-toggle-${slug}"></label>
            </label>
          </div>
        `;
      })
      .join("");
  };
  const close = () => modal.classList.add("hidden");

  btn.addEventListener("click", open);
  closeBtn?.addEventListener("click", close);
  cancelBtn?.addEventListener("click", close);
  modal.querySelector(".modal-backdrop")?.addEventListener("click", close);

  saveBtn?.addEventListener("click", async () => {
    const data = await api("/api/settings");
    const items = data?.items || [];
    // Save toggled states in parallel
    await Promise.all(
      items.map((row) => {
        const slug = slugify(row.category);
        const el = document.getElementById(`edit-toggle-${slug}`);
        if (!el) return null;
        const isActive = Boolean(el.checked);
        // Send current strength unchanged if not available
        const strength = row.filter_strength || "Weak";
        return api(`/api/settings/${encodeURIComponent(row.category)}`, {
          method: "POST",
          body: { filter_strength: strength, is_active: isActive },
        });
      })
    );

    // Re-render cards based on new actives
    await renderSettingsCards();
    close();
  });
})();

// Create New Category cloning
(function setupCreateCategory() {
  const btn = document.querySelector(".create-category-btn");
  const grid = document.querySelector(".cards_categories");
  const first = document.querySelector(".cards_categories .settings-card");
  if (!btn || !grid || !first) return;

  let counter = 1;
  const getNextId = () => {
    counter += 1;
    return counter;
  };

  btn.addEventListener("click", () => {
    const id = getNextId();
    const clone = first.cloneNode(true);

    // Update heading text
    const title = clone.querySelector(".card-title");
    const subtitle = clone.querySelector(".card-subtitle");
    if (title) title.textContent = `Category ${id}`;
    if (subtitle) subtitle.textContent = `Category ${id} Description`;

    // Re-id controls
    const toggle = clone.querySelector("#toggle1");
    if (toggle) toggle.id = `toggle${id}`;
    const toggleLbl = clone.querySelector('label[for="toggle1"]');
    if (toggleLbl) toggleLbl.setAttribute("for", `toggle${id}`);
    const body = clone.querySelector("#settings1Body");
    if (body) body.id = `settings${id}Body`;

    const yes = clone.querySelector("#yes1");
    const yesLbl = clone.querySelector('label[for="yes1"]');
    const no = clone.querySelector("#no1");
    const noLbl = clone.querySelector('label[for="no1"]');
    if (yes) {
      yes.id = `yes${id}`;
      yes.name = `block${id}`;
      yes.checked = false;
    }
    if (yesLbl) yesLbl.setAttribute("for", `yes${id}`);
    if (no) {
      no.id = `no${id}`;
      no.name = `block${id}`;
      no.checked = true;
    }
    if (noLbl) noLbl.setAttribute("for", `no${id}`);

    const group = clone.querySelector("#strength1Group");
    if (group) group.id = `strength${id}Group`;
    const label = clone.querySelector("#strength1Label");
    if (label) {
      label.id = `strength${id}Label`;
      label.textContent = "Weak";
      label.className = "strength-label is-weak";
    }
    const slider = clone.querySelector("#strength1");
    if (slider) {
      slider.id = `strength${id}`;
      slider.value = "1";
      slider.style.removeProperty("--fill");
    }

    // Insert before the create button card
    const createCard = document.querySelector(".create-category-card");
    grid.insertBefore(clone, createCard);

    // Wire behaviors
    wireCardBehaviors(id);
  });
})();

// Graph rendering + category select persistence
(function setupDashboardGraph() {
  try {
    const canvas = document.getElementById("lineChart");
    const select = document.getElementById("category-select");
    if (!canvas || !select) return;

    // Load last selected category
    chrome.storage?.local?.get(["selectedCategory"], ({ selectedCategory }) => {
      if (selectedCategory) select.value = selectedCategory;
    });

    // Persist on change
    select.addEventListener("change", () => {
      chrome.storage?.local?.set({ selectedCategory: select.value });
      draw();
    });

    function draw() {
      const ctx = canvas.getContext("2d");
      const w = canvas.width,
        h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // Grid
      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.lineWidth = 1;
      for (let i = 1; i < 6; i++) {
        const y = (h / 6) * i;
        ctx.beginPath();
        ctx.moveTo(60, y);
        ctx.lineTo(w - 20, y);
        ctx.stroke();
      }

      // Placeholder points
      const points = [
        [60, 210],
        [120, 120],
        [180, 160],
        [240, 130],
        [300, 60],
        [360, 140],
        [420, 130],
        [480, 150],
        [540, 100],
        [600, 50],
        [660, 130],
        [720, 200],
        [780, 240],
      ];

      const grad = ctx.createLinearGradient(0, 0, w, 0);
      grad.addColorStop(0, "rgba(232,103,90,0.8)");
      grad.addColorStop(1, "rgba(255,255,255,0.9)");
      ctx.lineWidth = 3;
      ctx.strokeStyle = grad;
      ctx.beginPath();
      for (let i = 0; i < points.length; i++) {
        const [x, y] = points[i];
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      const fillGrad = ctx.createLinearGradient(0, 0, 0, h);
      fillGrad.addColorStop(0, "rgba(232,103,90,0.12)");
      fillGrad.addColorStop(1, "rgba(232,103,90,0.02)");
      ctx.fillStyle = fillGrad;
      ctx.lineTo(points[points.length - 1][0], h - 20);
      ctx.lineTo(points[0][0], h - 20);
      ctx.closePath();
      ctx.fill();
    }

    draw();
  } catch (_) {
    /* no-op */
  }
})();


fetch("http://127.0.0.1:5050/api/settings/active/count")
  .then(res => res.json())
  .then(data => {
    document.getElementById("activeUsersCount").innerText = data.active_users;
  });

fetch("http://127.0.0.1:5050/api/settings/max-blocked")
  .then(res => res.json())
  .then(data => {
    document.getElementById("maxBlockedCategory").innerText = data.category || "N/A";
  });

  fetch("http://127.0.0.1:5050/api/settings/total-blocked")
  .then(res => res.json())
  .then(data => {
    document.getElementById("totalBlockedVideos").innerText = data.total_blocked || "N/A";
  });