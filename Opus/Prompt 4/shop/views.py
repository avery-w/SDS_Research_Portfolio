import json
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import chat, shipping
from .forms import (AccountForm, AddressForm, CheckoutForm, ImageForm, MessageForm, ProductForm, ReturnForm,
                    ShipForm, SignupForm, StoreForm)
from .models import CartItem, Message, Order, OrderItem, Product, ProductImage, SiteSettings, Store, User

S = Order.Status


# ---------- helpers ----------

def client_ip(request):
    # Caddy overwrites X-Forwarded-For with the real client IP, so the last hop is trustworthy.
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.rsplit(",", 1)[-1].strip() if xff else request.META.get("REMOTE_ADDR", "")


def hit(key, limit, window=60):
    """Count one hit on `key`; True when over `limit` within `window` seconds."""
    key = f"rl:{key}"
    cache.add(key, 0, window)
    try:
        return cache.incr(key) > limit
    except ValueError:  # expired between add and incr
        return False


def who(request):
    return f"u{request.user.pk}" if request.user.is_authenticated else client_ip(request)


def seller_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != User.Role.SELLER:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def site_context(request):
    ctx = {"site": SiteSettings.load()}
    if request.user.is_authenticated:
        ctx["cart_count"] = request.user.cart.aggregate(n=Sum("quantity"))["n"] or 0
        ctx["unread"] = request.user.received_messages.filter(read=False).count()
    return ctx


def json_body(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


RESTOCK = {S.CANCELLED, S.RETURNED}


def transition(orders, pk, frm, to, **fields):
    """Atomically move one order from a status in `frm` to `to`, restocking when needed.

    The status filter in the UPDATE makes double-submits and races no-ops.
    """
    with transaction.atomic():
        n = orders.filter(pk=pk, status__in=frm).update(status=to, updated=timezone.now(), **fields)
        if n and to in RESTOCK:
            for item in OrderItem.objects.filter(order_id=pk):
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    return bool(n)


# ---------- auth & account ----------

class RateLimitedLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "").lower()[:150]
        if hit(f"login-ip:{client_ip(request)}", 20, 300) | hit(f"login-user:{username}", 10, 300):
            messages.error(request, "Too many login attempts. Try again in a few minutes.")
            return render(request, self.template_name, {"form": self.get_form_class()(request)}, status=429)
        return super().post(request, *args, **kwargs)


def signup(request):
    if request.method == "POST" and hit(f"signup:{client_ip(request)}", 10, 3600):
        messages.error(request, "Too many sign-ups from your network. Try again later.")
        return redirect("home")
    allow = SiteSettings.load().allow_seller_signup
    form = SignupForm(request.POST or None, allow_sellers=allow)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("seller_dashboard" if user.role == User.Role.SELLER else "home")
    return render(request, "shop/form.html", {"form": form, "title": "Create an account"})


@login_required
def account(request):
    form = AccountForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("account")
    return render(request, "shop/account.html", {"form": form})


# ---------- catalog ----------

def home(request):
    q = request.GET.get("q", "").strip()[:100]
    products = Product.objects.visible().select_related("store").prefetch_related("images")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(store__name__icontains=q))
    page = Paginator(products, 24).get_page(request.GET.get("page"))
    return render(request, "shop/product_list.html", {"page": page, "q": q})


def store_detail(request, pk):
    store = get_object_or_404(Store, pk=pk, is_active=True, owner__is_active=True)
    page = Paginator(store.products.visible().prefetch_related("images"), 24).get_page(request.GET.get("page"))
    return render(request, "shop/product_list.html", {"page": page, "store": store})


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.visible().select_related("store"), pk=pk)
    return render(request, "shop/product_detail.html", {"product": product})


# ---------- cart & checkout ----------

def cart_lines(user):
    return list(user.cart.select_related("product__store__owner").order_by("product__store_id", "id"))


@login_required
def cart(request):
    lines = cart_lines(request.user)
    subtotal = sum((l.product.price * l.quantity for l in lines), Decimal(0))
    return render(request, "shop/cart.html", {"lines": lines, "subtotal": subtotal})


