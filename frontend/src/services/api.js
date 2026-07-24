// Toutes les communications avec le backend FastAPI passent par ici.
const BASE_URL = "http://127.0.0.1:8000";

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  async login(username, password) {
    const res = await fetch(`${BASE_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return handle(res);
  },

  async logout() {
    await fetch(`${BASE_URL}/logout`, {
      method: "POST",
      headers: authHeaders(),
    });
  },

  async suggestions() {
    const res = await fetch(`${BASE_URL}/suggestions`, { headers: authHeaders() });
    return handle(res);
  },

  async kpis() {
    const res = await fetch(`${BASE_URL}/kpis`, { headers: authHeaders() });
    return handle(res);
  },

  async ask(question, sessionId) {
    const res = await fetch(`${BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question, session_id: sessionId ?? null }),
    });
    return handle(res);
  },

  async listSessions() {
    const res = await fetch(`${BASE_URL}/sessions`, { headers: authHeaders() });
    return handle(res);
  },

  async createSession(sessionName) {
    const res = await fetch(`${BASE_URL}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ session_name: sessionName ?? null }),
    });
    return handle(res);
  },

  async getSessionMessages(sessionId) {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`, {
      headers: authHeaders(),
    });
    return handle(res);
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async securityOverview() {
    const res = await fetch(`${BASE_URL}/admin/security/overview`, { headers: authHeaders() });
    return handle(res);
  },

  async securityEvents({ limit = 100, status, action } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) params.set("status", status);
    if (action) params.set("action", action);
    const res = await fetch(`${BASE_URL}/admin/security/events?${params}`, {
      headers: authHeaders(),
    });
    return handle(res);
  },
};
