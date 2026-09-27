# Security Audit & Guidelines

This document details security considerations for each module and identifies where user input touches queries, file paths, and shell commands.

## Module 1: User Authentication & Profile Management

### Security Features
- JWT token-based authentication (djangorestframework-simplejwt)
- Password hashing with PBKDF2 (Django default)
- Minimum password length enforcement (8 characters)
- Common password validation
- Role-based access control (customer, seller, admin)

### Input Validation

#### User Registration Endpoint (`POST /api/users/register/`)
- **Input**: email, first_name, last_name, password, password2, role
- **Validation**: 
  - Email: Django EmailField validation
  - Password: django.contrib.auth.password_validation validators
  - Role: Choice field (customer, seller)
- **Reaches Database**: User and UserProfile models via ORM
- **Risk Level**: Low - all inputs validated, ORM prevents SQL injection

#### User Profile Update (`PATCH /api/profiles/{id}/`)
- **Input**: phone, address, city, state, zip_code, country, profile_image
- **Validation**:
  - String fields: Limited to 255 chars (model field constraints)
  - ImageField: Pillow library validates actual image file
  - User can only update own profile (permission check in view)
- **Risk Level**: Low

### Identified Issues & Mitigations

1. **Issue**: Password stored in request logs
   - **Mitigation**: Passwords never logged; use environment variables for logs
   - **Status**: Implemented

2. **Issue**: Profile images could contain malicious metadata
   - **Mitigation**: Pillow validates image; file uploaded to media/ directory (not web root)
   - **Status**: Mitigated

3. **Issue**: Email enumeration attack
   - **Mitigation**: Register endpoint shows generic error for duplicate email
   - **Status**: Implement in production

---

## Module 2: Products & Inventory Management

### Security Features
- Seller can only modify their own products
- Product SKU uniqueness enforced (database constraint)
- Stock levels validated before cart/order operations
- Image validation for product images

### Input Validation

#### Create/Update Product (`POST/PATCH /api/products/`)
- **Input**: name, description, price, stock, sku, category, weight_kg, dimensions, images
- **Validation**:
  - Price: DecimalField, MinValueValidator(0.01)
  - Stock: IntegerField, MinValueValidator(0)
  - Weight: DecimalField, MinValueValidator(0.01)
  - SKU: Unique constraint at database level
  - Images: ImageField validation
- **Reaches Database**: Product model via ORM
- **Risk Level**: Low

#### Search/Filter Products (`GET /api/products/`)
- **Input**: search query, category filter
- **Validation**:
  - SearchFilter uses Django ORM `icontains` (parameterized)
  - DjangoFilterBackend validates filter fields
- **Reaches Database**: Parameterized ORM queries
- **Risk Level**: Low

### Identified Issues

1. **Issue**: Seller weight/dimensions user-supplied
   - **Mitigation**: Used for shipping calculation only; admin-controlled rates
   - **Status**: Acceptable for MVP

2. **Issue**: Product description XSS
   - **Mitigation**: Stored as-is; frontend must escape on render
   - **Status**: Frontend responsibility

---

## Module 3: Shopping Cart & Checkout

### Security Features
- Cart tied to authenticated user
- Stock validation before adding items
- Quantity validation (min 1, max stock)
- Price calculated server-side (client price ignored)

### Input Validation

#### Add to Cart (`POST /api/cart/add_item/`)
- **Input**: product_id, quantity
- **Validation**:
  - product_id: IntegerField, validated against Product existence
  - quantity: IntegerField, min 1, checked against stock
- **Reaches Database**: CartItem model via ORM
- **Risk Level**: Low

#### Checkout (`POST /api/orders/checkout/`)
- **Input**: shipping_info (address, city, state, zip, country), billing_info, payment_method
- **Validation**:
  - Address fields: TextField, no validation (shipping service validates)
  - payment_method: Checked against allowed methods
  - Cart items verified to exist and have sufficient stock
- **Price Calculation**: Server-side, cart item prices used (not client-supplied)
- **Reaches Database**: Order and OrderItem models
- **Risk Level**: Low (price cannot be manipulated by client)

### Identified Issues

1. **Issue**: Address injection
   - **Mitigation**: Not interpreted as code; stored as-is
   - **Status**: Safe

2. **Issue**: Insufficient inventory check timing
   - **Mitigation**: Database transaction during checkout
   - **Status**: Implement database-level constraints

