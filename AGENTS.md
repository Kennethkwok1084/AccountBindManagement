# Repository Guidelines

Contributors help keep the ISP account manager reliable and auditable. This guide highlights how the Streamlit app is organized, how to work locally, and what to expect at review time.

## Project Structure & Module Organization
`app.py` bootstraps the Streamlit dashboard and composes helpers from `ui_components.py`, `utils/`, and `database/`. Feature pages live in `pages/`, ordered numerically and by emoji (for example `1_🗂️_账号管理.py`), so keep that prefix when adding new views. Persistence sits in `database/models.py` and `database/operations.py`, while automation logic belongs in `utils/` (see `scheduler.py` and `business_logic.py`). User-facing assets, sample spreadsheets, and the SQLite file live in `data/`, and deployment scripts reside in `deploy/` and Docker manifests at the repository root.

## Build, Test, and Development Commands
- `python -m pip install -r requirements.txt` installs the Streamlit, Pandas, and APScheduler stack used across modules.
- `streamlit run app.py` starts the local UI; use `--server.headless true` during CI-style runs.
- `python check_timezone.py` verifies OS/database timezone alignment before operating on real billing data.
- `docker compose up --build` (optional) launches the app with the bundled Dockerfile for parity with production.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, `snake_case` for functions and variables, and `CamelCase` for classes. Keep bilingual docstrings and comments consistent with existing modules when touching shared flows. New Streamlit pages should mirror the existing page naming pattern and expose a top-level `render()` style function for clarity. Use explicit imports from `database` and `utils` rather than relative wildcards to keep dependencies readable.

## Testing Guidelines
Automated tests are not yet in place; add focused `pytest` cases under a new `tests/` directory when introducing complex logic (for example, binding workflows or date calculations). For manual verification, run `streamlit run app.py`, upload synthetic spreadsheets from `data/`, and confirm key counters on the dashboard. Record any timezone checks with `python check_timezone.py` when maintaining scheduler or billing code.

## Commit & Pull Request Guidelines
Commit history follows Conventional Commit prefixes (`feat:`, `fix:`, `docs:`). Use an imperative, <=72 character summary and include scope when useful (e.g., `feat(database): add payment retry flag`). Pull requests should link relevant issues, list manual test commands, attach screenshots or exported files for UI/data changes, and call out schema updates so reviewers can refresh their local SQLite database before testing.

## Data & Deployment Notes
Never commit production spreadsheets or real SQLite dumps; keep sensitive files in `data/` but ensure `.gitignore` continues to exclude confidential artifacts. When updating Docker or deployment scripts, sync environment variables with `.streamlit/config.toml` and document any new secrets in `DEPLOYMENT.md` without embedding credentials.
