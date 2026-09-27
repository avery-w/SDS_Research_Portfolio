# API Examples

Complete examples for all major API endpoints.

## Authentication

### Register

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "SecurePass123",
    "full_name": "John Customer"
  }'
```

Response:
```json
{
  "id": 1,
  "email": "customer@example.com",
  "full_name": "John Customer",
  "role": "customer",
  "is_active": true,
  "created_at": "2024-01-15T10:00:00"
}
```

### Login

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=customer@example.com&password=SecurePass123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Get Current User

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Products

### List Products

```bash
# Get all products
curl -X GET "http://localhost:8000/products"

# Search products
curl -X GET "http://localhost:8000/products?search=laptop"

# Pagination
curl -X GET "http://localhost:8000/products?skip=0&limit=20"

# Filter by store
curl -X GET "http://localhost:8000/products?store_id=1"
```

Response:
```json
[
  {
    "id": 1,
    "store_id": 1,
    "name": "Laptop Pro",
    "description": "High performance laptop",
    "price": 1299.99,
    "quantity_available": 5,
    "sku": "LP001",
    "weight_oz": 48,
    "is_active": true,
    "created_at": "2024-01-10T00:00:00",
    "images": [],
    "reviews": []
  }
]
```

### Get Product Details

```bash
curl -X GET "http://localhost:8000/products/1"
```

### Add Product Review

```bash
curl -X POST "http://localhost:8000/products/1/reviews" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "comment": "Excellent product, highly recommend!"
  }'
```

## Cart

### View Cart

```bash
curl -X GET "http://localhost:8000/cart" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
[
  {
    "id": 1,
    "user_id": 2,
    "product_id": 1,
    "quantity": 2,
    "added_at": "2024-01-15T10:30:00",
    "product": {
      "id": 1,
      "name": "Laptop Pro",
      "price": 1299.99,
      ...
    }
  }
]
```

### Add to Cart

```bash
curl -X POST "http://localhost:8000/cart" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }'
```

### Update Cart Item Quantity

```bash
curl -X PUT "http://localhost:8000/cart/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 3
  }'
```

### Remove Item from Cart

```bash
curl -X DELETE "http://localhost:8000/cart/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Clear Cart

```bash
curl -X DELETE "http://localhost:8000/cart" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Addresses

### Create Address

```bash
curl -X POST "http://localhost:8000/addresses" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "street": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "country": "US",
    "is_default": true
  }'
```

### Get User Addresses

```bash
curl -X GET "http://localhost:8000/addresses" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Address

```bash
curl -X PUT "http://localhost:8000/addresses/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "street": "456 Elm St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78702",
    "country": "US",
    "is_default": false
  }'
```

## Checkout

### Calculate Shipping Rate

```bash
curl -X POST "http://localhost:8000/checkout/shipping-rate" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_zip": "90210",
    "weight_oz": 64
  }'
```

Response:
```json
{
  "rate": 12.50,
  "carrier": "UPS Ground",
  "estimated_days": 5
}
```

### Create Order

```bash
curl -X POST "http://localhost:8000/checkout/create-order" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address_id": 1
  }'
```

Response:
```json
{
  "id": 1,
  "customer_id": 2,
  "store_id": 1,
  "status": "pending",
  "total_amount": 2999.99,
  "shipping_cost": 15.50,
  "shipping_address_id": 1,
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "quantity": 2,
      "price_at_purchase": 1299.99
    }
  ],
  "created_at": "2024-01-15T11:00:00"
}
```

### Process Payment

```bash
curl -X POST "http://localhost:8000/checkout/process-payment" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "payment_method_id": "pm_test_4242424242424242"
  }'
```

## Orders

### List Orders

```bash
curl -X GET "http://localhost:8000/orders" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Order Details

```bash
curl -X GET "http://localhost:8000/orders/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cancel Order

```bash
curl -X POST "http://localhost:8000/orders/1/cancel" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Request Return

```bash
curl -X POST "http://localhost:8000/orders/1/request-return" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Mark as Shipped (Seller)

```bash
curl -X POST "http://localhost:8000/orders/1/mark-shipped?tracking_number=1Z999AA10123456784" \
  -H "Authorization: Bearer SELLER_TOKEN"
```

## Stores (Seller)

### Create Store

```bash
curl -X POST "http://localhost:8000/stores" \
  -H "Authorization: Bearer SELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Superstore",
    "description": "All your tech needs in one place"
  }'
```

### Get Store Products

```bash
curl -X GET "http://localhost:8000/stores/1/products" \
  -H "Authorization: Bearer SELLER_TOKEN"
```

### Add Product to Store

```bash
curl -X POST "http://localhost:8000/stores/1/products" \
  -H "Authorization: Bearer SELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop Pro",
    "description": "High performance laptop",
    "price": 1299.99,
    "quantity_available": 10,
    "sku": "LP001",
    "weight_oz": 48
  }'
```

### Update Product

```bash
curl -X PUT "http://localhost:8000/stores/1/products/1" \
  -H "Authorization: Bearer SELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 1199.99,
    "quantity_available": 8
  }'
```

## Chat

### Send Message

```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "How long does shipping take?"
  }'
```

### Get Messages

```bash
curl -X GET "http://localhost:8000/chat/messages" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Suggestions

```bash
curl -X GET "http://localhost:8000/chat/suggestions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Admin

### List Users

```bash
curl -X GET "http://localhost:8000/admin/users?skip=0&limit=10" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Change User Role

```bash
curl -X PUT "http://localhost:8000/admin/users/2/role?new_role=seller" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Deactivate User

```bash
curl -X POST "http://localhost:8000/admin/users/2/deactivate" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Get Sales Analytics

```bash
curl -X GET "http://localhost:8000/admin/analytics/sales" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Response:
```json
{
  "total_orders": 42,
  "total_revenue": 125430.50,
  "paid_orders": 38,
  "pending_orders": 4
}
```

### Get User Analytics

```bash
curl -X GET "http://localhost:8000/admin/analytics/users" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Response:
```json
{
  "total_users": 156,
  "customers": 142,
  "sellers": 12,
  "active_users": 138
}
```

### Get Product Analytics

```bash
curl -X GET "http://localhost:8000/admin/analytics/products" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Test Credentials (Demo Mode)

### Stripe Test Card
```
Number: 4242 4242 4242 4242
Exp: 12/25
CVC: 123
```

### Demo Users (After Creation)
```
Customer: customer@example.com
Seller: seller@example.com
Admin: admin@example.com
Password: (use your own password from registration)
```

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized for this action"
}
```

### 404 Not Found
```json
{
  "detail": "Product not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Not enough inventory"
}
```

## Rate Limiting (Production)

Add to your requests for production:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
```
