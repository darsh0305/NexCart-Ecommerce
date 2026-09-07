from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, get_user
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from orders.models import Order
from products.models import Product
from sellers.models import SellerProfile

from .forms import (
    AddressForm,
    LoginForm,
    ProfileUpdateForm,
    RegistrationForm,
)
from .models import Address, User
from .tokens import email_verification_token



# ==========================================
# REGISTER
# ==========================================

def register_view(request):

    if request.user.is_authenticated:
        if request.GET.get('role') == 'seller':
            logout(request)
        else:
            return redirect('home')

    if request.method == 'POST':

        form = RegistrationForm(request.POST)

        if form.is_valid():

            # Save user
            user = form.save(
                commit=False
            )

            # Email verification is NOT required for login
            user.is_email_verified = False

            user.save()

            if user.role == 'seller':
                from sellers.models import SellerProfile
                SellerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'store_name': f"{user.first_name or user.username}'s Store",
                        'phone': user.phone_number or '',
                        'is_approved': False,
                    }
                )

            # Create verification token
            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )

            token = email_verification_token.make_token(
                user
            )

            # Create verification URL
            verification_url = request.build_absolute_uri(
                reverse(
                    'verify_email',
                    kwargs={
                        'uidb64': uid,
                        'token': token
                    }
                )
            )

            # Send verification email
            send_mail(

                subject='Verify your NexCart account',

                message=(
                    f'Hello {user.first_name},\n\n'
                    f'Welcome to NexCart!\n\n'
                    f'Please verify your email using the link below:\n\n'
                    f'{verification_url}\n\n'
                    f'Thank you,\n'
                    f'NexCart Team'
                ),

                from_email=None,

                recipient_list=[
                    user.email
                ],

                fail_silently=True,
            )

            messages.success(
                request,
                'Your NexCart account has been created successfully!'
            )

            # User can login immediately
            return redirect('login')

    else:

        form = RegistrationForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


# ==========================================
# LOGIN
# ==========================================

def login_view(request):

    # If already logged in
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')
        if request.user.role == 'seller':
            return redirect('seller_dashboard')
        return redirect('home')

    if request.method == 'POST':

        form = LoginForm(
            request.POST
        )

        if form.is_valid():

            identifier = form.cleaned_data[
                'email'
            ]

            password = form.cleaned_data[
                'password'
            ]

            # Authenticate using email or username
            user = authenticate(
                request,
                username=identifier,
                email=identifier,
                password=password
            )

            if user is not None:

                # Login user
                # Email verification is NOT checked
                login(
                    request,
                    user
                )

                # Ensure session is properly set
                request.session.modified = True

                messages.success(
                    request,
                    f'Welcome back, '
                    f'{user.first_name or user.username}!'
                )

                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)

                if user.is_superuser or user.is_staff:
                    return redirect('admin_dashboard')

                if user.role == 'seller':
                    return redirect('seller_dashboard')

                return redirect(
                    'home'
                )

            else:

                messages.error(
                    request,
                    'Invalid email/username or password.'
                )

    else:

        form = LoginForm()

    return render(
        request,
        'accounts/login.html',
        {
            'form': form,
            'next': request.GET.get('next', '')
        }
    )


# ==========================================
# LOGOUT
# ==========================================

def logout_view(request):
    """
    Logout view that properly clears all session data
    and prevents session-related issues.
    """
    logout(request)
    
    # Create response to home
    response = redirect('home')
    
    # Clear any cached user-related cookies
    response.delete_cookie('sessionid')
    
    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return response


# ==========================================
# PROFILE
# ==========================================

@login_required
@never_cache
def profile_view(request):
    """
    Display and edit user profile.
    Ensures the current logged-in user's profile is always shown with rich account overview details.
    """
    # Refresh user from database to ensure we have the latest data
    current_user = User.objects.get(pk=request.user.pk)

    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=current_user
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your profile information has been updated successfully.'
            )
            return redirect('profile')
    else:
        form = ProfileUpdateForm(
            instance=current_user
        )

    # Fetch customer orders & stats
    orders_qs = Order.objects.filter(user=current_user).order_by('-created_at')
    total_orders = orders_qs.count()
    recent_orders = orders_qs.prefetch_related('items__product')[:3]
    active_orders_count = orders_qs.filter(
        status__in=['pending', 'confirmed', 'processing', 'shipped', 'out_for_delivery']
    ).count()

    # Fetch customer addresses
    addresses_qs = Address.objects.filter(user=current_user).order_by('-is_default', '-created_at')
    total_addresses = addresses_qs.count()
    default_address = addresses_qs.filter(is_default=True).first() or addresses_qs.first()

    return render(
        request,
        'accounts/profile.html',
        {
            'form': form,
            'user': current_user,
            'total_orders': total_orders,
            'recent_orders': recent_orders,
            'active_orders_count': active_orders_count,
            'total_addresses': total_addresses,
            'default_address': default_address,
            'saved_addresses': addresses_qs[:2],
        }
    )


# ==========================================
# VERIFY EMAIL
# ==========================================

def verify_email(
    request,
    uidb64,
    token
):

    try:

        uid = force_str(
            urlsafe_base64_decode(
                uidb64
            )
        )

        user = User.objects.get(
            pk=uid
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):

        user = None

    # Check verification token
    if (
        user is not None
        and email_verification_token.check_token(
            user,
            token
        )
    ):

        user.is_email_verified = True

        user.save(
            update_fields=[
                'is_email_verified'
            ]
        )

        messages.success(
            request,
            'Your email has been verified successfully!'
        )

        return redirect(
            'login'
        )

    else:

        messages.error(
            request,
            'Verification link is invalid or has expired.'
        )

        return redirect(
            'login'
        )


