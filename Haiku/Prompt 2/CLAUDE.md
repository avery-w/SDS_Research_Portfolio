# Forty Acres Market

- Stack: Flask 3.1 + stdlib sqlite3 (no ORM), Jinja templates, one `static/app.js`. Venv at `.venv`.
- Verify changes with `.venv/bin/python test_app.py` (uses a temp DB and temp upload dir, never calls Claude).
- Error contract lives in the `app.py` docstring and README "Error contract" table; keep both in sync when adding routes.
- Raise `BadInput` for user-correctable 400s; `abort(401/403/404/409)` for the rest. `/api/*` routes answer JSON automatically.
- CSRF: forms need `{{ csrf() }}` (from `_macros.html`); JSON APIs are exempt only with `Content-Type: application/json`.
- Import macros `with context` (they read `status_labels` from the context processor).
- Money is integer cents everywhere; percentages go through `pct_of()` (Decimal, half-up).
- Stock moves only in `api_checkout` and `order_status` (RESTOCKED statuses), inside `BEGIN IMMEDIATE`.
- Chatbot: `anthropic` SDK raises TypeError (not AnthropicError) when no credentials exist, so `chatbot._get_client` gates on `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` env vars.
- Demo data: `flask --app app seed` (password `demo-pass-123`).
