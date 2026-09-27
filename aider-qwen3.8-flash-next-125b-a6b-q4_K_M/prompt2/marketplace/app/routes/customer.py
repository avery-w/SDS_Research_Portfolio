from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.product import Product
from app.models.cart import CartItem
from app.models.order import Order, ReturnRequest
from app.utils.sanitizers import sanitize_string, sanitize_search_query, sanitize_quantity
from app.models.store import Store

bp = Blueprint("customer", __name__, url_prefix="/api/customer")

@bp.route("/products", methods=["GET"])
def browse_products():
    category = sanitize_search_query(request.args.get("category", ""))
    search = sanitize_search_query(request.args.get("q", ""))
    page = int(request.args.get("page", 1))
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    products = query.paginate(page=page, per_page=20)
    return jsonify({"products": [{"id": p.id, "name": p.name, "price": float(p.price), "stock": p.stock_quantity} for p in products.items], "total": products.total})

@bp.route("/cart", methods=["POST"])
@login_required
def add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = int(data.get("product_id", 0))
    qty = sanitize_quantity(data.get("quantity", 1))
    product = Product.query.get_or_404(product_id)
    existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        existing.quantity += qty
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=qty))
    db.session.commit()
    return jsonify({"status": "added"})

@bp.route("/orders", methods=["GET"])
@login_required
def my_orders():
    orders = Order.query.filter_by(customer_id=current_user.id).all()
    return jsonify([{"id": o.id, "status": o.status, "total": float(o.total_amount)} for o in orders])

@bp.route("/orders/<int:order_id>/cancel", methods=["PATCH"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
    if not order or order.status not in ("pending", "confirmed"):
        return jsonify({"error": "Cannot cancel"}), 400
    order.status = "cancelled"
    db.session.commit()
    return jsonify({"status": "cancelled"})

@bp.route("/orders/<int:order_id>/return", methods=["POST"])
@login_required
def request_return(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
    if not order:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    reason = sanitize_string(data.get("reason", ""))
    rr = ReturnRequest(order_id=order.id, customer_id=current_user.id, reason=reason)
    db.session.add(rr)
    db.session.commit()
    return jsonify({"id": rr.id, "status": rr.status}), 201
