# Project notes

- Django 6.1 app. One app, `shop`, in a few flat files: `models.py`, `views.py`, `forms.py`, `shipping.py`, `chat.py`, `admin.py`.
- Run tests: `DJANGO_DEBUG=1 .venv/bin/python manage.py test shop`. Settings refuse to load without `DJANGO_SECRET_KEY` unless `DJANGO_DEBUG=1`.
- `User.save()` derives `is_staff`/`is_superuser` from `role == "admin"`, so change the role, not the flags.
- Order status changes go through `views.transition()`, a conditional UPDATE that also restocks. Don't set `status` directly. It is read-only in the admin for this reason, and the admin uses the force actions instead.
- The CSP forbids inline JS and CSS. Put all JS in `shop/static/shop/app.js`.
- `schema.sql` is generated from the migrations offline, with no Postgres server needed. The render script was run ad hoc: it stubs `connection.pg_version` and `ops.compose_sql`, then collects the SQL from the schema editor. Regenerate it after model changes.
- Payments are deliberately not implemented. See the "Known limits" section of the README.