@login_required
@require_POST
def cart_set(request, pk):
    """Set quantity of a product in the cart (0 removes it)."""
    product = get_object_or_404(Product.objects.visible(), pk=pk)
    try:
        qty = max(0, min(int(request.POST.get("quantity", 1)), 99))
    except ValueError:
        qty = 1
    if request.POST.get("add"):
        line = request.user.cart.filter(product=product).first()
        qty = min(qty + (line.quantity if line else 0), 99)
    if qty == 0:
        request.user.cart.filter(product=product).delete()
    elif qty > product.stock:
        messages.error(request, f"Only {product.stock} of {product.name} in stock.")
    else:
        CartItem.objects.update_or_create(user=request.user, product=product, defaults={"quantity": qty})
        messages.success(request, "Cart updated.")
    return redirect("cart")


class CheckoutError(Exception):
    pass


def group_by_store(lines):
    groups = defaultdict(list)
    for l in lines:
        groups[l.product.store].append(l)
    return groups


def quote_cart(lines, dest):
    """Per-store UPS rates. Each store's items ship as their own shipment from the origin."""
    quotes, source = {}, "ups"
    for store, ls in group_by_store(lines).items():
        rates, src = shipping.quote([(l.product, l.quantity) for l in ls], dest)
        quotes[store] = rates
        source = src if src == "estimate" else source
    return quotes, source


def place_orders(user, lines, d):
    for l in lines:
        p = l.product
        if not (p.is_active and p.store.is_active and p.store.owner.is_active):
            raise CheckoutError(f"{p.name} is no longer available.")
    quotes, _ = quote_cart(lines, d)  # network call, kept outside the transaction
    if any(d["service"] not in r for r in quotes.values()):
        raise CheckoutError("That shipping service isn't available for this address.")

    with transaction.atomic():
        if set(user.cart.values_list("product_id", "quantity")) != {(l.product_id, l.quantity) for l in lines}:
            raise CheckoutError("Your cart changed. Please review it and try again.")
        locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[l.product_id for l in lines]).order_by("pk")}
        orders = []
        for store, ls in group_by_store(lines).items():
            for l in ls:
                if locked[l.product_id].stock < l.quantity:
                    raise CheckoutError(f"Only {locked[l.product_id].stock} of {l.product.name} left in stock.")
            subtotal = sum((locked[l.product_id].price * l.quantity for l in ls), Decimal(0))
            ship = quotes[store][d["service"]]
            order = Order.objects.create(
                customer=user, store=store, ship_name=d["name"], ship_line1=d["line1"], ship_city=d["city"],
                ship_state=d["state"], ship_zip=d["zip"], shipping_service=shipping.SERVICES[d["service"]],
                shipping_cost=ship, subtotal=subtotal, total=subtotal + ship,
            )
            for l in ls:
                p = locked[l.product_id]
                OrderItem.objects.create(order=order, product=p, product_name=p.name, unit_price=p.price, quantity=l.quantity)
                Product.objects.filter(pk=p.pk).update(stock=F("stock") - l.quantity)
            orders.append(order)
        user.cart.all().delete()
    # ponytail: no payment capture. Add Stripe Checkout (create session here, mark paid via webhook) before taking real money.
    return orders


@login_required
def checkout(request):
    lines = cart_lines(request.user)
    if not lines:
        return redirect("cart")
    form = CheckoutForm(request.POST or None, initial={"name": request.user.get_full_name()})
    if request.method == "POST" and form.is_valid():
        try:
            orders = place_orders(request.user, lines, form.cleaned_data)
        except (CheckoutError, shipping.ShippingError) as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Placed {len(orders)} order(s).")
            return redirect("orders")
    subtotal = sum((l.product.price * l.quantity for l in lines), Decimal(0))
    return render(request, "shop/checkout.html", {"form": form, "lines": lines, "subtotal": subtotal})


@login_required
@require_POST
def api_shipping_rates(request):
    """POST {name?, line1, city, state, zip} -> UPS rates for the current cart, summed across sellers."""
    if hit(f"rates:{who(request)}", 30):
        return JsonResponse({"error": "Too many requests."}, status=429)
    form = AddressForm(json_body(request) or {})
    form.fields["name"].required = False
    if not form.is_valid():
        return JsonResponse({"error": "Invalid address.", "fields": form.errors}, status=400)
    lines = cart_lines(request.user)
    if not lines:
        return JsonResponse({"error": "Cart is empty."}, status=400)
    try:
        quotes, source = quote_cart(lines, form.cleaned_data)
    except shipping.ShippingError as e:
        return JsonResponse({"error": str(e)}, status=400)
    codes = [c for c in shipping.SERVICES if all(c in r for r in quotes.values())]
    return JsonResponse({
        "origin": "110 Inner Campus Drive, Austin, TX 78705",
        "source": source,
        "shipments": len(quotes),
        "rates": [{"code": c, "service": shipping.SERVICES[c], "amount": str(sum(r[c] for r in quotes.values()))}
                  for c in codes],
    })


