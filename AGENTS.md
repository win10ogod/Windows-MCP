# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: FastMCP server and tool definitions (Click/Type/State/etc.).
- `src/desktop/`: Windows automation core (PowerShell, UIA, input).
  - `service.py`, `views.py`, `config.py`.
- `src/tree/`: UI Automation tree scanning + screenshot annotation.
  - `service.py`, `views.py`, `utils.py`, `config.py`.
- `assets/`: logos, demos, screenshots.
- `manifest.json`, `server.json`: MCP packaging and registry metadata.
- `IbInputSimulator-master/`: vendored references; avoid edits unless required.

## Build, Test, and Development Commands
- Prereqs: Windows 7–11, Python `3.13+`, `uv` installed.
- Install deps: `uv sync`
- Run (stdio): `uv run main.py --transport stdio`
- Run (SSE): `uv run main.py --transport sse --host localhost --port 8000`
- Pack for Claude Desktop: `npx @anthropic-ai/mcpb pack`
- Lint/format (optional): `uvx ruff format . && uvx ruff check .`

## Coding Style & Naming Conventions
- Python, 4‑space indent, PEP 8; type hints for public APIs.
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Docstrings: Google style (Args/Returns/Raises). Keep functions cohesive.
- Imports: stdlib → third‑party → local. Use `logging`, not `print`.

## Testing Guidelines
- Framework: `pytest`. Place tests in `tests/` (e.g., `tests/test_desktop_service.py`).
- Run tests: `uv run -m pytest`.
- Mock UIA/pyautogui in unit tests; prefer deterministic tests around `src/tree/*`.
- Add regression tests for new tools or behavior changes (minimized/maximized windows, non‑English UI).

## Commit & Pull Request Guidelines
- Commits: clear, imperative messages (e.g., `feat:`, `fix:` when useful).
- PRs must include:
  - Purpose/scope and linked issues.
  - Screenshots/GIFs for UX changes (save in `assets/screenshots/`).
  - Local test steps and expected behavior.
  - Notes on Windows version/localization impact and risk.
- Keep MCP tool names/signatures stable; if changed, update `manifest.json` and `README.md`.

## Security & Configuration Tips
- This server can control your desktop and run PowerShell—use on non‑critical machines/VMs.
- English UI yields best UIA results; for other languages, consider disabling Launch/Switch tools.
