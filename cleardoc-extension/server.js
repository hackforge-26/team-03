const express = require("express");
const initSqlJs = require("sql.js");
const cors = require("cors");
const { v4: uuidv4 } = require("uuid");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = 3847;

app.use(cors());
app.use(express.json({ limit: "5mb" }));
app.use(express.urlencoded({ extended: true, limit: "5mb" }));

// ── Database ────────────────────────────────────────────────
const DB_PATH = path.join(__dirname, "cleardoc.db");
let db = null;

async function initDB() {
  const SQL = await initSqlJs();

  if (fs.existsSync(DB_PATH)) {
    const buf = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buf);
  } else {
    db = new SQL.Database();
  }

  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      device_id TEXT UNIQUE NOT NULL,
      full_name TEXT NOT NULL,
      email TEXT NOT NULL,
      language TEXT DEFAULT 'en',
      created_at TEXT DEFAULT (datetime('now'))
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      original_text TEXT NOT NULL,
      file_name TEXT,
      doc_type TEXT DEFAULT 'other',
      language TEXT DEFAULT 'en',
      is_saved INTEGER DEFAULT 0,
      meaning TEXT,
      key_points TEXT,
      steps TEXT,
      deadline TEXT,
      urgency_flag INTEGER DEFAULT 0,
      urgency_message TEXT,
      processing_time_ms INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  saveDB();
  console.log("  🗄️  Database: SQLite (sql.js WASM)");
}

function saveDB() {
  if (!db) return;
  const data = db.export();
  fs.writeFileSync(DB_PATH, Buffer.from(data));
}

// ── Anthropic Client ────────────────────────────────────────
let anthropicClient = null;
if (process.env.ANTHROPIC_API_KEY) {
  try {
    const Anthropic = require("@anthropic-ai/sdk");
    anthropicClient = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    console.log("  🧠 Anthropic API: configured");
  } catch (e) {
    console.log("  ⚠️  Anthropic SDK load failed, using demo mode");
  }
} else {
  console.log("  🎭 Anthropic API: demo mode (set ANTHROPIC_API_KEY for real AI)");
}

const SYSTEM_PROMPT = `You are ClearDoc — a document simplification assistant that helps 
people who are confused by official documents. Your users include
elderly people, immigrants, low-income families, and people with
learning disabilities.

RULES:
1. Always respond with ONLY valid JSON — no extra text, no markdown
2. Simplify to 8th grade reading level maximum
3. Be warm, clear, and reassuring — the user is stressed
4. Never give legal or medical advice — explain what the document SAYS, not what the user should do legally
5. Always respond in the language specified in the request
6. Detect document type automatically from content
7. Extract ALL deadlines — they are critical

RESPONSE FORMAT (strict JSON):
{
  "doc_type": "medical_bill|legal_notice|govt_form|landlord_letter|other",
  "deadline": "specific date mentioned or null",
  "meaning": "2-3 sentence plain English explanation of what this document means for the user",
  "key_points": [
    {"label": "Status", "value": "the current status"},
    {"label": "Missing Item", "value": "what is missing if anything"},
    {"label": "Amount", "value": "monetary amount if applicable"}
  ],
  "steps": [
    {"title": "step title", "description": "brief description"},
    {"title": "step 2 title", "description": "brief description"}
  ],
  "urgency_flag": true or false,
  "urgency_message": "specific deadline info or null"
}`;

// ── Demo Results ────────────────────────────────────────────
const DEMO_RESULTS = {
  medical: {
    doc_type: "medical_bill",
    deadline: "April 15, 2025",
    meaning: "Your health insurance claim for your recent ER visit was partially approved, but they need more information. They've covered the hospital stay, but the final doctor's evaluation is pending review because the correct diagnosis code wasn't included on the initial form.",
    key_points: [
      { label: "Status", value: "Partially Approved" },
      { label: "Missing Item", value: "Provider Diagnosis Code (Form HC-1500)" },
      { label: "Covered Amount", value: "$1,450.00 (Hospital Facility Fee)" }
    ],
    steps: [
      { title: "Download Form HC-1500", description: "Available on your provider's patient portal." },
      { title: "Get Doctor's Signature", description: "Have Dr. Smith's office fill in the diagnosis code and sign." },
      { title: "Upload to Portal", description: "Submit the completed form via the claims portal before April 15." }
    ],
    urgency_flag: true, urgency_message: "Action required by April 15 — don't miss this deadline."
  },
  legal: {
    doc_type: "legal_notice",
    deadline: "March 25, 2025",
    meaning: "Your landlord says you haven't paid March rent. A $75 late fee has been added. If you don't pay by March 25, they can begin formal eviction proceedings. This is the first notice — you have time to fix this.",
    key_points: [
      { label: "Status", value: "First Notice — Not Yet in Eviction" },
      { label: "Amount Due", value: "$1,325.00 (Rent + $75 Late Fee)" },
      { label: "Deadline", value: "March 25, 2025" }
    ],
    steps: [
      { title: "Pay $1,325 online", description: "Visit portal.oakwoodproperties.com or call (555) 890-1234." },
      { title: "Request a payment plan", description: "If you can't pay in full, contact the landlord before the deadline." },
      { title: "Keep your receipts", description: "Save all payment confirmations as proof." }
    ],
    urgency_flag: true, urgency_message: "Action required by March 25 — eviction proceedings begin after this date."
  },
  govt: {
    doc_type: "govt_form",
    deadline: "April 10, 2025",
    meaning: "Your California driver's license will be suspended on April 10 because you don't have the required SR-22 insurance certificate on file. You need to file an SR-22, pay a $125 reinstatement fee, and maintain the insurance for 3 years.",
    key_points: [
      { label: "Status", value: "Suspension Pending" },
      { label: "Missing Item", value: "SR-22 Financial Responsibility Certificate" },
      { label: "Reinstatement Fee", value: "$125.00" }
    ],
    steps: [
      { title: "Contact your insurance company", description: "Ask them to file an SR-22 certificate with the DMV immediately." },
      { title: "Pay the $125 reinstatement fee", description: "Pay online at dmv.ca.gov or call (800) 777-0133." },
      { title: "Do NOT drive until lifted", description: "Driving during suspension is a criminal misdemeanor." }
    ],
    urgency_flag: true, urgency_message: "Action required by April 10 — your license will be suspended."
  }
};

