// ClearDoc Popup Script
// Handles all UI interactions in the extension popup

document.addEventListener("DOMContentLoaded", () => {
  // ── DOM Elements ─────────────────────────────────────────────
  const tabs = document.querySelectorAll(".tab");
  const tabContents = document.querySelectorAll(".tab-content");

  const docText = document.getElementById("doc-text");
  const docLanguage = document.getElementById("doc-language");
  const btnExplain = document.getElementById("btn-explain");
  const btnExtractPage = document.getElementById("btn-extract-page");
  const loading = document.getElementById("loading");
  const result = document.getElementById("result");
  const error = document.getElementById("error");

  const settingApiUrl = document.getElementById("setting-api-url");
  const settingLanguage = document.getElementById("setting-language");
  const settingUserId = document.getElementById("setting-user-id");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const btnCheckHealth = document.getElementById("btn-check-health");
  const healthStatus = document.getElementById("health-status");

  let currentDocumentId = null;

  // ── Tab Switching ────────────────────────────────────────────
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tabContents.forEach((tc) => tc.classList.remove("active"));

      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");

      // Load history when switching to history tab
      if (tab.dataset.tab === "history") loadHistory();
    });
  });

  // ── Load Settings ────────────────────────────────────────────
  chrome.storage.sync.get(
    { apiUrl: "http://localhost:8000", language: "en", userId: null },
    (items) => {
      settingApiUrl.value = items.apiUrl;
      settingLanguage.value = items.language;
      settingUserId.textContent = items.userId || "Not set";
      docLanguage.value = items.language;
    }
  );

  // ── Save Settings ────────────────────────────────────────────
  btnSaveSettings.addEventListener("click", () => {
    const newSettings = {
      apiUrl: settingApiUrl.value.replace(/\/$/, ""),
      language: settingLanguage.value,
    };

    chrome.storage.sync.set(newSettings, () => {
      btnSaveSettings.textContent = "✓ Saved!";
      setTimeout(() => (btnSaveSettings.textContent = "Save Settings"), 1500);
    });
  });

  // ── Check Backend Health ─────────────────────────────────────
  btnCheckHealth.addEventListener("click", async () => {
    healthStatus.style.display = "block";
    healthStatus.textContent = "Checking...";
    healthStatus.className = "health-status";

    try {
      const response = await fetch(`${settingApiUrl.value}/health`);
      const data = await response.json();

      if (data.status === "ok") {
        healthStatus.textContent = "✅ Backend is connected!";
        healthStatus.classList.add("health-ok");
      } else {
        healthStatus.textContent = `⚠️ Backend degraded: ${JSON.stringify(data.services)}`;
        healthStatus.classList.add("health-warn");
      }
    } catch (err) {
      healthStatus.textContent = "❌ Cannot connect to backend. Check the URL.";
      healthStatus.classList.add("health-error");
    }
  });

  // ── Explain Button ───────────────────────────────────────────
  btnExplain.addEventListener("click", () => {
    const text = docText.value.trim();
    if (!text) {
      showError("Please paste some document text first.");
      return;
    }
    explainDocument(text, docLanguage.value);
  });

  // ── Extract Page Text ────────────────────────────────────────
  btnExtractPage.addEventListener("click", async () => {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      const response = await chrome.tabs.sendMessage(tab.id, {
        action: "getSelectedText",
      });

      if (response && response.text) {
        docText.value = response.text;
      } else {
        // Fallback: extract all page text
        const pageResponse = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => document.body.innerText,
        });

        if (pageResponse && pageResponse[0]) {
          docText.value = pageResponse[0].result.substring(0, 10000);
        }
      }
    } catch (err) {
      showError("Could not extract text from this page.");
    }
  });

  // ── Explain Document ─────────────────────────────────────────
  async function explainDocument(text, language) {
    showLoading();

    try {
      const response = await chrome.runtime.sendMessage({
        action: "explain",
        text: text,
        language: language,
      });

      if (response.success) {
        showResult(response.data);
      } else {
        showError(response.error || "Failed to explain document.");
      }
    } catch (err) {
      showError(
        "Could not connect to ClearDoc backend. Check Settings tab."
      );
    }
  }

  // ── Follow-up ────────────────────────────────────────────────
  document.getElementById("btn-followup").addEventListener("click", () => {
    const box = document.getElementById("followup-box");
    box.style.display = box.style.display === "none" ? "flex" : "none";
  });

  document
    .getElementById("btn-followup-send")
    .addEventListener("click", sendFollowup);

  document
    .getElementById("followup-input")
    .addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendFollowup();
    });

  async function sendFollowup() {
    const input = document.getElementById("followup-input");
    const question = input.value.trim();
    if (!question || !currentDocumentId) return;

    const answerDiv = document.getElementById("followup-answer");
    answerDiv.style.display = "block";
    answerDiv.textContent = "Thinking...";

    try {
      const response = await chrome.runtime.sendMessage({
        action: "followup",
        documentId: currentDocumentId,
        question: question,
      });

      if (response.success) {
        answerDiv.textContent = response.data.answer;
      } else {
        answerDiv.textContent = "Could not get answer.";
      }
    } catch (err) {
      answerDiv.textContent = "Connection error.";
    }

    input.value = "";
  }

  // ── Save to History ──────────────────────────────────────────
  document.getElementById("btn-save").addEventListener("click", async () => {
    if (!currentDocumentId) return;

    const btn = document.getElementById("btn-save");
    btn.textContent = "Saving...";

    try {
      await chrome.runtime.sendMessage({
        action: "saveToHistory",
        documentId: currentDocumentId,
      });
      btn.textContent = "✓ Saved!";
    } catch (err) {
      btn.textContent = "Failed";
    }

    setTimeout(() => (btn.textContent = "💾 Save"), 2000);
  });

  // ── Load History ─────────────────────────────────────────────
  async function loadHistory() {
    const historyList = document.getElementById("history-list");

    try {
      const config = await chrome.runtime.sendMessage({ action: "getConfig" });
      if (!config.success) return;

      const response = await fetch(
        `${config.data.apiUrl}/history?user_id=${config.data.userId}&limit=20`
      );

      if (!response.ok) throw new Error("Failed to load history");

      const items = await response.json();

      if (items.length === 0) {
        historyList.innerHTML =
          '<p class="history-empty">No saved documents yet.</p>';
        return;
      }

      historyList.innerHTML = items
        .map(
          (item) => `
        <div class="history-item" data-id="${item.id}">
          <div class="history-item-header">
            <span class="history-type">${item.doc_type.replace(/_/g, " ")}</span>
            ${item.urgency_flag ? '<span class="history-urgency">⚠️</span>' : ""}
          </div>
          <p class="history-preview">${item.summary_preview}</p>
          <span class="history-date">${new Date(item.created_at).toLocaleDateString()}</span>
        </div>
      `
        )
        .join("");

      // Click to view full result
      historyList.querySelectorAll(".history-item").forEach((el) => {
        el.addEventListener("click", async () => {
          const id = el.dataset.id;
          try {
            const res = await fetch(
              `${config.data.apiUrl}/history/${id}`
            );
            if (res.ok) {
              const data = await res.json();
              // Switch to explain tab and show result
              document.querySelector('.tab[data-tab="explain"]').click();
              showResult(data);
            }
          } catch (err) {
            // Silent fail
          }
        });
      });
    } catch (err) {
      historyList.innerHTML =
        '<p class="history-empty">Could not load history.</p>';
    }
  }

  // ── UI Helpers ───────────────────────────────────────────────
  function showLoading() {
    loading.style.display = "flex";
    result.style.display = "none";
    error.style.display = "none";
  }

  function showResult(data) {
    loading.style.display = "none";
    result.style.display = "block";
    error.style.display = "none";

    currentDocumentId = data.document_id;

    document.getElementById("result-summary").textContent = data.summary;

    const keypointsList = document.getElementById("result-keypoints");
    keypointsList.innerHTML = "";
    (data.key_points || []).forEach((point) => {
      const li = document.createElement("li");
      li.textContent = point;
      keypointsList.appendChild(li);
    });

    const nextstepsList = document.getElementById("result-nextsteps");
    nextstepsList.innerHTML = "";
    (data.next_steps || []).forEach((step) => {
      const li = document.createElement("li");
      li.textContent = step;
      nextstepsList.appendChild(li);
    });

    if (data.urgency_flag && data.urgency_message) {
      document.getElementById("result-urgency").style.display = "block";
      document.getElementById("result-urgency-msg").textContent =
        data.urgency_message;
    } else {
      document.getElementById("result-urgency").style.display = "none";
    }
  }

  function showError(message) {
    loading.style.display = "none";
    result.style.display = "none";
    error.style.display = "block";
    document.getElementById("error-msg").textContent = message;
  }

  // Retry button
  document.getElementById("btn-retry").addEventListener("click", () => {
    const text = docText.value.trim();
    if (text) explainDocument(text, docLanguage.value);
  });

  // Options link
  document.getElementById("link-options").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
});
