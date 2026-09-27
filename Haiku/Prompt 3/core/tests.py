from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import UserProfile, Store, Product
from rest_framework.test import APIClient
from rest_framework import status


class UserRegistrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_customer(self):
        response = self.client.post('/api/users/register/', {
            'email': 'customer@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'role': 'customer'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='customer@test.com').exists())

    def test_register_seller(self):
        response = self.client.post('/api/users/register/', {
            'email': 'seller@test.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'role': 'seller'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = UserProfile.objects.get(user__email='seller@test.com')
        self.assertEqual(profile.role, 'seller')

    def test_register_password_mismatch(self):
        response = self.client.post('/api/users/register/', {
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'password2': 'DifferentPass!',
            'role': 'customer'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        response = self.client.post('/api/users/register/', {
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '123',
            'password2': '123',
            'role': 'customer'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='seller@test.com',
            email='seller@test.com',
            password='SecurePass123!'
        )
        self.profile = UserProfile.objects.create(user=self.user, role='seller')
        self.store = Store.objects.create(
            seller=self.user,
            name='Test Store',
            description='A test store',
            address='123 Main St',
            city='Austin',
            state='TX',
            zip_code='78701',
            country='USA'
        )

    def test_create_product(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/products/', {
            'store_id': self.store.id,
            'name': 'Test Product',
            'description': 'A test product',
            'price': '99.99',
            'stock': 10,
            'sku': 'TEST001',
            'category': 'Electronics',
            'weight_kg': '1.5'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_search_products(self):
        Product.objects.create(
            store=self.store,
            name='Laptop',
            description='A powerful laptop',
            price=999.99,
            stock=5,
            sku='LAP001',
            category='Electronics',
            weight_kg=2.0
        )
        response = self.client.get('/api/products/?search=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_filter_by_category(self):
        Product.objects.create(
            store=self.store,
            name='Phone',
            description='A smartphone',
            price=599.99,
            stock=10,
            sku='PHN001',
            category='Electronics',
            weight_kg=0.3
        )
        response = self.client.get('/api/products/?category=Electronics')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CartTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='SecurePass123!'
        )
        self.seller = User.objects.create_user(
            username='seller@test.com',
            email='seller@test.com',
            password='SecurePass123!'
        )
        UserProfile.objects.create(user=self.seller, role='seller')
        self.store = Store.objects.create(
            seller=self.seller,
            name='Test Store',
            address='123 Main St',
            city='Austin',
            state='TX',
            zip_code='78701',
            country='USA'
        )
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            description='A test product',
            price=99.99,
            stock=10,
            sku='TEST001',
            category='Electronics',
            weight_kg=1.0
        )

    def test_add_to_cart(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/cart/add_item/', {
            'product_id': self.product.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_cart(self):
        self.client.force_authenticate(user=self.customer)
        self.client.post('/api/cart/add_item/', {
            'product_id': self.product.id,
            'quantity': 1
        })
        response = self.client.get('/api/cart/my_cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
