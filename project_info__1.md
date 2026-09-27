# SDS_Research_Portfolio — Codebase Overview

> **Direct answer to the question asked ("what email is associated to my account")**
>
> **There is no account, and therefore no email address, associated with you anywhere in this
> repository.** This directory is a *research corpus* — a collection of AI-generated demo
> e-commerce codebases — not an application you have a login on. Nothing here authenticates a
> real person, and there is no user record, session store, or identity database belonging to
> the user `avery`.
>
> I checked every place a personal email could plausibly hide:
>
> | Where I looked | Result |
> |---|---|
> | `.git/config` (git `user.email` is the most common accidental personal-email leak) | No `[user]` section at all — only `remote.origin` = `https://github.com/avery-w/SDS_Research_Portfolio.git` |
> | All `.env` / `.env.example` / `.ENV.example` files | Only placeholders: `OPENAI_API_KEY=`, `your_openai_key`, `UPS_CLIENT_ID=`, `DATABASE_URL=...`. **No real secrets, no personal addresses.** |
> | Every `seed_admin.py` in the repo | Hard-coded *demo* identities: `admin@marketplace.local` / `admin123` (Grok family); `admin@example.com` (`Sonnet 5/Prompt 0` takes email as a CLI arg) |
> | `README.md` files | Documented demo logins: `customer@example.com`, `seller@example.com`, `admin@example.com`, all with password `password123` (Copilot_prompt2) |
> | Mail config in `config.py` (Kimi_prompt1) | `MAIL_DEFAULT_SENDER` = `"no-reply@mercado.local"`, `MAIL_SERVER=""` — a local placeholder, sending is suppressed by default |
> | Django env templates (Aider) | `DEFAULT_FROM_EMAIL=noreply@your.domain.com` — an unfilled template string |
> | Git remote owner | `avery-w` is a **GitHub username handle**, not an email address |
>
> **None of these is "your account."** They are fictional fixtures that the generated demo
> apps create for themselves on first run. I will not guess or invent an address — the honest
> answer is that the information does not exist in this repository.
>
> **If you mean a real subscription/account outside this repo** (Sixth AI, GitHub, a hosting
> provider, etc.): this repo cannot answer that, and Explore Mode has no network or account
> access. You would need to check that service's own account/billing settings directly. If you
> tell me *which* service, I can point you at the exact page, but I cannot read your account.

---

## Summary

