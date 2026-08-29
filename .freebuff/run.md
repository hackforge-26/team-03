# ClearDoc Full-Stack Preview — Run Doc

## How to reproduce the artifacts

1. Install Node.js dependencies:
   ```
   cd cleardoc-extension
   npm install
   ```

2. No `.env` file needed — the server runs in demo mode by default.
   To enable real AI, set `ANTHROPIC_API_KEY` before starting.

## How to run the server

Start the Express server:
```
cd cleardoc-extension
node server.js
```

The server runs on port **3847** and serves:
- `GET /` — Sign-up page (exact Stitch design)
- `GET /app.html` — Main app with Screen 2 result layout
- `POST /api/signup` — Create account (SQLite)
- `POST /api/explain` — Explain document (demo mode or Anthropic API)
- `POST /api/followup` — Follow-up questions
- `GET /api/history/:deviceId` — View saved documents
- `POST /api/save` — Save document to history
- `GET /api/health` — Backend health check

## Key files
- `index.html` — Sign-up page (Google Stitch design)
- `app.html` — Main app with Screen 2 result layout (deadline banner, meaning, labeled key points, interactive checklist with particle burst)
- `server.js` — Express backend with sql.js (WASM SQLite) + Anthropic proxy
- `package.json` — Dependencies

## Screen 2 Result Format
The backend returns results in this structured format:
```json
{
  "doc_type": "medical_bill",
  "deadline": "April 15, 2025",
  "meaning": "Plain English explanation...",
  "key_points": [
    {"label": "Status", "value": "Partially Approved"},
    {"label": "Missing Item", "value": "Provider Diagnosis Code"}
  ],
  "steps": [
    {"title": "Download Form HC-1500", "description": "Available on portal"},
    {"title": "Get Doctor's Signature", "description": "Fill in diagnosis code"}
  ],
  "urgency_flag": true,
  "urgency_message": "Action required by April 15..."
}
```
