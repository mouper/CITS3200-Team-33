# AI Recommendation Filter - Team 33 Project for CITS3200

---

## Issue Creation Guidelines

To keep our workflow organized and efficient, please follow these conventions when creating a new issue:

### Use Present Tense in the Title

Write issue titles in **present tense**, using a verb that describes the action.

- Good: `Create navbar component`
- Bad: `Created navbar component`, `Navbar was created`

### Add an Image of the Design

Include a **screenshot or link** to the relevant design (e.g., from Figma) to give visual context for the task.

### List Reusable Components and Styles

If the issue involves building **reusable components or styles**, list them out clearly.

#### Example List:

- components/Navbar.tsx
- components/Button.tsx

### Reporting a Bug

Start the issue with 'Bug:'

- e.g. Bug: Save button broken

---

## Branch Naming Convention

This project follows a consistent branch naming strategy to improve collaboration and maintain clarity across development activities.

### Branch Types

- **`feature/`**  
  Used for adding, refactoring, or removing a feature.

- **`bugfix/`**  
  Used for fixing a bug.

- **`test/`**  
  Used for experimenting or prototyping outside of a specific ticket or issue.

### Reference

After the branch category, include the **reference** to the issue or ticket you're working on. If there's no reference, use `no-ref`.

### Example Branch Name

`feature/issue-42/create-new-button-component`

---

## Commit Message Convention

Commit messages should be clear, concise, and follow a structured format to communicate changes effectively.

### Categories

Start your commit message with one of the following categories:

- **`feat`** — Adding a new feature
- **`fix`** — Fixing a bug
- **`refactor`** — Improving code for performance or readability, without changing behavior
- **`chore`** — Maintenance tasks (e.g. documentation, formatting, tests, cleanup)

### Format

Each commit message should follow this pattern:
**`<category>: statement`**

- The **category** is followed by a colon `:` and a space
- Each **statement** is a short, imperative verb phrase
- Separate multiple statements with a **semicolon `;`**

### Example Commit Message

`feat: add button component`

---

## Project Structure

```
CITS3200-Team-33/                 # Root project repo
├─ docs/                            # Project documentation (sprint deliverables + Figma design)
├─ data/                            # Datasets, small fixtures, evaluation goldsets
├─ scripts/                         # Utility scripts for dataset prep and evaluation
├─ packages/                        # All code grouped as packages
│  ├─ extension/                    # Chrome MV3 extension
│  │  └─ src/
│  │     ├─ content/                # Content scripts (YouTube scraping, selectors)
│  │     ├─ worker/                 # Worker for classification, cache, blocking logic
│  │     ├─ db/                     # IndexedDB wrapper + cache manager
│  │     ├─ ui/                     # Popup & Settings dashboard
│  │     ├─ lib/                    # Shared utility functions
│  │     └─ static/                 # Static assets + styles
│  │        └─ assets/              # Images, icons, etc
│  │        └─ css/                 # CSS stylesheets
│  │        └─ js/                  # Javascript files
│  │
│  ├─ llm-client/                   # LLM access & model interaction package
│  │  ├─ src/                       # Core client (API wrappers, parsers, rate limit control)
│  │  └─ models/                    # Prompts, templates, model configs, versioned assets
│  │
│  ├─ analytics/                    # Local analytics & event aggregation logic
│  │
│  └─ shared/                       # Shared constants, enums, types used across packages
│
└─ tests/                           # Centralised test suite (unit, integration, end-to-end, perf)
```

---

# YouTube URL Scraping Integration

This feature enables dynamic scraping of YouTube video URLs from the homepage and automatic metadata processing.

## How It Works

1. **Content Script** (`packages/extension/src/content/youtube-scraper.js`)
   - Runs on YouTube pages
   - Continuously monitors for recommended video URLs
   - Extracts video IDs from various YouTube URL formats
   - Sends URLs to the service worker in batches

2. **Service Worker** (`packages/extension/src/worker/service-worker.js`)
   - Receives URLs from content script
   - Queues URLs for processing
   - Sends batches to the server API
   - Handles retries and error recovery

