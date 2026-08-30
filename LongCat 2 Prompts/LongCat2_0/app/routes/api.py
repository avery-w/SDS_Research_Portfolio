from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (User, Product, Order, OrderItem, CartItem, Store,
                        Category, Message)
from app.services.shipping import ShippingService
from app.utils.decorators import customer_required, admin_required
from app.utils.helpers import generate_order_number

api_bp = Blueprint('api', __name__)


@api_bp.route('/products', methods=['GET'])
def api_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    category = request.args.get('category')
    search = request.args.get('q', '')
    sort = request.args.get('sort', 'newest')

    query = Product.query.filter_by(is_active=True)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            query = query.filter_by(category_id=cat.id)

    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'products': [{
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'price': p.price,
            'image_url': p.image_url,
            'rating': p.rating,
            'store': p.store.name,
            'category': p.category.name if p.category else None
        } for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'current_page': products.page
    })


@api_bp.route('/product/<slug>', methods=['GET'])
def api_product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    return jsonify({
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'description': product.description,
        'price': product.price,
        'compare_at_price': product.compare_at_price,
        'sku': product.sku,
        'quantity': product.quantity,
        'weight': product.weight,
        'image_url': product.image_url,
        'rating': product.rating,
        'review_count': product.review_count,
        'store': {
            'id': product.store.id,
            'name': product.store.name
        },
        'category': product.category.name if product.category else None,
        'tags': product.tags,
        'in_stock': product.is_in_stock
    })


@api_bp.route('/cart', methods=['GET'])
@login_required
@customer_required
def api_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    items = []
    for item in cart_items:
        items.append({
            'id': item.id,
            'product_id': item.product_id,
            'name': item.product.name,
            'price': item.product.price,
            'quantity': item.quantity,
            'subtotal': item.product.price * item.quantity,
            'image_url': item.product.image_url,
            'max_quantity': item.product.quantity
        })
    subtotal = sum(i['subtotal'] for i in items)
    return jsonify({
        'items': items,
        'subtotal': subtotal,
        'item_count': sum(i['quantity'] for i in items)
    })


@api_bp.route('/cart/add', methods=['POST'])
@login_required
@customer_required
def api_add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    product = Product.query.get_or_404(product_id)
    if not product.is_in_stock:
        return jsonify({'error': 'Product out of stock'}), 400

    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if cart_item:
        new_qty = cart_item.quantity + quantity
        if new_qty > product.quantity:
            return jsonify({'error': f'Only {product.quantity} available'}), 400
        cart_item.quantity = new_qty
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=min(quantity, product.quantity)
        )
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({'message': 'Added to cart', 'cart_item_id': cart_item.id})


@api_bp.route('/cart/update/<int:item_id>', methods=['PUT'])
@login_required
@customer_required
def api_update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    quantity = data.get('quantity', 1)

    if quantity < 1:
        db.session.delete(cart_item)
    elif quantity > cart_item.product.quantity:
        return jsonify({'error': 'Not enough stock'}), 400
    else:
        cart_item.quantity = quantity

    db.session.commit()
    return jsonify({'message': 'Cart updated'})


@api_bp.route('/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
@customer_required
def api_remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'message': 'Item removed'})


@api_bp.route('/checkout/calculate-shipping', methods=['POST'])
@login_required
@customer_required
def api_calculate_shipping():
    data = request.get_json()
    shipping_service = ShippingService()

    rate = shipping_service.calculate_rate(
        weight=data.get('weight', 1.0),
        destination_zip=data.get('destination_zip', ''),
        destination_city=data.get('destination_city', ''),
        destination_state=data.get('destination_state', ''),
        method=data.get('method', 'ground')
    )
    return jsonify(rate)


@api_bp.route('/checkout', methods=['POST'])
@login_required
@customer_required
def api_checkout():
    data = request.get_json()
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

    shipping_service = ShippingService()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total_weight = sum(
        (item.product.weight or 1.0) * item.quantity for item in cart_items
    )

    shipping_rate = shipping_service.calculate_rate(
        weight=total_weight,
        destination_zip=data.get('shipping_zip', ''),
        destination_city=data.get('shipping_city', ''),
        destination_state=data.get('shipping_state', ''),
        method=data.get('shipping_method', 'ground')
    )

    shipping_cost = shipping_rate['rate']
    if subtotal >= 75.0:
        shipping_cost = 0.0

    tax_amount = subtotal * 0.0825
    total = subtotal + shipping_cost + tax_amount

    stores = {}
    for item in cart_items:
        store_id = item.product.store_id
        if store_id not in stores:
            stores[store_id] = []
        stores[store_id].append(item)

    orders_created = []
    for store_id, items in stores.items():
        order_subtotal = sum(i.product.price * i.quantity for i in items)
        order_shipping = shipping_cost / len(stores) if shipping_cost > 0 else 0
        order_tax = order_subtotal * 0.0825
        order_total = order_subtotal + order_shipping + order_tax

        order = Order(
            order_number=generate_order_number(),
            customer_id=current_user.id,
            store_id=store_id,
            status='pending',
            subtotal=order_subtotal,
            shipping_cost=order_shipping,
            tax_amount=order_tax,
            total=order_total,
            shipping_address=data.get('shipping_address', ''),
            shipping_city=data.get('shipping_city', ''),
            shipping_state=data.get('shipping_state', ''),
            shipping_zip=data.get('shipping_zip', ''),
            shipping_country=data.get('shipping_country', 'US'),
            shipping_method=data.get('shipping_method', 'standard'),
            payment_method=data.get('payment_method', 'credit_card'),
            payment_status='paid',
            notes=data.get('notes', '')
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product.id,
                product_name=item.product.name,
                product_price=item.product.price,
                quantity=item.quantity,
                subtotal=item.product.price * item.quantity
            )
            db.session.add(order_item)
            product = Product.query.get(item.product.id)
            product.quantity -= item.quantity

        orders_created.append(order.order_number)

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    return jsonify({
        'message': 'Order placed successfully',
        'orders': orders_created,
        'total': total,
        'shipping': shipping_cost,
        'tax': tax_amount
    })


