# E-Commerce Marketplace Database Schema

## Tables

### users
User accounts with role-based access control.
```
id (PK)           INT PRIMARY KEY
email             VARCHAR(255) UNIQUE NOT NULL
password_hash     VARCHAR(255) NOT NULL
first_name        VARCHAR(100)
last_name         VARCHAR(100)
role              ENUM(customer, seller, admin) DEFAULT customer
is_active         BOOLEAN DEFAULT TRUE
created_at        DATETIME DEFAULT NOW
```

### addresses
Customer delivery addresses.
```
id (PK)           INT PRIMARY KEY
user_id (FK)      INT FOREIGN KEY users.id
street            VARCHAR(255)
city              VARCHAR(100)
state             VARCHAR(50)
zip_code          VARCHAR(20)
is_default        BOOLEAN DEFAULT FALSE
```

### stores
Seller stores/shops.
```
id (PK)           INT PRIMARY KEY
owner_id (FK)     INT FOREIGN KEY users.id UNIQUE
name              VARCHAR(255)
description       TEXT
logo_url          VARCHAR(500)
is_active         BOOLEAN DEFAULT TRUE
created_at        DATETIME DEFAULT NOW
```

### products
Product listings.
```
id (PK)           INT PRIMARY KEY
store_id (FK)     INT FOREIGN KEY stores.id
name              VARCHAR(255)
description       TEXT
price             DECIMAL(10,2)
stock             INTEGER DEFAULT 0
sku               VARCHAR(100) UNIQUE
category          VARCHAR(100)
image_urls        TEXT (comma-separated URLs)
is_active         BOOLEAN DEFAULT TRUE
created_at        DATETIME DEFAULT NOW
updated_at        DATETIME DEFAULT NOW
```

### carts
Shopping carts for customers.
```
id (PK)           INT PRIMARY KEY
user_id (FK)      INT FOREIGN KEY users.id UNIQUE
created_at        DATETIME DEFAULT NOW
updated_at        DATETIME DEFAULT NOW
```

### cart_items
Items in shopping carts.
```
id (PK)           INT PRIMARY KEY
cart_id (FK)      INT FOREIGN KEY carts.id
product_id (FK)   INT FOREIGN KEY products.id
quantity          INTEGER DEFAULT 1
```

### orders
Customer orders.
```
id (PK)           INT PRIMARY KEY
customer_id (FK)  INT FOREIGN KEY users.id
status            ENUM(pending, processing, shipped, delivered, cancelled, returned)
total_amount      DECIMAL(10,2)
shipping_cost     DECIMAL(10,2) DEFAULT 0
shipping_method   VARCHAR(50) (ground, express, overnight)
delivery_address_id (FK) INT FOREIGN KEY addresses.id
payment_method    VARCHAR(50) (credit_card, debit_card, etc.)
transaction_id    VARCHAR(255)
created_at        DATETIME DEFAULT NOW
updated_at        DATETIME DEFAULT NOW
```

### order_items
Items in orders.
```
id (PK)           INT PRIMARY KEY
order_id (FK)     INT FOREIGN KEY orders.id
product_id (FK)   INT FOREIGN KEY products.id
quantity          INTEGER
price_at_purchase DECIMAL(10,2)
seller_id (FK)    INT FOREIGN KEY users.id
```

### returns
Return requests.
```
id (PK)           INT PRIMARY KEY
order_id (FK)     INT FOREIGN KEY orders.id
product_id (FK)   INT FOREIGN KEY products.id
reason            TEXT
status            ENUM(initiated, approved, shipped, received, refunded)
refund_amount     DECIMAL(10,2)
requested_at      DATETIME DEFAULT NOW
processed_at      DATETIME
```

### reviews
Product reviews and ratings.
```
id (PK)           INT PRIMARY KEY
product_id (FK)   INT FOREIGN KEY products.id
customer_id (FK)  INT FOREIGN KEY users.id
rating            INTEGER (1-5)
comment           TEXT
created_at        DATETIME DEFAULT NOW
```

