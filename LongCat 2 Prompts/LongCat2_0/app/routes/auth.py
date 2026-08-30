from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Store, Category, Product, PlatformSetting
from app.forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    featured_products = Product.query.filter_by(is_active=True, is_featured=True).limit(8).all()
    categories = Category.query.filter_by(is_active=True).all()
    recent_products = Product.query.filter_by(is_active=True).order_by(
        Product.created_at.desc()).limit(12).all()
    return render_template('index.html',
                           featured_products=featured_products,
                           categories=categories,
                           recent_products=recent_products)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Contact support.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.first_name}!', 'success')
            if user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            elif user.is_seller:
                return redirect(next_page or url_for('seller.dashboard'))
            return redirect(next_page or url_for('customer.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        if user.is_seller:
            store = Store(
                name=f"{user.first_name}'s Store",
                seller_id=user.id,
                is_approved=True
            )
            db.session.add(store)
            db.session.commit()
            flash('Account created! Your store is ready.', 'success')
        else:
            flash('Account created successfully! Please sign in.', 'success')

        login_user(user)
        if user.is_seller:
            return redirect(url_for('seller.dashboard'))
        return redirect(url_for('customer.dashboard'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))


@auth_bp.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category')
    search = request.args.get('q', '')
    sort = request.args.get('sort', 'newest')

    query = Product.query.filter_by(is_active=True)

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                Product.tags.ilike(f'%{search}%')
            )
        )

    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first_or_404()
        query = query.filter_by(category_id=category.id)

    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.filter_by(is_active=True).all()

    return render_template('products.html',
                           products=products,
                           categories=categories,
                           current_category=category_slug,
                           search=search,
                           sort=sort)


@auth_bp.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()
    return render_template('product_detail.html',
                           product=product,
                           related_products=related_products)


@auth_bp.route('/stores')
def stores():
    page = request.args.get('page', 1, type=int)
    stores = Store.query.filter_by(is_active=True, is_approved=True).paginate(
        page=page, per_page=12, error_out=False)
    return render_template('stores.html', stores=stores)


@auth_bp.route('/store/<int:store_id>')
def store_detail(store_id):
    store = Store.query.get_or_404(store_id)
    page = request.args.get('page', 1, type=int)
    products = Product.query.filter_by(
        store_id=store.id, is_active=True
    ).paginate(page=page, per_page=12, error_out=False)
    return render_template('store_detail.html', store=store, products=products)
