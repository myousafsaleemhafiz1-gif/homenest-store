import os
import re
import secrets
import csv
import io
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, func, or_, select, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    orders: Mapped[list['Order']] = relationship(back_populates='user')

class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    compare_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    image_2: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_3: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_4: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_description: Mapped[str] = mapped_column(String(260), default='', nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    badge: Mapped[str] = mapped_column(String(60), default='', nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=4.8, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str] = mapped_column(String(500), default='', nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default='cod', nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), default='cod_due', nullable=False)
    shipping_payment_status: Mapped[str] = mapped_column(String(30), default='not_required', nullable=False)
    payment_tracker: Mapped[str | None] = mapped_column(String(140), nullable=True)
    shipping_payment_reference: Mapped[str | None] = mapped_column(String(140), nullable=True)
    payment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_token: Mapped[str] = mapped_column(String(100), default='', nullable=False, unique=True, index=True)
    stock_committed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default='Pending', nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    user: Mapped[User | None] = relationship(back_populates='orders')
    items: Mapped[list['OrderItem']] = relationship(back_populates='order', cascade='all, delete-orphan')

class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    product_title: Mapped[str] = mapped_column(String(180), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), default='', nullable=False)
    order: Mapped[Order] = relationship(back_populates='items')

class Coupon(Base):
    __tablename__ = 'coupons'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    percent_off: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "homenest.db")}')
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '0') == '1',
)


def db():
    return SessionLocal()

@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


def slugify(text: str) -> str:
    value = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return value or secrets.token_hex(4)


def money(value):
    try:
        return f"{load_store_settings().get('currency_symbol','₨')}{Decimal(value):,.0f}"
    except Exception:
        return '₨0'

app.jinja_env.filters['money'] = money
app.jinja_env.globals['store_name'] = 'HomeNest Store'


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(24)
    return session['csrf_token']

@app.context_processor
def inject_globals():
    cart_count = sum(int(q) for q in session.get('cart', {}).values())
    s = db()
    pending_count = s.scalar(select(func.count(Order.id)).where(Order.status == 'Pending')) or 0
    low_stock_count = s.scalar(select(func.count(Product.id)).where(Product.active.is_(True), Product.stock.between(1,10))) or 0
    return {
        'pending': pending_count,
        'low_stock': low_stock_count,
        'csrf_token': csrf_token(),
        'cart_count': cart_count,
        'current_user': g.get('current_user'),
        'categories': get_categories(),
        'settings': load_store_settings(),
    }

@app.before_request
def load_user_and_guard_csrf():
    user_id = session.get('user_id')
    g.current_user = db().get(User, user_id) if user_id else None
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.endpoint not in {'static', 'safepay_success', 'safepay_webhook'}:
        supplied = request.form.get('_csrf') or request.headers.get('X-CSRF-Token')
        if supplied and secrets.compare_digest(supplied, session.get('csrf_token', '')):
            return
        if request.endpoint in {'add_to_cart', 'update_cart', 'remove_cart', 'apply_coupon'} and request.is_json:
            supplied = (request.get_json(silent=True) or {}).get('_csrf')
            if supplied and secrets.compare_digest(supplied, session.get('csrf_token', '')):
                return
        abort(400, description='Invalid or missing CSRF token.')


def get_categories():
    s = db()
    return [r[0] for r in s.query(Product.category).filter(Product.active.is_(True)).distinct().order_by(Product.category).all()]


