// ClearDoc API Helper Module
// Shared utilities for extension API communication

const ClearDocAPI = {
  DEFAULT_API_URL: "http://localhost:8000",

  async getConfig() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(
        {
          apiUrl: this.DEFAULT_API_URL,
          language: "en",
          userId: null,
        },
        (items) => {
          if (!items.userId) {
            items.userId = "ext-" + crypto.randomUUID();
            chrome.storage.sync.set({ userId: items.userId });
          }
          resolve(items);
        }
      );
    });
  },

  async explain(text, language) {
    const config = await this.getConfig();
    const formData = new FormData();
    formData.append("text", text);
    formData.append("language", language || config.language);
    formData.append("user_id", config.userId);

    const response = await fetch(`${config.apiUrl}/explain`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  },

  async followup(documentId, question, language) {
    const config = await this.getConfig();
    const response = await fetch(`${config.apiUrl}/followup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: documentId,
        question: question,
        language: language || config.language,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  },

  async getHistory(limit = 20, offset = 0) {
    const config = await this.getConfig();
    const response = await fetch(
      `${config.apiUrl}/history?user_id=${config.userId}&limit=${limit}&offset=${offset}`
    );

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  },

  async saveToHistory(documentId) {
    const config = await this.getConfig();
    const response = await fetch(`${config.apiUrl}/history/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: documentId,
        user_id: config.userId,
      }),
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  },

  async healthCheck() {
    const config = await this.getConfig();
    const response = await fetch(`${config.apiUrl}/health`);
    return response.json();
  },
};
