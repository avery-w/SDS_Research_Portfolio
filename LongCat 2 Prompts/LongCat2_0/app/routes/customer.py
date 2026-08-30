from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import (User, Product, CartItem, Order, OrderItem, Store,
                        Message, ReturnRequest, Category)
from app.forms import (CartAddForm, CheckoutForm, ReturnRequestForm,
                       MessageForm, UserProfileForm)
from app.utils.decorators import customer_required, active_user_required
from app.services.shipping import ShippingService
from app.utils.helpers import generate_order_number, generate_slug

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    recent_orders = Order.query.filter_by(
        customer_id=current_user.id
    ).order_by(Order.created_at.desc()).limit(5).all()
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    pending_orders = Order.query.filter(
        Order.customer_id == current_user.id,
        Order.status.in_(['pending', 'processing', 'shipped'])
    ).count()
    return render_template('customer/dashboard.html',
                           recent_orders=recent_orders,
                           cart_count=cart_count,
                           pending_orders=pending_orders)


@customer_bp.route('/cart')
@login_required
@customer_required
def cart():
    cart_items = CartItem.query.filter_by(
        user_id=current_user.id
    ).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('customer/cart.html',
                           cart_items=cart_items,
                           subtotal=subtotal)


@customer_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active or not product.is_in_stock:
        flash('Product is not available.', 'danger')
        return redirect(url_for('auth.product_detail', slug=product.slug))

    form = CartAddForm()
    quantity = form.quantity.data or 1

    if quantity > product.quantity:
        flash(f'Only {product.quantity} items available.', 'warning')
        return redirect(url_for('auth.product_detail', slug=product.slug))

    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if cart_item:
        new_qty = cart_item.quantity + quantity
        if new_qty > product.quantity:
            flash(f'Cannot add more. Only {product.quantity} available.', 'warning')
            return redirect(url_for('customer.cart'))
        cart_item.quantity = new_qty
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    flash(f'{product.name} added to cart.', 'success')
    return redirect(url_for('customer.cart'))


@customer_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
@customer_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('customer.cart'))

    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        db.session.delete(cart_item)
    elif quantity > cart_item.product.quantity:
        flash(f'Only {cart_item.product.quantity} available.', 'warning')
    else:
        cart_item.quantity = quantity

    db.session.commit()
    return redirect(url_for('customer.cart'))


@customer_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
@customer_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('customer.cart'))
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('customer.cart'))


@customer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@customer_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('auth.products'))

    form = CheckoutForm()
    if request.method == 'GET':
        form.shipping_address.data = current_user.address or ''
        form.shipping_city.data = current_user.city or ''
        form.shipping_state.data = current_user.state or ''
        form.shipping_zip.data = current_user.zip_code or ''

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_service = ShippingService()

    if form.validate_on_submit():
        total_weight = sum(
            (item.product.weight or 1.0) * item.quantity for item in cart_items
        )
        shipping_rate = shipping_service.calculate_rate(
            weight=total_weight,
            destination_zip=form.shipping_zip.data,
            destination_city=form.shipping_city.data,
            destination_state=form.shipping_state.data,
            method=form.shipping_method.data
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
                shipping_address=form.shipping_address.data,
                shipping_city=form.shipping_city.data,
                shipping_state=form.shipping_state.data,
                shipping_zip=form.shipping_zip.data,
                shipping_country=form.shipping_country.data,
                shipping_method=form.shipping_method.data,
                payment_method=form.payment_method.data,
                payment_status='paid',
                notes=form.notes.data
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

        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash('Order placed successfully!', 'success')
        return redirect(url_for('customer.orders'))

    return render_template('customer/checkout.html',
                           form=form,
                           cart_items=cart_items,
                           subtotal=subtotal,
                           shipping_service=shipping_service)


@customer_bp.route('/orders')
@login_required
@customer_required
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    query = Order.query.filter_by(customer_id=current_user.id)
    if status != 'all':
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('customer/orders.html', orders=orders, current_status=status)


@customer_bp.route('/order/<order_number>')
@login_required
@customer_required
def order_detail(order_number):
    order = Order.query.filter_by(
        order_number=order_number, customer_id=current_user.id
    ).first_or_404()
    return render_template('customer/order_detail.html', order=order)


@customer_bp.route('/order/<order_number>/cancel', methods=['POST'])
@login_required
@customer_required
def cancel_order(order_number):
    order = Order.query.filter_by(
        order_number=order_number, customer_id=current_user.id
    ).first_or_404()

    if order.status not in ['pending', 'processing']:
        flash('This order cannot be cancelled.', 'danger')
        return redirect(url_for('customer.order_detail', order_number=order_number))

    order.status = 'cancelled'
    order.cancelled_at = db.func.now()
    for item in order.items:
        product = Product.query.get(item.product_id)
        product.quantity += item.quantity
    db.session.commit()
    flash('Order cancelled successfully.', 'info')
    return redirect(url_for('customer.orders'))


@customer_bp.route('/order/<order_number>/return', methods=['GET', 'POST'])
@login_required
@customer_required
def request_return(order_number):
    order = Order.query.filter_by(
        order_number=order_number, customer_id=current_user.id
    ).first_or_404()

    if order.status != 'delivered':
        flash('Only delivered orders can be returned.', 'danger')
        return redirect(url_for('customer.order_detail', order_number=order_number))

    existing = ReturnRequest.query.filter_by(order_id=order.id).first()
    if existing:
        flash('A return request already exists for this order.', 'warning')
        return redirect(url_for('customer.order_detail', order_number=order_number))

    form = ReturnRequestForm()
    if form.validate_on_submit():
        return_req = ReturnRequest(
            order_id=order.id,
            customer_id=current_user.id,
            reason=form.reason.data,
            description=form.description.data,
            refund_amount=order.total
        )
        db.session.add(return_req)
        db.session.commit()
        flash('Return request submitted successfully.', 'success')
        return redirect(url_for('customer.order_detail', order_number=order_number))

    return render_template('customer/return_request.html', form=form, order=order)


@customer_bp.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    conversations = db.session.query(
        db.func.max(Message.id).label('last_id')
    ).filter(
        db.or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).group_by(
        db.func.least(Message.sender_id, Message.recipient_id),
        db.func.greatest(Message.sender_id, Message.recipient_id)
    ).subquery()

    message_ids = db.session.query(conversations.c.last_id).all()
    message_ids = [m[0] for m in message_ids]
    messages = Message.query.filter(
        Message.id.in_(message_ids)
    ).order_by(Message.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('customer/messages.html', messages=messages)


@customer_bp.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    form = MessageForm()

    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=user_id,
            content=form.content.data
        )
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('customer.conversation', user_id=user_id))

    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            db.and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()

    for msg in messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()

    return render_template('customer/conversation.html',
                           messages=messages,
                           other_user=other_user,
                           form=form)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@active_user_required
def profile():
    form = UserProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.zip_code = form.zip_code.data
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('customer.profile'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.zip_code.data = current_user.zip_code
    return render_template('customer/profile.html', form=form)
