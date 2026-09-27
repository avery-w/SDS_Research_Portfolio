import json
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from . import shipping
from .models import CartItem, Order, Product, Store, User

ADDR = {"name": "Ann", "line1": "1 Main St", "city": "Dallas", "state": "TX", "zip": "75201", "service": "03"}


class MarketplaceTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("seller", "s@x.com", "pw-long-enough-1", role="seller")
        self.seller2 = User.objects.create_user("seller2", "s2@x.com", "pw-long-enough-1", role="seller")
        self.customer = User.objects.create_user("cust", "c@x.com", "pw-long-enough-1")
        self.store = Store.objects.create(owner=self.seller, name="S1")
        self.store2 = Store.objects.create(owner=self.seller2, name="S2")
        dims = dict(weight_lb=2, length_in=10, width_in=8, height_in=4)
        self.p1 = Product.objects.create(store=self.store, name="Mug", price=Decimal("10.00"), stock=5, **dims)
        self.p2 = Product.objects.create(store=self.store2, name="Hat", price=Decimal("20.00"), stock=1, **dims)

    def test_shipping_rules(self):
        box = shipping.Package(1, [20, 20, 20])  # 8000/139 = 57.6 -> dim weight wins
        self.assertEqual(box.billable_lb, 58)
        self.assertTrue(shipping.Package(60, [10, 10, 10]).additional_handling)
        heavy = mock.Mock(length_in=10, width_in=10, height_in=1, weight_lb=50)
        pkgs = shipping.pack([(heavy, 4)])  # 200 lb must split under the 150 lb limit
        self.assertEqual([p.weight for p in pkgs], [150, 50])
        pkgs = shipping.pack([(self.p1, 100)])
        self.assertTrue(all(shipping._fits(p) for p in pkgs))
        self.assertEqual(sum(p.weight for p in pkgs), 200)
        self.assertEqual(shipping.zone_for("78705"), 2)
        self.assertEqual(shipping.zone_for("10001"), 7)
        near, far = shipping.estimate([box], "78705"), shipping.estimate([box], "10001")
        self.assertLess(near["03"], far["03"])
        self.assertLess(near["03"], near["01"])
        big = mock.Mock(length_in=120, width_in=1, height_in=1, weight_lb=1)
        big.name = "Pole"
        with self.assertRaises(shipping.ShippingError):
            shipping.pack([(big, 1)])

    def test_checkout_splits_by_store_and_decrements_stock(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.p1, quantity=2)
        CartItem.objects.create(user=self.customer, product=self.p2, quantity=1)
        r = self.client.post("/api/shipping/rates/", json.dumps(ADDR), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["shipments"], 2)
        self.client.post("/checkout/", ADDR)
        self.assertEqual(Order.objects.count(), 2)
        o = Order.objects.get(store=self.store)
        self.assertEqual(o.subtotal, Decimal("20.00"))
        self.assertEqual(o.total, o.subtotal + o.shipping_cost)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 3)
        self.assertFalse(CartItem.objects.exists())

    def test_checkout_rejects_oversell(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.p2, quantity=2)
        self.client.post("/checkout/", ADDR)
        self.assertFalse(Order.objects.exists())
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.stock, 1)

    def test_cancel_restocks_once(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.p1, quantity=2)
        self.client.post("/checkout/", ADDR)
        o = Order.objects.get()
        self.client.post(f"/orders/{o.pk}/cancel/")
        self.client.post(f"/orders/{o.pk}/cancel/")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)

    def test_access_control(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.p1, quantity=1)
        self.client.post("/checkout/", ADDR)
        o = Order.objects.get()
        self.assertEqual(self.client.get("/seller/").status_code, 403)
        self.assertEqual(self.client.get("/staff/analytics/").status_code, 302)
        self.client.force_login(self.seller2)  # other seller cannot see or touch this order or product
        self.assertEqual(self.client.get(f"/seller/orders/{o.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/seller/products/{self.p1.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/orders/{o.pk}/").status_code, 404)
        self.client.force_login(self.seller)
        self.client.post(f"/seller/orders/{o.pk}/", {"action": "ship", "tracking_number": "1Z999AA10123456784"})
        o.refresh_from_db()
        self.assertEqual(o.status, "shipped")

    def test_signup_cannot_create_admin(self):
        self.client.post("/accounts/signup/", {"username": "evil", "email": "e@x.com", "role": "admin",
                                               "password1": "Very-long-pass-123", "password2": "Very-long-pass-123"})
        self.assertFalse(User.objects.filter(username="evil").exists())

    def test_chat_is_read_only_and_uses_catalog(self):
        self.client.force_login(self.customer)
        fake = mock.Mock(stop_reason="end_turn", content=[mock.Mock(type="text", text="Try the Mug.")])
        with mock.patch("shop.chat.client.beta.messages.create", return_value=fake) as create:
            r = self.client.post("/api/chat/", json.dumps({"message": "any mug?"}), content_type="application/json")
        self.assertEqual(r.json()["reply"], "Try the Mug.")
        self.assertIn("Mug", create.call_args.kwargs["system"][1]["text"])
        self.assertNotIn("tools", create.call_args.kwargs)

    def test_pages_render(self):
        admin = User.objects.create_superuser("root", "r@x.com", "pw-long-enough-1")
        self.assertTrue(admin.is_staff and admin.role == "admin")
        for path in ["/", "/?q=mug", f"/products/{self.p1.pk}/", f"/stores/{self.store.pk}/", "/accounts/login/", "/accounts/signup/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.p1, quantity=1)
        for path in ["/cart/", "/checkout/", "/accounts/profile/", "/messages/", f"/messages/{self.seller.pk}/?product={self.p1.pk}"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.client.post(f"/messages/{self.seller.pk}/", {"body": "Is it dishwasher safe?", "product": self.p1.pk})
        self.client.post("/checkout/", ADDR)
        o = Order.objects.get()
        self.assertEqual(self.client.get(f"/orders/{o.pk}/").status_code, 200)
        self.client.force_login(self.seller)
        for path in ["/seller/", "/seller/products/new/", f"/seller/products/{self.p1.pk}/", f"/seller/orders/{o.pk}/",
                     "/messages/", f"/messages/{self.customer.pk}/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.client.force_login(admin)
        for path in ["/staff/analytics/", "/manage/", "/manage/shop/order/", f"/manage/shop/order/{o.pk}/change/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
