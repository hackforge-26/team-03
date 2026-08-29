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

```
cd cleardoc-extension
node server.js
```

Port **3847**. Endpoints:
- `GET /` — Screen 1: Sign-up page
- `GET /app.html` — Screen 2-4: Main app with bottom nav (Home/History/Upload/Help)
- `GET /result.html?id=<docId>` — Screen 3: Standalone result detail from history
- `POST /api/signup` — Create account
- `POST /api/explain` — Explain document
- `POST /api/followup` — Follow-up questions
- `GET /api/history/:deviceId` — Saved documents
- `POST /api/save` — Save to history
- `GET /api/health` — Health check

## Screen Flow
1. **Screen 1 (index.html)** — Sign Up → creates user → redirects to app
2. **Screen 2 (app.html#home)** — Paste/load doc → language chips → Simplify Now → Screen 2 result
3. **Screen 3 (result.html)** — Tap history item → full result detail
4. **Screen 4 (app.html#upload)** — Upload zone with file picker + camera scan
5. **Bottom Nav** — Home, History, Upload, Help tabs

## Key files
- `index.html` — Screen 1: Stitch sign-up
- `app.html` — Screens 2+4: Main app with bottom nav + all tabs
- `result.html` — Screen 3: Detail view from history
- `server.js` — Express + sql.js + Anthropic proxy
