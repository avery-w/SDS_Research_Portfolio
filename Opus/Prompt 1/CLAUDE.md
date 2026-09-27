# Project notes

- Flask marketplace in `marketplace/`. Run tests with `.venv/bin/python tests/test_app.py`.
- Money is stored as integer cents everywhere (`*_cents` columns, `money` Jinja filter, `to_cents` parser).
- Checkout creates one `Order` per store. Status changes must go through `Order.set_status`, which keeps stock in sync.
- Allowed status changes: `CUSTOMER_TRANSITIONS` and `SELLER_TRANSITIONS` in `models.py`; admins may set any status.
- `schema.sql` is generated from the models (`CreateTable` over `db.metadata.sorted_tables`, PostgreSQL dialect). Regenerate it after model changes.
- Shipping origin is fixed at 110 Inner Campus Drive, Austin, TX 78705 (`shipping.ORIGIN`).
- Chat uses `claude-opus-5` by default (`CHAT_MODEL`) with server-side refusal fallbacks; it only calls Claude when `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` is set.
