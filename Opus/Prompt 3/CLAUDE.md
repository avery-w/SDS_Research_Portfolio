# Longhorn Market (Flask marketplace)

- Run tests: `.venv/bin/python test_app.py` and `.venv/bin/python shipping.py`. The test stubs `shipping.zone_for_zip`, so it needs no network.
- Money is always integer cents. Prices and shipping are recomputed server side at checkout, never trusted from the client.
- Order status rules live in `models.TRANSITIONS`; `Order.change_status` restocks on cancel/return. Admin may move any non-terminal order anywhere.
- One route/template serves order detail for customer, seller and admin (`shop.order_role` decides, 404 for others).
- `shipping.py` rate card is an approximation (ponytail comment). UPS zone comes from pgeocode distance, which downloads GeoNames data on first use. On python.org macOS builds that needs `SSL_CERT_FILE=$(python -m certifi)`.
- Chatbot uses `claude-opus-5`, low effort, `fallbacks="default"` with beta `server-side-fallback-2026-07-01`. No API key on this machine, so it was verified with a mocked httpx2 transport only.
- CSP forbids inline scripts: all JS goes in `static/app.js`.
- Payments are deliberately not implemented (marked in `shop.checkout`).
- `schema.sql` is generated from the models; regenerate it after model changes rather than hand editing.
- README has a per-module "user input reaches query/path/shell" audit. Keep it current when adding inputs.