def cart_items():
    s = db()
    cart = session.get('cart', {})
    items, subtotal = [], Decimal('0')
    clean = {}
    for pid, qty in cart.items():
        try:
            product_id = int(pid); quantity = max(1, min(int(qty), 99))
        except (ValueError, TypeError):
            continue
        product = s.get(Product, product_id)
        if not product or not product.active or product.stock <= 0:
            continue
        quantity = min(quantity, product.stock)
        line = Decimal(product.price) * quantity
        subtotal += line
        clean[str(product_id)] = quantity
        items.append({'product': product, 'quantity': quantity, 'line_total': line})
    if clean != cart:
        session['cart'] = clean
    return items, subtotal


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.current_user or not g.current_user.is_admin:
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)
    return wrapper


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.current_user:
            flash('Please sign in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapper


def seed_data():
    s = db()
    if not s.query(Product).count():
        products = [
            ('AeroBeat Wireless Earbuds', 'electronics', 3499, 4999, 42, 'https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=900&q=85', 'Low-latency wireless audio with a compact charging case.', 'Crisp everyday sound, touch controls, dual microphones, USB-C charging and a pocket-friendly case.', 'BEST SELLER'),
            ('PulseFit Smart Band', 'electronics', 4999, 6999, 28, 'https://images.unsplash.com/photo-1557935728-e6d1eaabe558?auto=format&fit=crop&w=900&q=85', 'Fitness tracking, sleep insights and smart notifications.', 'A lightweight smart band with activity tracking, heart-rate monitoring, phone notifications and a bright color display.', 'TRENDING'),
            ('VoltMax 20,000mAh Power Bank', 'electronics', 4299, 5499, 34, 'https://images.unsplash.com/photo-1609592424754-6e6d0c4e08a3?auto=format&fit=crop&w=900&q=85', 'High-capacity backup power with dual output.', 'Reliable portable charging for phones, earbuds, cameras and other everyday devices.', 'VALUE PICK'),
            ('Luma Desk Lamp Pro', 'home', 3899, 4999, 19, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=85', 'Minimal LED desk lighting with warm-to-cool modes.', 'A modern desk lamp designed for study, work and relaxed evening lighting with adjustable brightness.', 'NEW'),
            ('CloudSoft Cushion Set', 'home', 2799, 3499, 56, 'https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?auto=format&fit=crop&w=900&q=85', 'Soft textured cushions for a cozy living space.', 'A set of premium-feel cushions with durable covers and a neutral palette that fits modern interiors.', ''),
            ('Urban Carry Backpack', 'fashion', 4599, 5999, 31, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=85', 'Clean everyday backpack with laptop compartment.', 'Designed for college, work and day-to-day travel with organized internal storage.', 'POPULAR'),
            ('Everyday Chrono Watch', 'fashion', 6299, 7999, 14, 'https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=900&q=85', 'Classic chronograph look with an everyday profile.', 'A versatile statement watch with a clean dial, comfortable strap and timeless proportions.', ''),
            ('AromaMist Mini Diffuser', 'beauty', 3199, 3999, 22, 'https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=900&q=85', 'Compact home fragrance and ambient mist.', 'A quiet, compact diffuser for bedrooms, desks and relaxing spaces.', 'COZY PICK'),
            ('GlowCare Self-Care Kit', 'beauty', 5499, 6499, 17, 'https://images.unsplash.com/photo-1556229010-6c3f2c9ca5f8?auto=format&fit=crop&w=900&q=85', 'A curated everyday self-care essentials set.', 'A simple giftable collection designed around everyday care routines and thoughtful presentation.', 'GIFT IDEA'),
            ('Nordic Ceramic Mug Pair', 'home', 2199, 2899, 40, 'https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?auto=format&fit=crop&w=900&q=85', 'Two-piece ceramic mug set with a clean silhouette.', 'A durable ceramic pair for tea, coffee and relaxed mornings.', ''),
            ('FlexiPhone Stand', 'accessories', 1699, 2299, 63, 'https://images.unsplash.com/photo-1586953208448-b95a79798f07?auto=format&fit=crop&w=900&q=85', 'Adjustable desk stand for phones and small tablets.', 'A compact stand for video calls, recipes, streaming and desktop organization.', 'LOW STOCK'),
            ('Breeze Travel Bottle', 'accessories', 1899, 2599, 71, 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=85', 'Reusable insulated bottle for everyday carry.', 'A simple insulated bottle designed for commuting, college and travel.', ''),
        ]
        for p in products:
            title, cat, price, compare, stock, image, short, desc, badge = p
            s.add(Product(title=title, slug=slugify(title), category=cat, price=price, compare_price=compare, stock=stock, image_url=image, short_description=short, description=desc, badge=badge, rating=Decimal('4.7'), review_count=97))
    if not s.query(Coupon).filter_by(code='WELCOME10').first():
        s.add(Coupon(code='WELCOME10', percent_off=10))
    if not s.query(User).filter_by(email='admin@homenest.local').first():
        s.add(User(name='HomeNest Admin', email='admin@homenest.local', password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD', 'admin12345')), is_admin=True))
    s.commit()

Base.metadata.create_all(engine)

def ensure_product_media_columns():
    # Lightweight migration for existing SQLite installs.
    if engine.dialect.name != 'sqlite':
        return
    cols = {c['name'] for c in inspect(engine).get_columns('products')}
    with engine.begin() as conn:
        for col in ('image_2','image_3','image_4'):
            if col not in cols:
                conn.execute(text(f'ALTER TABLE products ADD COLUMN {col} VARCHAR(500)'))

ensure_product_media_columns()

def ensure_order_payment_columns():
    # Lightweight SQLite migration for existing local installs.
    if engine.dialect.name != 'sqlite':
        return
    existing = {c['name'] for c in inspect(engine).get_columns('orders')}
    definitions = {
        'payment_status': "VARCHAR(40) NOT NULL DEFAULT 'cod_due'",
        'shipping_payment_status': "VARCHAR(30) NOT NULL DEFAULT 'not_required'",
        'payment_tracker': 'VARCHAR(140)',
        'shipping_payment_reference': 'VARCHAR(140)',
        'payment_verified_at': 'DATETIME',
        'view_token': "VARCHAR(100) NOT NULL DEFAULT ''",
        'stock_committed': 'BOOLEAN NOT NULL DEFAULT 1',
    }
    with engine.begin() as conn:
        for col, definition in definitions.items():
            if col not in existing:
                conn.execute(text(f'ALTER TABLE orders ADD COLUMN {col} {definition}'))
        rows = conn.execute(text("SELECT id, view_token, shipping, payment_status, shipping_payment_status FROM orders")).mappings().all()
        for row in rows:
            token = row['view_token'] or secrets.token_urlsafe(32)
            payment_status = row['payment_status'] or 'cod_due'
            shipping_status = row['shipping_payment_status'] or ('not_required' if Decimal(str(row['shipping'] or 0)) == 0 else 'not_required')
            conn.execute(text("UPDATE orders SET view_token=:token, payment_status=:ps, shipping_payment_status=:sps, stock_committed=1 WHERE id=:id"), {'token': token, 'ps': payment_status, 'sps': shipping_status, 'id': row['id']})

ensure_order_payment_columns()
seed_data()

def ensure_local_seed_media():
    s = db()
    mapping = {
        'AeroBeat Wireless Earbuds':'earbuds.svg','PulseFit Smart Band':'smart-band.svg','VoltMax 20,000mAh Power Bank':'power-bank.svg',
        'Luma Desk Lamp Pro':'desk-lamp.svg','CloudSoft Cushion Set':'cushions.svg','Urban Carry Backpack':'backpack.svg',
        'Everyday Chrono Watch':'watch.svg','AromaMist Mini Diffuser':'diffuser.svg','GlowCare Self-Care Kit':'selfcare.svg',
        'Nordic Ceramic Mug Pair':'mugs.svg','FlexiPhone Stand':'phone-stand.svg','Breeze Travel Bottle':'bottle.svg'
    }
    changed=False
    for title, fn in mapping.items():
        path=f'/static/uploads/{fn}'
        if s.scalar(select(Product).where(Product.title==title, Product.image_url.like('http%'))):
            prod=s.scalar(select(Product).where(Product.title==title))
            if prod and os.path.exists(os.path.join(UPLOAD_DIR,fn)):
                prod.image_url=path
                for slot in (2,3,4):
                    candidate=f'/static/uploads/{os.path.splitext(fn)[0]}-{slot}.svg'
                    if os.path.exists(os.path.join(UPLOAD_DIR, os.path.basename(candidate))):
                        setattr(prod, f'image_{slot}', candidate)
                changed=True
    s.commit() if changed else None
ensure_local_seed_media()

@app.route('/')
def home():
    s = db()
    featured = s.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.badge.desc(), Product.id.desc()).limit(8)).all()
    return render_template('home.html', featured=featured, settings=load_store_settings())

@app.route('/shop')
def shop():
    s = db()
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    sort = request.args.get('sort', 'featured')
    stmt = select(Product).where(Product.active.is_(True))
    if query:
        like = f'%{query}%'
        stmt = stmt.where(or_(Product.title.ilike(like), Product.short_description.ilike(like), Product.category.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    if sort == 'price-low':
        stmt = stmt.order_by(Product.price.asc())
    elif sort == 'price-high':
        stmt = stmt.order_by(Product.price.desc())
    elif sort == 'newest':
        stmt = stmt.order_by(Product.created_at.desc())
    else:
        stmt = stmt.order_by(Product.badge.desc(), Product.id.desc())
    products = s.scalars(stmt).all()
    return render_template('shop.html', products=products, query=query, selected_category=category, selected_sort=sort)

@app.route('/product/<slug>')
def product_detail(slug):
    s = db(); product = s.scalar(select(Product).where(Product.slug == slug, Product.active.is_(True)))
    if not product: abort(404)
    related = s.scalars(select(Product).where(Product.active.is_(True), Product.category == product.category, Product.id != product.id).limit(4)).all()
    return render_template('product.html', product=product, related=related)

@app.post('/cart/add')
def add_to_cart():
    data = request.get_json(silent=True) or request.form
    try: pid = int(data.get('product_id')); qty = max(1, min(int(data.get('quantity', 1)), 99))
    except (ValueError, TypeError): return jsonify(ok=False, message='Invalid product.'), 400
    p = db().get(Product, pid)
    if not p or not p.active: return jsonify(ok=False, message='Product not found.'), 404
    cart = dict(session.get('cart', {})); key = str(pid)
    cart[key] = min(cart.get(key, 0) + qty, p.stock)
    session['cart'] = cart
    return jsonify(ok=True, message=f'{p.title} added to cart.', count=sum(cart.values()))

@app.post('/buy-now')
def buy_now():
    data = request.get_json(silent=True) or request.form
    try:
        pid = int(data.get('product_id')); qty = max(1, min(int(data.get('quantity', 1)), 99))
    except (ValueError, TypeError):
        return jsonify(ok=False, message='Invalid product.'), 400
    p = db().get(Product, pid)
    if not p or not p.active or p.stock <= 0:
        return jsonify(ok=False, message='Product is unavailable.'), 400
    session['cart'] = {str(pid): min(qty, p.stock)}
    session.pop('discount', None); session.pop('coupon_code', None)
    return jsonify(ok=True, url=url_for('checkout'))

@app.route('/cart')
def cart():
    items, subtotal = cart_items()
    settings=load_store_settings()
    discount = Decimal(session.get('discount', '0'))
    threshold=Decimal(settings.get('free_shipping_threshold','5000')); fee=Decimal(settings.get('shipping_fee','250')); shipping = Decimal('0') if subtotal >= threshold else (fee if subtotal else Decimal('0'))
    total = subtotal - discount + shipping
    return render_template('cart.html', items=items, subtotal=subtotal, discount=discount, shipping=shipping, total=total)

@app.post('/cart/update')
def update_cart():
    data = request.get_json(silent=True) or request.form
    cart = dict(session.get('cart', {}))
    try: pid = int(data.get('product_id')); qty = int(data.get('quantity'))
    except (ValueError, TypeError): return jsonify(ok=False), 400
    p = db().get(Product, pid)
    if not p or qty <= 0:
        cart.pop(str(pid), None)
    else:
        cart[str(pid)] = min(qty, p.stock)
    session['cart'] = cart
    return jsonify(ok=True, count=sum(cart.values()))

@app.post('/cart/remove')
def remove_cart():
    data = request.get_json(silent=True) or request.form
    try: pid = int(data.get('product_id'))
    except (ValueError, TypeError): return jsonify(ok=False), 400
    cart = dict(session.get('cart', {})); cart.pop(str(pid), None); session['cart'] = cart
    return jsonify(ok=True, count=sum(cart.values()))

@app.post('/cart/coupon')
def apply_coupon():
    code = ((request.get_json(silent=True) or request.form).get('code') or '').strip().upper()
    s = db(); coupon = s.scalar(select(Coupon).where(Coupon.code == code, Coupon.active.is_(True)))
    if not coupon:
        session.pop('discount', None); session.pop('coupon_code', None)
        return jsonify(ok=False, message='Coupon not found.')
    items, subtotal = cart_items()
    discount = (subtotal * Decimal(coupon.percent_off) / Decimal('100')).quantize(Decimal('0.01'))
    session['discount'] = str(discount); session['coupon_code'] = coupon.code
    return jsonify(ok=True, message=f'{coupon.code} applied.', discount=float(discount))


def public_base_url():
    return os.getenv('PUBLIC_BASE_URL', 'http://127.0.0.1:5000').rstrip('/')

def safepay_is_configured():
    return bool(os.getenv('SAFEPAY_API_KEY'))

def safepay_client():
    if not safepay_is_configured():
        raise RuntimeError('Safepay is not configured. Add SAFEPAY_API_KEY to .env.')
    from safepay_python.safepay import Safepay
    return Safepay({
        'environment': os.getenv('SAFEPAY_ENV', 'sandbox'),
        'apiKey': os.getenv('SAFEPAY_API_KEY', ''),
        'v1Secret': os.getenv('SAFEPAY_V1_SECRET', ''),
        'webhookSecret': os.getenv('SAFEPAY_WEBHOOK_SECRET', ''),
    })

def build_shipping_payment_url(order):
    env = safepay_client()
    amount = int((Decimal(order.shipping) * Decimal('100')).quantize(Decimal('1')))
    response = env.set_payment_details({'amount': amount, 'currency': 'PKR'})
    payload = response.get('data', {}) if isinstance(response, dict) else {}
    tracker = payload.get('token') if isinstance(payload, dict) else None
    if not tracker:
        raise RuntimeError('Safepay did not return a payment tracker.')
    order.payment_tracker = tracker
    env_name = os.getenv('SAFEPAY_ENV', 'sandbox')
    redirect_url = f"{public_base_url()}/payment/safepay/success"
    cancel_url = f"{public_base_url()}/payment/safepay/cancel?order={order.order_number}&token={order.view_token}"
    checkout_url = env.get_checkout_url({
        'beacon': tracker,
        'orderId': order.order_number,
        'source': 'custom',
        'cancelUrl': cancel_url,
        'redirectUrl': redirect_url,
        'webhooks': True,
    })
    return checkout_url

def _commit_order_stock(order, s):
    if order.stock_committed:
        return True
    for item in order.items:
        product = s.get(Product, item.product_id)
        if not product or not product.active or product.stock < item.quantity:
            return False
    for item in order.items:
        product = s.get(Product, item.product_id)
        product.stock -= item.quantity
    order.stock_committed = True
    return True

def mark_shipping_payment_paid(order, reference=None, tracker=None):
    s = db()
    fresh = s.get(Order, order.id)
    if not fresh:
        return False
    if fresh.shipping_payment_status == 'paid':
        return True
    if tracker and fresh.payment_tracker and tracker != fresh.payment_tracker:
        return False
    if not _commit_order_stock(fresh, s):
        fresh.status = 'Payment Issue'
        fresh.payment_status = 'payment_stock_check_failed'
        s.commit()
        return False
    fresh.shipping_payment_status = 'paid'
    fresh.payment_status = 'shipping_paid_cod'
    fresh.payment_method = 'cod_shipping_prepay'
    fresh.shipping_payment_reference = reference or fresh.shipping_payment_reference or tracker or 'safepay'
    fresh.payment_verified_at = datetime.now(timezone.utc)
    fresh.status = 'Pending'
    s.commit()
    return True

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    items, subtotal = cart_items()
    if not items:
        flash('Your cart is empty.', 'info'); return redirect(url_for('shop'))
    discount = Decimal(session.get('discount', '0'))
    settings = load_store_settings()
    threshold = Decimal(settings.get('free_shipping_threshold','5000'))
    fee = Decimal(settings.get('shipping_fee','250'))
    shipping = Decimal('0') if subtotal >= threshold else fee
    total = subtotal - discount + shipping
    prepay_enabled = bool(settings.get('cod_shipping_prepay_enabled', True)) and shipping > 0 and safepay_is_configured()
    full_cod_enabled = bool(settings.get('cod_enabled', True))
    if request.method == 'POST':
        f = request.form
        method = f.get('payment_method', 'cod_shipping_prepay' if prepay_enabled else 'cod')
        if method == 'cod_shipping_prepay' and not prepay_enabled:
            flash('Online delivery-fee payment is not configured yet. Please choose another method or ask the store administrator to configure Safepay.', 'error')
            return render_template('checkout.html', items=items, subtotal=subtotal, discount=discount, shipping=shipping, total=total, prepay_enabled=prepay_enabled, full_cod_enabled=full_cod_enabled, gateway_configured=safepay_is_configured())
        if method == 'cod' and not full_cod_enabled and not (shipping == 0 and prepay_enabled):
            flash('Full Cash on Delivery is currently unavailable.', 'error')
            return redirect(url_for('checkout'))
        name, email, phone, address, city = [f.get(k, '').strip() for k in ('name','email','phone','address','city')]
        if not all([name, email, phone, address, city]) or '@' not in email:
            flash('Please complete all required checkout fields.', 'error')
            return render_template('checkout.html', items=items, subtotal=subtotal, discount=discount, shipping=shipping, total=total, prepay_enabled=prepay_enabled, full_cod_enabled=full_cod_enabled, gateway_configured=safepay_is_configured())
        s = db()
        fresh_items = []
        for item in items:
            p = s.get(Product, item['product'].id)
            if not p or p.stock < item['quantity']:
                flash(f"Not enough stock for {item['product'].title}.", 'error')
                return redirect(url_for('cart'))
            fresh_items.append((p, item['quantity']))
        order_no = 'HN' + datetime.now(timezone.utc).strftime('%y%m%d') + secrets.token_hex(3).upper()
        requires_shipping_payment = method == 'cod_shipping_prepay' and shipping > 0
        order = Order(
            order_number=order_no,
            user_id=g.current_user.id if g.current_user else None,
            customer_name=name, email=email, phone=phone, address=address, city=city, notes=f.get('notes','').strip(),
            subtotal=subtotal, discount=discount, shipping=shipping, total=total,
            payment_method='cod_shipping_prepay' if requires_shipping_payment else 'cod',
            payment_status='shipping_payment_pending' if requires_shipping_payment else 'cod_due',
            shipping_payment_status='pending' if requires_shipping_payment else ('not_required' if shipping == 0 else 'unpaid'),
            view_token=secrets.token_urlsafe(32), stock_committed=not requires_shipping_payment,
            status='Payment Pending' if requires_shipping_payment else 'Pending',
        )
        s.add(order); s.flush()
        for p, qty in fresh_items:
            order.items.append(OrderItem(product_id=p.id, product_title=p.title, unit_price=p.price, quantity=qty, image_url=p.image_url))
            if not requires_shipping_payment:
                p.stock -= qty
        if requires_shipping_payment:
            try:
                checkout_url = build_shipping_payment_url(order)
            except Exception as exc:
                s.rollback()
                flash(f'Online delivery payment could not be started: {exc}', 'error')
                return redirect(url_for('checkout'))
            s.commit()
            session['pending_order_id'] = order.id
            return redirect(checkout_url)
        s.commit()
        session['cart'] = {}; session.pop('discount', None); session.pop('coupon_code', None)
        session['last_order_token'] = order.view_token
        session.pop('pending_order_id', None)
        return redirect(url_for('order_success', order_number=order.order_number))
    return render_template('checkout.html', items=items, subtotal=subtotal, discount=discount, shipping=shipping, total=total, prepay_enabled=prepay_enabled, full_cod_enabled=full_cod_enabled, gateway_configured=safepay_is_configured())

@app.route('/payment/safepay/success', methods=['GET','POST'])
def safepay_success():
    order_no = request.values.get('order_id') or request.values.get('orderId')
    tracker = request.values.get('tracker') or request.values.get('token')
    sig = request.values.get('sig')
    reference = request.values.get('ref')
    if not order_no:
        flash('The payment response did not include an order reference.', 'error')
        return redirect(url_for('shop'))
    s = db(); order = s.scalar(select(Order).where(Order.order_number == order_no))
    if not order: abort(404)
    if not ((g.current_user and order.user_id == g.current_user.id) or session.get('pending_order_id') == order.id or session.get('last_order_token') == order.view_token):
        abort(404)
    if order.shipping_payment_status == 'paid':
        return redirect(url_for('order_success', order_number=order.order_number))
    valid = False
    try:
        if sig and tracker and safepay_is_configured():
            valid = bool(safepay_client().is_signature_valid({'sig': sig, 'tracker': tracker}))
    except Exception:
        valid = False
    if valid and (not order.payment_tracker or tracker == order.payment_tracker):
        mark_shipping_payment_paid(order, reference=reference, tracker=tracker)
        session['cart'] = {}; session.pop('discount', None); session.pop('coupon_code', None); session['last_order_token'] = order.view_token; session.pop('pending_order_id', None)
        return redirect(url_for('order_success', order_number=order.order_number))
    return render_template('payment_pending.html', order=order, payment_returned=True)

@app.route('/payment/safepay/cancel')
def safepay_cancel():
    order_no = request.args.get('order','')
    token = request.args.get('token','')
    s = db(); order = s.scalar(select(Order).where(Order.order_number == order_no, Order.view_token == token)) if order_no and token else None
    if not order: abort(404)
    return render_template('payment_pending.html', order=order, payment_returned=False, cancelled=True)

@app.post('/webhooks/safepay')
def safepay_webhook():
    if not safepay_is_configured():
        return jsonify(ok=False), 503
    payload = request.get_json(silent=True) or {}
    signature = request.headers.get('x-sfpy-signature') or request.headers.get('X-SFPY-SIGNATURE')
    try:
        valid = bool(safepay_client().is_webhook_valid({'x-sfpy-signature': signature or ''}, {'data': payload}))
    except Exception:
        valid = False
    if not valid:
        return jsonify(ok=False, error='invalid signature'), 400
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        data = payload
    def find_value(obj, keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, (str, int)):
                    return str(v)
                found = find_value(v, keys)
                if found: return found
        elif isinstance(obj, list):
            for v in obj:
                found = find_value(v, keys)
                if found: return found
        return None
    order_no = find_value(data, {'order_id','orderId'})
    tracker = find_value(data, {'tracker','token'})
    reference = find_value(data, {'ref','reference','transaction_id','transactionId'})
    event_name = (find_value(data, {'event','eventName','type'}) or '').lower()
    if not order_no:
        return jsonify(ok=True)
    s = db(); order = s.scalar(select(Order).where(Order.order_number == order_no))
    if not order:
        return jsonify(ok=True)
    success_event = any(flag in event_name for flag in ('succeed','success','paid','captur')) or not event_name
    if success_event:
        ok = mark_shipping_payment_paid(order, reference=reference, tracker=tracker)
        return jsonify(ok=ok)
    return jsonify(ok=True)

@app.route('/order/success/<order_number>')
def order_success(order_number):
    s = db(); order = s.scalar(select(Order).where(Order.order_number == order_number))
    if not order: abort(404)
    allowed = False
    if g.current_user and order.user_id == g.current_user.id:
        allowed = True
    elif session.get('last_order_token') == order.view_token:
        allowed = True
    elif session.get('pending_order_id') == order.id:
        allowed = True
    if not allowed:
        abort(404)
    return render_template('order_success.html', order=order)

@app.route('/register', methods=['GET','POST'])
def register():
    if g.current_user: return redirect(url_for('account'))
    if request.method == 'POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); pw=request.form.get('password','')
        if len(name)<2 or '@' not in email or len(pw)<8:
            flash('Enter a valid name, email and an 8+ character password.', 'error')
        elif db().scalar(select(User).where(User.email==email)):
            flash('An account with that email already exists.', 'error')
        else:
            s=db(); u=User(name=name,email=email,password_hash=generate_password_hash(pw)); s.add(u); s.commit(); session.clear(); session['user_id']=u.id; flash('Welcome to HomeNest.', 'success'); return redirect(url_for('account'))
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if g.current_user: return redirect(url_for('account'))
    if request.method == 'POST':
        email=request.form.get('email','').strip().lower(); pw=request.form.get('password','')
        u=db().scalar(select(User).where(User.email==email))
        if not u or not check_password_hash(u.password_hash,pw):
            flash('Invalid email or password.', 'error')
        else:
            session.clear(); session['user_id']=u.id; session['csrf_token']=secrets.token_urlsafe(24)
            next_url=request.args.get('next') or request.form.get('next') or url_for('account')
            return redirect(next_url if next_url.startswith('/') else url_for('account'))
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear(); flash('You have been signed out.', 'info'); return redirect(url_for('home'))

@app.route('/account')
@login_required
def account():
    s=db(); orders=s.scalars(select(Order).where(Order.user_id==g.current_user.id).order_by(Order.created_at.desc())).all()
    return render_template('account.html', orders=orders)

@app.route('/about')
def about(): return render_template('simple.html', page_title='About HomeNest', content_title='Thoughtful products. Better everyday living.', paragraphs=['HomeNest Store is a modern multi-category store focused on practical products for home, lifestyle, accessories, electronics and personal care.','The storefront is built for fast browsing, clear product information and a low-friction checkout experience.'])

@app.route('/contact')
def contact(): return render_template('simple.html', page_title='Contact', content_title='We’re here to help.', paragraphs=['For order questions, product help or general support, email support@homenest.local.','For a real deployment, replace this placeholder address with your business email and add your preferred phone / WhatsApp support channel.'])

# Admin
ADMIN_STATUSES = ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled')
ADMIN_SETTINGS_FILE = os.path.join(BASE_DIR, 'store_settings.json')
ALLOWED_IMAGE_EXTENSIONS = {'png','jpg','jpeg','webp','gif','svg'}


def save_upload(file_storage, prefix):
    if not file_storage or not file_storage.filename:
        return ''
    raw = secure_filename(file_storage.filename)
    ext = raw.rsplit('.', 1)[-1].lower() if '.' in raw else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Use PNG, JPG, JPEG, WEBP, GIF or SVG images.')
    filename = f"{prefix}-{secrets.token_hex(5)}.{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, filename))
    return f"/static/uploads/{filename}"

def load_store_settings():
    defaults = {
        'store_name': 'HomeNest Store',
        'logo_path': '/static/uploads/homenest-logo.png',
        'favicon_path': '/static/uploads/homenest-logo.png',
        'support_email': 'support@homenest.local',
        'support_phone': '+92 300 0000000',
        'free_shipping_threshold': '5000',
        'shipping_fee': '250',
        'currency_symbol': '₨',
        'cod_enabled': True,
        'cod_shipping_prepay_enabled': True,
        'store_notice': 'Free delivery on orders over ₨5,000',
        'hero_kicker': 'Curated for everyday life',
        'hero_title': 'Good design. Useful things.',
        'hero_text': 'Discover smart electronics, home upgrades, style essentials and feel-good finds — selected to make everyday life a little better.',
        'promo_title': 'Better finds, occasionally.',
        'promo_text': 'Get useful product drops and special offers without the spammy feeling.',
        'hero_image': '/static/uploads/hero-default.svg',
        'footer_text': 'Thoughtful finds for modern everyday living — from useful tech to cozy home upgrades.',
    }
    try:
        with open(ADMIN_SETTINGS_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            defaults.update(data)
    except (OSError, ValueError):
        pass
    # Upgrade the built-in logo reference from earlier HomeNest builds.
    if defaults.get('logo_path') in {'/static/uploads/homenest-logo.svg', '', None}:
        defaults['logo_path'] = '/static/uploads/homenest-logo.png'
    if defaults.get('favicon_path') in {'/static/uploads/homenest-logo.svg', '', None}:
        defaults['favicon_path'] = '/static/uploads/homenest-favicon.png'
    return defaults


def save_store_settings(settings):
    with open(ADMIN_SETTINGS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)


def admin_audit(action, detail=''):
    """Small local audit trail without adding a new DB migration requirement."""
    path = os.path.join(BASE_DIR, 'admin_activity.log')
    try:
        stamp = datetime.now(timezone.utc).isoformat()
        actor = getattr(g.current_user, 'email', 'unknown')
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'time': stamp, 'actor': actor, 'action': action, 'detail': detail}, ensure_ascii=False) + '\n')
    except OSError:
        pass


def parse_page(default=1):
    try:
        return max(1, int(request.args.get('page', default)))
    except (TypeError, ValueError):
        return default


@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if g.current_user and g.current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        admin_email = 'admin@homenest.local'
        if username == os.getenv('ADMIN_USERNAME','admin'):
            u = db().scalar(select(User).where(User.email == admin_email))
            if u and u.is_admin and check_password_hash(u.password_hash, password):
                session.clear()
                session['user_id'] = u.id
                session['csrf_token'] = secrets.token_urlsafe(24)
                admin_audit('admin_login')
                return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'error')
    return render_template('admin_login.html')


@app.route('/admin')
@admin_required
def admin_dashboard():
    s = db()
    now = datetime.now(timezone.utc)
    period = request.args.get('period', '30')
    days = 7 if period == '7' else 90 if period == '90' else 30
    since = now - timedelta(days=days)

    orders = s.scalars(select(Order).order_by(Order.created_at.desc()).limit(8)).all()
    products = s.scalars(select(Product).order_by(Product.stock.asc(), Product.id.desc())).all()
    revenue = s.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != 'Cancelled')) or 0
    period_revenue = s.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != 'Cancelled', Order.created_at >= since)) or 0
    customers = s.scalar(select(func.count(User.id)).where(User.is_admin.is_(False))) or 0
    pending = s.scalar(select(func.count(Order.id)).where(Order.status == 'Pending')) or 0
    processing = s.scalar(select(func.count(Order.id)).where(Order.status == 'Processing')) or 0
    low_stock = s.scalar(select(func.count(Product.id)).where(Product.stock <= 10, Product.active.is_(True))) or 0
    out_stock = s.scalar(select(func.count(Product.id)).where(Product.stock <= 0, Product.active.is_(True))) or 0
    order_count = s.scalar(select(func.count(Order.id)).where(Order.status != 'Cancelled', Order.created_at >= since)) or 0
    avg_order = (Decimal(period_revenue) / order_count) if order_count else Decimal('0')

    daily = []
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).date()
        start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        amount = s.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != 'Cancelled', Order.created_at >= start, Order.created_at < end)) or 0
        daily.append({'label': d.strftime('%d %b'), 'value': float(amount)})
    max_value = max([x['value'] for x in daily] or [1])
    for x in daily:
        x['height'] = round((x['value'] / max_value) * 100, 2) if max_value else 0

    category_rows = s.query(Product.category, func.count(Product.id)).filter(Product.active.is_(True)).group_by(Product.category).order_by(func.count(Product.id).desc()).all()
    active_count = s.scalar(select(func.count(Product.id)).where(Product.active.is_(True))) or 0
    status_counts = {status: s.scalar(select(func.count(Order.id)).where(Order.status == status)) or 0 for status in ADMIN_STATUSES}
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_orders = s.scalar(select(func.count(Order.id)).where(Order.created_at >= today_start)) or 0
    today_revenue = s.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != 'Cancelled', Order.created_at >= today_start)) or 0
    inventory_value = s.scalar(select(func.coalesce(func.sum(Product.price * Product.stock), 0)).where(Product.active.is_(True))) or 0
    top_products = []
    rows = s.query(OrderItem.product_title, func.sum(OrderItem.quantity).label('qty'), func.sum(OrderItem.unit_price * OrderItem.quantity).label('sales')).join(Order, Order.id == OrderItem.order_id).filter(Order.status != 'Cancelled').group_by(OrderItem.product_title).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    for name, qty, sales in rows:
        top_products.append({'name': name, 'qty': int(qty or 0), 'sales': sales or 0})
    return render_template('admin_dashboard.html', orders=orders, products=products[:10], revenue=revenue,
                           period_revenue=period_revenue, customers=customers, pending=pending,
                           processing=processing, low_stock=low_stock, out_stock=out_stock,
                           avg_order=avg_order, order_count=order_count, active_count=active_count,
                           daily=daily, period=days, category_rows=category_rows,
                           status_counts=status_counts, today_orders=today_orders, today_revenue=today_revenue,
                           inventory_value=inventory_value, top_products=top_products,
                           settings=load_store_settings())


