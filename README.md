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

## Running the browser extension

1. Open Chrome → go to chrome://extensions.
2. Toggle Developer mode.
3. Click “Load unpacked” → select the src folder (location = CITS3200-Team-33/packages/extension/src)
4. Pin the extension. Click the toolbar icon → in the popup, click “Open Dashboard”.

---

### Start the backend when the frontend is running

Option A — Windows (recommended during development):

```
scripts\dev.ps1
```

- Starts the Flask server on `http://127.0.0.1:5050` and tries to open Chrome with the unpacked extension loaded.
- The dashboard shows a status line under “Overview”: `Backend: Online` or `Backend: Offline`.

Option B — Manual steps:

1. Start the Flask server (from repo root):

```
python server\run.py
```

2. Load/open the extension dashboard (see steps above under “Running the browser extension”).
3. Confirm health: visit `http://127.0.0.1:5050/health` (should return `{ "status": "ok" }`).
   - The dashboard will also show the status line.

Notes:

- Default host/port are `127.0.0.1:5050`. Change by setting `FLASK_RUN_PORT` (or `PORT`).
- CORS is enabled for `/api/*`, `/health`, and `/version` for local dev. Lock this down for production.

---

## Running categorisation on cached videos (llm-client)

Prerequisites:

- Python with `requests` (and optionally `python-dotenv` if you use a `.env` file)
- Your `.env` at the repo root with:
  - `OPENAI_API_KEY=sk-...`
  - Optional: `OPENAI_MODEL_ID=gpt-5-nano`

### Option A: One-off categorisation run (reads from metadata cache DB, writes to categorised DB)

1. Ensure the DBs are initialised and the metadata cache has items.
   - If you already have the `databases/` layer running elsewhere, you can skip this.
2. From repo root, run:

```
python -c "import os,sys; sys.path.insert(0,'packages/llm-client/src'); from categorise_runner import run_once; model=os.getenv('OPENAI_MODEL_ID','gpt-5-nano'); print('Rows written:', run_once(model))"
```

This will:

- Fetch fresh (uncategorised) metadata rows from the cache
- Build a compact prompt
- Call the model with your `OPENAI_API_KEY`
- Parse and validate strict JSON
- Persist to `categorised_videos` DB

### Option B: Dry-run with dummy input (no DB writes)

From repo root:

```
python packages/llm-client/tests/e2e_llm_dummy_test.py
```

This prints the raw input, triaged payload, full prompt, live LLM response, and the final JSON that would be written to the DB.

---

## Running the local Flask service (server)

A lightweight Flask service is scaffolded under `server/` to expose local endpoints for metadata, classification, watched events, allostatic settings, and stats. Implementation stubs are provided; handlers will be added next.

Setup:

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

3. Run the server:

```
python server/run.py
```

The service binds to `127.0.0.1` on the port from `server/.env` (default 5050). Future `/api/*` endpoints will require the `X-LOCAL-TOKEN` header from the env file.

---

## Populating the databases with test data
1. The following steps must be done in the virtual environment with the .db files created ( after all the steps above in 'Running the local Flask service (server)' has been completed)

2. Create a smaller test json file

```
python scripts/json_sampler.py --fraction 0.2 --seed 42
# change the value after --fraction to change the size of data sampled e.g. --fraction 0.2 = 20% of 397 (the number of videos in youtube_sample_397.json)
```

3. Categorise and populate categorised.db + metadata_cache.db with test_metadata.json
```
python scripts/load_and_categorise.py
```