function getDemoResult(text) {
  const lower = text.toLowerCase();
  if (lower.includes("medical") || lower.includes("bill") || lower.includes("patient") || lower.includes("hospital") || lower.includes("charge") || lower.includes("valley medical")) return DEMO_RESULTS.medical;
  if (lower.includes("rent") || lower.includes("lease") || lower.includes("tenant") || lower.includes("landlord") || lower.includes("eviction")) return DEMO_RESULTS.legal;
  if (lower.includes("dmv") || lower.includes("license") || lower.includes("suspension") || lower.includes("vehicle") || lower.includes("sr-22")) return DEMO_RESULTS.govt;
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10).slice(0, 3);
  return {
    doc_type: "other",
    deadline: null,
    meaning: sentences.length > 0 ? "This document appears to be about: " + sentences[0].trim() + ". " + (sentences[1] ? sentences[1].trim() + "." : "") : "This document contains information that we're analyzing for you.",
    key_points: [
      { label: "Type", value: "Document" },
      { label: "Action Needed", value: "Review carefully" },
      { label: "Status", value: "Requires attention" }
    ],
    steps: [
      { title: "Read the full document", description: "Review every section carefully." },
      { title: "Note any deadlines", description: "Mark important dates on your calendar." },
      { title: "Contact the sender if needed", description: "Use the contact info in the document." }
    ],
    urgency_flag: false, urgency_message: null
  };
}

// ── API Routes ──────────────────────────────────────────────

// Sign up
app.post("/api/signup", (req, res) => {
  const { full_name, email } = req.body;
  if (!full_name || !email) return res.status(400).json({ error: "Full name and email are required" });

  // Check existing
  const existing = db.exec("SELECT * FROM users WHERE email = ?", [email]);
  if (existing.length > 0 && existing[0].values.length > 0) {
    const row = existing[0].values[0];
    return res.json({ success: true, user: { id: row[0], device_id: row[1], full_name: row[2], email: row[3] }, message: "Welcome back!" });
  }

  const userId = uuidv4();
  const deviceId = "web-" + uuidv4();
  try {
    db.run("INSERT INTO users (id, device_id, full_name, email) VALUES (?, ?, ?, ?)", [userId, deviceId, full_name, email]);
    saveDB();
    res.json({ success: true, user: { id: userId, device_id: deviceId, full_name, email }, message: "Account created!" });
  } catch (err) {
    console.error("Signup error:", err);
    res.status(500).json({ error: "Failed to create account" });
  }
});

// Explain
app.post("/api/explain", async (req, res) => {
  const { text, language, user_id } = req.body;
  if (!text || !text.trim()) return res.status(400).json({ error: "Document text is required" });

  const start = Date.now();
  let result;

  if (anthropicClient) {
    try {
      const response = await anthropicClient.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 1000,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: `Language to respond in: ${language || "en"}\n\nDocument:\n${text.substring(0, 10000)}` }]
      });
      let raw = response.content[0].text.trim();
      if (raw.startsWith("```")) { raw = raw.split("```")[1]; if (raw.startsWith("json")) raw = raw.substring(4); }
      result = JSON.parse(raw);
    } catch (err) {
      console.error("Anthropic error:", err.message);
      result = getDemoResult(text);
    }
  } else {
    result = getDemoResult(text);
  }

  result.processing_time_ms = Date.now() - start;

  // Save to DB
  if (user_id) {
    try {
      const userRes = db.exec("SELECT id FROM users WHERE device_id = ?", [user_id]);
      if (userRes.length > 0 && userRes[0].values.length > 0) {
        const dbUserId = userRes[0].values[0][0];
        const docId = uuidv4();
        db.run(
          "INSERT INTO documents (id, user_id, original_text, doc_type, language, meaning, key_points, steps, deadline, urgency_flag, urgency_message, processing_time_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          [docId, dbUserId, text.substring(0, 10000), result.doc_type || "other", language || "en", result.meaning || result.summary || "", JSON.stringify(result.key_points), JSON.stringify(result.steps), result.deadline || null, result.urgency_flag ? 1 : 0, result.urgency_message || null, result.processing_time_ms]
        );
        saveDB();
        result.document_id = docId;
      }
    } catch (err) {
      console.error("Save error:", err.message);
    }
  }

  res.json(result);
});

