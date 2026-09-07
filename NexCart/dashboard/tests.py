from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from products.models import Category, Product
from sellers.models import SellerProfile
from accounts.models import Address
from orders.models import Order, OrderItem

User = get_user_model()


class AdminOrderManagementTests(TestCase):

    def setUp(self):
        self.client = Client()

        # Admin Staff User
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@nexcart.com',
            password='adminpassword123',
            is_staff=True,
            is_superuser=True
        )

        # Normal Customer
        self.customer = User.objects.create_user(
            username='customer1',
            email='cust1@example.com',
            password='password123',
            first_name='Alice',
            last_name='Smith',
            role='customer'
        )

        # Seller
        self.seller = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='password123',
            role='seller'
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller,
            store_name='ElectroTech Store',
            phone='9876543210',
            city='Bangalore',
            state='Karnataka',
            pincode='560001',
            is_approved=True
        )

        # Category
        self.category, _ = Category.objects.get_or_create(
            name='Gadgets Cat',
            defaults={'slug': 'gadgets-cat'}
        )

        # Product
        self.product = Product.objects.create(
            name='Bluetooth Speaker 20W',
            slug='bluetooth-speaker-20w',
            category=self.category,
            seller=self.seller,
            price=Decimal('2000.00'),
            discount_percentage=Decimal('15.00'),
            stock=15,
            status='active'
        )

        # Address
        self.address = Address.objects.create(
            user=self.customer,
            full_name='Alice Smith',
            phone='9123456780',
            address_line_1='Flat 402, Sunshine Heights',
            city='Bangalore',
            state='Karnataka',
            pincode='560001',
            is_default=True
        )

        # Order
        self.order1 = Order.objects.create(
            user=self.customer,
            address=self.address,
            shipping_name='Alice Smith',
            shipping_phone='9123456780',
            shipping_address='Flat 402, Sunshine Heights',
            shipping_city='Bangalore',
            shipping_state='Karnataka',
            shipping_pincode='560001',
            order_number='NC-ADMINTEST1',
            subtotal=Decimal('1700.00'),
            delivery_charge=Decimal('0.00'),
            total_amount=Decimal('1700.00'),
            payment_method='cod',
            payment_status='pending',
            status='pending'
        )

        OrderItem.objects.create(
            order=self.order1,
            product=self.product,
            product_name='Smart Watch Ultra',
            price=Decimal('2699.10'),
            quantity=1,
            total_price=Decimal('2699.10')
        )

        # Order 2 (Shipped, Razorpay, Paid)
        self.order2 = Order.objects.create(
            user=self.customer,
            address=self.address,
            order_number='NC-ADMINTEST2',
            subtotal=Decimal('5398.20'),
            delivery_charge=Decimal('0.00'),
            total_amount=Decimal('5398.20'),
            payment_method='razorpay',
            payment_status='paid',
            status='shipped'
        )
        OrderItem.objects.create(
            order=self.order2,
            product=self.product,
            product_name='Smart Watch Ultra',
            price=Decimal('2699.10'),
            quantity=2,
            total_price=Decimal('5398.20')
        )

    def test_admin_access_protection_for_regular_customers(self):
        self.client.login(username='customer1', password='password123')
        response = self.client.get(reverse('admin_orders'))
        self.assertRedirects(response, reverse('home'))

    def test_admin_orders_list_view(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('admin_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NC-ADMINTEST1')
        self.assertContains(response, 'NC-ADMINTEST2')
        self.assertContains(response, 'Alice Smith')

    def test_admin_search_order_by_number(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('admin_orders'), {'search': 'ADMINTEST1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NC-ADMINTEST1')
        self.assertNotContains(response, 'NC-ADMINTEST2')

    def test_admin_filter_by_status(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('admin_orders'), {'status': 'shipped'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NC-ADMINTEST2')
        self.assertNotContains(response, 'NC-ADMINTEST1')

    def test_admin_filter_by_payment_status(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('admin_orders'), {'payment_status': 'paid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NC-ADMINTEST2')
        self.assertNotContains(response, 'NC-ADMINTEST1')

    def test_admin_order_detail_view(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.get(reverse('admin_order_detail', kwargs={'order_id': self.order1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order #NC-ADMINTEST1')
        self.assertContains(response, 'ElectroTech Store')
        self.assertContains(response, 'Smart Watch Ultra')

    def test_admin_update_delivery_status_to_delivered(self):
        self.client.login(username='adminuser', password='adminpassword123')
        response = self.client.post(
            reverse('admin_update_order_status', kwargs={'order_id': self.order1.id}),
            {'status': 'delivered'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'delivered')
        # COD order delivered should automatically update payment_status to paid
        self.assertEqual(self.order1.payment_status, 'paid')
