# Project notes

- Run: `.venv/bin/flask --app app seed` then `.venv/bin/flask --app app run`. Checks: `.venv/bin/python test_app.py` and `.venv/bin/python shipping.py`. Keep both passing.
- All auth, CSRF, validation and error-shape rules live in `core.py`. New routes must use `@require(...)` and `Form(...)` so the README "Error contract" stays true. Update the README endpoint tables when adding routes.
- Item status changes must go through `core.set_item_status` (it does the stock accounting). Order status is derived, never stored.
- Use `Model.query...paginate()` (legacy Query). `db.paginate()` only accepts `select()` and 500s on Query objects.
- anthropic SDK 1.x raises `TypeError` ("Could not resolve authentication method") when no credentials exist. `chatbot.py` catches that and falls back to offline mode.
- Chatbot uses `claude-opus-5` with the tool runner, adaptive thinking, effort `low`, and `fallbacks="default"` (beta `server-side-fallback-2026-07-01`).
