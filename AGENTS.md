# AGENTS.md

## Purpose

This file is internal project context for future coding sessions.
Read this before making non-trivial changes.

Project: `a-little-new`
Type: desktop PyQt6 app for managing site lists, categories, per-site paths, shared paths, and batch URL checks.
Primary target: Windows.

## Current Architecture

The project was refactored away from a monolithic `main.py`.

- `main.py`
  Thin entrypoint. It only calls `url_auto_opener.app.run()`.
- `url_auto_opener/app.py`
  Creates `QApplication`, wires dependencies, starts `MainWindow`.
- `url_auto_opener/window.py`
  Main UI layer. Contains widget creation and user interaction flows.
  It should not absorb JSON parsing or low-level HTTP logic again.
- `url_auto_opener/state.py`
  State repository. Handles:
  loading `sites.json`,
  normalizing imported JSON,
  generating default site names,
  saving current state,
  backup of invalid state files before overwrite.
- `url_auto_opener/url_service.py`
  URL normalization, URL building, HTTP status checks, browser opening.
- `url_auto_opener/workers.py`
  Background workers for path checks. Keeps network operations off the GUI thread.
- `url_auto_opener/models.py`
  Dataclasses and typed request/result structures.
- `tests/test_state.py`
  Tests for state normalization and invalid file backup behavior.
- `tests/test_url_service.py`
  Tests for URL normalization and status classification.

## Important Invariants

- Keep network checks out of the GUI thread.
  `check_site_paths()` and `check_common_paths_by_category()` must stay responsive.
- Keep state as typed dataclasses, not raw dictionaries.
  `Site` and `AppState` are the source of truth.
- Keep JSON compatibility with the current persisted structure:
  `sites` list and `common_paths` list.
- Preserve the invalid-state safety behavior:
  if `sites.json` is broken, the app must not silently overwrite it.
  The old file is backed up on the next successful save.
- Redirects are intentionally classified separately from success.
  Do not collapse them back into plain green `OK`.
- `window.py` may coordinate workflows, but low-level serialization and HTTP logic belong in services.

## Data Model

Persisted JSON shape:

```json
{
  "sites": [
    {
      "name": "Example",
      "category": "MODX Revo",
      "base_url": "https://example.com/",
      "manager_url": "https://example.com/manager/",
      "paths": ["catalog", "contacts"]
    }
  ],
  "common_paths": ["robots.txt", "sitemap.xml"]
}
```

Legacy import compatibility exists for older payloads with `main_url` and `paths`.

## Working Rules For Future Changes

- If a change is purely about JSON/state handling, start in `state.py`.
- If a change is purely about URL behavior, start in `url_service.py`.
- If a change is about long-running checks, use `workers.py` and signals.
- If a change is about screen behavior or widget flow, use `window.py`.
- Do not move business logic back into `main.py`.
- Prefer adding tests when changing:
  JSON normalization,
  backup behavior,
  URL classification,
  URL building.

## Common Commands

Setup:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run:

```powershell
python main.py
```

Tests:

```powershell
python -m unittest discover -s tests
```

Compile smoke check:

```powershell
python -m compileall main.py url_auto_opener tests
```

Build exe:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

## Known Practical Notes

- The repository has been used on Windows with CRLF warnings in git.
  Do not treat those warnings as functional problems by default.
- `sites.json` is local runtime data and may contain user state.
  Be careful when changing save/load behavior.
- `webbrowser` opening is wrapped in `UrlService.open_in_browser()`.
  Keep browser fallback behavior there.
- Closing the window during active checks is intentionally blocked in `window.py`.

## When Starting A New Task

Minimal reading order:

1. `AGENTS.md`
2. `README.md`
3. The specific module for the task:
   `window.py`, `state.py`, `url_service.py`, or `workers.py`
4. Related tests

## Refactor History

Recent major change:

- The app was modularized from a single large `main.py` into a package.
- Basic automated tests were added.
- Background URL checks and state safety behavior were preserved during the refactor.