# ---------- customer orders ----------

@login_required
def orders(request):
    page = Paginator(request.user.orders.select_related("store"), 20).get_page(request.GET.get("page"))
    return render(request, "shop/order_list.html", {"page": page})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("store"), pk=pk, customer=request.user)
    return render(request, "shop/order_detail.html", {"order": order, "return_form": ReturnForm()})


@login_required
@require_POST
def order_cancel(request, pk):
    if not transition(request.user.orders, pk, [S.PLACED], S.CANCELLED):
        messages.error(request, "This order can no longer be cancelled.")
    return redirect("order_detail", pk=pk)


@login_required
@require_POST
def order_return(request, pk):
    form = ReturnForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please give a reason for the return.")
    elif not transition(request.user.orders, pk, [S.SHIPPED, S.DELIVERED], S.RETURN_REQUESTED,
                        return_reason=form.cleaned_data["return_reason"]):
        messages.error(request, "A return can't be requested for this order.")
    else:
        messages.success(request, "Return requested. The seller will review it.")
    return redirect("order_detail", pk=pk)


# ---------- seller ----------

@seller_required
def seller_dashboard(request):
    store = Store.objects.filter(owner=request.user).first()
    form = StoreForm(request.POST or None, instance=store)
    if request.method == "POST" and form.is_valid():
        form.instance.owner = request.user
        form.save()
        messages.success(request, "Store saved.")
        return redirect("seller_dashboard")
    ctx = {"form": form, "store": store}
    if store:
        ctx["products"] = store.products.all()
        ctx["orders"] = store.orders.select_related("customer")[:50]
        ctx["sales"] = store.orders.exclude(status__in=[S.CANCELLED, S.RETURNED]).aggregate(n=Count("id"), total=Sum("subtotal"))
    return render(request, "shop/seller_dashboard.html", ctx)


def own_store(user):
    store = Store.objects.filter(owner=user).first()
    if not store:
        raise Http404("Create your store first.")
    return store


@seller_required
def product_edit(request, pk=None):
    store = own_store(request.user)
    product = get_object_or_404(Product, pk=pk, store=store) if pk else Product(store=store)
    is_image = request.method == "POST" and request.POST.get("form") == "image" and pk
    form = ProductForm(request.POST if request.method == "POST" and not is_image else None, instance=product)
    image_form = (ImageForm(request.POST, request.FILES) if is_image else ImageForm()) if pk else None
    target = image_form if is_image else form
    if request.method == "POST" and target.is_valid():
        if is_image:
            if product.images.count() >= 10:
                messages.error(request, "A product can have at most 10 images.")
                return redirect("product_edit", pk=pk)
            image_form.instance.product = product
        target.save()
        messages.success(request, "Saved.")
        return redirect("product_edit", pk=product.pk)
    return render(request, "shop/product_edit.html", {"form": form, "image_form": image_form, "product": product})


@seller_required
@require_POST
def image_delete(request, pk):
    image = get_object_or_404(ProductImage, pk=pk, product__store__owner=request.user)
    image.image.delete(save=False)
    image.delete()
    return redirect("product_edit", pk=image.product_id)


SELLER_ACTIONS = {
    "ship": ([S.PLACED], S.SHIPPED),
    "deliver": ([S.SHIPPED], S.DELIVERED),
    "cancel": ([S.PLACED], S.CANCELLED),
    "approve_return": ([S.RETURN_REQUESTED], S.RETURNED),
    "deny_return": ([S.RETURN_REQUESTED], S.DELIVERED),
}


