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