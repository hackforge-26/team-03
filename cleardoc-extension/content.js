// ClearDoc Content Script
// Injects overlay UI into web pages and extracts text

(function () {
  "use strict";

  // Prevent double-injection
  if (window.__cleardoc_loaded) return;
  window.__cleardoc_loaded = true;

  // ── Overlay Manager ──────────────────────────────────────────
  class ClearDocOverlay {
    constructor() {
      this.container = null;
      this.isLoading = false;
      this.currentDocumentId = null;
    }

    create() {
      if (this.container) this.container.remove();

      this.container = document.createElement("div");
      this.container.id = "cleardoc-overlay";
      this.container.innerHTML = `
        <div class="cleardoc-backdrop" id="cleardoc-backdrop"></div>
        <div class="cleardoc-panel" id="cleardoc-panel">
          <div class="cleardoc-header">
            <div class="cleardoc-logo">
              <span class="cleardoc-icon">📘</span>
              <span class="cleardoc-title">ClearDoc</span>
            </div>
            <button class="cleardoc-close" id="cleardoc-close" aria-label="Close">✕</button>
          </div>
          
          <div class="cleardoc-body" id="cleardoc-body">
            <!-- Loading State -->
            <div class="cleardoc-loading" id="cleardoc-loading">
              <div class="cleardoc-spinner"></div>
              <p>Understanding your document...</p>
            </div>
            
            <!-- Result State -->
            <div class="cleardoc-result" id="cleardoc-result" style="display:none">
              <div class="cleardoc-summary" id="cleardoc-summary"></div>
              
              <div class="cleardoc-section">
                <h3>📋 Key Points</h3>
                <ul id="cleardoc-keypoints"></ul>
              </div>
              
              <div class="cleardoc-section">
                <h3>✅ What To Do Next</h3>
                <ol id="cleardoc-nextsteps"></ol>
              </div>
              
              <div class="cleardoc-urgency" id="cleardoc-urgency" style="display:none">
                <span class="cleardoc-urgency-icon">⚠️</span>
                <span id="cleardoc-urgency-msg"></span>
              </div>
              
              <div class="cleardoc-actions">
                <button class="cleardoc-btn cleardoc-btn-secondary" id="cleardoc-save">
                  💾 Save to History
                </button>
                <button class="cleardoc-btn cleardoc-btn-primary" id="cleardoc-followup">
                  💬 Ask Follow-up
                </button>
              </div>
              
              <!-- Follow-up Input -->
              <div class="cleardoc-followup-box" id="cleardoc-followup-box" style="display:none">
                <input type="text" id="cleardoc-followup-input" 
                       placeholder="Ask a question about this document..." />
                <button class="cleardoc-btn cleardoc-btn-primary" id="cleardoc-followup-send">
                  Send
                </button>
              </div>
              <div class="cleardoc-followup-answer" id="cleardoc-followup-answer" style="display:none"></div>
            </div>
            
            <!-- Error State -->
            <div class="cleardoc-error" id="cleardoc-error" style="display:none">
              <span class="cleardoc-error-icon">❌</span>
              <p id="cleardoc-error-msg"></p>
              <button class="cleardoc-btn cleardoc-btn-secondary" id="cleardoc-retry">
                Try Again
              </button>
            </div>
          </div>
          
          <div class="cleardoc-footer">
            <span>Powered by ClearDoc</span>
          </div>
        </div>
      `;

      document.body.appendChild(this.container);
      this.bindEvents();
    }

    bindEvents() {
      // Close button
      document
        .getElementById("cleardoc-close")
        .addEventListener("click", () => this.hide());
      document
        .getElementById("cleardoc-backdrop")
        .addEventListener("click", () => this.hide());

      // Follow-up toggle
      document
        .getElementById("cleardoc-followup")
        .addEventListener("click", () => {
          const box = document.getElementById("cleardoc-followup-box");
          box.style.display = box.style.display === "none" ? "flex" : "none";
        });

      // Follow-up send
      document
        .getElementById("cleardoc-followup-send")
        .addEventListener("click", () => this.sendFollowup());

      // Enter key in follow-up input
      document
        .getElementById("cleardoc-followup-input")
        .addEventListener("keydown", (e) => {
          if (e.key === "Enter") this.sendFollowup();
        });

      // Save to history
      document
        .getElementById("cleardoc-save")
        .addEventListener("click", () => this.saveToHistory());

      // Retry
      document
        .getElementById("cleardoc-retry")
        .addEventListener("click", () => {
          if (this.lastText) this.explain(this.lastText);
        });

      // Escape key to close
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") this.hide();
      });
    }

    show() {
      this.create();
      this.container.style.display = "flex";
      // Prevent page scroll
      document.body.style.overflow = "hidden";
    }

    hide() {
      if (this.container) {
        this.container.style.display = "none";
        this.container.remove();
        this.container = null;
      }
      document.body.style.overflow = "";
    }

    showLoading() {
      document.getElementById("cleardoc-loading").style.display = "flex";
      document.getElementById("cleardoc-result").style.display = "none";
      document.getElementById("cleardoc-error").style.display = "none";
    }

    showResult(data) {
      document.getElementById("cleardoc-loading").style.display = "none";
      document.getElementById("cleardoc-result").style.display = "block";
      document.getElementById("cleardoc-error").style.display = "none";

      this.currentDocumentId = data.document_id;

      // Summary
      document.getElementById("cleardoc-summary").textContent = data.summary;

      // Key points
      const keypointsList = document.getElementById("cleardoc-keypoints");
      keypointsList.innerHTML = "";
      (data.key_points || []).forEach((point) => {
        const li = document.createElement("li");
        li.textContent = point;
        keypointsList.appendChild(li);
      });

      // Next steps
      const nextstepsList = document.getElementById("cleardoc-nextsteps");
      nextstepsList.innerHTML = "";
      (data.next_steps || []).forEach((step) => {
        const li = document.createElement("li");
        li.textContent = step;
        nextstepsList.appendChild(li);
      });

      // Urgency
      if (data.urgency_flag && data.urgency_message) {
        document.getElementById("cleardoc-urgency").style.display = "flex";
        document.getElementById("cleardoc-urgency-msg").textContent =
          data.urgency_message;
      } else {
        document.getElementById("cleardoc-urgency").style.display = "none";
      }
    }

    showError(message) {
      document.getElementById("cleardoc-loading").style.display = "none";
      document.getElementById("cleardoc-result").style.display = "none";
      document.getElementById("cleardoc-error").style.display = "flex";
      document.getElementById("cleardoc-error-msg").textContent = message;
    }

    async explain(text) {
      this.lastText = text;
      this.show();
      this.showLoading();

      try {
        const response = await chrome.runtime.sendMessage({
          action: "explain",
          text: text,
        });

        if (response.success) {
          this.showResult(response.data);
        } else {
          this.showError(response.error || "Failed to explain document.");
        }
      } catch (err) {
        this.showError(
          "Could not connect to ClearDoc. Check your settings."
        );
      }
    }

    async sendFollowup() {
      const input = document.getElementById("cleardoc-followup-input");
      const question = input.value.trim();
      if (!question || !this.currentDocumentId) return;

      const answerDiv = document.getElementById("cleardoc-followup-answer");
      answerDiv.style.display = "block";
      answerDiv.textContent = "Thinking...";

      try {
        const response = await chrome.runtime.sendMessage({
          action: "followup",
          documentId: this.currentDocumentId,
          question: question,
        });

        if (response.success) {
          answerDiv.textContent = response.data.answer;
        } else {
          answerDiv.textContent = "Could not get answer. Try again.";
        }
      } catch (err) {
        answerDiv.textContent = "Connection error. Try again.";
      }

      input.value = "";
    }

    async saveToHistory() {
      if (!this.currentDocumentId) return;

      const btn = document.getElementById("cleardoc-save");
      btn.textContent = "Saving...";
      btn.disabled = true;

      try {
        await chrome.runtime.sendMessage({
          action: "saveToHistory",
          documentId: this.currentDocumentId,
        });
        btn.textContent = "✓ Saved!";
      } catch (err) {
        btn.textContent = "Save failed";
      }

      setTimeout(() => {
        btn.textContent = "💾 Save to History";
        btn.disabled = false;
      }, 2000);
    }
  }

  // ── Initialize ───────────────────────────────────────────────
  const overlay = new ClearDocOverlay();

  // Listen for messages from background script (context menu)
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "showOverlay") {
      overlay.explain(request.text);
    }
    if (request.action === "getSelectedText") {
      const selected = window.getSelection().toString().trim();
      sendResponse({ text: selected });
    }
  });

  // ── Floating Button ──────────────────────────────────────────
  // Add a small floating button that appears when text is selected
  let floatingBtn = null;

  document.addEventListener("mouseup", (e) => {
    setTimeout(() => {
      const selected = window.getSelection().toString().trim();

      if (selected.length > 20) {
        // Only show for meaningful selections
        if (!floatingBtn) {
          floatingBtn = document.createElement("div");
          floatingBtn.id = "cleardoc-float-btn";
          floatingBtn.innerHTML = "📘 Explain";
          floatingBtn.addEventListener("click", () => {
            overlay.explain(selected);
            floatingBtn.style.display = "none";
          });
          document.body.appendChild(floatingBtn);
        }

        // Position near selection
        const range = window.getSelection().getRangeAt(0);
        const rect = range.getBoundingClientRect();
        floatingBtn.style.left = `${rect.left + window.scrollX}px`;
        floatingBtn.style.top = `${rect.top + window.scrollY - 40}px`;
        floatingBtn.style.display = "flex";
      } else {
        if (floatingBtn) floatingBtn.style.display = "none";
      }
    }, 10);
  });

  // Hide floating button when clicking elsewhere
  document.addEventListener("mousedown", (e) => {
    if (floatingBtn && !floatingBtn.contains(e.target)) {
      floatingBtn.style.display = "none";
    }
  });
})();
