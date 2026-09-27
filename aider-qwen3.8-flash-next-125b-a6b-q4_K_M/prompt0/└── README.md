
## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/products` | List/search products |
| GET | `/api/products/<id>` | Product detail |
| POST | `/api/checkout` | Place order (JSON) |
| POST | `/api/shipping/rates` | Get UPS rates |
| POST | `/chatbot/chat/send` | AI chatbot message |

## Roles
- **Customer**: browse, search, cart, checkout, order history, returns
- **Seller**: store management, product CRUD, inventory, fulfill orders, messaging
- **Admin**: manage all users/stores/products/orders, override actions, analytics dashboard
