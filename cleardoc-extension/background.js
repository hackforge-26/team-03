// ClearDoc Background Service Worker
// Handles API calls, context menus, and extension lifecycle

const DEFAULT_API_URL = "http://localhost:8000";

// ── Storage Helpers ────────────────────────────────────────────
async function getConfig() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      {
        apiUrl: DEFAULT_API_URL,
        language: "en",
        userId: null,
      },
      (items) => {
        // Generate persistent user ID if not set
        if (!items.userId) {
          items.userId = "ext-" + crypto.randomUUID();
          chrome.storage.sync.set({ userId: items.userId });
        }
        resolve(items);
      }
    );
  });
}

// ── Context Menu ───────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "cleardoc-explain",
    title: "📘 Explain with ClearDoc",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "cleardoc-compare",
    title: "🔍 Compare with ClearDoc",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "cleardoc-explain" && info.selectionText) {
    // Send selected text to content script to show overlay
    chrome.tabs.sendMessage(tab.id, {
      action: "showOverlay",
      text: info.selectionText,
      mode: "explain",
    });
  }

  if (info.menuItemId === "cleardoc-compare" && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      action: "showOverlay",
      text: info.selectionText,
      mode: "compare",
    });
  }
});

// ── Message Handler ────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "explain") {
    handleExplain(request.text, request.language)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true; // Keep message channel open for async response
  }

  if (request.action === "compare") {
    handleCompare(request.documentId)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === "followup") {
    handleFollowup(request.documentId, request.question, request.language)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === "saveToHistory") {
    handleSaveToHistory(request.documentId)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === "getConfig") {
    getConfig().then((config) => sendResponse({ success: true, data: config }));
    return true;
  }
});

// ── API Calls ──────────────────────────────────────────────────
async function handleExplain(text, language) {
  const config = await getConfig();

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
}

async function handleCompare(documentId) {
  const config = await getConfig();

  const response = await fetch(`${config.apiUrl}/compare/${documentId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

async function handleFollowup(documentId, question, language) {
  const config = await getConfig();

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
}

async function handleSaveToHistory(documentId) {
  const config = await getConfig();

  const response = await fetch(`${config.apiUrl}/history/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_id: documentId,
      user_id: config.userId,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}