// Follow-up
app.post("/api/followup", async (req, res) => {
  const { document_id, question, language } = req.body;
  if (!question || !question.trim()) return res.status(400).json({ error: "Question is required" });

  let originalText = "";
  if (document_id) {
    const docRes = db.exec("SELECT original_text FROM documents WHERE id = ?", [document_id]);
    if (docRes.length > 0 && docRes[0].values.length > 0) originalText = docRes[0].values[0][0];
  }

  if (anthropicClient) {
    try {
      const response = await anthropicClient.messages.create({
        model: "claude-sonnet-4-6", max_tokens: 500,
        system: `You are ClearDoc. Answer the user's follow-up question about their document. Answer in language: ${language || "en"}. Be warm, clear, at 8th grade reading level. Be specific to THEIR document.`,
        messages: [{ role: "user", content: `Document:\n${originalText}\n\nQuestion: ${question}` }]
      });
      return res.json({ answer: response.content[0].text });
    } catch (err) { console.error("Followup error:", err.message); }
  }

  res.json({ answer: `Based on this document, regarding your question "${question}" — I'd recommend reviewing the relevant section carefully and contacting the issuing organization directly. Many organizations offer options or accommodations if you explain your situation. Look for phone numbers or contact information in the original document.` });
});

// History
app.get("/api/history/:deviceId", (req, res) => {
  const { deviceId } = req.params;
  const limit = parseInt(req.query.limit) || 20;
  const userRes = db.exec("SELECT id FROM users WHERE device_id = ?", [deviceId]);
  if (userRes.length === 0 || userRes[0].values.length === 0) return res.json([]);
  const userId = userRes[0].values[0][0];
  const docs = db.exec("SELECT id, meaning, doc_type, language, urgency_flag, created_at FROM documents WHERE user_id = ? AND is_saved = 1 ORDER BY created_at DESC LIMIT ?", [userId, limit]);
  if (docs.length === 0) return res.json([]);
  res.json(docs[0].values.map(r => ({ id: r[0], summary: r[1], doc_type: r[2], language: r[3], urgency_flag: !!r[4], created_at: r[5] })));
});

// Get document
app.get("/api/document/:docId", (req, res) => {
  const docRes = db.exec("SELECT * FROM documents WHERE id = ?", [req.params.docId]);
  if (docRes.length === 0 || docRes[0].values.length === 0) return res.status(404).json({ error: "Not found" });
  const r = docRes[0].values[0];
  res.json({ id: r[0], meaning: r[7], key_points: JSON.parse(r[8] || "[]"), steps: JSON.parse(r[9] || "[]"), deadline: r[10], urgency_flag: !!r[11], urgency_message: r[12], doc_type: r[4], language: r[5], original_text: r[2], created_at: r[14] });
});

// Save
app.post("/api/save", (req, res) => {
  const { document_id } = req.body;
  if (!document_id) return res.status(400).json({ error: "document_id required" });
  db.run("UPDATE documents SET is_saved = 1 WHERE id = ?", [document_id]);
  saveDB();
  res.json({ success: true });
});

// Delete
app.delete("/api/document/:docId/:deviceId", (req, res) => {
  const userRes = db.exec("SELECT id FROM users WHERE device_id = ?", [req.params.deviceId]);
  if (userRes.length === 0 || userRes[0].values.length === 0) return res.status(404).json({ error: "User not found" });
  db.run("DELETE FROM documents WHERE id = ? AND user_id = ?", [req.params.docId, userRes[0].values[0][0]]);
  saveDB();
  res.json({ success: true });
});

// Health
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", services: { database: "ok", anthropic: anthropicClient ? "configured" : "demo-mode" } });
});

// Static files
app.use(express.static(__dirname));
app.get("*", (req, res) => res.sendFile(path.join(__dirname, "index.html")));

// ── Start ───────────────────────────────────────────────────
(async () => {
  await initDB();
  app.listen(PORT, () => {
    console.log(`\n  📘 ClearDoc running at http://localhost:${PORT}\n`);
  });
})();
