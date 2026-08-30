from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import (User, Store, Product, Order, Category, Message,
                        ReturnRequest, PlatformSetting)
from app.forms import (AdminUserForm, CategoryForm, PlatformSettingsForm,
                       OrderStatusForm)
from app.utils.decorators import admin_required
from app.utils.helpers import save_image, generate_slug
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_sellers = User.query.filter_by(role='seller').count()
    total_customers = User.query.filter_by(role='customer').count()
    total_stores = Store.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    active_returns = ReturnRequest.query.filter_by(status='pending').count()

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    revenue_30d = db.session.query(
        func.coalesce(func.sum(Order.total), 0)
    ).filter(
        Order.created_at >= thirty_days_ago,
        Order.status.in_(['delivered', 'shipped', 'processing'])
    ).scalar()

    orders_30d = Order.query.filter(Order.created_at >= thirty_days_ago).count()
    new_users_30d = User.query.filter(User.created_at >= thirty_days_ago).count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    top_products = db.session.query(
        Product, func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_sellers=total_sellers,
                           total_customers=total_customers,
                           total_stores=total_stores,
                           total_products=total_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           active_returns=active_returns,
                           revenue_30d=revenue_30d,
                           orders_30d=orders_30d,
                           new_users_30d=new_users_30d,
                           recent_orders=recent_orders,
                           recent_users=recent_users,
                           top_products=top_products)


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    daily_revenue = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total).label('revenue'),
        func.count(Order.id).label('order_count')
    ).filter(
        Order.status.in_(['delivered', 'shipped', 'processing'])
    ).group_by(
        func.date(Order.created_at)
    ).order_by(
        func.date(Order.created_at).desc()
    ).limit(30).all()

    category_sales = db.session.query(
        Category.name,
        func.sum(OrderItem.subtotal).label('total_sales'),
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(Product, Product.category_id == Category.id
    ).join(OrderItem, OrderItem.product_id == Product.id
    ).group_by(Category.name).order_by(
        func.sum(OrderItem.subtotal).desc()
    ).all()

    top_sellers = db.session.query(
        Store.name,
        func.sum(Order.total).label('total_revenue'),
        func.count(Order.id).label('order_count')
    ).join(Order).filter(
        Order.status.in_(['delivered', 'shipped'])
    ).group_by(Store.name).order_by(
        func.sum(Order.total).desc()
    ).limit(10).all()

    order_status_counts = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()

    return render_template('admin/analytics.html',
                           daily_revenue=daily_revenue,
                           category_sales=category_sales,
                           top_sellers=top_sellers,
                           order_status_counts=order_status_counts)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    role = request.args.get('role', 'all')
    status = request.args.get('status', 'all')

    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    if role != 'all':
        query = query.filter_by(role=role)
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/users.html',
                           users=users,
                           search=search,
                           current_role=role,
                           current_status=status)


@admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm()
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data.lower()
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.users'))
    elif request.method == 'GET':
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        form.role.data = user.role
        form.is_active.data = user.is_active
    return render_template('admin/edit_user.html', form=form, user=user)


