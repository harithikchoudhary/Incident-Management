// Central API client for the Incident Management backend.
// In dev, Vite proxies /api to the FastAPI server (see vite.config.js).
// Override with VITE_API_BASE for a fully-qualified backend URL if needed.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  dashboard: () => request("/api/dashboard"),
  listIncidents: () => request("/api/incidents"),
  getIncident: (id) => request(`/api/incidents/${encodeURIComponent(id)}`),
  getConversation: (id) =>
    request(`/api/incidents/${encodeURIComponent(id)}/conversation`),
  searchIncidents: (q, application, environment) => {
    const params = new URLSearchParams({ q });
    if (application) params.set("application", application);
    if (environment) params.set("environment", environment);
    return request(`/api/incidents/search?${params.toString()}`);
  },
  chat: (message, conversationHistory = [], sessionId = null) =>
    request("/api/incidents/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory,
        session_id: sessionId,
      }),
    }),
  listChatSessions: () => request("/api/chat/sessions"),
  getChatSessionMessages: (sessionId) =>
    request(`/api/chat/sessions/${encodeURIComponent(sessionId)}/messages`),
  createChatSession: () =>
    request("/api/chat/sessions", { method: "POST", body: JSON.stringify({}) }),
  deleteChatSession: (sessionId) =>
    request(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),
  runIngestion: () =>
    request("/api/ingestion/mock-chat", {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

export { API_BASE };
