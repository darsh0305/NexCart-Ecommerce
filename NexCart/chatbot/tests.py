import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from chatbot.context_builder import build_nexcart_context
from chatbot.gemini_service import get_gemini_response
from orders.models import Order, OrderItem
from products.models import Category, Product


class GeminiFallbackTests(TestCase):
    @override_settings(GEMINI_API_KEY='')
    def test_get_gemini_response_falls_back_when_key_missing(self):
        response = get_gemini_response('What are your trending products?')

        self.assertTrue(response)
        self.assertIn('NexCart AI', response)

    @override_settings(GEMINI_API_KEY='')
    def test_chat_view_returns_success_when_gemini_is_unconfigured(self):
        client = Client()
        response = client.post(
            '/chatbot/chat/',
            data=json.dumps({'message': 'What are the trending products?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('NexCart AI', payload['response'])

    def test_build_nexcart_context_filters_relevant_products(self):
        electronics = Category.objects.create(name='Electronics Search Test', slug='electronics-search-test')
        fashion = Category.objects.create(name='Fashion Search Test', slug='fashion-search-test')

        Product.objects.create(
            category=electronics,
            name='Samsung Galaxy S25',
            description='Flagship phone',
            price=Decimal('50000.00'),
            stock=10,
            image='products/test.jpg',
            status='active',
            is_active=True,
        )
        Product.objects.create(
            category=fashion,
            name='Urban Hoodie',
            description='Warm hoodie',
            price=Decimal('2000.00'),
            stock=20,
            image='products/test2.jpg',
            status='active',
            is_active=True,
        )

        context = build_nexcart_context(None, 'show me Electronics Search Test under 60000')

        self.assertIn('Samsung Galaxy S25', context)
        self.assertNotIn('Urban Hoodie', context)

    def test_build_nexcart_context_includes_recent_customer_order(self):
        User = get_user_model()
        user = User.objects.create_user(username='alice', email='alice@example.com', password='pass1234')

        electronics = Category.objects.create(name='Electronics Order Test', slug='electronics-order-test')
        product = Product.objects.create(
            category=electronics,
            name='Bluetooth Speaker',
            description='Portable speaker',
            price=Decimal('1500.00'),
            stock=8,
            image='products/speaker.jpg',
            status='active',
            is_active=True,
        )

        order = Order.objects.create(
            user=user,
            order_number='NXC-1001',
            subtotal=Decimal('1500.00'),
            delivery_charge=Decimal('0.00'),
            total_amount=Decimal('1500.00'),
            payment_method='cod',
            payment_status='paid',
            status='confirmed',
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name='Bluetooth Speaker',
            price=Decimal('1500.00'),
            quantity=1,
            total_price=Decimal('1500.00'),
        )

        context = build_nexcart_context(user, 'track my order')

        self.assertIn('Order Number: NXC-1001', context)
        self.assertIn('Status: confirmed', context)