@api_bp.route('/orders', methods=['GET'])
@login_required
@customer_required
def api_orders():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(
        customer_id=current_user.id
    ).order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)

    return jsonify({
        'orders': [{
            'order_number': o.order_number,
            'status': o.status,
            'total': o.total,
            'created_at': o.created_at.isoformat(),
            'item_count': o.items.count()
        } for o in orders.items],
        'total': orders.total,
        'pages': orders.pages
    })


@api_bp.route('/order/<order_number>', methods=['GET'])
@login_required
@customer_required
def api_order_detail(order_number):
    order = Order.query.filter_by(
        order_number=order_number, customer_id=current_user.id
    ).first_or_404()

    return jsonify({
        'order_number': order.order_number,
        'status': order.status,
        'subtotal': order.subtotal,
        'shipping_cost': order.shipping_cost,
        'tax_amount': order.tax_amount,
        'total': order.total,
        'shipping_address': order.shipping_address,
        'shipping_city': order.shipping_city,
        'shipping_state': order.shipping_state,
        'shipping_zip': order.shipping_zip,
        'shipping_method': order.shipping_method,
        'tracking_number': order.tracking_number,
        'payment_status': order.payment_status,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_name': item.product_name,
            'product_price': item.product_price,
            'quantity': item.quantity,
            'subtotal': item.subtotal
        } for item in order.items]
    })


@api_bp.route('/seller/orders', methods=['GET'])
@login_required
def api_seller_orders():
    if not current_user.is_seller:
        return jsonify({'error': 'Unauthorized'}), 403

    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(
        store_id=current_user.store.id
    ).order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)

    return jsonify({
        'orders': [{
            'order_number': o.order_number,
            'status': o.status,
            'total': o.total,
            'customer': o.customer.full_name,
            'created_at': o.created_at.isoformat()
        } for o in orders.items],
        'total': orders.total
    })


@api_bp.route('/admin/stats', methods=['GET'])
@login_required
@admin_required
def api_admin_stats():
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    total_revenue = db.session.query(
        func.coalesce(func.sum(Order.total), 0)
    ).filter(Order.status.in_(['delivered', 'shipped'])).scalar()

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    revenue_30d = db.session.query(
        func.coalesce(func.sum(Order.total), 0)
    ).filter(
        Order.created_at >= thirty_days_ago,
        Order.status.in_(['delivered', 'shipped', 'processing'])
    ).scalar()

    return jsonify({
        'total_users': User.query.count(),
        'total_orders': Order.query.count(),
        'total_revenue': float(total_revenue or 0),
        'revenue_30d': float(revenue_30d or 0),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'total_products': Product.query.count(),
        'total_stores': Store.query.count()
    })


@api_bp.route('/messages', methods=['GET'])
@login_required
def api_messages():
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter(
        db.or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).order_by(Message.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)

    return jsonify({
        'messages': [{
            'id': m.id,
            'sender': m.sender.full_name,
            'recipient': m.recipient.full_name,
            'content': m.content[:100],
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat()
        } for m in messages.items]
    })


@api_bp.route('/messages/send', methods=['POST'])
@login_required
def api_send_message():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    content = data.get('content', '').strip()

    if not content or not recipient_id:
        return jsonify({'error': 'Missing required fields'}), 400

    recipient = User.query.get_or_404(recipient_id)
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({
        'message': 'Message sent',
        'id': message.id,
        'created_at': message.created_at.isoformat()
    })


@api_bp.route('/categories', methods=['GET'])
def api_categories():
    categories = Category.query.filter_by(is_active=True).all()
    return jsonify({
        'categories': [{
            'id': c.id,
            'name': c.name,
            'slug': c.slug,
            'description': c.description,
            'product_count': c.products.count()
        } for c in categories]
    })
