from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()


class AdminLoginTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        # Create Admin user (superuser & staff)
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@nexcart.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User'
        )

        # Create Seller user
        self.seller_user = User.objects.create_user(
            username='selleruser',
            email='seller@nexcart.com',
            password='SellerPassword123!',
            role='seller',
            first_name='Seller',
            last_name='User'
        )

        # Create Customer user
        self.customer_user = User.objects.create_user(
            username='customeruser',
            email='customer@nexcart.com',
            password='CustomerPassword123!',
            role='customer',
            first_name='Customer',
            last_name='User'
        )

    def test_admin_login_using_email(self):
        """Admin can log in using their email on the login page and is redirected to admin dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'admin@nexcart.com',
            'password': 'AdminPassword123!'
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

        # Check that user is authenticated as the admin in session
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_login_using_username(self):
        """Admin can log in using their username on the login page and is redirected to admin dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'adminuser',
            'password': 'AdminPassword123!'
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_admin_login_with_next_param(self):
        """Admin login respects next parameter if provided."""
        response = self.client.post(reverse('login') + '?next=/products/', {
            'email': 'admin@nexcart.com',
            'password': 'AdminPassword123!'
        })
        self.assertRedirects(response, '/products/')

    def test_seller_login_redirects_to_seller_dashboard(self):
        """Seller user logs in and is redirected to seller dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'seller@nexcart.com',
            'password': 'SellerPassword123!'
        })
        self.assertRedirects(response, reverse('seller_dashboard'))

    def test_customer_login_redirects_to_home(self):
        """Customer user logs in and is redirected to home page."""
        response = self.client.post(reverse('login'), {
            'email': 'customer@nexcart.com',
            'password': 'CustomerPassword123!'
        })
        self.assertRedirects(response, reverse('home'))

    def test_admin_already_logged_in_redirects_to_admin_dashboard(self):
        """When an admin is already logged in, visiting login page redirects to admin dashboard."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_invalid_login(self):
        """Invalid credentials show error and don't log in."""
        response = self.client.post(reverse('login'), {
            'email': 'admin@nexcart.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email/username or password.')


class AddressManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123',
            first_name='Darsh',
            last_name='Patel',
            role='customer'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            role='customer'
        )

    def test_add_first_address_auto_default(self):
        """First address added by user automatically becomes default."""
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('add_address'), {
            'full_name': 'Darsh Patel',
            'phone': '9876543210',
            'address_type': 'home',
            'address_line_1': 'Flat 101, Galaxy Apts',
            'address_line_2': 'Bodakdev',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'pincode': '380054',
            'landmark': 'Near Sindhu Bhavan',
        })
        self.assertRedirects(response, reverse('address_list'))
        from accounts.models import Address
        address = Address.objects.get(user=self.user1, full_name='Darsh Patel')
        self.assertTrue(address.is_default)

    def test_multiple_addresses_and_set_default(self):
        """User can add multiple addresses and switch default address."""
        from accounts.models import Address
        addr1 = Address.objects.create(
            user=self.user1,
            full_name='Darsh Home',
            phone='9876543210',
            address_type='home',
            address_line_1='Home address 1',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380054',
            is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user1,
            full_name='Darsh Work',
            phone='9876543210',
            address_type='work',
            address_line_1='Work address 2',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380015',
            is_default=False
        )

        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('set_default_address', kwargs={'address_id': addr2.id}))
        self.assertRedirects(response, reverse('address_list'))

        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_edit_address(self):
        """User can edit their own address."""
        from accounts.models import Address
        addr = Address.objects.create(
            user=self.user1,
            full_name='Darsh Patel',
            phone='9876543210',
            address_type='home',
            address_line_1='Old Street',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380054',
            is_default=True
        )
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('edit_address', kwargs={'address_id': addr.id}), {
            'full_name': 'Darsh K Patel',
            'phone': '9876543211',
            'address_type': 'home',
            'address_line_1': 'New Street 456',
            'address_line_2': 'New Area',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'pincode': '380054',
            'landmark': 'Near Park',
            'is_default': True,
        })
        self.assertRedirects(response, reverse('address_list'))
        addr.refresh_from_db()
        self.assertEqual(addr.full_name, 'Darsh K Patel')
        self.assertEqual(addr.address_line_1, 'New Street 456')

    def test_delete_default_address_reassigns_default(self):
        """Deleting default address automatically designates another address as default."""
        from accounts.models import Address
        addr1 = Address.objects.create(
            user=self.user1,
            full_name='Address 1',
            phone='9876543210',
            address_type='home',
            address_line_1='Street 1',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380054',
            is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user1,
            full_name='Address 2',
            phone='9876543210',
            address_type='work',
            address_line_1='Street 2',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380015',
            is_default=False
        )

        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('delete_address', kwargs={'address_id': addr1.id}))
        self.assertRedirects(response, reverse('address_list'))

        self.assertFalse(Address.objects.filter(id=addr1.id).exists())
        addr2.refresh_from_db()
        self.assertTrue(addr2.is_default)

    def test_address_security_isolation_between_users(self):
        """Customer cannot view, edit, or delete another customer's address."""
        from accounts.models import Address
        user2_addr = Address.objects.create(
            user=self.user2,
            full_name='User2 Address',
            phone='9111111111',
            address_type='home',
            address_line_1='User2 Street',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001',
            is_default=True
        )

        # Login as user1
        self.client.login(username='user1', password='password123')

        # Try to edit user2's address
        edit_response = self.client.get(reverse('edit_address', kwargs={'address_id': user2_addr.id}))
        self.assertEqual(edit_response.status_code, 404)

        # Try to delete user2's address
        delete_response = self.client.post(reverse('delete_address', kwargs={'address_id': user2_addr.id}))
        self.assertEqual(delete_response.status_code, 404)

        # Try to set user2's address as default
        default_response = self.client.post(reverse('set_default_address', kwargs={'address_id': user2_addr.id}))
        self.assertEqual(default_response.status_code, 404)


class AdminDashboardViewTests(TestCase):

    def setUp(self):
        self.client = Client()

        # Admin Staff User
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@nexcart.com',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True
        )

        # Normal Customer
        self.customer = User.objects.create_user(
            username='custuser',
            email='cust@example.com',
            password='password123',
            role='customer'
        )

        # Seller
        self.seller = User.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='password123',
            role='seller'
        )

    def test_admin_dashboard_accessible_by_staff(self):
        """Staff/superuser can access admin dashboard and view context."""
        self.client.login(username='adminuser', password='AdminPassword123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/admin_dashboard.html')
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'Total Users')
        self.assertContains(response, 'Total Sellers')
        self.assertContains(response, 'Total Products')
        self.assertContains(response, 'Total Orders')

    def test_admin_dashboard_inaccessible_by_customer(self):
        """Normal customer is blocked from accessing the admin dashboard and redirected."""
        self.client.login(username='custuser', password='password123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_admin_dashboard_inaccessible_by_anonymous_user(self):
        """Unauthenticated user is redirected to login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('admin_dashboard')}")