3. **Server API** (`server/app/routes/metadata.py`)
   - Receives URL batches from extension
   - Extracts video IDs from URLs
   - Fetches metadata using YouTube Data API
   - Stores metadata in `metadata_cache.db`
   - Avoids duplicate processing

4. **Background Categorizer** (`server/app/background.py`)
   - Continuously monitors for fresh metadata
   - Automatically categorizes new videos
   - Moves processed videos to categorized database

## Configuration

### Content Script Settings

In `youtube-scraper.js`:
- `scrapeDelay`: Time between URL scans (default: 2000ms)
- `maxUrlsPerBatch`: Maximum URLs per batch (default: 10)

### Service Worker Settings

In `service-worker.js`:
- `SERVER_URL`: Your server URL (default: http://localhost:5000)
- `BATCH_SIZE`: URLs per API call (default: 10)
- `PROCESSING_DELAY`: Delay between batches (default: 2000ms)
- `MAX_RETRIES`: Retry attempts for failed requests (default: 3)

## API Endpoints

- `POST /api/metadata/batch` - Process multiple URLs from extension
- `POST /api/metadata/fetch` - Fetch single video metadata
- `GET /api/metadata/fresh` - Get fresh metadata awaiting processing
- `GET /api/metadata/<video_id>` - Get specific video metadata

## Monitoring

### Browser Console
Check for logs from:
- `[YouTube Scraper]` - Content script activity
- `[Service Worker]` - Background processing

### Server Logs
Monitor for:
- API requests from extension
- Metadata processing
- Background categorization activity

### Database
Check `databases/metadata_cache.db` for:
- Fresh metadata awaiting processing
- Processed metadata with timestamps

## Troubleshooting

### Extension Not Working
1. Check browser console for errors
2. Verify extension is loaded and enabled
3. Ensure you're on a YouTube page
4. Check manifest.json permissions

### Server Not Receiving URLs
1. Verify server is running on correct port
2. Check CORS settings
3. Look for network errors in browser console
4. Test API endpoint manually

### Metadata Not Processing
1. Check `YT_API_KEY` environment variable
2. Verify YouTube API quota
3. Check server logs for API errors
4. Ensure background categorizer is enabled

### Background Categorizer Not Running
1. Set `CLASSIFIER_AUTORUN=true`
2. Check server logs for categorization activity
3. Verify LLM client is properly configured
4. Check database for fresh metadata

## URL Patterns Supported

The scraper detects URLs in these formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

## Performance Considerations

- URLs are deduplicated automatically
- Processing is batched to avoid API rate limits
- Failed requests are retried with exponential backoff
- Old URLs are cleaned up automatically
- Background processing runs continuously but efficiently

---

# Setup and Usage Instructions

## 1. Setup the Extension and Server

1. Create a Python venv and install deps:

```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell command
source .venv/bin/activate # macOS/ Linux command
pip install -r server/requirements.txt
```

2. Create env file:

```
copy server/env.example server/.env # Windows PowerShell command
cp server/env.example server/.env # macOS/ Linux command

```

3. Populate environment variables:

Populate the following keys in the .env file with your real confidential keys.
```
# External APIs
YT_API_KEY=your-youtube-api-key
OPENAI_API_KEY=your-openai-api-key
```

4. Run the server:

```
python server/run.py
```

The service binds to `127.0.0.1` on the port from `server/.env` (default 5050). Future `/api/*` endpoints will require the `X-LOCAL-TOKEN` header from the env file.

When the server starts for the first time, it automatically initializes all databases and sets user settings to default values. The following categories are set as active by default:
- Sensational/Outrage News
- Politics
- Gaming
- Sexual and Explicit
- Violent and Graphic
- Controversial and Conspiracy Theories


## 3. Load the Extension

1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select `packages/extension/src/`
4. Pin the extension
5. The extension should now be active 
   - Please note that the server must be running for the extension to function


## 4. Use the Extension

1. Click the toolbar icon → in the popup, click “Open Dashboard”
2. Adjust the content category filter settings
3. Visit `https://www.youtube.com`
4. Wait for the initial categoriser loading screen to end
5. Enjoy your customised YouTube video feed!