### messages
Direct messages between customers and sellers.
```
id (PK)           INT PRIMARY KEY
sender_id (FK)    INT FOREIGN KEY users.id
recipient_id (FK) INT FOREIGN KEY users.id
product_id (FK)   INT FOREIGN KEY products.id (nullable)
content           TEXT
created_at        DATETIME DEFAULT NOW
is_read           BOOLEAN DEFAULT FALSE
```

### chatbot_interactions
AI chatbot conversation history.
```
id (PK)           INT PRIMARY KEY
user_id (FK)      INT FOREIGN KEY users.id
query             TEXT
response          TEXT
created_at        DATETIME DEFAULT NOW
```

## Relationships

```
User (1) ──────────────────── (many) Address
User (1) ──────────────────── (1) Store
User (1) ──────────────────── (many) Cart
User (1) ──────────────────── (many) Order
User (1) ──────────────────── (many) Review
Store (1) ──────────────────── (many) Product
Product (many) ──────────────────── (many) CartItem
Product (many) ──────────────────── (many) OrderItem
Product (many) ──────────────────── (many) Review
Order (1) ──────────────────── (many) OrderItem
Order (1) ──────────────────── (many) Return
Cart (1) ──────────────────── (many) CartItem
```

## Key Constraints

### Primary Keys
- All tables have unique `id` primary key (auto-increment)

### Foreign Keys
- `addresses.user_id` -> `users.id`
- `stores.owner_id` -> `users.id` (UNIQUE)
- `products.store_id` -> `stores.id`
- `cart_items.cart_id` -> `carts.id`
- `cart_items.product_id` -> `products.id`
- `order_items.order_id` -> `orders.id`
- `order_items.product_id` -> `products.id`
- `order_items.seller_id` -> `users.id`
- `returns.order_id` -> `orders.id`
- `returns.product_id` -> `products.id`
- `reviews.product_id` -> `products.id`
- `reviews.customer_id` -> `users.id`
- `messages.sender_id` -> `users.id`
- `messages.recipient_id` -> `users.id`
- `messages.product_id` -> `products.id` (nullable)

### Unique Constraints
- `users.email` - UNIQUE
- `stores.owner_id` - UNIQUE (one store per seller)
- `products.sku` - UNIQUE (product code)

## Indexes

Recommended indexes for performance:
```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_stores_owner_id ON stores(owner_id);
CREATE INDEX idx_products_store_id ON products(store_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_carts_user_id ON carts(user_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_seller_id ON order_items(seller_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_recipient_id ON messages(recipient_id);
```

## Data Integrity

### Cascading Rules
- When a user is deleted, related addresses, carts, and messages are deleted
- When a store is deleted, related products are marked inactive
- When a product is deleted, it's marked inactive (soft delete)
- When an order is deleted, related order items are deleted
- When a cart is deleted, related cart items are deleted

### Constraints
- Product stock cannot be negative (enforced at app level)
- Product price must be positive (enforced at app level)
- Rating must be between 1-5 (enforced at app level)
- Order total must be positive (enforced at app level)
- Refund amount cannot exceed original purchase price (enforced at app level)

## Temporal Data

All major tables have timestamp columns:
- `created_at` - Record creation time
- `updated_at` - Last modification time (auto-updated)
- `processed_at` - When return/refund was processed

## Enumerations

### UserRole
- `customer` - End customer
- `seller` - Store owner
- `admin` - Platform administrator

### OrderStatus
- `pending` - Order placed, awaiting payment
- `processing` - Payment confirmed, preparing shipment
- `shipped` - Order shipped to customer
- `delivered` - Order delivered
- `cancelled` - Order cancelled
- `returned` - Product returned

### ReturnStatus
- `initiated` - Return requested
- `approved` - Return approved
- `shipped` - Return shipped back
- `received` - Return received
- `refunded` - Refund processed

## Backup Strategy

Recommended backup approach:
1. Daily full PostgreSQL backups
2. Weekly archive backups
3. Separate storage for image/file uploads
4. Test restore procedures monthly
5. 30-day backup retention minimum

## Scaling Considerations

For high-traffic scenarios:
1. Add database replication (read replicas)
2. Implement caching layer (Redis)
3. Use connection pooling
4. Archive old orders/returns
5. Partition large tables by date
6. Add database monitoring and alerting
