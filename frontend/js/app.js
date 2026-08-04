let token = localStorage.getItem("casino_token");

function captureAttribution() {
  try {
    const q = new URLSearchParams(window.location.search);
    const keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "ttclid", "gclid", "fbclid"];
    const parts = [];
    for (const k of keys) {
      const v = (q.get(k) || "").trim();
      if (v) parts.push(k + "=" + v.slice(0, 120));
    }
    if (parts.length) {
      localStorage.setItem("casino_src", parts.join(";").slice(0, 256));
      history.replaceState({}, "", window.location.pathname + window.location.hash);
    }
  } catch { /* noop */ }
}
captureAttribution();

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(path, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && localStorage.getItem("casino_token")) {
    localStorage.removeItem("casino_token");
    sessionStorage.removeItem("casino_fair_commit");
    location.href = "/";
    throw new Error(data.detail || "Sesión expirada");
  }
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
  return data;
}

async function sha256hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

let fairPreCommit = null;

async function initFair() {
  try {
    const st = await api("/api/games/fair/state");
    const cur = st.server_seed_commit;
    if (cur && cur !== sessionStorage.getItem("casino_fair_commit")) {
      sessionStorage.setItem("casino_fair_commit", cur);
    }
    fairPreCommit = sessionStorage.getItem("casino_fair_commit");
  } catch {
    fairPreCommit = null;
  }
}

function renderFair(data) {
  const el = document.getElementById("fair-badge");
  if (!el || !data?.fair) return;
  const f = data.fair;
  const expected = f.commit_published_before || fairPreCommit;
  let html = `Ronda #${f.round_no} · seed cliente <code>${f.client_seed.slice(0, 10)}…</code>`;
  if (expected) {
    html += ` · <span class="verify-pending">verificando hash…</span>`;
    sha256hex(f.server_seed_used).then((h) => {
      const ok = h === expected;
      const span = el.querySelector(".verify-pending");
      if (span) {
        span.className = ok ? "verify-ok" : "verify-bad";
        span.textContent = ok
          ? "✓ sha256(seed del servidor) == commit previo — ronda verificada"
          : "✗ FALLO DE VERIFICACIÓN — no confíes en esta ronda";
      }
    });
  } else {
    html += ` · <span class="verify-pending">commit no disponible — recarga para obtener el commit</span>`;
  }
  el.innerHTML = html;
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
  const body = { email, password };
  if (!isLogin) {
    const username = document.getElementById("username").value.trim();
    if (username) body.username = username;
    const src = localStorage.getItem("casino_src");
    if (src) body.source = src;
  }
  const data = await api(path, { method: "POST", body: JSON.stringify(body) });
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
  document.getElementById("username").style.display = loginMode ? "" : "none";
});

async function loadLeaderboard() {
  const el = document.getElementById("leaderboard");
  if (!el) return;
  const rows = await api("/api/games/leaderboard");
  el.innerHTML = rows.map((r) => `<li><span class="rank">#${rows.indexOf(r) + 1}</span><span class="pseudonym">${r.username}</span><span class="chips">${r.chips} fichas</span></li>`).join("");
}

async function loadHistory() {
  const wrap = document.getElementById("history-wrap");
  if (!wrap) return;
  const rows = await api("/api/games/history");
  if (!rows.length) {
    wrap.innerHTML = '<p class="hint">Aún sin partidas.</p>';
    return;
  }
  wrap.innerHTML = `<ul class="history">${rows
    .map((h) => {
      const sign = h.net >= 0 ? "+" : "";
      const cls = h.net > 0 ? "pos" : h.net < 0 ? "neg" : "zero";
      return `<li><span class="row-game">${h.game}</span> apuesta <strong>${h.bet}</strong> · <span class="${cls}">${sign}${h.net}</span> <em>${h.at.slice(0, 16).replace("T", " ")}</em></li>`;
    })
    .join("")}</ul>`;
}

function injectLogout() {
  if (document.getElementById("logout-btn")) return;
  const bar = document.querySelector(".site-header .chip-bar");
  if (!bar) return;
  const b = document.createElement("button");
  b.id = "logout-btn";
  b.className = "logout-btn";
  b.type = "button";
  b.textContent = "Salir";
  b.addEventListener("click", () => {
    localStorage.removeItem("casino_token");
    sessionStorage.removeItem("casino_fair_commit");
    location.href = "/";
  });
  bar.appendChild(b);
}

async function initApp() {
  if (!token) {
    document.getElementById("lobby-view")?.setAttribute("hidden", "");
    return;
  }
  document.getElementById("auth-view")?.setAttribute("hidden", "");
  document.getElementById("lobby-view")?.removeAttribute("hidden");
  injectLogout();
  try {
    const me = await api("/api/auth/me");
    setChips(me.chips);
    const uname = document.getElementById("username-label");
    if (uname) uname.textContent = me.username || "player";
  } catch {
    return;
  }
  initFair();
  loadLeaderboard();
  loadHistory();
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