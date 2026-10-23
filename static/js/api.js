/**
 * Ari Chat API Client
 */
const API = {
  TOKEN_KEY: "ari_auth_token",
  USER_KEY: "ari_auth_user",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  setAuth(token, user) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },

  clearAuth() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  getUser() {
    const raw = localStorage.getItem(this.USER_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(endpoint, {
      ...options,
      headers
    });

    if (res.status === 401) {
      this.clearAuth();
      window.dispatchEvent(new CustomEvent("ari:unauthorized"));
      throw new Error("Session expired. Please log in again.");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API Request failed");
    }

    return res.json();
  },

  // Auth Endpoints
  async register(username, email, password) {
    const data = await this.request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password })
    });
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async login(username, password) {
    const data = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async guestLogin() {
    const data = await this.request("/api/auth/guest", {
      method: "POST"
    });
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async getMe() {
    return this.request("/api/auth/me");
  },

  // Chat Endpoints
  async getConversations() {
    return this.request("/api/chat/conversations");
  },

  async createConversation(title = "New Chat", model = "ari-assistant") {
    return this.request("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title, model })
    });
  },

  async getConversation(id) {
    return this.request(`/api/chat/conversations/${id}`);
  },

  async renameConversation(id, title) {
    return this.request(`/api/chat/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title })
    });
  },

  async deleteConversation(id) {
    return this.request(`/api/chat/conversations/${id}`, {
      method: "DELETE"
    });
  },

  // Memory Endpoints
  async getMemories() {
    return this.request("/api/memories/");
  },

  async createMemory(key, value, category = "preference") {
    return this.request("/api/memories/", {
      method: "POST",
      body: JSON.stringify({ key, value, category })
    });
  },

  async deleteMemory(id) {
    return this.request(`/api/memories/${id}`, {
      method: "DELETE"
    });
  },

  async clearMemories() {
    return this.request("/api/memories/", {
      method: "DELETE"
    });
  },

  // Health
  async getHealth() {
    return this.request("/api/health");
  },

  // Model Management & Pulling
  async getModels() {
    return this.request("/api/models");
  },

  async pullModel(modelId = "ari-assistant-3b") {
    return this.request("/api/models/pull", {
      method: "POST",
      body: JSON.stringify({ model_id: modelId })
    });
  },

  async getPullStatus() {
    return this.request("/api/models/pull-status");
  },

  async cancelPull() {
    return this.request("/api/models/cancel-pull", {
      method: "POST"
    });
  },

  async switchModel(modelId) {
    return this.request("/api/models/switch", {
      method: "POST",
      body: JSON.stringify({ model_id: modelId })
    });
  },

  // Auto-Updater Endpoints
  async checkUpdate() {
    return this.request("/api/system/update/check");
  },

  async startUpdate() {
    return this.request("/api/system/update/download", {
      method: "POST"
    });
  },

  async getUpdateStatus() {
    return this.request("/api/system/update/status");
  },

  async cancelUpdate() {
    return this.request("/api/system/update/cancel", {
      method: "POST"
    });
  },

  async applyUpdate() {
    return this.request("/api/system/update/apply", {
      method: "POST"
    });
  }
};