---

## Module 4: Orders & Fulfillment

### Security Features
- Order number generated server-side (UUID-based)
- Customer can only view/modify their own orders
- Seller can view orders containing their products
- Admin can override actions
- Tracking number not exposed to tampering

### Input Validation

#### Request Return (`POST /api/returns/request_return/`)
- **Input**: order_item_id, reason, description
- **Validation**:
  - order_item_id: Verified customer owns order
  - reason: Choice field (defective, wrong_item, not_as_described, changed_mind, other)
  - description: TextField, no special interpretation
- **Reaches Database**: ReturnRequest model
- **Risk Level**: Low

#### Request Cancellation (`POST /api/cancellations/request_cancellation/`)
- **Input**: order_id, reason
- **Validation**:
  - order_id: Verified customer owns order
  - Can only cancel pending orders (status check)
  - reason: TextField
- **Reaches Database**: CancellationRequest model
- **Risk Level**: Low

### Identified Issues

1. **Issue**: Refund amount not validated on admin approval
   - **Mitigation**: Set by admin in approve endpoint; logged for audit
   - **Status**: Implement audit logging

---

## Module 5: Messaging System

### Security Features
- Messages tied to authenticated users
- Users can only see messages they sent or received
- Message content not interpreted as code

### Input Validation

#### Send Message (`POST /api/messages/send_message/`)
- **Input**: recipient_id, subject, content, product_id
- **Validation**:
  - recipient_id: Verified user exists
  - subject: CharField(max_length=255)
  - content: TextField
  - product_id: Optional, verified product exists
- **Reaches Database**: Message model
- **Risk Level**: Low (content stored as-is; frontend escapes on display)

### Identified Issues

1. **Issue**: Message content XSS risk
   - **Mitigation**: Frontend must escape when displaying
   - **Status**: Frontend responsibility

2. **Issue**: Message spam potential
   - **Mitigation**: Implement rate limiting per user
   - **Status**: Add in production

---

## Module 6: AI Chatbot

### Security Features
- Chatbot responses logged in ChatbotLog model
- User messages stored for audit trail
- No external API calls in MVP (rule-based only)

### Input Validation

#### Chatbot Chat Endpoint (`POST /api/chatbot/chat/`)
- **Input**: message, product_id
- **Validation**:
  - message: CharField, required
  - product_id: Optional, verified product exists
- **Processing**: Rule-based matching (no LLM in MVP)
- **Reaches Database**: ChatbotLog model
- **Risk Level**: Low

### When Integrating LLM API

1. **Input Sanitization**: Escape user message before sending to LLM
2. **Rate Limiting**: Limit API calls per user
3. **Cost Controls**: Set hard caps on token usage
4. **Response Validation**: Never execute chatbot responses as code
5. **Logging**: Log all LLM prompts and responses

---

## Module 7: Shipping & Rate Calculation

### Security Features
- Shipping rates controlled by admin only
- Calculation based on weight, distance, carrier
- Origin address hardcoded (not user-supplied)

### Input Validation

#### Calculate Shipping (`POST /api/orders/checkout/`)
- **Input**: weight_kg (from product), destination_zip
- **Validation**:
  - weight_kg: From product model (seller-supplied but admin-controlled)
  - destination_zip: Used in shipping.py _get_ups_zone()
- **Calculation Logic** (shipping.py):
  ```python
  origin_prefix = int(origin_zip[:3])  # Can fail if invalid format
  dest_prefix = int(dest_zip[:3])      # Validation needed
  ```
  - **Issue**: ZIP code format not validated
  - **Mitigation**: Add regex validation: `^\d{5}(-\d{4})?$`

### Identified Issues

1. **Issue**: ZIP code format not validated
   - **Mitigation**: Add regex validation in serializer
   - **Status**: Fix required before production

2. **Issue**: Distance calculation simplified
   - **Mitigation**: Current implementation uses prefix comparison (not actual miles)
   - **Status**: Acceptable for MVP; replace with real ZIP distance API for production

---

## File Upload Security

### Product Images
- **Path**: `media/products/{filename}`
- **Validation**: ImageField + Pillow validation
- **Risk**: Low (file type checked, no path traversal possible)

