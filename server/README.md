# Local Flask Service (skeleton)

This directory contains the skeleton for a local Flask micro-service that will expose endpoints for:

- Metadata fetch and cache management
- LLM classification triggers and results access
- Watched events logging
- Allostatic parameters management
- Health and stats

No API route implementations are included yet. Route modules are placeholders to implement next.

## Structure

```
server/
  requirements.txt
  env.example
  run.py
  app/
    __init__.py
    config.py
    security.py
    background.py
    routes/
      __init__.py
      metadata.py
      classifier.py
      watched.py
      allostasis.py
      stats.py
```

## Setup

1. Create and activate a virtual environment

```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
```

2. Install dependencies

```
pip install -r server/requirements.txt
```

3. Create your local env file

```
copy server/env.example server/.env  # Windows
# then edit server/.env to set LOCAL_API_TOKEN, YT_API_KEY, etc.
```

## Running (development)

From the repo root:

```
python server/run.py
```

The service binds to 127.0.0.1 and the port defined by `PORT` in server/.env (default 5050).

## Auth Header (to be enforced)

All `/api/*` routes will require the header:

```
X-LOCAL-TOKEN: <value from server/.env LOCAL_API_TOKEN>
```

## Next steps

- Implement route blueprints in `app/routes/*.py`
- Register blueprints inside `app/__init__.py`
- Add token enforcement middleware in `app/security.py`
- Implement background classifier trigger in `app/background.py`
