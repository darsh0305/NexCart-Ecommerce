from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from products.models import Category, Product, ProductSizeVariant


class CheckoutLinkTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice',
            email='alice@example.com',
            password='securepass123',
        )
        self.category = Category.objects.create(
            name='Checkout Test Category',
            slug='checkout-test-category',
        )
        self.product = Product.objects.create(
            category=self.category,
            seller=self.user,
            name='Checkout Test Product',
            slug='checkout-test-product',
            description='Test product',
            price='799.00',
            stock=10,
            image='products/test.jpg',
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )

    def test_checkout_button_links_to_checkout_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('cart_detail'))

        self.assertContains(
            response,
            reverse('checkout')
        )

    def test_checkout_summary_uses_cart_delivery_totals(self):
        self.product.price = '299.00'
        self.product.save(update_fields=['price'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('checkout'))

        self.assertContains(response, '₹30.00')
        self.assertContains(response, '₹329.00')


class FashionCartSizeTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='fashionuser',
            email='fashion@example.com',
            password='securepass123',
        )
        self.fashion_category, _ = Category.objects.get_or_create(
            name="Fashion",
            defaults={'slug': 'fashion'}
        )
        self.fashion_product = Product.objects.create(
            category=self.fashion_category,
            name='Cart Test Cotton T-Shirt',
            slug='cart-test-cotton-tshirt',
            description='Stylish t-shirt',
            price='599.00',
            stock=12,
            image='products/tshirt.jpg',
        )
        # Create size variants: S (1), M (5), L (0), XL (6)
        ProductSizeVariant.objects.create(product=self.fashion_product, size='S', stock=1)
        ProductSizeVariant.objects.create(product=self.fashion_product, size='M', stock=5)
        ProductSizeVariant.objects.create(product=self.fashion_product, size='L', stock=0)
        ProductSizeVariant.objects.create(product=self.fashion_product, size='XL', stock=6)

        self.electronics_category, _ = Category.objects.get_or_create(
            name='Cart Electronics',
            defaults={'slug': 'cart-electronics'}
        )
        self.electronics_product = Product.objects.create(
            category=self.electronics_category,
            name='Cart Test Wireless Mouse',
            slug='cart-test-wireless-mouse',
            description='Optical mouse',
            price='499.00',
            stock=20,
            image='products/mouse.jpg',
        )

    def test_fashion_product_add_to_cart_without_size_fails(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {}
        )
        # Should redirect back to product detail to select size
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CartItem.objects.filter(product=self.fashion_product).count(), 0)

    def test_fashion_product_add_different_sizes_creates_separate_cart_items(self):
        self.client.force_login(self.user)
        # Add Size S
        self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {'size': 'S'}
        )
        # Add Size XL
        self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {'size': 'XL'}
        )

        cart_items = CartItem.objects.filter(product=self.fashion_product)
        self.assertEqual(cart_items.count(), 2)
        sizes = set(cart_items.values_list('size', flat=True))
        self.assertEqual(sizes, {'S', 'XL'})

    def test_fashion_size_stock_limit_enforcement(self):
        self.client.force_login(self.user)
        # Size L has 0 stock -> should fail
        response_l = self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {'size': 'L'}
        )
        self.assertEqual(CartItem.objects.filter(product=self.fashion_product, size='L').count(), 0)

        # Size S has 1 stock -> first add succeeds
        self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {'size': 'S'}
        )
        item_s = CartItem.objects.get(product=self.fashion_product, size='S')
        self.assertEqual(item_s.quantity, 1)

        # Second add for Size S exceeds stock -> stays 1
        self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.fashion_product.id}),
            {'size': 'S'}
        )
        item_s.refresh_from_db()
        self.assertEqual(item_s.quantity, 1)

    def test_non_fashion_product_adds_without_size(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.electronics_product.id}),
            {}
        )
        self.assertEqual(response.status_code, 302)
        cart_item = CartItem.objects.get(product=self.electronics_product)
        self.assertIsNone(cart_item.size)

