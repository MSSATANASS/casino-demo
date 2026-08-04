let token = localStorage.getItem("casino_token");

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(path, { ...opts, headers });
  return res.json();
}

function setChips(chips) {
  const el = document.getElementById("balance");
  if (el) el.textContent = chips;
}

const authForm = document.getElementById("auth-form");
authForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const isLogin = document.getElementById("auth-btn").dataset.mode === "login";
  const path = isLogin ? "/api/auth/login" : "/api/auth/register";
  const data = await api(path, { method: "POST", body: JSON.stringify({ email, password }) });
  if (data.token) {
    localStorage.setItem("casino_token", data.token);
    location.reload();
  } else {
    alert(data.detail || "Error");
  }
});

document.getElementById("toggle-auth")?.addEventListener("click", (e) => {
  e.preventDefault();
  const loginMode = document.getElementById("auth-btn").dataset.mode === "login";
  document.getElementById("auth-title").textContent = loginMode ? "Registro" : "Login";
  document.getElementById("auth-btn").textContent = loginMode ? "Crear cuenta" : "Entrar";
  document.getElementById("auth-btn").dataset.mode = loginMode ? "register" : "login";
});

async function loadLeaderboard() {
  const el = document.getElementById("leaderboard");
  if (!el) return;
  const rows = await api("/api/games/leaderboard");
  el.innerHTML = rows.map((r) => `<li>${r.email}: ${r.chips} fichas</li>`).join("");
}

async function initApp() {
  if (!token) {
    document.getElementById("lobby-view")?.setAttribute("hidden", "");
    return;
  }
  document.getElementById("auth-view")?.setAttribute("hidden", "");
  document.getElementById("lobby-view")?.removeAttribute("hidden");
  const me = await api("/api/auth/me");
  setChips(me.chips);
  loadLeaderboard();
}

initApp();

/* ============================================================
   Shared premium helpers (confetti, toast, shake)
   ============================================================ */

// Lightweight canvas confetti burst — no external deps.
function confetti(count = 120) {
  let canvas = document.getElementById("confetti-canvas");
  if (!canvas) {
    canvas = document.createElement("canvas");
    canvas.id = "confetti-canvas";
    document.body.appendChild(canvas);
  }
  const ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const colors = ["#ffd700", "#fff3b0", "#b8860b", "#ffffff", "#f5c542"];
  const parts = [];
  for (let i = 0; i < count; i++) {
    parts.push({
      x: Math.random() * canvas.width,
      y: -20 - Math.random() * canvas.height * 0.3,
      w: 6 + Math.random() * 8,
      h: 8 + Math.random() * 10,
      vx: (Math.random() - 0.5) * 3,
      vy: 2 + Math.random() * 4,
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.2,
      color: colors[(Math.random() * colors.length) | 0],
    });
  }
  let frames = 0;
  const maxFrames = 160;
  (function tick() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const p of parts) {
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }
    frames++;
    if (frames < maxFrames) requestAnimationFrame(tick);
    else { ctx.clearRect(0, 0, canvas.width, canvas.height); canvas.remove(); }
  })();
}

// "last win +X" toast
function showToast(msg, ms = 2600) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  requestAnimationFrame(() => toast.classList.add("show"));
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toast.classList.remove("show"), ms);
}

// shake an element (lose feedback)
function shakeEl(el) {
  if (!el) return;
  el.classList.remove("shake");
  void el.offsetWidth; // restart animation
  el.classList.add("shake");
}