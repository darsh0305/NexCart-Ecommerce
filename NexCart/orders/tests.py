from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from products.models import Category, Product, ProductSizeVariant
from sellers.models import SellerProfile
from accounts.models import Address
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem

User = get_user_model()


class OrderHistoryAndInvoiceTests(TestCase):

    def setUp(self):
        self.client = Client()

        # Customer 1
        self.customer1 = User.objects.create_user(
            username='cust1',
            email='cust1@example.com',
            password='password123',
            role='customer'
        )

        # Customer 2
        self.customer2 = User.objects.create_user(
            username='cust2',
            email='cust2@example.com',
            password='password123',
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
            store_name='Apex Electronics',
            phone='9876543210',
            city='Bangalore',
            state='Karnataka',
            pincode='560001',
            is_approved=True
        )

        # Category
        self.category, _ = Category.objects.get_or_create(
            name='Test Electronics Cat',
            defaults={'slug': 'test-electronics-cat'}
        )

        # Product
        self.product = Product.objects.create(
            name='Wireless Headphones Pro',
            slug='wireless-headphones-pro',
            category=self.category,
            seller=self.seller,
            price=Decimal('1500.00'),
            discount_percentage=Decimal('10.00'),
            stock=20,
            status='active'
        )

        # Address for Customer 1
        self.address = Address.objects.create(
            user=self.customer1,
            full_name='John Doe',
            phone='9876543210',
            address_line_1='123 Main Street',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001',
            landmark='Near Metro Station',
            is_default=True
        )

        # Order for Customer 1
        self.order = Order.objects.create(
            user=self.customer1,
            address=self.address,
            shipping_name='John Doe',
            shipping_phone='9876543210',
            shipping_address='123 Main Street',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_pincode='400001',
            order_number='NC-TESTORDER1',
            subtotal=Decimal('1350.00'),
            delivery_charge=Decimal('0.00'),
            total_amount=Decimal('1350.00'),
            payment_method='cod',
            payment_status='pending',
            status='confirmed'
        )


        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name='Wireless Headphones Pro',
            price=Decimal('1350.00'),
            quantity=1,
            total_price=Decimal('1350.00')
        )

    def test_my_orders_page_authenticated(self):
        self.client.login(username='cust1', password='password123')
        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NC-TESTORDER1')
        self.assertContains(response, 'Apex Electronics')
        self.assertContains(response, 'Wireless Headphones Pro')

    def test_order_detail_page_owner(self):
        self.client.login(username='cust1', password='password123')
        response = self.client.get(reverse('order_detail', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order #NC-TESTORDER1')
        self.assertContains(response, 'Apex Electronics')
        self.assertContains(response, 'Delivery Status')

    def test_order_detail_access_restriction_for_other_users(self):
        # Customer 2 should NOT be able to view Customer 1's order
        self.client.login(username='cust2', password='password123')
        response = self.client.get(reverse('order_detail', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 404)

    def test_reorder_functionality(self):
        self.client.login(username='cust1', password='password123')
        response = self.client.get(reverse('reorder_order', kwargs={'order_id': self.order.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.get(user=self.customer1)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product, self.product)

    def test_cancel_order_restores_stock(self):
        initial_stock = self.product.stock
        self.client.login(username='cust1', password='password123')
        response = self.client.post(reverse('cancel_order', kwargs={'order_id': self.order.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + 1)

    def test_download_invoice_pdf(self):
        self.client.login(username='cust1', password='password123')
        response = self.client.get(reverse('download_invoice', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_view_invoice_html_non_fashion(self):
        self.client.login(username='cust1', password='password123')
        response = self.client.get(reverse('view_invoice', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/invoice.html')
        self.assertEqual(response.context['has_fashion'], False)
        # Should not show Size column header
        self.assertNotContains(response, '<th class="text-center" style="width: 70px;">Size</th>')



class OrderTrackingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username='trackseller',
            email='trackseller@example.com',
            password='password123',
            role='seller'
        )
        self.customer1 = User.objects.create_user(
            username='trackcust1',
            email='trackcust1@example.com',
            password='password123',
            role='customer'
        )
        self.customer2 = User.objects.create_user(
            username='trackcust2',
            email='trackcust2@example.com',
            password='password123',
            role='customer'
        )

        self.category = Category.objects.create(name='Track Test Cat', slug='track-test-cat')
        self.product = Product.objects.create(
            category=self.category,
            seller=self.seller,
            name='Track Test Product',
            slug='track-test-prod',
            description='Test description',
            price=1500,
            stock=10,
            status='active',
            is_active=True
        )

        self.address = Address.objects.create(
            user=self.customer1,
            full_name='Track Cust',
            phone='9876543210',
            address_type='home',
            address_line_1='123 Main St',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            is_default=True
        )

        self.order = Order.objects.create(
            user=self.customer1,
            address=self.address,
            order_number='NEX-TRACK-101',
            subtotal=1500,
            delivery_charge=0,
            total_amount=1500,
            payment_method='cod',
            payment_status='pending',
            status='pending',
            shipping_name='Track Cust',
            shipping_phone='9876543210',
            shipping_address='123 Main St',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=1500,
            quantity=1,
            total_price=1500
        )

    def test_customer_view_order_tracking(self):
        """Customer can track their order and see timeline."""
        self.client.login(username='trackcust1', password='password123')
        response = self.client.get(reverse('order_tracking', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_tracking.html')
        self.assertContains(response, 'Live Delivery Timeline')
        self.assertContains(response, 'NEX-TRACK-101')
        self.assertEqual(response.context['current_status'], 'pending')
        self.assertEqual(response.context['current_index'], 0)

    def test_customer_cannot_track_other_customer_order(self):
        """Customer cannot view another customer's tracking page."""
        self.client.login(username='trackcust2', password='password123')
        response = self.client.get(reverse('order_tracking', kwargs={'order_id': self.order.id}))
        self.assertEqual(response.status_code, 404)

    def test_seller_updates_delivery_status(self):
        """Seller can update delivery status of order containing their product."""
        self.client.login(username='trackseller', password='password123')
        response = self.client.post(
            reverse('update_delivery_status', kwargs={'order_id': self.order.id}),
            {'delivery_status': 'SHIPPED'}
        )
        self.assertRedirects(response, reverse('seller_orders'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')

    def test_delivered_cod_marks_payment_paid(self):
        """Updating status of COD order to DELIVERED automatically marks payment as paid."""
        self.client.login(username='trackseller', password='password123')
        self.client.post(
            reverse('update_delivery_status', kwargs={'order_id': self.order.id}),
            {'delivery_status': 'DELIVERED'}
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')
        self.assertEqual(self.order.payment_status, 'paid')


class FashionOrderSizeFlowTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username='sizecustomer',
            email='sizecust@example.com',
            password='password123',
            role='customer'
        )
        self.seller = User.objects.create_user(
            username='fashionseller',
            email='fashionseller@example.com',
            password='password123',
            role='seller'
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller,
            store_name='Fashion Hub',
            phone='9876543211',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001',
            is_approved=True
        )
        self.fashion_cat, _ = Category.objects.get_or_create(
            name="Fashion",
            defaults={'slug': 'fashion'}
        )
        self.fashion_product = Product.objects.create(
            seller=self.seller,
            category=self.fashion_cat,
            name='Order Test Denim Jacket',
            slug='order-test-denim-jacket',
            description='Warm denim jacket',
            price=Decimal('1499.00'),
            stock=6,
            image='products/jacket.jpg'
        )
        self.variant_s = ProductSizeVariant.objects.create(product=self.fashion_product, size='S', stock=1)
        self.variant_l = ProductSizeVariant.objects.create(product=self.fashion_product, size='L', stock=5)

        self.address = Address.objects.create(
            user=self.customer,
            full_name='Size Cust',
            phone='9876543210',
            address_line_1='123 Fashion Street',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001',
            is_default=True
        )

    def test_complete_fashion_size_order_and_invoice_flow(self):
        self.client.login(username='sizecustomer', password='password123')

        # 1. Add to cart with size L (quantity 2)
        cart = Cart.objects.create(user=self.customer)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.fashion_product,
            quantity=2,
            size='L'
        )

        # 2. Place COD order
        response = self.client.post(reverse('place_order', kwargs={'address_id': self.address.id}))
        self.assertEqual(response.status_code, 302)

        order = Order.objects.filter(user=self.customer).first()
        self.assertIsNotNone(order)
        order_item = order.items.first()
        self.assertIsNotNone(order_item)
        self.assertEqual(order_item.size, 'L')
        self.assertEqual(order_item.quantity, 2)

        # Verify size variant stock deduction: Size L went from 5 to 3
        self.variant_l.refresh_from_db()
        self.assertEqual(self.variant_l.stock, 3)
        self.variant_s.refresh_from_db()
        self.assertEqual(self.variant_s.stock, 1)

        # Total product stock should now be 4 (1 from S + 3 from L)
        self.fashion_product.refresh_from_db()
        self.assertEqual(self.fashion_product.stock, 4)

        # 3. Order detail view displays size
        detail_response = self.client.get(reverse('order_detail', kwargs={'order_id': order.id}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Size:')
        self.assertContains(detail_response, 'L')

        # 4. View invoice HTML displays size for fashion products
        view_inv_response = self.client.get(reverse('view_invoice', kwargs={'order_id': order.id}))
        self.assertEqual(view_inv_response.status_code, 200)
        self.assertEqual(view_inv_response.context['has_fashion'], True)
        self.assertContains(view_inv_response, 'Size')
        self.assertContains(view_inv_response, 'L')

        # 5. Download invoice PDF generates successfully
        invoice_response = self.client.get(reverse('download_invoice', kwargs={'order_id': order.id}))
        self.assertEqual(invoice_response.status_code, 200)
        self.assertEqual(invoice_response['Content-Type'], 'application/pdf')

        # 6. View invoice with ?download=pdf also downloads PDF
        inv_dl_param_response = self.client.get(reverse('view_invoice', kwargs={'order_id': order.id}) + '?download=pdf')
        self.assertEqual(inv_dl_param_response.status_code, 200)
        self.assertEqual(inv_dl_param_response['Content-Type'], 'application/pdf')



