from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import Category, Product


class ProductGalleryFallbackTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='testpass123',
            role='seller'
        )
        self.category = Category.objects.create(name='Electronics Test', slug='electronics-test-category')
        self.product = Product.objects.create(
            category=self.category,
            seller=self.user,
            name='Test Product',
            slug='test-product-fallback-gallery',
            description='Test product description',
            price=100,
            stock=10,
            image='products/test-image.png',
            status='active',
        )

    def test_product_detail_has_gallery_fallback(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('gallery_images_json', response.context)
        self.assertEqual(len(response.context['gallery_images']), 1)
        self.assertEqual(response.context['gallery_images'][0], self.product.image.url)

    def test_product_detail_shows_expected_delivery(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('expected_delivery_date', response.context)
        self.assertIn('delivery_start_date', response.context)
        self.assertIn('delivery_end_date', response.context)

        # Expected delivery day and date format in HTML for in-stock product
        expected_date = response.context['expected_delivery_date']
        day_str = expected_date.strftime('%A')
        self.assertContains(response, 'Expected Delivery:')
        self.assertContains(response, day_str)
        self.assertContains(response, 'delivery-estimate-card')
        self.assertContains(response, 'deliveryPincodeInput')

    def test_product_detail_out_of_stock_delivery(self):
        self.product.stock = 0
        self.product.status = 'out_of_stock'
        self.product.save()

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delivery Currently Unavailable')

    def test_pincodes_near_each_other_have_same_delivery_date(self):
        # Two pincodes in Delhi (110001 and 110088)
        resp1 = self.client.get(reverse('check_pincode_delivery'), {'pincode': '110001'})
        resp2 = self.client.get(reverse('check_pincode_delivery'), {'pincode': '110088'})

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)

        data1 = resp1.json()
        data2 = resp2.json()

        self.assertEqual(data1['delivery_days'], data2['delivery_days'])
        self.assertEqual(data1['expected_delivery_date'], data2['expected_delivery_date'])

    def test_pincodes_far_apart_have_different_delivery_dates(self):
        # Local MMR (400001 - 1 day) vs Delhi (110001 - 3 days) vs North-East (795001 - 7 days)
        resp_local = self.client.get(reverse('check_pincode_delivery'), {'pincode': '400001'})
        resp_north = self.client.get(reverse('check_pincode_delivery'), {'pincode': '110001'})
        resp_far = self.client.get(reverse('check_pincode_delivery'), {'pincode': '795001'})

        data_local = resp_local.json()
        data_north = resp_north.json()
        data_far = resp_far.json()

        self.assertNotEqual(data_local['delivery_days'], data_north['delivery_days'])
        self.assertNotEqual(data_north['delivery_days'], data_far['delivery_days'])
        self.assertNotEqual(data_local['expected_delivery_date'], data_far['expected_delivery_date'])

    def test_invalid_pincode_handling(self):
        resp = self.client.get(reverse('check_pincode_delivery'), {'pincode': '123'})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['success'])

    def test_coordinate_location_lookup(self):
        # Coordinates for Delhi (~28.6, 77.2)
        resp = self.client.get(reverse('check_pincode_delivery'), {'lat': '28.6139', 'lng': '77.2090'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['pincode'], '110001')
        self.assertIn('Delhi', data['location'])