`SDS_Research_Portfolio` is a **benchmark corpus for comparing AI coding agents**, not a
software product. It contains the output of roughly **nine different model families** — each
given the *same* natural-language specification ("build a multi-vendor e-commerce marketplace
with UPS shipping estimation and an AI shopping assistant") and asked to produce a working
application. Each model's output is preserved side by side so the results can be compared on
completeness, architectural quality, security posture, and depth of domain modelling.

The practical upshot for anyone working in this directory: **you are almost never looking at
one application.** You are looking at ~30 independent, mutually incompatible implementations
of the same app, scattered across a deep folder hierarchy. Almost every file you open is an
instance of a pattern that repeats several times over with small, meaningful variations.

## Architecture

There is no single architecture. There is a **repeated specification** implemented under
**five distinct technical stacks**, which is precisely the point of the corpus.

**The recurring specification.** Every implementation is asked for the same feature set:

- Multi-role accounts — `customer`, `seller`, `admin`
- Product catalog with search/category filtering, image upload
- Cart and checkout with money handled in **integer cents** (never floats)
- UPS shipping rate estimation, always originating from the *same* fictional warehouse:
  `110 Inner Campus Drive, Austin, TX 78705`
- Orders with a lifecycle and **service requests** (`cancellation`, `return`)
- Seller storefronts + order fulfilment
- Direct buyer↔seller messaging
- An AI shopping assistant that degrades to a deterministic rule-based responder when no
  API key is configured
- Admin analytics/oversight

**The five stacks observed:**

| Stack | Framework shape | Examples |
|---|---|---|
| **FastAPI + SQLAlchemy/SQLModel** | `run.py` / `main.py` entrypoint, `app/` package, Pydantic **JWT** auth (`ACCESS_TOKEN_EXPIRE_MINUTES`) | `Grok4.5/grok_0..3`, `Kilo-Auto Prompts/kilo_auto_0..1` |
| **Flask + SQLAlchemy (app-factory)** | `config.py` with `BaseConfig` / `DevelopmentConfig` / `TestingConfig` / `ProductionConfig`, `create_app()`, Flask-Login sessions, Jinja templates | `Kimi Prompts/Kimi_prompt1`, `Sonnet 5 (Claude CLI)/Prompt 0`, `LongCat 2 Prompts/LongCat2_0`, `Kilo-Auto Prompts/kilo_auto_0` |
| **Flask + raw SQLite** | Single `app.py`, hand-written `schema.sql`, raw `sqlite3` with placeholders, no ORM | `Copilot Prompts/Copilot_prompt1..3` |
| **Django / DRF** | `manage.py`, one Django app per bounded context, `settings.py` + `urls.py` per app | `Kimi Prompts/Kimi_prompt0`, `Aider Prompts/prompt-00..03` |
| **JS frontend** | Vite + `src/`, `package.json` | `GPT Prompts/GPT-5 mini_prompt4` |

**Execution model.** Every Python project starts the same way — there is no shared runtime,
no monorepo tooling, no root `manage.py` or `pyproject.toml`. You enter one project
directory, install its own `requirements.txt`, and start *its* entrypoint
(`python run.py` / `python app.py` / `uvicorn main:app --reload` / `python manage.py
runserver`). The generated apps then **self-provision**: on first boot they create their
database (`Base.metadata.create_all`, or executing `schema.sql`, or Django migrations) and
seed demo data, including the demo accounts listed at the top of this document.

**Configuration model.** Every stack uses the same idiom: a config layer reads environment
variables with **safe, working defaults**, so the app runs with zero configuration in
development and hardens itself in production. In `Kimi Prompts/Kimi_prompt1/config.py` this is
made explicit — `ProductionConfig` flips `SESSION_COOKIE_SECURE` to `True` and
`MAIL_SUPPRESS_SEND` to `False`, while `TestingConfig` swaps in an in-memory SQLite database
(`sqlite://`) and disables CSRF and rate limiting. Third-party integrations (UPS, OpenAI,
Anthropic) are **off by default** and fall back to modelled/rule-based behaviour, which is why
none of these apps require real credentials to run.

## Directory Structure

```
SDS_Research_Portfolio/                (git repo: github.com/avery-w/SDS_Research_Portfolio)
├── Aider Prompts/                     — Aider agent's output
│   ├── prompt-00/ … prompt-03/        — Django/DRF; prompt-03 is the fullest (Docker + nginx)
├── Copilot Prompts/
│   ├── Copilot_prompt0/               — Django, split into users/products/orders/chat apps
│   ├── Copilot_prompt1/               — Flask app.py + templates/static
│   ├── Copilot_prompt2/               — Flask + raw SQLite; ships schema.sql, marketplace.db,
│   │                                    uploads/, and a SECURITY_AUDIT.md
│   └── Copilot_prompt3/               — Flask, Dockerised, has tests/
├── GPT Prompts/
│   ├── GPT-5 mini_prompt0..3/         — Python services (Flask/FastAPI) with Dockerfiles
│   └── GPT-5 mini_prompt4/            — Vite/JS single-page frontend (the only JS entrypoint)
├── Grok4.5/
│   ├── grok_0/ grok_1/ Grok_2/ Grok_3/ — FastAPI + SQLModel; each has seed_admin.py
├── Kilo-Auto Prompts/
│   ├── kilo_auto_0/ kilo_auto_1/      — FastAPI, FastAPI docs at /docs; kilo_auto_1 has tests/
│   ├── kilo_auto_2/ kilo_auto_3/      — empty
├── Kimi Prompts/
│   ├── Kimi_prompt0/                  — Django/DRF (accounts, carts, catalog, stores, marketplace)
│   ├── Kimi_prompt1/                  — Flask, the most rigorously engineered Flask variant
│   │                                    (config.py, settings_service.py, money.py, clock.py)
│   ├── Kimi_prompt2/ Kimi_prompt3/    — empty
├── LongCat 2 Prompts/
│   ├── LongCat2_0/                    — Python app w/ migrations/ + tests/ + pytest.ini
│   ├── LongCat2_3/                    — empty
├── Minimax Prompts/Minimax_prompt0..3/ — empty
├── Sonnet 5 (Claude CLI)/
│   └── Prompt 0/                      — Flask app-factory, CLI-driven seed_admin.py, test_app.py,
│                                        committed .venv/
├── New folder/                        — empty
├── .git/                              — no [user] section (no personal email)
├── .pytest_cache/ .vscode/
```

**Two important structural facts:** (1) several folders are **empty placeholders**
(`Minimax_*`, `Kimi_prompt2/3`, `kilo_auto_2/3`, `LongCat2_3`, `New folder`) — a model was
assigned a slot but produced nothing, which is itself a data point in a benchmark. (2) The
numbered `prompt-N` suffixes line up across families, meaning **`prompt-0` across all
families is the same task**; comparing like-numbered folders is the intended comparison.

## Key Abstractions

These are the recurring domain abstractions that recur, in some form, in nearly every project.

### `User` / account model
- **File**: `Kimi Prompts/Kimi_prompt1/marketplace/models/user.py` (canonical, most complete
  version); `Copilot Prompts/Copilot_prompt2/schema.sql` (raw-SQL version);
  `Grok4.5/grok_0/app/models.py` (SQLModel version)
- **Responsibility**: one table holds *every* role. `role` (`customer`/`seller`/`admin`) and
  `status` (`active`/`suspended`) are deliberately **separate columns** so an admin can promote
  or suspend a user without migrating rows.
- **Interface**: `set_password()` / `check_password()` (Werkzeug `generate_password_hash`,
  never plaintext); `is_admin` / `is_seller` / `is_customer` / `is_active` properties;
  `register_failed_login()` implementing **lockout after 8 failures for 15 minutes**;
  `to_summary()` for safe JSON serialisation.
- **Non-obvious**: identity is exposed externally as a **`public_id`** (`usr_…`), never the
  integer primary key. `auth_version` is bumped on password change and on
  `invalidate_sessions()`, which is the mechanism that force-logs-out every existing session
  after a credential change.

### `PlatformSetting` + `settings_service`
- **File**: `Kimi Prompts/Kimi_prompt1/marketplace/services/settings_service.py`
- **Responsibility**: the **single source of truth for every tunable knob** on the platform.
  A frozen-dataclass registry (`DEFAULTS`) simultaneously seeds the database, renders the admin
  settings screen, and validates submitted values.
- **Interface**: `get()/get_bool()/get_int()/get_float()/get_str()/get_list()` typed accessors;
  `update_many()` for atomic batch edits; `public_settings()` which filters on the
  `is_public` flag.
- **Lifecycle**: `ensure_defaults()` creates only *missing* rows, so restarting the app is
  idempotent and does not clobber admin edits.
- **Why it is interesting**: this is the clearest example in the corpus of "configuration as
  domain data." Settings live in the database (so an admin can change the commission rate at
  runtime) *but* are declared in code (so they can't be typoed into an invalid state). The
  `coerce_value()` function accepts the messy strings that HTML forms actually send
  (`"on"`, `"yes"`, `"1"`, `"enabled"`) and rejects anything unclear with a human-readable
  `SettingError`.

### Order + service requests
- **Files**: `Copilot Prompts/Copilot_prompt2/schema.sql`, `Kimi Prompts/Kimi_prompt1/marketplace/models/order.py`
- **Responsibility**: money is stored **exclusively as integer cents**
  (`price_cents`, `subtotal_cents`, `shipping_cents`, `total_cents`), with database-level
  `CHECK (price_cents >= 0)` constraints.
- **Service requests** are the "post-order" escape hatch, constrained by a CHECK to
  `('cancellation', 'return')` — this is where the marketplace's return-window policy
  (`return_window_days`, default 30) is enforced.
- **Note for the earlier "cancel subscription" request**: this corpus contains **no
  subscription concept anywhere** — no `Subscription` model, no billing table, no Stripe or
  payment-processor integration, and no recurring charge of any kind. The closest thing that
  exists is `service_requests.kind = 'cancellation'`, which cancels a *one-off order* and
  involves no account, no email, and no stored payment method.

### UPS shipping engine
- **Files**: `Kimi Prompts/Kimi_prompt1/marketplace/services/ups.py`,
  `Kimi Prompts/Kimi_prompt1/config.py` (the `UPS_*` block)
- **Responsibility**: estimates shipping cost. `UPS_ENABLED = False` by default and the
  README (Copilot_prompt2) is explicit: *"it does not call UPS or represent a shipping quote."*
  It is a **transparent local model** of UPS pricing.
- **Interface**: account credentials via OAuth client-credentials
  (`UPS_CLIENT_ID` / `UPS_CLIENT_SECRET` / `UPS_ACCOUNT_NUMBER`), base URL
  `https://onlinetools.ups.com`, with a rate limit (`240/hour`) and a quote TTL (`45 min`).
- **Non-obvious detail worth knowing**: the surcharge tables in `config.py` encode *real*
  published UPS accessorial rates — fuel surcharge `0.1475`, residential `$6.60`, delivery-area
  `$6.25`, extended delivery area `$10.10`, additional handling `$24.00`, large package
  `$130.00`, signature required `$7.20`, adult signature `$8.30`, Saturday delivery `$21.00`,
  insurance `$1.05` per `$100`, and dimensional weight divisor `139`. This is unusually
  domain-accurate and is a genuine differentiator when comparing implementations.

### `seed_admin.py`
- **Files**: `Grok4.5/grok_0..3/seed_admin.py`, `Sonnet 5 (Claude CLI)/Prompt 0/seed_admin.py`
- **Responsibility**: bootstrap the first administrator, because there is no public path to
  create one.
- **Two distinct philosophies visible in the corpus** — and this is the single most
  security-relevant comparison in the repo:
  - **Grok family**: hard-codes `admin@marketplace.local` with the password `admin123`,
    idempotently promoting the account if it already exists. Convenient, but the credential
    is in version control. `Grok_3` at least prints
    *"WARNING: Change this password immediately in production."*
  - **Sonnet 5, Prompt 0**: takes `email password "Name"` as **CLI arguments** — no credential
    is ever committed, and the script *refuses* to run if the user already exists.
    This is the better pattern and worth copying.

## Data Flow

The canonical request path, as implemented in the Flask app-factory variants
(`Kimi Prompts/Kimi_prompt1`, `Sonnet 5 (Claude CLI)/Prompt 0`):

1. `run.py` (or `app.py`) calls the factory — e.g. `create_app()` — which loads
   `config.py`, selecting `DevelopmentConfig` / `TestingConfig` / `ProductionConfig` from
   `CONFIG_MAP` based on `FLASK_ENV`.
2. The factory initialises extensions from `marketplace/extensions.py` (a **single shared
   `db` object** imported everywhere — the classic Flask circular-import avoidance pattern),
   registers blueprints, and runs startup hooks.
3. On first boot, `ensure_defaults()` seeds `PlatformSetting` rows and the demo-data seeder
   creates demo users/stores/products.
4. A request hits a blueprint route; the route reads tunables through
   `settings_service.get_*()` rather than hard-coded constants — so `commission_rate`
   (default `0.08`), `default_tax_rate` (default `0.0825`, Austin TX), and
   `free_shipping_threshold_cents` (default `7500`) are all admin-editable at runtime.
5. Cart/checkout flows call the shipping engine and the money helpers; all arithmetic stays
   in integer cents and is converted to display strings only at the presentation edge.
6. Admin edits POST to `update_many()`, which **validates every field before writing any**
   — a single bad field rolls the whole batch back (`db.session.rollback()`), so settings can
   never be left half-applied.
7. The chatbot endpoint runs the LLM path only if `chatbot_use_llm` is on *and* an API key
   exists; otherwise the deterministic rule engine answers, escalating to a human when a
   message contains any of the `chatbot_handoff_keywords`
   (`human`, `agent`, `representative`, `manager`, `complaint`).

## Non-Obvious Behaviors & Design Decisions

- **Everything is a demo, and the code says so honestly.** `Copilot_prompt2/README.md` lists
  exactly what production would additionally need: managed database, HTTPS, real UPS credential
  flow, real payment processor, object storage, edge CSRF, rate limiting, secure session
  cookies, secrets manager. Treat every README in this repo as an accurate statement of its own
  limits — these are unusually candid about being scaffolds.
- **No payments exist at all.** Despite "checkout," there is no payment processor, no card
  storage, no Stripe/Braintree dependency anywhere in the corpus. Checkout creates an order
  record and computes shipping; money is never actually moved.
- **Optional integrations are the norm, not a workaround.** UPS, OpenAI, and Anthropic are all
  off unless keys are supplied, with a documented rule-based fallback. This is why the corpus is
  runnable offline and why `OPENAI_API_KEY=` being empty in every `.env.example` is intentional,
  not an oversight.
- **`MAIL_SUPPRESS_SEND = True` by default.** The apps have full mail configuration
  (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_DEFAULT_SENDER = "no-reply@mercado.local"`)
  but **cannot send email in development**. `ProductionConfig` flips it to `False`. So
  password-reset and verification flows exist in code but are inert locally — a common source of
  "why did no email arrive?" confusion.
- **`auth_version` is the session-invalidation primitive.** Rather than tracking individual
  sessions, a counter is bumped; any session carrying a stale version is rejected. Elegant, but
  it means *all* of a user's sessions die when they change their password — including the one
  they are currently using, if a re-login isn't handled.
- **`public_id` vs. integer PK.** Sequential integer IDs are never exposed in URLs or JSON;
  a `usr_…`/store-style prefixed public ID is used instead. This is anti-enumeration hardening
  applied consistently in the better implementations and absent in the weaker ones.
- **Validation ordering is deliberate.** In `update_many()`, coercion runs for *every* key
  before *any* write, and errors are accumulated rather than raised on first failure. The
  comment in the source states this directly: a single bad field cannot leave settings
  half-applied.
- **Lockout constants are hard-coded, not configured.** `register_failed_login(threshold=8,
  lock_minutes=15)` — unlike nearly everything else in the app, these are not in the settings
  registry. A reader expecting to tune lockout policy through the admin UI will not find it.
- **`TestingConfig` is a genuinely separate runtime.** In-memory SQLite, CSRF disabled, rate
  limiting disabled, mail suppressed, and a hard-coded `SECRET_KEY = "testing-secret-key"`.
  Tests against it exercise real code paths, but **not** the CSRF or rate-limiting layers.
- **`.venv/` is committed inside `Sonnet 5 (Claude CLI)/Prompt 0/`.** A virtual environment in
  version control; do not treat it as source, and do not run tooling across it.
- **Cross-`.env` inconsistency is a real trap.** Env variable naming diverges between projects
  (`DATABASE_URL` vs `DATABASE_PATH` vs `DB_HOST`/`DB_PORT`; `SECRET_KEY` vs
  `DJANGO_SECRET_KEY`). There is **no shared environment file** — copying one project's `.env`
  into another will silently fail to take effect, because the app just falls back to defaults.
- **The only real secret found is not a secret.** `Grok4.5/grok_1/.env` is committed, but
  contains only placeholder text (`SECRET_KEY=change-me-to-a-long-random-string…`) and empty API
  keys. No credential material is exposed in the repository — worth stating plainly, since
  committed `.env` files are normally the first thing to worry about.

## Module Reference

| File / Directory | Purpose |
|---|---|
| `Kimi Prompts/Kimi_prompt1/config.py` | Best example of the layered config pattern (Base/Dev/Test/Prod + `_env_*` coercion helpers) |
| `Kimi Prompts/Kimi_prompt1/marketplace/services/settings_service.py` | DB-backed, code-declared platform tunables; atomic validated batch updates |
| `Kimi Prompts/Kimi_prompt1/marketplace/models/user.py` | Canonical user model: roles, lockout, `auth_version`, `public_id` |
| `Kimi Prompts/Kimi_prompt1/marketplace/services/ups.py` | UPS rate model (no live calls by default) |
| `Kimi Prompts/Kimi_prompt1/marketplace/extensions.py` | Shared `db` object — the Flask circular-import workaround |
| `Kimi Prompts/Kimi_prompt1/marketplace/money.py` | Integer-cents money helpers |
| `Kimi Prompts/Kimi_prompt1/marketplace/clock.py` | Centralised UTC time source (`utcnow`, `minutes_from_now`) |
| `Copilot Prompts/Copilot_prompt2/schema.sql` | Portable SQL schema; clearest statement of the domain model and its CHECK constraints |
| `Copilot Prompts/Copilot_prompt2/README.md` | Documented demo logins + explicit production-gap list |
| `Copilot Prompts/Copilot_prompt2/SECURITY_AUDIT.md` | Every user-controlled value reaching a query/file/shell boundary, with mitigation |
| `Grok4.5/grok_0..3/seed_admin.py` | Hard-coded demo admin (the anti-pattern to avoid) |
| `Sonnet 5 (Claude CLI)/Prompt 0/seed_admin.py` | CLI-argument admin seeding; refuses duplicates (the pattern to copy) |
| `Sonnet 5 (Claude CLI)/Prompt 0/.env.example` | Anthropic + UPS config; both optional with documented fallbacks |
| `Aider Prompts/prompt-03/` | Most complete Django deployment: `Dockerfile`, `docker-compose.yml`, `nginx.conf` |
| `GPT Prompts/GPT-5 mini_prompt4/` | The only JS/Vite frontend in the corpus |
| `Kilo-Auto Prompts/kilo_auto_1/tests/` | One of very few projects shipping tests |
| `LongCat 2 Prompts/LongCat2_0/migrations/` | One of very few projects with real migrations |

## Suggested Reading Order

1. **`Copilot Prompts/Copilot_prompt2/README.md`** — start here. It states the task, the demo
   accounts, and the honest production gap list in one page. Fastest way to understand what
   every project in this repo is *trying* to be.
2. **`Copilot Prompts/Copilot_prompt2/schema.sql`** — the domain model in ~70 lines of SQL. You
   will see this same model re-expressed in ORM form in every other project.
3. **`Kimi Prompts/Kimi_prompt1/config.py`** — how configuration, secrets, and environment
   switching are handled across the corpus; also where the UPS constants live.
4. **`Kimi Prompts/Kimi_prompt1/marketplace/services/settings_service.py`** — the most
   sophisticated piece of engineering in the repo; a good yardstick for judging the other
   implementations.
5. **`Kimi Prompts/Kimi_prompt1/marketplace/models/user.py`** — the identity/security model:
   roles, lockout, session invalidation, public IDs.
6. **`Sonnet 5 (Claude CLI)/Prompt 0/seed_admin.py`** vs. **`Grok4.5/grok_0/seed_admin.py`** —
   read back to back. Two lines of reasoning about the same trivial problem produce visibly
   different security outcomes, which is the most compact illustration of what this portfolio is
   measuring.

---

*Report generated in Explore Mode (read-only). I did not modify, run, or install anything in
this repository. Files examined: `config.py` and the identity/settings stack of
`Kimi Prompts/Kimi_prompt1`; `seed_admin.py` across the Grok 4.5 and Sonnet 5 families;
`.env` / `.env.example` templates from Grok 4.5, Kilo-Auto, Copilot, Aider, and Sonnet 5;
`schema.sql` and `README.md` from `Copilot Prompts/Copilot_prompt2`; the user model from
`Kimi Prompts/Kimi_prompt1`; `.git/config`; and directory listings across all nine model
families.*
