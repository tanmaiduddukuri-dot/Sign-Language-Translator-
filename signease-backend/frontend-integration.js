// Add this near the top of your SignEase <script>.
const API_BASE_URL = "http://127.0.0.1:8000"; // Replace with deployed backend URL later.

function authHeaders() {
  const token = localStorage.getItem("signeaseToken");
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// Replace login() with this version.
async function backendLogin(e) {
  e.preventDefault();
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("loginEmail").value,
        password: document.getElementById("loginPassword").value
      })
    });
    localStorage.setItem("signeaseToken", data.accessToken);
    localStorage.setItem("signeaseUser", JSON.stringify(data.user));
    currentUser = data.user;
    toast("Login successful");
    showPage("app");
  } catch (err) { toast(err.message); }
}

// Replace register() with this version.
async function backendRegister(e) {
  e.preventDefault();
  const password = document.getElementById("regPassword").value;
  const confirm = document.getElementById("regConfirm").value;
  if (password !== confirm) return toast("Passwords do not match.");
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("regName").value,
        email: document.getElementById("regEmail").value,
        phone: document.getElementById("regPhone").value,
        language: document.getElementById("regLang").value,
        password
      })
    });
    localStorage.setItem("signeaseToken", data.accessToken);
    localStorage.setItem("signeaseUser", JSON.stringify(data.user));
    currentUser = data.user;
    toast("Account created");
    showPage("app");
  } catch (err) { toast(err.message); }
}

// Use these from your existing functions.
async function backendSaveTranslation(sign, translation) {
  return api("/translations", {
    method: "POST",
    body: JSON.stringify({ sign, translation, input: "Camera/Demo" })
  });
}
async function backendGetTranslations() { return api("/translations"); }
async function backendDeleteTranslation(id) {
  return api(`/translations/${id}`, { method: "DELETE" });
}
async function backendClearTranslations() {
  return api("/translations", { method: "DELETE" });
}

async function backendGetSigns() { return api("/signs"); }
async function backendGetFavorites() { return api("/favorites"); }
async function backendAddFavorite(signName) {
  return api("/favorites", { method: "POST", body: JSON.stringify({ signName }) });
}
async function backendRemoveFavorite(signName) {
  return api(`/favorites/${encodeURIComponent(signName)}`, { method: "DELETE" });
}

async function backendGetProgress() { return api("/progress"); }
async function backendSetProgress(progress, course = "Basic Greetings") {
  return api("/progress", {
    method: "PUT",
    body: JSON.stringify({ progress, course })
  });
}

async function backendSubmitFeedback(rating, type, message) {
  return api("/feedback", {
    method: "POST",
    body: JSON.stringify({ rating, type, message })
  });
}

async function backendUpdateProfile() {
  return api("/me", {
    method: "PUT",
    body: JSON.stringify({
      name: document.getElementById("profileName").value,
      email: document.getElementById("profileEmail").value,
      phone: document.getElementById("profilePhone").value,
      language: document.getElementById("profileLang").value
    })
  });
}

// Then change your HTML forms:
// onsubmit="login(event)"     -> onsubmit="backendLogin(event)"
// onsubmit="register(event)"  -> onsubmit="backendRegister(event)"
