# Austin Market — Secure Full-Stack E-commerce Marketplace

Multi-role marketplace (Customer / Seller / Admin) built with FastAPI, SQLAlchemy, and a modern dark UI.  
Designed with real-world security practices for customer and merchant data.

## Quick Start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # set a strong SECRET_KEY (≥32 random chars)
python seed_admin.py              # admin@marketplace.local / admin123
python run.py
```

- UI: http://localhost:8000  
- API docs: http://localhost:8000/docs  

---

## Roles

| Role | Capabilities |
|------|--------------|
| **Customer** | Browse/search, cart, checkout, order history, cancel/return, AI chat, message sellers |
| **Seller** | Store + products (image upload), inventory, fulfill own orders |
| **Admin** | All users/stores/products/orders, deactivate accounts, override statuses, analytics, platform settings |

## Additional Features

- **Checkout shipping API** — UPS-style dimensional weight + zone rates  
  Origin: **110 Inner Campus Drive, Austin, TX 78705**
- **AI chatbot** — steers users to message sellers in-app for product/order questions
- JWT auth, bcrypt passwords, role guards on every protected endpoint

---

## Security Analysis — User Input Touch Points

After each module was built, every place user input reaches a query, file path, or potential command was reviewed.

### 1. Auth (`app/routers/auth.py`, `app/auth.py`)

| Input | Reaches | Sanitization |
|-------|---------|--------------|
| `email` | ORM filter `User.email == …` | Lower-cased + stripped. SQLAlchemy binds the value — **no string-concatenated SQL**. |
| `password` | bcrypt hash / verify only | Never stored plain, never logged, never used in queries/paths/shell. |
| `role` (register) | Enum column | Pydantic validator restricts to `customer` \| `seller` only. |

**No file paths. No shell commands.**

### 2. Customer (`app/routers/customer.py`)

| Input | Reaches | Sanitization |
|-------|---------|--------------|
| Search `q` | ORM `ilike` | Value bound as parameter (`like = f"%{q}%"` then `.filter(…ilike(like))`). SQLAlchemy escapes. Max length 100. |
| `product_id`, `item_id`, `order_id` | ORM equality filters | FastAPI parses as `int`. Used only as bound parameters. Ownership always checked (`user_id == current_user.id`). |
| `quantity` | ORM insert/update | Pydantic `ge=1, le=999`. |

**No file paths. No shell commands.**

### 3. Seller – product images (`app/routers/seller.py`)

| Input | Reaches | Sanitization |
|-------|---------|--------------|
| Form fields (name, price, …) | ORM insert | Form constraints + type checks. |
| **Image filename** | File system | **Original filename is never used.** Extension is allow-listed (`.jpg/.jpeg/.png/.webp/.gif`). On-disk name = `uuid4().hex + ext`. Path = `os.path.join(UPLOAD_DIR, safe_name)`. Resolved path is verified to stay under `UPLOAD_DIR` (blocks traversal). Size capped at 5 MB. |
| `product_id` / `order_id` | ORM | Integer path params + ownership filters (`store_id == seller’s store`). |
| Order `status` | Enum column | Constrained by `OrderStatus`; explicit transition matrix. |

**No shell commands. No user-controlled paths.**

### 4. Checkout / Shipping / Chat / Messages (`app/routers/api.py`)

| Input | Reaches | Sanitization |
|-------|---------|--------------|
| `dest_zip`, dimensions | Pure Python math | Validated by Pydantic (`gt=0`, length limits). Never touches DB/files/shell. |
| `shipping_address`, `shipping_zip` | ORM insert | Length-limited; bound parameters. |
| Chat `message` | Rule engine or OpenAI API payload | Max 1000 chars. **Never** used in SQL, file paths, or shell. |
| Message `content`, `receiver_id` | ORM insert | Content stripped; IDs are integers; receiver existence + active check. |

### 5. Admin (`app/routers/admin.py`)

| Input | Reaches | Sanitization |
|-------|---------|--------------|
| Entity IDs | ORM filters | Integers only. |
| `role` / `status` | Enum columns | Constrained by Python enums. |
| Settings `key` | ORM | Regex `^[a-zA-Z0-9_.-]+$` — no path separators or injection characters. |
| Settings `value` | ORM text column | Max length 2000. |

**No file paths. No shell commands.**

### Cross-cutting controls

- **SQL injection**: All DB access is SQLAlchemy ORM with bound parameters. Zero raw SQL built from user strings.
- **Path traversal**: Uploads use server-generated UUID names; final path is checked to remain under `UPLOAD_DIR`.
- **Command injection**: The application never invokes a shell with user data.
- **AuthN / AuthZ**: JWT required on protected routes; role checked via `require_role`; deactivated accounts rejected with 403.
- **XSS (frontend)**: All dynamic text rendered via `esc()` (HTML entity encoding) before insertion into the DOM.
- **Secrets**: `SECRET_KEY` and `OPENAI_API_KEY` loaded from environment; never hard-coded for production.

---

## Project Layout

```
marketplace/
├── app/
│   ├── main.py, config.py, database.py
│   ├── models.py          # full schema
│   ├── schemas.py         # Pydantic validation
│   ├── auth.py, shipping.py, chatbot.py
│   ├── routers/           # auth, customer, seller, admin, api
│   ├── templates/         # modern UI
│   └── static/
├── uploads/
├── requirements.txt
├── .env.example
├── seed_admin.py
├── run.py
└── README.md
```

## Production Checklist

- [ ] Strong random `SECRET_KEY`
- [ ] PostgreSQL instead of SQLite
- [ ] Official UPS Rating API
- [ ] Real payment provider (Stripe, etc.)
- [ ] HTTPS + restricted CORS origins
- [ ] Rate limiting / WAF in front of the app
- [ ] Never commit `.env`

MIT License.