@seller_required
def seller_order(request, pk):
    mine = Order.objects.filter(store__owner=request.user)
    order = get_object_or_404(mine.select_related("customer"), pk=pk)
    ship_form = ShipForm(request.POST or None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action not in SELLER_ACTIONS:
            raise PermissionDenied
        frm, to = SELLER_ACTIONS[action]
        extra = {}
        if action == "ship":
            if not ship_form.is_valid():
                return render(request, "shop/order_detail.html", {"order": order, "seller": True, "ship_form": ship_form})
            extra["tracking_number"] = ship_form.cleaned_data["tracking_number"]
        if not transition(mine, pk, frm, to, **extra):
            messages.error(request, "That action isn't allowed for this order's status.")
        return redirect("seller_order", pk=pk)
    return render(request, "shop/order_detail.html", {"order": order, "seller": True, "ship_form": ShipForm()})


# ---------- messaging ----------

def can_message(me, other):
    if not other.is_active or other == me:
        return False
    return (
        other.role in (User.Role.SELLER, User.Role.ADMIN)
        or me.role == User.Role.ADMIN
        or Order.objects.filter(customer=other, store__owner=me).exists()
        or Message.objects.filter(sender=other, recipient=me).exists()
    )


@login_required
def inbox(request):
    msgs = (Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
            .select_related("sender", "recipient").order_by("-created")[:500])
    threads = {}
    for m in msgs:  # ponytail: in-Python grouping of the latest 500 messages; move to a Thread model if inboxes grow
        other = m.recipient if m.sender_id == request.user.pk else m.sender
        t = threads.setdefault(other.pk, {"other": other, "last": m, "unread": 0})
        t["unread"] += m.recipient_id == request.user.pk and not m.read
    return render(request, "shop/inbox.html", {"threads": threads.values()})


@login_required
def thread(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    if not can_message(request.user, other):
        raise Http404
    form = MessageForm(request.POST or None)
    if request.method == "POST":
        if hit(f"msg:{request.user.pk}", 20):
            messages.error(request, "You're sending messages too quickly.")
        elif form.is_valid():
            product = Product.objects.filter(pk=request.POST.get("product") or 0, store__owner__in=[other, request.user]).first()
            order = Order.objects.filter(Q(customer=request.user, store__owner=other) | Q(customer=other, store__owner=request.user),
                                         pk=request.POST.get("order") or 0).first()
            Message.objects.create(sender=request.user, recipient=other, body=form.cleaned_data["body"], product=product, order=order)
            return redirect("thread", user_id=other.pk)
    convo = Message.objects.filter(Q(sender=request.user, recipient=other) | Q(sender=other, recipient=request.user)).select_related("product", "order")
    convo.filter(recipient=request.user, read=False).update(read=True)
    about = {"product": request.GET.get("product", ""), "order": request.GET.get("order", "")}
    return render(request, "shop/thread.html", {"other": other, "convo": convo, "form": form, "about": about})


# ---------- chatbot ----------

@login_required
@require_POST
def api_chat(request):
    if not SiteSettings.load().chatbot_enabled:
        return JsonResponse({"error": "The assistant is disabled."}, status=503)
    if hit(f"chat:{request.user.pk}", 10) or hit(f"chat-day:{request.user.pk}", 200, 86400):
        return JsonResponse({"error": "Too many messages. Please wait a moment."}, status=429)
    text = str((json_body(request) or {}).get("message", "")).strip()[:1000]
    if not text:
        return JsonResponse({"error": "Empty message."}, status=400)
    history = request.session.get("chat", [])
    answer = chat.reply(request.user, history, text, SiteSettings.load().site_name)
    request.session["chat"] = (history + [{"role": "user", "content": text}, {"role": "assistant", "content": answer}])[-chat.MAX_HISTORY:]
    return JsonResponse({"reply": answer})


# ---------- admin analytics ----------

@staff_member_required
def analytics(request):
    since = timezone.now() - timedelta(days=30)
    sold = Order.objects.exclude(status__in=[S.CANCELLED, S.RETURNED])
    totals = sold.aggregate(revenue=Sum("total"), gmv=Sum("subtotal"), shipping=Sum("shipping_cost"), orders=Count("id"))
    commission = (totals["gmv"] or 0) * SiteSettings.load().commission_percent / 100
    ctx = {
        "totals": totals,
        "commission": commission,
        "by_status": Order.objects.values("status").annotate(n=Count("id")).order_by("status"),
        "daily": sold.filter(created__gte=since).annotate(day=TruncDate("created")).values("day")
                     .annotate(orders=Count("id"), revenue=Sum("subtotal")).order_by("-day"),
        "top_products": OrderItem.objects.filter(order__in=sold).values("product_id", "product_name")
                        .annotate(units=Sum("quantity"), revenue=Sum(F("unit_price") * F("quantity"))).order_by("-revenue")[:10],
        "top_stores": sold.values("store__name").annotate(orders=Count("id"), revenue=Sum("subtotal")).order_by("-revenue")[:10],
        "users": User.objects.values("role").annotate(n=Count("id")).order_by("role"),
        "admin_url": settings.ADMIN_URL,
    }
    return render(request, "shop/analytics.html", ctx)
