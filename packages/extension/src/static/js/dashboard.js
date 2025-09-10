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
      const el = document.getElementById("backend-health");
      if (el) {
        el.classList.remove("status-online", "status-offline");
        el.classList.add(ok ? "status-online" : "status-offline");
        el.lastElementChild?.nodeType === Node.TEXT_NODE;
        const text = ok ? "Backend: Online" : "Backend: Offline";
        el.childNodes.forEach((n) => {
          if (n.nodeType === Node.TEXT_NODE) n.textContent = ` ${text}`;
        });
      }
    } catch (_) {
      const el = document.getElementById("backend-health");
      if (el) {
        el.classList.remove("status-online");
        el.classList.add("status-offline");
        el.childNodes.forEach((n) => {
          if (n.nodeType === Node.TEXT_NODE)
            n.textContent = " Backend: Offline";
        });
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

// Utility to sync slider fill percent
function setSliderFill(sliderEl) {
  const min = parseInt(sliderEl.min || "0", 10);
  const max = parseInt(sliderEl.max || "100", 10);
  const val = parseInt(sliderEl.value || String(min), 10);
  const pct = ((val - min) * 100) / (max - min);
  sliderEl.style.setProperty("--fill", pct + "%");
}

// Helpers to wire behaviors for a settings card by numeric id
function wireCardBehaviors(cardId) {
  // Toggle body
  const toggle = document.getElementById(`toggle${cardId}`);
  const body = document.getElementById(`settings${cardId}Body`);
  if (toggle && body) {
    const apply = () => body.classList.toggle("hidden", !toggle.checked);
    apply();
    toggle.addEventListener("change", apply);
  }

  // Slider behavior
  const slider = document.getElementById(`strength${cardId}`);
  const label = document.getElementById(`strength${cardId}Label`);
  const group = document.getElementById(`strength${cardId}Group`);
  const yesRadio = document.getElementById(`yes${cardId}`);
  const noRadio = document.getElementById(`no${cardId}`);
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

  slider.addEventListener("input", (e) =>
    applyState(parseInt(e.target.value, 10))
  );
  yesRadio.addEventListener("change", () => {
    if (yesRadio.checked) {
      slider.value = "4";
      applyState(4);
    }
  });
  noRadio.addEventListener("change", () => {
    if (noRadio.checked) {
      if (parseInt(slider.value, 10) === 4) slider.value = "3";
      applyState(parseInt(slider.value, 10));
    }
  });
}

// Initial card is 1
wireCardBehaviors(1);

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
