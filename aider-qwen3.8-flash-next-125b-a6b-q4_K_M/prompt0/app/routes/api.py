from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.models.cart import Cart, CartItem
from app.services.shipping import ShippingService
from app.utils.decorators import admin_required, seller_required

api_bp = Blueprint("api", __name__)

@api_bp.route("/products", methods=["GET"])
def api_list_products():
    q = request.args.get("q", "")
    category_id = request.args.get("category_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Product.query.filter_by(is_active=True)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter(Product.category_id == category_id)

    pagination = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=per_page)
    return jsonify({
        "products": [
            {
                "id": p.id, "name": p.name, "price": float(p.price),
                "stock": p.stock_quantity, "sku": p.sku,
                "images": [img.image_url for img in p.images],
                "store": p.store.name,
            }
            for p in pagination.items
        ],
        "page": pagination.page,
        "total_pages": pagination.pages,
        "total_items": pagination.total,
    })

@api_bp.route("/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id):
    p = Product.query.get_or_404(product_id)
    return jsonify({
        "id": p.id, "name": p.name, "description": p.description,
        "price": float(p.price), "stock": p.stock_quantity, "sku": p.sku,
        "images": [img.image_url for img in p.images],
        "store": {"id": p.store.id, "name": p.store.name},
    })

@api_bp.route("/checkout", methods=["POST"])
@login_required
def api_checkout():
    """
    POST /api/checkout
    Body JSON:
    {
        "cart_items": [{"product_id": 1, "quantity": 2}],
        "shipping_address": {
            "street": "...", "city": "...", "state": "...", "zip": "..."
        },
        "shipping_method": "02"
    }
    """
    data = request.get_json()
    if not data:
        abort(400)

    cart_items = data.get("cart_items", [])
    addr = data.get("shipping_address", {})
    shipping_method = data.get("shipping_method", "02")

    subtotal = 0
    total_weight = 0
    max_dims = (0, 0, 0)
    order_items_data = []

    for ci in cart_items:
        product = Product.query.get(ci["product_id"])
        if not product or not product.is_active:
            abort(404, "Product not found")
        qty = ci["quantity"]
        subtotal += float(product.price) * qty
        total_weight += product.weight_oz * qty
        max_dims = (
            max(max_dims[0], product.length_in),
            max(max_dims[1], product.width_in),
            max(max_dims[2], product.height_in),
        )
        order_items_data.append({
            "product_id": product.id,
            "quantity": qty,
            "unit_price": float(product.price),
            "seller_id": product.store.owner_id,
        })

    rates = ShippingService.get_shipping_rates(
        addr.get("street", ""), addr.get("city", ""),
        addr.get("state", ""), addr.get("zip", ""),
        total_weight, max_dims[0], max_dims[1], max_dims[2],
    )
    selected = next((r for r in rates if r["service_code"] == shipping_method), rates[0] if rates else {"cost": 0})
    shipping_cost = selected["cost"]
    total = subtotal + shipping_cost

    import uuid
    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:12].upper()}",
        customer_id=current_user.id,
        status=OrderStatus.CONFIRMED,
        shipping_address_street=addr.get("street", ""),
        shipping_address_city=addr.get("city", ""),
        shipping_address_state=addr.get("state", ""),
        shipping_address_zip=addr.get("zip", ""),
        shipping_method=shipping_method,
        shipping_cost=shipping_cost,
        subtotal=subtotal,
        total=total,
    )
    db.session.add(order)
    db.session.flush()

    for oi in order_items_data:
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=oi["product_id"],
            quantity=oi["quantity"],
            unit_price=oi["unit_price"],
            seller_id=oi["seller_id"],
        ))
        prod = Product.query.get(oi["product_id"])
        prod.stock_quantity -= oi["quantity"]

    db.session.commit()
    return jsonify({"order_id": order.id, "order_number": order.order_number, "total": float(total)}), 201

@api_bp.route("/shipping/rates", methods=["POST"])
def api_shipping_rates():
    """
    POST /api/shipping/rates
    Body JSON:
    {
        "dest_street": "...", "dest_city": "...", "dest_state": "...", "dest_zip": "...",
        "weight_oz": 16, "length_in": 10, "width_in": 8, "height_in": 6
    }
    """
    data = request.get_json()
    rates = ShippingService.get_shipping_rates(
        data.get("dest_street", ""), data.get("dest_city", ""),
        data.get("dest_state", ""), data.get("dest_zip", ""),
        data.get("weight_oz", 0), data.get("length_in", 0),
        data.get("width_in", 0), data.get("height_in", 0),
    )
    return jsonify({"rates": rates})
