from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import (User, Store, Product, Order, OrderItem, Category,
                        Message, ReturnRequest)
from app.forms import StoreForm, ProductForm, OrderStatusForm, MessageForm
from app.utils.decorators import seller_required
from app.utils.helpers import save_image, generate_slug
from sqlalchemy import func

seller_bp = Blueprint('seller', __name__)


@seller_bp.route('/dashboard')
@login_required
@seller_required
def dashboard():
    store = current_user.store
    total_products = Product.query.filter_by(store_id=store.id).count()
    total_orders = Order.query.filter_by(store_id=store.id).count()
    pending_orders = Order.query.filter_by(
        store_id=store.id, status='pending'
    ).count()
    recent_orders = Order.query.filter_by(store_id=store.id).order_by(
        Order.created_at.desc()).limit(10).all()
    low_stock = Product.query.filter(
        Product.store_id == store.id,
        Product.quantity <= 5
    ).order_by(Product.quantity.asc()).limit(10).all()

    total_revenue = db.session.query(
        func.coalesce(func.sum(Order.total), 0)
    ).filter(
        Order.store_id == store.id,
        Order.status.in_(['delivered', 'shipped'])
    ).scalar()

    return render_template('seller/dashboard.html',
                           store=store,
                           total_products=total_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           recent_orders=recent_orders,
                           low_stock=low_stock,
                           total_revenue=total_revenue)


@seller_bp.route('/store', methods=['GET', 'POST'])
@login_required
@seller_required
def manage_store():
    store = current_user.store
    form = StoreForm()
    if form.validate_on_submit():
        store.name = form.name.data
        store.description = form.description.data
        if form.logo.data:
            logo_path = save_image(form.logo.data, 'logos')
            if logo_path:
                store.logo_url = logo_path
        if form.banner.data:
            banner_path = save_image(form.banner.data, 'banners')
            if banner_path:
                store.banner_url = banner_path
        db.session.commit()
        flash('Store updated successfully.', 'success')
        return redirect(url_for('seller.manage_store'))
    elif request.method == 'GET':
        form.name.data = store.name
        form.description.data = store.description
    return render_template('seller/manage_store.html', form=form, store=store)


@seller_bp.route('/products')
@login_required
@seller_required
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    status = request.args.get('status', 'all')

    query = Product.query.filter_by(store_id=current_user.store.id)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    elif status == 'low_stock':
        query = query.filter(Product.quantity <= 5)

    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('seller/products.html',
                           products=products,
                           search=search,
                           current_status=status)


@seller_bp.route('/product/add', methods=['GET', 'POST'])
@login_required
@seller_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        slug = generate_slug(form.name.data)
        base_slug = slug
        counter = 1
        while Product.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            price=form.price.data,
            compare_at_price=form.compare_at_price.data,
            sku=form.sku.data,
            quantity=form.quantity.data,
            weight=form.weight.data or 0,
            weight_unit=form.weight_unit.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            store_id=current_user.store.id,
            tags=form.tags.data,
            is_active=form.is_active.data
        )

        if form.image.data:
            image_path = save_image(form.image.data, 'products')
            if image_path:
                product.image_url = image_path

        db.session.add(product)
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('seller.products'))
    return render_template('seller/product_form.html', form=form, title='Add Product')


@seller_bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@seller_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.store_id != current_user.store.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('seller.products'))

    form = ProductForm()
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.compare_at_price = form.compare_at_price.data
        product.sku = form.sku.data
        product.quantity = form.quantity.data
        product.weight = form.weight.data or 0
        product.weight_unit = form.weight_unit.data
        product.category_id = form.category_id.data if form.category_id.data != 0 else None
        product.tags = form.tags.data
        product.is_active = form.is_active.data

        if form.image.data:
            image_path = save_image(form.image.data, 'products')
            if image_path:
                product.image_url = image_path

        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('seller.products'))
    elif request.method == 'GET':
        form.name.data = product.name
        form.description.data = product.description
        form.price.data = product.price
        form.compare_at_price.data = product.compare_at_price
        form.sku.data = product.sku
        form.quantity.data = product.quantity
        form.weight.data = product.weight
        form.weight_unit.data = product.weight_unit
        form.category_id.data = product.category_id or 0
        form.tags.data = product.tags
        form.is_active.data = product.is_active

    return render_template('seller/product_form.html', form=form, title='Edit Product', product=product)


@seller_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
@seller_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.store_id != current_user.store.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('seller.products'))
    product.is_active = False
    db.session.commit()
    flash('Product deactivated.', 'info')
    return redirect(url_for('seller.products'))


@seller_bp.route('/orders')
@login_required
@seller_required
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    query = Order.query.filter_by(store_id=current_user.store.id)
    if status != 'all':
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('seller/orders.html', orders=orders, current_status=status)


@seller_bp.route('/order/<order_number>', methods=['GET', 'POST'])
@login_required
@seller_required
def order_detail(order_number):
    order = Order.query.filter_by(
        order_number=order_number, store_id=current_user.store.id
    ).first_or_404()
    form = OrderStatusForm()
    if form.validate_on_submit():
        order.status = form.status.data
        if form.tracking_number.data:
            order.tracking_number = form.tracking_number.data
        if form.notes.data:
            order.notes = form.notes.data
        if form.status.data == 'shipped':
            order.shipped_at = db.func.now()
        elif form.status.data == 'delivered':
            order.delivered_at = db.func.now()
        db.session.commit()
        flash('Order status updated.', 'success')
        return redirect(url_for('seller.order_detail', order_number=order_number))
    elif request.method == 'GET':
        form.status.data = order.status
        form.tracking_number.data = order.tracking_number
        form.notes.data = order.notes
    return render_template('seller/order_detail.html', order=order, form=form)


@seller_bp.route('/messages')
@login_required
@seller_required
def messages():
    page = request.args.get('page', 1, type=int)
    conversations = db.session.query(
        func.max(Message.id).label('last_id')
    ).filter(
        db.or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).group_by(
        func.least(Message.sender_id, Message.recipient_id),
        func.greatest(Message.sender_id, Message.recipient_id)
    ).subquery()

    message_ids = db.session.query(conversations.c.last_id).all()
    message_ids = [m[0] for m in message_ids]
    messages = Message.query.filter(
        Message.id.in_(message_ids)
    ).order_by(Message.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('seller/messages.html', messages=messages)


@seller_bp.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
@seller_required
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
        return redirect(url_for('seller.conversation', user_id=user_id))

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

    return render_template('seller/conversation.html',
                           messages=messages,
                           other_user=other_user,
                           form=form)


@seller_bp.route('/returns')
@login_required
@seller_required
def returns():
    page = request.args.get('page', 1, type=int)
    returns = ReturnRequest.query.join(Order).filter(
        Order.store_id == current_user.store.id
    ).order_by(ReturnRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('seller/returns.html', returns=returns)


@seller_bp.route('/return/<int:return_id>/<action>', methods=['POST'])
@login_required
@seller_required
def handle_return(return_id, action):
    return_req = ReturnRequest.query.get_or_404(return_id)
    if return_req.order.store_id != current_user.store.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('seller.returns'))

    if action == 'approve':
        return_req.status = 'approved'
        return_req.order.status = 'returned'
    elif action == 'reject':
        return_req.status = 'rejected'
    else:
        flash('Invalid action.', 'danger')
        return redirect(url_for('seller.returns'))

    db.session.commit()
    flash(f'Return request {action}d.', 'success')
    return redirect(url_for('seller.returns'))