# ==========================================
# ADDRESS MANAGEMENT
# ==========================================

@login_required
def address_list(request):
    addresses = Address.objects.filter(
        user=request.user
    )

    return render(
        request,
        'accounts/address_list.html',
        {
            'addresses': addresses
        }
    )


@login_required
def add_address(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = AddressForm(request.POST)

        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()

            # If this is the first address, automatically make it default.
            if not Address.objects.filter(
                user=request.user
            ).exclude(
                id=address.id
            ).exists():
                address.is_default = True
                address.save(
                    update_fields=['is_default']
                )

            # If user selected this address as default, make other addresses non-default.
            elif address.is_default:
                Address.objects.filter(
                    user=request.user
                ).exclude(
                    id=address.id
                ).update(
                    is_default=False
                )

            messages.success(
                request,
                'Address added successfully.'
            )

            if next_url:
                return redirect(next_url)
            return redirect('address_list')
    else:
        form = AddressForm()

    return render(
        request,
        'accounts/address_form.html',
        {
            'form': form,
            'title': 'Add Address',
            'next': next_url,
        }
    )


@login_required
def edit_address(
    request,
    address_id
):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = AddressForm(
            request.POST,
            instance=address
        )

        if form.is_valid():
            address = form.save()

            if address.is_default:
                Address.objects.filter(
                    user=request.user
                ).exclude(
                    id=address.id
                ).update(
                    is_default=False
                )

            messages.success(
                request,
                'Address updated successfully.'
            )

            if next_url:
                return redirect(next_url)
            return redirect('address_list')
    else:
        form = AddressForm(
            instance=address
        )

    return render(
        request,
        'accounts/address_form.html',
        {
            'form': form,
            'title': 'Edit Address',
            'address': address,
            'next': next_url,
        }
    )


@login_required
def delete_address(
    request,
    address_id
):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    was_default = address.is_default
    address.delete()

    # If default address was deleted, choose another address as default.
    if was_default:
        new_default = Address.objects.filter(
            user=request.user
        ).first()

        if new_default:
            new_default.is_default = True
            new_default.save(
                update_fields=['is_default']
            )

    messages.success(
        request,
        'Address deleted successfully.'
    )

    return redirect('address_list')


@login_required
def set_default_address(
    request,
    address_id
):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    Address.objects.filter(
        user=request.user
    ).update(
        is_default=False
    )

    address.is_default = True
    address.save(
        update_fields=['is_default']
    )

    messages.success(
        request,
        'Default address updated.'
    )

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)

    return redirect('address_list')


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def admin_check(user):
    return (
        user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


@user_passes_test(
    admin_check,
    login_url='login'
)
def admin_dashboard(request):

    User = get_user_model()

    # --------------------------------------------------------
    # USERS & SELLERS
    # --------------------------------------------------------

    total_users = User.objects.count()

    total_sellers = User.objects.filter(
        role='seller'
    ).count() if hasattr(User, 'role') else SellerProfile.objects.count()

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    total_products = Product.objects.count()

    low_stock_products = Product.objects.filter(
        stock__lte=5,
        stock__gt=0
    ).count()

    out_of_stock_products = Product.objects.filter(
        stock=0
    ).count()

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    total_orders = Order.objects.count()

    pending_orders = Order.objects.filter(
        status='pending'
    ).count()

    confirmed_orders = Order.objects.filter(
        status='confirmed'
    ).count()

    shipped_orders = Order.objects.filter(
        status='shipped'
    ).count()

    out_for_delivery_orders = Order.objects.filter(
        status='out_for_delivery'
    ).count()

    delivered_orders = Order.objects.filter(
        status='delivered'
    ).count()

    cancelled_orders = Order.objects.filter(
        status='cancelled'
    ).count()

    # --------------------------------------------------------
    # PAYMENTS & REVENUE
    # --------------------------------------------------------

    total_revenue = (
        Order.objects.filter(
            payment_status='paid'
        ).aggregate(
            total=Sum('total_amount')
        )['total']
        or Decimal('0.00')
    )

    paid_payments = Order.objects.filter(
        payment_status='paid'
    ).count()

    pending_payments = Order.objects.filter(
        payment_status='pending'
    ).count()

    failed_payments = Order.objects.filter(
        payment_status='failed'
    ).count()

    cod_orders = Order.objects.filter(
        payment_method='cod'
    ).count()

    # --------------------------------------------------------
    # RECENT ORDERS & SALES ANALYTICS
    # --------------------------------------------------------

    recent_orders = Order.objects.select_related(
        'user'
    ).order_by(
        '-created_at'
    )[:10]

    daily_sales = (
        Order.objects.filter(
            payment_status='paid'
        )
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            total=Sum('total_amount'),
            orders=Count('id')
        )
        .order_by('date')
    )

    if not daily_sales.exists():
        daily_sales = (
            Order.objects.all()
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Sum('total_amount'),
                orders=Count('id')
            )
            .order_by('date')
        )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'shipped_orders': shipped_orders,
        'out_for_delivery_orders': out_for_delivery_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'paid_payments': paid_payments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'cod_orders': cod_orders,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'recent_orders': recent_orders,
        'daily_sales': daily_sales,
    }

    return render(
        request,
        'accounts/admin_dashboard.html',
        context
    )
