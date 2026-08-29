// ClearDoc Options Page Script

document.addEventListener("DOMContentLoaded", () => {
  const apiUrl = document.getElementById("api-url");
  const defaultLanguage = document.getElementById("default-language");
  const showFloatingBtn = document.getElementById("show-floating-btn");
  const autoDetectLang = document.getElementById("auto-detect-lang");
  const userIdDisplay = document.getElementById("user-id-display");
  const saveStatus = document.getElementById("save-status");

  // ── Load Settings ────────────────────────────────────────────
  chrome.storage.sync.get(
    {
      apiUrl: "http://localhost:8000",
      language: "en",
      showFloatingBtn: true,
      autoDetectLang: true,
      userId: null,
    },
    (items) => {
      apiUrl.value = items.apiUrl;
      defaultLanguage.value = items.language;
      showFloatingBtn.checked = items.showFloatingBtn;
      autoDetectLang.checked = items.autoDetectLang;

      if (!items.userId) {
        items.userId = "ext-" + crypto.randomUUID();
        chrome.storage.sync.set({ userId: items.userId });
      }
      userIdDisplay.textContent = items.userId;
    }
  );

  // ── Test Connection ──────────────────────────────────────────
  document
    .getElementById("btn-test-connection")
    .addEventListener("click", async () => {
      const resultEl = document.getElementById("connection-result");
      resultEl.style.display = "block";
      resultEl.textContent = "Testing connection...";
      resultEl.className = "connection-result";

      try {
        const response = await fetch(`${apiUrl.value}/health`);
        const data = await response.json();

        if (data.status === "ok") {
          resultEl.textContent = `✅ Connected! Services: PostgreSQL=${data.services.postgresql}, Redis=${data.services.redis}`;
          resultEl.classList.add("connection-ok");
        } else {
          resultEl.textContent = `⚠️ Degraded: ${JSON.stringify(data.services)}`;
          resultEl.classList.add("connection-warn");
        }
      } catch (err) {
        resultEl.textContent = `❌ Connection failed: ${err.message}`;
        resultEl.classList.add("connection-error");
      }
    });

  // ── Save Settings ────────────────────────────────────────────
  document.getElementById("btn-save").addEventListener("click", () => {
    const settings = {
      apiUrl: apiUrl.value.replace(/\/$/, ""),
      language: defaultLanguage.value,
      showFloatingBtn: showFloatingBtn.checked,
      autoDetectLang: autoDetectLang.checked,
    };

    chrome.storage.sync.set(settings, () => {
      saveStatus.textContent = "✓ Settings saved!";
      saveStatus.style.color = "#22c55e";
      setTimeout(() => (saveStatus.textContent = ""), 2000);
    });
  });

  // ── Regenerate User ID ───────────────────────────────────────
  document
    .getElementById("btn-regenerate-id")
    .addEventListener("click", () => {
      const newId = "ext-" + crypto.randomUUID();
      chrome.storage.sync.set({ userId: newId }, () => {
        userIdDisplay.textContent = newId;
      });
    });

  // ── Clear History ────────────────────────────────────────────
  document
    .getElementById("btn-clear-history")
    .addEventListener("click", async () => {
      if (!confirm("Are you sure you want to clear all saved documents?")) return;

      try {
        const items = await chrome.storage.sync.get(["apiUrl", "userId"]);
        const response = await fetch(
          `${items.apiUrl}/history?user_id=${items.userId}&limit=50`
        );
        const history = await response.json();

        for (const item of history) {
          await fetch(
            `${items.apiUrl}/history/${item.id}?user_id=${items.userId}`,
            { method: "DELETE" }
          );
        }

        alert("History cleared successfully.");
      } catch (err) {
        alert("Could not clear history. Check your connection.");
      }
    });

  // ── Export Data ──────────────────────────────────────────────
  document
    .getElementById("btn-export-data")
    .addEventListener("click", async () => {
      try {
        const items = await chrome.storage.sync.get(["apiUrl", "userId"]);
        const response = await fetch(
          `${items.apiUrl}/history?user_id=${items.userId}&limit=50`
        );
        const history = await response.json();

        // Fetch full details for each item
        const fullData = [];
        for (const item of history) {
          try {
            const res = await fetch(`${items.apiUrl}/history/${item.id}`);
            if (res.ok) fullData.push(await res.json());
          } catch (e) {
            // Skip failed items
          }
        }

        const blob = new Blob([JSON.stringify(fullData, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `cleardoc-export-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        alert("Could not export data.");
      }
    });
});
