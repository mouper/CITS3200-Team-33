# Mellow - Youtube Recommendation Filter
Team 33 Project for CITS3200

---

## Description

Mellow is a local Chrome/Edge extension plus Flask server that filters YouTube video recommendations using a lightweight probabilistic filter and an LLM-based categorizer. The content script scrapes visible video URLs, the service worker batches them to the local server for metadata, and the background worker categorizes these videos. The extension adds overlays to the YouTube page to block videos or entire sections (e.g., Shorts/Playables) according to user settings. 

Each content category has settings you control:
- Toggle a category Active/Inactive. Inactive categories are never filtered (strength is ignored).
- Choose a filter strength per active category (Weak, Moderate, Strong, Extra Strong, Blocked).

The probabilistic filter maintains a per-category block probability that increases with watchtime and decays over time. The chosen strength scales how quickly the probability rises and the rate of decay, a higher strength increases the blocking probability at a faster rate and takes longer to decay. “Blocked” is a special strength that always blocks that category.

---

# Setup and Usage Instructions

## 1. Setup the Extension and Server

1. Clone the repository:

```
git clone https://github.com/mouper/CITS3200-Team-33.git
```


2. Create a Python venv and install deps:

```
python -m venv .venv # Depending on your system, you may need to use 'python3' instead
. .venv/Scripts/activate  # Windows PowerShell command
source .venv/bin/activate # macOS/ Linux command
pip install -r server/requirements.txt
```

3. Create env file:

```
copy server/env.example server/.env # Windows PowerShell command
cp server/env.example server/.env # macOS/ Linux command

```

4. Populate environment variables:

Populate the following keys in the .env file with your real confidential keys.
```
# External APIs
YT_API_KEY=your-youtube-api-key
OPENAI_API_KEY=your-openai-api-key
```

5. Run the server:

```
python server/run.py
```

The service binds to `127.0.0.1` on the port from `server/.env` (default 5050).

When the server starts for the first time, it automatically initializes all databases and sets user settings to default values. The following categories are set as active by default with the filter strength set to 'Moderate':
- Sensational/Outrage News
- Politics
- Gaming
- Sexual and Explicit
- Violent and Graphic
- Controversial and Conspiracy Theories


## 2. Load the Extension

1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select `packages/extension/src/`
4. Pin the extension
5. The extension should now be active 
   - Please note that the server must be running for the extension to function


## 3. Use the Extension

1. Click the toolbar icon → in the popup, click “Open Dashboard”
2. Adjust the content category filter settings
3. Visit `https://www.youtube.com`
5. Enjoy your customised YouTube video feed!

---

# Testing Instructions

## 1. Install Test Dependencies

Make sure you have a Python virtual environment activated and all dependencies installed:

```sh
pip install -r server/requirements.txt
```

## 2. Run All Tests

From the project root, run:

```sh
pytest -v
```

This will automatically discover and run all unit, integration, and end-to-end tests in the `tests/` folder and package subfolders.

## 3. Run Specific Test Files

To run a single test file, use:

```sh
pytest tests/test_categorised_db.py
```

Or for a package test:

```sh
pytest packages/llm_client/tests/test_metadata_triage.py
```

## 4. Troubleshooting

- If you see `ModuleNotFoundError: No module named 'databases'`, ensure your project root is on `PYTHONPATH` or run tests from the root directory.
- If you get database lock errors, make sure tests are not running in parallel unless designed for it.
- For flaky tests, rerun with `pytest --maxfail=1 -v` to see detailed output.

## 5. Test Structure

- All tests are in the `tests/` folder and package-specific `tests/` subfolders.
- Fixtures and test helpers are defined in `tests/conftest.py`.
- Each test file targets a specific module or feature.

---