@admin_bp.route('/user/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/stores')
@login_required
@admin_required
def stores():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    query = Store.query
    if status == 'pending':
        query = query.filter_by(is_approved=False)
    elif status == 'active':
        query = query.filter_by(is_active=True, is_approved=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    stores = query.order_by(Store.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/stores.html', stores=stores, current_status=status)


@admin_bp.route('/store/<int:store_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_store(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_approved = True
    store.is_active = True
    db.session.commit()
    flash(f'Store "{store.name}" approved.', 'success')
    return redirect(url_for('admin.stores'))


@admin_bp.route('/store/<int:store_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_store(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_active = not store.is_active
    db.session.commit()
    status = 'activated' if store.is_active else 'deactivated'
    flash(f'Store {status}.', 'success')
    return redirect(url_for('admin.stores'))


@admin_bp.route('/products')
@login_required
@admin_required
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/products.html', products=products, search=search)


@admin_bp.route('/product/<int:product_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status = 'activated' if product.is_active else 'deactivated'
    flash(f'Product {status}.', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    query = Order.query
    if status != 'all':
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/orders.html', orders=orders, current_status=status)


@admin_bp.route('/order/<order_number>', methods=['GET', 'POST'])
@login_required
@admin_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    form = OrderStatusForm()
    if form.validate_on_submit():
        order.status = form.status.data
        if form.tracking_number.data:
            order.tracking_number = form.tracking_number.data
        if form.notes.data:
            order.notes = form.notes.data
        if form.status.data == 'cancelled':
            order.cancelled_at = db.func.now()
            for item in order.items:
                product = Product.query.get(item.product_id)
                product.quantity += item.quantity
        db.session.commit()
        flash('Order updated.', 'success')
        return redirect(url_for('admin.order_detail', order_number=order_number))
    elif request.method == 'GET':
        form.status.data = order.status
        form.tracking_number.data = order.tracking_number
        form.notes.data = order.notes
    return render_template('admin/order_detail.html', order=order, form=form)


@admin_bp.route('/order/<order_number>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_order(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    order.status = 'cancelled'
    order.cancelled_at = db.func.now()
    for item in order.items:
        product = Product.query.get(item.product_id)
        product.quantity += item.quantity
    db.session.commit()
    flash('Order cancelled.', 'info')
    return redirect(url_for('admin.order_detail', order_number=order_number))


@admin_bp.route('/returns')
@login_required
@admin_required
def returns():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    query = ReturnRequest.query
    if status != 'all':
        query = query.filter_by(status=status)
    returns = query.order_by(ReturnRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/returns.html', returns=returns, current_status=status)


@admin_bp.route('/return/<int:return_id>/handle', methods=['POST'])
@login_required
@admin_required
def handle_return(return_id):
    return_req = ReturnRequest.query.get_or_404(return_id)
    action = request.form.get('action')
    admin_notes = request.form.get('admin_notes', '')

    if action == 'approve':
        return_req.status = 'approved'
        return_req.order.status = 'returned'
        return_req.admin_notes = admin_notes
    elif action == 'reject':
        return_req.status = 'rejected'
        return_req.admin_notes = admin_notes
    else:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin.returns'))

    db.session.commit()
    flash(f'Return request {action}d.', 'success')
    return redirect(url_for('admin.returns'))


@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            slug=generate_slug(form.name.data),
            description=form.description.data,
            icon=form.icon.data,
            is_active=form.is_active.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added.', 'success')
        return redirect(url_for('admin.categories'))

    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', form=form, categories=categories)


@admin_bp.route('/category/<int:cat_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    form = PlatformSettingsForm()

    if form.validate_on_submit():
        settings_map = {
            'platform_name': form.platform_name.data,
            'shipping_base_rate': str(form.shipping_base_rate.data),
            'free_shipping_threshold': str(form.free_shipping_threshold.data),
            'tax_rate': str(form.tax_rate.data / 100),
            'platform_fee_percent': str(form.platform_fee_percent.data),
            'support_email': form.support_email.data
        }
        for key, value in settings_map.items():
            setting = PlatformSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = PlatformSetting(key=key, value=value)
                db.session.add(setting)
        db.session.commit()
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))
    elif request.method == 'GET':
        form.platform_name.data = get_setting('platform_name', 'LongCat Marketplace')
        form.shipping_base_rate.data = float(get_setting('shipping_base_rate', '5.99'))
        form.free_shipping_threshold.data = float(get_setting('free_shipping_threshold', '75.00'))
        form.tax_rate.data = float(get_setting('tax_rate', '0.0825')) * 100
        form.platform_fee_percent.data = float(get_setting('platform_fee_percent', '5.0'))
        form.support_email.data = get_setting('support_email', 'support@longcatmarketplace.com')

    return render_template('admin/settings.html', form=form)


def get_setting(key, default=''):
    setting = PlatformSetting.query.filter_by(key=key).first()
    return setting.value if setting else default
