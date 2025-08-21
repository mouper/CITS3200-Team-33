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
