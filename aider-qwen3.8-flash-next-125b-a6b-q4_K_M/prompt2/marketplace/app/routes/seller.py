from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.store import Store
from app.models.product import Product
from app.models.order import Order
from app.utils.sanitizers import sanitize_string, sanitize_file_path, validate_extension
from app.utils.validators import validate_price
from werkzeug.utils import secure_filename
from PIL import Image
import os, uuid

bp = Blueprint("seller", __name__, url_prefix="/api/seller")

def seller_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role not in ("seller", "admin"):
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return wrapper

@bp.route("/store", methods=["POST"])
@login_required
@seller_required
def create_store():
    data = request.get_json(silent=True) or {}
    name = sanitize_string(data.get("name", ""))
    desc = sanitize_string(data.get("description", ""))
    store = Store(name=name, description=desc, seller_id=current_user.id)
    db.session.add(store)
    db.session.commit()
    return jsonify({"id": store.id, "name": store.name}), 201

@bp.route("/products", methods=["POST"])
@login_required
@seller_required
def add_product():
    data = request.get_json(silent=True) or {}
    name = sanitize_string(data.get("name", ""))
    desc = sanitize_string(data.get("description", ""))
    price = data.get("price")
    stock = int(data.get("stock_quantity", 0))
    category = sanitize_string(data.get("category", ""))
    store_id = int(data.get("store_id", 0))
    store = Store.query.filter_by(id=store_id, seller_id=current_user.id).first()
    if not store:
        return jsonify({"error": "Store not found"}), 404
    if not validate_price(price):
        return jsonify({"error": "Invalid price"}), 400
    product = Product(name=name, description=desc, price=price, stock_quantity=stock, category=category, store_id=store.id)
    db.session.add(product)
    db.session.commit()
    return jsonify({"id": product.id}), 201

@bp.route("/products/<int:product_id>/images", methods=["POST"])
@login_required
@seller_required
def upload_image(product_id):
    product = Product.query.filter_by(id=product_id, store__seller_id=current_user.id).first()
    if not product:
        return jsonify({"error": "Not found"}), 404
    file = request.files.get("image")
    if not file or not validate_extension(file.filename):
        return jsonify({"error": "Invalid file"}), 400
    safe_name = sanitize_file_path(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(product.store_id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, unique_name)
    file.save(filepath)
    # Resize
    img = Image.open(filepath)
    img.thumbnail((1200, 1200))
    img.save(filepath)
    product.image_paths = (product.image_paths or []) + [filepath]
    db.session.commit()
    return jsonify({"path": filepath}), 201

@bp.route("/orders", methods=["GET"])
@login_required
@seller_required
def seller_orders():
    orders = Order.query.filter_by(seller_id=current_user.id).all()
    return jsonify([{
        "id": o.id, "status": o.status, "total": float(o.total_amount),
        "items": [{"product_id": i.product_id, "qty": i.quantity} for i in o.items]
    } for o in orders])

@bp.route("/orders/<int:order_id>/fulfill", methods=["PATCH"])
@login_required
@seller_required
def fulfill_order(order_id):
    order = Order.query.filter_by(id=order_id, seller_id=current_user.id).first()
    if not order:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    order.status = sanitize_string(data.get("status", "shipped"))
    order.tracking_number = sanitize_string(data.get("tracking_number", ""))
    db.session.commit()
    return jsonify({"status": order.status})