### Store Assets
- **Path**: `media/stores/{filename}`
- **Validation**: ImageField + Pillow validation
- **Risk**: Low

### Profile Images
- **Path**: `media/profiles/{filename}`
- **Validation**: ImageField + Pillow validation
- **Risk**: Low

**Recommendation**: Add UUID to filename for uniqueness and to prevent directory enumeration.

---

## Database Security

- All queries use Django ORM (parameterized)
- No raw SQL with user input
- Foreign key constraints at database level
- Unique constraints for SKU, email, etc.

**Recommendation**: Use PostgreSQL in production (not SQLite) for:
- Better concurrency handling
- Row-level locking
- Encryption at rest options

---

## API Authentication

- JWT tokens expire after 24 hours (configurable)
- Refresh tokens required to get new access token
- Tokens not stored in database (stateless)
- HTTPS required in production (SECURE_SSL_REDIRECT=True)

**Recommendation**: 
- Short-lived access tokens (15 minutes)
- Rotate refresh tokens on use
- Implement token blacklist for logout

---

## CORS & CSRF Protection

- CORS configured for frontend only (`CORS_ALLOWED_ORIGINS`)
- CSRF middleware enabled
- JWT auth immune to CSRF (no cookie-based auth)

**Configuration**:
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']
```

**Production**: Update to your domain.

---

## Admin Panel Security

- Requires superuser login (session-based auth)
- Not exposed via JWT API (separate from API auth)
- Protected by Django admin middleware

**Recommendation**:
- Disable admin panel in production if not needed
- Use strong superuser credentials
- Setup IP whitelisting for admin access

---

## Environment Variables

**Production .env should never contain**:
- Database passwords (use AWS Secrets Manager)
- API keys in plaintext (use environment-based secrets)
- Debug mode enabled

**Use**:
```bash
DEBUG=False
SECRET_KEY=<generate-strong-key>
DB_PASSWORD=<strong-password>
STRIPE_API_KEY=sk_live_...
```

---

## Logging & Audit Trail

**What's logged**:
- User registration/login
- Product create/update/delete
- Order creation and status changes
- Admin actions (in ReturnRequest, CancellationRequest)
- Chatbot interactions (ChatbotLog)

**What's NOT logged**:
- Passwords
- Payment card details
- Full email addresses in logs (for PII)

**Recommendation**: Implement centralized logging with Sentry or Datadog.

---

## Payment Processing

**Stripe Integration** (MVP does not implement):
- Tokens provided by Stripe.js (card data never sent to backend)
- Payment intent created server-side
- Webhook listener validates payment completion
- Never log or store full card numbers

**When implementing**:
- Use Stripe's hosted checkout (Hosted Payment Page)
- Store only Stripe payment ID (stripe_payment_id field ready)
- Validate webhook signatures

---

## Regulatory Compliance

### GDPR (If EU users)
- Data export endpoint needed
- Right to deletion implementation
- Privacy policy linking

### PCI DSS (If storing payment info)
- Never store full card numbers
- Use Stripe tokenization only
- Encrypt data at rest

### CCPA (If California users)
- Privacy policy required
- Opt-out mechanisms for data sale

---

## Production Checklist

- [ ] Generate strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS to real domain
- [ ] Enable SSL (SECURE_SSL_REDIRECT=True)
- [ ] Use PostgreSQL (not SQLite)
- [ ] Setup Redis for rate limiting
- [ ] Implement Sentry for error tracking
- [ ] Setup log aggregation (CloudWatch, DataDog)
- [ ] Enable HTTPS only (HSTS header)
- [ ] Implement rate limiting on API endpoints
- [ ] Setup firewall rules (WAF)
- [ ] Regular security updates
- [ ] Penetration testing before launch
- [ ] Insurance for data breach
- [ ] Terms of Service & Privacy Policy

---

## Ongoing Security Maintenance

1. **Weekly**: Review error logs for suspicious patterns
2. **Monthly**: Update dependencies (`pip list --outdated`)
3. **Quarterly**: Security audit of new features
4. **Annually**: Full penetration test

Use `safety` package to check for known vulnerabilities:
```bash
pip install safety
safety check
```

---

## Report a Vulnerability

If you find a security issue, please email security@marketplace.local with:
- Description of vulnerability
- Affected version/code
- Steps to reproduce
- Proposed fix (if any)

Do not publicly disclose until we've patched.