@app.route('/admin/orders')
@admin_required
def admin_orders():
    s = db(); page = parse_page(); per_page = 15
    q = request.args.get('q','').strip(); status = request.args.get('status','').strip()
    stmt = select(Order).order_by(Order.created_at.desc())
    if q:
        like = f'%{q}%'
        stmt = stmt.where(or_(Order.order_number.ilike(like), Order.customer_name.ilike(like), Order.email.ilike(like), Order.phone.ilike(like)))
    if status in ADMIN_STATUSES:
        stmt = stmt.where(Order.status == status)
    total = s.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    orders = s.scalars(stmt.offset((page-1)*per_page).limit(per_page)).all()
    pages = max(1, (total + per_page - 1)//per_page)
    return render_template('admin_orders.html', orders=orders, q=q, status=status, page=page, pages=pages, total=total, statuses=ADMIN_STATUSES)


@app.post('/admin/orders/<int:oid>/status')
@admin_required
def admin_order_status(oid):
    s = db(); o = s.get(Order, oid)
    if not o: abort(404)
    status = request.form.get('status','Pending')
    if status not in ADMIN_STATUSES: abort(400)
    old = o.status; o.status = status; s.commit()
    admin_audit('order_status', f'{o.order_number}: {old} -> {status}')
    flash(f'{o.order_number} updated to {status}.', 'success')
    next_url = request.form.get('next') or url_for('admin_orders')
    return redirect(next_url if next_url.startswith('/') else url_for('admin_orders'))


@app.route('/admin/orders/<int:oid>')
@admin_required
def admin_order_detail(oid):
    s = db(); order = s.get(Order, oid)
    if not order: abort(404)
    return render_template('admin_order_detail.html', order=order, statuses=ADMIN_STATUSES)


@app.route('/admin/products', methods=['GET','POST'])
@admin_required
def admin_products():
    s = db()
    if request.method == 'POST':
        f = request.form; title = f.get('title','').strip(); price = f.get('price','').strip()
        try:
            price_d = Decimal(price); stock = int(f.get('stock','0'))
            compare = Decimal(f.get('compare_price') or price_d)
        except (InvalidOperation, ValueError):
            flash('Invalid price or stock.', 'error'); return redirect(url_for('admin_products'))
        if not title or price_d < 0 or stock < 0:
            flash('Enter a valid title, price and stock.', 'error')
        else:
            base_slug = slugify(title); slug = base_slug; n = 2
            while s.scalar(select(Product).where(Product.slug == slug)):
                slug = f'{base_slug}-{n}'; n += 1
            media=[]
            for key in ('image_file','image_file_2','image_file_3','image_file_4'):
                up=request.files.get(key)
                media.append(save_upload(up, 'product') if up and up.filename else None)
            primary = media[0] or '/static/uploads/product-default.svg'
            s.add(Product(title=title, slug=slug, category=f.get('category','home').strip() or 'home', price=price_d,
                          compare_price=compare, stock=stock, image_url=primary, image_2=media[1], image_3=media[2], image_4=media[3],
                          short_description=f.get('short_description','').strip(), description=f.get('description','').strip(),
                          badge=f.get('badge','NEW').strip(), rating=Decimal('4.8'), review_count=0, active=True))
            s.commit(); admin_audit('product_created', title); flash('Product added.', 'success')
        return redirect(url_for('admin_products'))

    q = request.args.get('q','').strip(); cat = request.args.get('category','').strip(); stock_filter = request.args.get('stock','').strip(); page = parse_page(); per_page = 20
    stmt = select(Product).order_by(Product.id.desc())
    if q:
        like = f'%{q}%'; stmt = stmt.where(or_(Product.title.ilike(like), Product.slug.ilike(like), Product.category.ilike(like)))
    if cat: stmt = stmt.where(Product.category == cat)
    if stock_filter == 'low': stmt = stmt.where(Product.stock.between(1,10))
    elif stock_filter == 'out': stmt = stmt.where(Product.stock <= 0)
    elif stock_filter == 'active': stmt = stmt.where(Product.active.is_(True))
    elif stock_filter == 'inactive': stmt = stmt.where(Product.active.is_(False))
    total = s.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    products = s.scalars(stmt.offset((page-1)*per_page).limit(per_page)).all()
    pages = max(1, (total + per_page - 1)//per_page)
    categories = [r[0] for r in s.query(Product.category).distinct().order_by(Product.category).all()]
    stats = {
        'all': s.scalar(select(func.count(Product.id))) or 0,
        'active': s.scalar(select(func.count(Product.id)).where(Product.active.is_(True))) or 0,
        'low': s.scalar(select(func.count(Product.id)).where(Product.active.is_(True), Product.stock.between(1,10))) or 0,
        'out': s.scalar(select(func.count(Product.id)).where(Product.active.is_(True), Product.stock <= 0)) or 0,
    }
    return render_template('admin_products.html', products=products, q=q, category=cat, stock_filter=stock_filter,
                           categories=categories, page=page, pages=pages, total=total, stats=stats)


@app.post('/admin/products/<int:pid>/edit')
@admin_required
def admin_product_edit(pid):
    s = db(); p = s.get(Product,pid)
    if not p: abort(404)
    f = request.form
    try:
        p.price = Decimal(f.get('price','0')); p.compare_price = Decimal(f.get('compare_price') or p.price); p.stock = max(0, int(f.get('stock','0')))
    except (InvalidOperation, ValueError):
        flash('Invalid price or stock.', 'error'); return redirect(url_for('admin_products'))
    p.title = f.get('title',p.title).strip() or p.title
    p.category = f.get('category',p.category).strip() or p.category
    for key, attr in [('image_file','image_url'),('image_file_2','image_2'),('image_file_3','image_3'),('image_file_4','image_4')]:
        uploaded = request.files.get(key)
        if uploaded and uploaded.filename:
            try: setattr(p, attr, save_upload(uploaded, 'product'))
            except ValueError as exc: flash(str(exc), 'error'); return redirect(request.form.get('next') or url_for('admin_products'))
    p.short_description = f.get('short_description',p.short_description).strip()
    p.description = f.get('description',p.description).strip(); p.badge = f.get('badge',p.badge).strip(); p.active = (f.get('active') == 'on')
    s.commit(); admin_audit('product_updated', f'{p.id}:{p.title}'); flash('Product updated.', 'success')
    return redirect(request.form.get('next') or url_for('admin_products'))


@app.post('/admin/products/<int:pid>/stock')
@admin_required
def admin_product_stock(pid):
    s = db(); p = s.get(Product, pid)
    if not p: abort(404)
    try: delta = int(request.form.get('delta','0'))
    except ValueError: abort(400)
    if abs(delta) > 100000: abort(400)
    old = p.stock; p.stock = max(0, old + delta); s.commit(); admin_audit('stock_adjustment', f'{p.title}: {old} -> {p.stock}')
    flash(f'Stock updated: {old} → {p.stock}.', 'success')
    return redirect(request.form.get('next') or url_for('admin_products'))


@app.post('/admin/products/<int:pid>/delete')
@admin_required
def admin_product_delete(pid):
    s = db(); p = s.get(Product,pid)
    if p:
        title=p.title; s.delete(p); s.commit(); admin_audit('product_deleted', title); flash('Product deleted.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/customers')
@admin_required
def admin_customers():
    s = db(); q = request.args.get('q','').strip(); page = parse_page(); per_page = 20
    stmt = select(User).where(User.is_admin.is_(False)).order_by(User.created_at.desc())
    if q:
        like=f'%{q}%'; stmt=stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    total=s.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users=s.scalars(stmt.offset((page-1)*per_page).limit(per_page)).all()
    rows=[]
    for u in users:
        count=s.scalar(select(func.count(Order.id)).where(Order.user_id==u.id)) or 0
        spent=s.scalar(select(func.coalesce(func.sum(Order.total),0)).where(Order.user_id==u.id, Order.status!='Cancelled')) or 0
        rows.append((u,count,spent))
    pages=max(1,(total+per_page-1)//per_page)
    return render_template('admin_customers.html', customers=rows, q=q, page=page, pages=pages, total=total)


@app.route('/admin/customers/<int:uid>')
@admin_required
def admin_customer_detail(uid):
    s=db(); user=s.get(User,uid)
    if not user or user.is_admin: abort(404)
    orders=s.scalars(select(Order).where(Order.user_id==uid).order_by(Order.created_at.desc())).all()
    spent=s.scalar(select(func.coalesce(func.sum(Order.total),0)).where(Order.user_id==uid,Order.status!='Cancelled')) or 0
    return render_template('admin_customer_detail.html', user=user, orders=orders, spent=spent)


@app.route('/admin/coupons', methods=['GET','POST'])
@admin_required
def admin_coupons():
    s=db()
    if request.method=='POST':
        code=request.form.get('code','').strip().upper(); raw=request.form.get('percent_off','0')
        try: pct=Decimal(raw)
        except InvalidOperation: pct=Decimal('0')
        if not re.fullmatch(r'[A-Z0-9_-]{3,40}',code) or pct<=0 or pct>100:
            flash('Use a valid coupon code and discount from 0.01 to 100%.','error')
        elif s.scalar(select(Coupon).where(Coupon.code==code)):
            flash('That coupon code already exists.','error')
        else:
            s.add(Coupon(code=code,percent_off=pct,active=True)); s.commit(); admin_audit('coupon_created',code); flash('Coupon created.','success')
        return redirect(url_for('admin_coupons'))
    coupons=s.scalars(select(Coupon).order_by(Coupon.id.desc())).all()
    return render_template('admin_coupons.html', coupons=coupons)


@app.post('/admin/coupons/<int:cid>/toggle')
@admin_required
def admin_coupon_toggle(cid):
    s=db(); c=s.get(Coupon,cid)
    if not c: abort(404)
    c.active=not c.active; s.commit(); admin_audit('coupon_toggle',f'{c.code}:{c.active}'); flash(f'{c.code} is now {"active" if c.active else "paused"}.','success')
    return redirect(url_for('admin_coupons'))


@app.post('/admin/coupons/<int:cid>/delete')
@admin_required
def admin_coupon_delete(cid):
    s=db(); c=s.get(Coupon,cid)
    if c: code=c.code; s.delete(c); s.commit(); admin_audit('coupon_deleted',code); flash('Coupon deleted.','success')
    return redirect(url_for('admin_coupons'))


@app.route('/admin/settings', methods=['GET','POST'])
@admin_required
def admin_settings():
    settings=load_store_settings()
    if request.method=='POST':
        try: threshold=Decimal(request.form.get('free_shipping_threshold','5000'))
        except InvalidOperation: threshold=Decimal('5000')
        try:
            logo = save_upload(request.files.get('logo_file'), 'logo') if request.files.get('logo_file') else settings.get('logo_path','')
            hero = save_upload(request.files.get('hero_file'), 'hero') if request.files.get('hero_file') else settings.get('hero_image','')
        except ValueError as exc:
            flash(str(exc), 'error'); return redirect(url_for('admin_settings'))
        settings.update({
            'store_name': request.form.get('store_name','HomeNest Store').strip() or 'HomeNest Store',
            'logo_path': logo or '/static/uploads/homenest-logo.png',
            'favicon_path': logo or '/static/uploads/homenest-logo.png',
            'hero_image': hero,
            'support_email': request.form.get('support_email','').strip(),
            'support_phone': request.form.get('support_phone','').strip(),
            'free_shipping_threshold': str(max(0, threshold)),
            'shipping_fee': request.form.get('shipping_fee','250').strip() or '250',
            'currency_symbol': request.form.get('currency_symbol','₨').strip() or '₨',
            'cod_enabled': request.form.get('cod_enabled') == 'on',
            'cod_shipping_prepay_enabled': request.form.get('cod_shipping_prepay_enabled') == 'on',
            'store_notice': request.form.get('store_notice','').strip(),
            'hero_kicker': request.form.get('hero_kicker','').strip() or 'Curated for everyday life',
            'hero_title': request.form.get('hero_title','').strip() or 'Good design. Useful things.',
            'hero_text': request.form.get('hero_text','').strip(),
            'promo_title': request.form.get('promo_title','').strip() or 'Better finds, occasionally.',
            'promo_text': request.form.get('promo_text','').strip(),
            'footer_text': request.form.get('footer_text','').strip(),
        })
        save_store_settings(settings); admin_audit('store_settings_updated'); flash('Store settings saved.','success')
        return redirect(url_for('admin_settings'))
    return render_template('admin_settings.html', settings=settings, safepay_configured=safepay_is_configured(), safepay_env=os.getenv('SAFEPAY_ENV','sandbox'))


@app.route('/admin/security', methods=['GET','POST'])
@admin_required
def admin_security():
    if request.method=='POST':
        current=request.form.get('current_password',''); new=request.form.get('new_password',''); confirm=request.form.get('confirm_password','')
        if not check_password_hash(g.current_user.password_hash,current): flash('Current password is incorrect.','error')
        elif len(new)<10: flash('Use a password of at least 10 characters.','error')
        elif new!=confirm: flash('New passwords do not match.','error')
        else:
            s=db(); g.current_user.password_hash=generate_password_hash(new); s.commit(); admin_audit('admin_password_changed'); session['csrf_token']=secrets.token_urlsafe(24); flash('Admin password changed.','success')
        return redirect(url_for('admin_security'))
    return render_template('admin_security.html')


@app.route('/admin/export/<kind>.csv')
@admin_required
def admin_export(kind):
    s=db(); out=io.StringIO(); writer=csv.writer(out)
    if kind=='orders':
        writer.writerow(['Order','Date','Customer','Email','Phone','City','Subtotal','Discount','Shipping','Total','Payment','Status'])
        for o in s.scalars(select(Order).order_by(Order.created_at.desc())).all():
            writer.writerow([o.order_number, o.created_at.isoformat(), o.customer_name, o.email, o.phone, o.city, o.subtotal, o.discount, o.shipping, o.total, o.payment_method, o.status])
    elif kind=='products':
        writer.writerow(['ID','Title','Category','Price','Compare Price','Stock','Active','Created'])
        for p in s.scalars(select(Product).order_by(Product.id)).all():
            writer.writerow([p.id,p.title,p.category,p.price,p.compare_price,p.stock,p.active,p.created_at.isoformat()])
    elif kind=='customers':
        writer.writerow(['ID','Name','Email','Joined','Orders'])
        for u in s.scalars(select(User).where(User.is_admin.is_(False)).order_by(User.id)).all():
            count=s.scalar(select(func.count(Order.id)).where(Order.user_id==u.id)) or 0
            writer.writerow([u.id,u.name,u.email,u.created_at.isoformat(),count])
    else:
        abort(404)
    admin_audit('export',kind)
    response=app.response_class(out.getvalue(),mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition']=f'attachment; filename=homenest_{kind}_{datetime.now().strftime("%Y%m%d")}.csv'
    return response


@app.route('/api/search')
def api_search():
    q=request.args.get('q','').strip()
    if not q: return jsonify(results=[])
    s=db(); like=f'%{q}%'; ps=s.scalars(select(Product).where(Product.active.is_(True), or_(Product.title.ilike(like), Product.category.ilike(like))).limit(6)).all()
    return jsonify(results=[{'title':p.title,'price':float(p.price),'url':url_for('product_detail',slug=p.slug),'image':p.image_url} for p in ps])

@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404

if __name__ == '__main__':
    from waitress import serve
    # Waitress is used even locally so the run experience is closer to a deployable WSGI app.
    serve(app, host='127.0.0.1', port=int(os.getenv('PORT','5000')))
