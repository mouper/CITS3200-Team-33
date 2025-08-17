# CITS3200_Team_33# CITS3200_Team_33

## Project Structure

```
CITS3200-Team-33/                 # Root project repo
├─ docs/                            # Project documentation (minutes, specs, ADRs, designs)
├─ data/                            # Datasets, small fixtures, evaluation goldsets
├─ scripts/                         # Utility scripts for dataset prep and evaluation
├─ packages/                        # All code grouped as packages
│  ├─ extension/                    # Chrome MV3 extension
│  │  ├─ src/
│  │  │  ├─ content/                # Content scripts (YouTube scraping, selectors)
│  │  │  ├─ worker/                 # Worker for classification, cache, blocking logic
│  │  │  ├─ db/                     # IndexedDB wrapper + cache manager
│  │  │  ├─ ui/                     # Popup & Settings dashboard
│  │  │  ├─ lib/                    # Shared utility functions
│  │  │  └─ styles/                 # CSS/Tailwind styling
│  │
│  ├─ llm-client/                   # LLM access & model interaction package
│  │  ├─ src/                       # Core client (API wrappers, parsers, rate limit control)
│  │  └─ models/                    # Prompts, templates, model configs, versioned assets
│  │
│  ├─ analytics/                    # Local analytics & event aggregation logic
│  │
│  └─ shared/                       # Shared constants, enums, types used across packages
│
├─ tests/                           # Centralised test suite (unit, integration, end-to-end, perf)
```
