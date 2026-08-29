# ClearDoc Browser Extension

A Chrome/Edge/Firefox extension that lets you understand any document directly from your browser. Select text on any webpage, right-click, and get an instant plain-English explanation powered by AI.

## Features

- 📘 **Right-Click Explain** — Select text on any webpage → right-click → "Explain with ClearDoc"
- 📋 **Floating Button** — Text selection shows a quick "Explain" button
- 💬 **Follow-up Questions** — Ask questions about the document in context
- 📊 **Document Comparison** — Flag unusual or unfair clauses
- 📚 **History** — Save and revisit past explanations
- ⚙️ **Configurable** — Set your backend URL, language preferences, and more

## How It Works

```
1. User selects text on any webpage
2. Extension sends text to ClearDoc backend API
3. Backend calls Claude AI to simplify the document
4. Result displayed in a beautiful overlay — no page navigation needed
```

## Installation

### Option 1: Load as Developer (Recommended for Testing)

1. **Start your ClearDoc backend** (see main README)
2. Open Chrome and go to `chrome://extensions/`
3. Enable **Developer mode** (top right toggle)
4. Click **Load unpacked**
5. Select the `cleardoc-extension/` folder
6. The extension icon appears in your toolbar

### Option 2: Package for Distribution

1. Go to `chrome://extensions/`
2. Click **Pack extension**
3. Select the `cleardoc-extension/` folder
4. This creates a `.crx` file you can distribute

### Option 3: Publish to Chrome Web Store

1. Zip the `cleardoc-extension/` folder
2. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
3. Pay the one-time $5 fee
4. Upload your zip file
5. Fill in store listing details
6. Submit for review

## Configuration

### First Time Setup

1. Click the extension icon in your toolbar
2. Go to the **Settings** tab
3. Enter your ClearDoc backend URL (e.g., `https://your-cleardoc-backend.com`)
4. Click **Test Connection** to verify
5. Choose your default language
6. Click **Save Settings**

### Required Backend

This extension requires a running ClearDoc backend API. See the main project README for setup instructions.

**Quick Start with Docker:**
```bash
cd cleardoc-backend
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
# Backend runs at http://localhost:8000
```

## Usage

### Method 1: Right-Click Context Menu

1. Select any text on a webpage (medical bill, legal notice, etc.)
2. Right-click the selected text
3. Click **"📘 Explain with ClearDoc"**
4. An overlay appears with the simplified explanation

### Method 2: Floating Button

1. Select text on any webpage
2. A small "📘 Explain" button appears near your selection
3. Click it to get the explanation

### Method 3: Popup

1. Click the extension icon in your toolbar
2. Paste document text into the text area
3. Select your language
4. Click **"Explain This Document"**

### Method 4: Extract Page Text

1. Click the extension icon
2. Click **"📄 Extract Text from This Page"**
3. The page text is automatically extracted
4. Click **"Explain This Document"**

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/explain` | POST | Main document explanation |
| `/followup` | POST | Follow-up questions |
| `/compare/{id}` | GET | Document comparison |
| `/history` | GET | View saved documents |
| `/history/save` | POST | Save to history |
| `/health` | GET | Backend health check |

## File Structure

```
cleardoc-extension/
├── manifest.json          # Extension configuration
├── background.js          # Service worker (API calls)
├── content.js             # Content script (page injection)
├── popup.html             # Popup UI
├── popup.js               # Popup logic
├── options.html           # Settings page
├── options.js             # Settings logic
├── styles/
│   ├── popup.css          # Popup styles
│   ├── overlay.css        # In-page overlay styles
│   └── options.css        # Settings styles
├── icons/
│   ├── icon16.png         # Toolbar icon
│   ├── icon48.png         # Extension page icon
│   ├── icon128.png        # Store icon
│   └── generate-icons.html # Helper to generate PNGs
└── README.md              # This file
```

## Permissions

| Permission | Why |
|------------|-----|
| `storage` | Store user settings and preferences |
| `activeTab` | Access current tab for text extraction |
| `contextMenus` | Right-click "Explain with ClearDoc" menu |
| `identity` | Optional: OAuth if you add user accounts later |

## Privacy

- **No tracking** — The extension only communicates with your backend
- **Local storage** — Settings stored locally via `chrome.storage`
- **No data collection** — We don't collect any user data
- **User ID** — A random UUID generated locally, never leaves your devices

## Troubleshooting

### "Could not connect to ClearDoc backend"
1. Make sure your backend is running
2. Check the URL in Settings (no trailing slash)
3. Ensure CORS allows your extension (add `chrome-extension://` to allowed origins)

### Floating button doesn't appear
1. Make sure the content script is loaded (check extension details)
2. Try refreshing the page
3. Some pages block content scripts (e.g., Chrome Web Store, `chrome://` pages)

### Right-click menu missing
1. Disable and re-enable the extension
2. Make sure you have text selected before right-clicking

## Browser Compatibility

- ✅ Chrome 88+
- ✅ Edge 88+
- ✅ Firefox 109+ (Manifest V3 support required)
- ⚠️ Safari (not yet supported — requires native app)

## License

MIT
