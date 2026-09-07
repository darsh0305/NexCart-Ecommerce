from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from products.models import Category, Product
from sellers.models import SellerProfile

User = get_user_model()


# ============================================================
# ADMIN ACCESS PROTECTION
# ============================================================

def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff/superuser.
    """
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(
                request,
                'You do not have permission to access the admin dashboard.'
            )
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================
# ADMIN DASHBOARD OVERVIEW
# ============================================================

@admin_required
def admin_dashboard(request):

    total_users = User.objects.count()

    total_sellers = SellerProfile.objects.count()

    approved_sellers = SellerProfile.objects.filter(
        is_approved=True
    ).count()

    pending_sellers = SellerProfile.objects.filter(
        is_approved=False
    ).count()

    total_products = Product.objects.count()

    active_products = Product.objects.filter(
        is_active=True
    ).count()

    total_orders = Order.objects.count()

    pending_orders = Order.objects.filter(
        status='pending'
    ).count()

    total_revenue = (
        Order.objects.filter(
            payment_status='paid'
        ).aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )

    recent_orders = Order.objects.select_related(
        'user'
    ).order_by(
        '-created_at'
    )[:8]

    pending_seller_list = SellerProfile.objects.filter(
        is_approved=False
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )[:5]

    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'approved_sellers': approved_sellers,
        'pending_sellers': pending_sellers,
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'pending_seller_list': pending_seller_list,
    }

    return render(
        request,
        'dashboard/admin_dashboard.html',
        context
    )


# ============================================================
# ADMIN ORDERS MANAGEMENT
# ============================================================

@admin_required
def admin_orders(request):

    orders = Order.objects.select_related(
        'user',
        'address'
    ).prefetch_related(
        'items__product__seller__seller_profile'
    ).order_by(
        '-created_at'
    )

    # Search
    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:
        if search.isdigit():
            orders = orders.filter(
                Q(id=int(search)) |
                Q(order_number__icontains=search) |
                Q(address__phone__icontains=search)
            )
        else:
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(address__full_name__icontains=search)
            )

    # Delivery status filter
    status = request.GET.get(
        'status',
        ''
    ).strip()

    if status:
        orders = orders.filter(
            status=status
        )

    # Payment status filter
    payment_status = request.GET.get(
        'payment_status',
        ''
    ).strip()

    if payment_status:
        orders = orders.filter(
            payment_status=payment_status
        )

    context = {
        'orders': orders,
        'search': search,
        'selected_status': status,
        'selected_payment_status': payment_status,
        'total_orders_count': Order.objects.count(),
    }

    return render(
        request,
        'dashboard/orders.html',
        context
    )


# ============================================================
# ADMIN ORDER DETAILS
# ============================================================

@admin_required
def admin_order_detail(
    request,
    order_id
):
    if str(order_id).isdigit():
        order = get_object_or_404(
            Order.objects.select_related(
                'user',
                'address'
            ).prefetch_related(
                'items__product__seller__seller_profile'
            ),
            id=int(order_id)
        )
    else:
        order = get_object_or_404(
            Order.objects.select_related(
                'user',
                'address'
            ).prefetch_related(
                'items__product__seller__seller_profile'
            ),
            order_number=order_id
        )

    return render(
        request,
        'dashboard/order_detail.html',
        {
            'order': order
        }
    )


# ============================================================
# ADMIN UPDATE DELIVERY STATUS
# ============================================================

@admin_required
def admin_update_order_status(
    request,
    order_id
):
    if str(order_id).isdigit():
        order = get_object_or_404(Order, id=int(order_id))
    else:
        order = get_object_or_404(Order, order_number=order_id)

    if request.method == 'POST':
        new_status = request.POST.get(
            'status'
        )

        allowed_statuses = [
            'pending',
            'confirmed',
            'processing',
            'shipped',
            'out_for_delivery',
            'delivered',
            'cancelled',
        ]

        if new_status not in allowed_statuses:
            messages.error(
                request,
                'Invalid delivery status.'
            )
            return redirect(
                'admin_order_detail',
                order_id=order.id
            )

        old_status = order.status
        order.status = new_status

        # If status updated to cancelled from non-cancelled, restore product stock
        if new_status == 'cancelled' and old_status != 'cancelled':
            for item in order.items.select_related('product'):
                if item.product:
                    item.product.stock += item.quantity
                    if item.product.stock > 0 and item.product.status == 'out_of_stock':
                        item.product.status = 'active'
                        item.product.is_active = True
                    item.product.save(
                        update_fields=[
                            'stock',
                            'status',
                            'is_active',
                            'updated_at'
                        ]
                    )

        # If COD and marked delivered, update payment status to paid
        if new_status == 'delivered' and order.payment_method == 'cod' and order.payment_status == 'pending':
            order.payment_status = 'paid'
            order.save(
                update_fields=[
                    'status',
                    'payment_status',
                    'updated_at'
                ]
            )
            messages.success(
                request,
                f'Order #{order.id} status updated to Delivered and Cash on Delivery marked as Paid.'
            )
        else:
            order.save(
                update_fields=[
                    'status',
                    'updated_at'
                ]
            )
            messages.success(
                request,
                f'Order #{order.id} status updated to {order.get_status_display()} successfully.'
            )

    return redirect(
        'admin_order_detail',
        order_id=order.id
    )


# ============================================================
# SELLER APPROVAL QUICK ACTIONS
# ============================================================

@admin_required
@require_POST
def approve_seller_quick(request, seller_id):
    seller_profile = get_object_or_404(SellerProfile, id=seller_id)
    seller_profile.is_approved = True
    seller_profile.save(update_fields=['is_approved', 'updated_at'])
    messages.success(
        request,
        f"Seller '{seller_profile.store_name}' has been approved successfully."
    )
    return redirect('admin_dashboard')


@admin_required
@require_POST
def reject_seller_quick(request, seller_id):
    seller_profile = get_object_or_404(SellerProfile, id=seller_id)
    seller_profile.is_approved = False
    seller_profile.save(update_fields=['is_approved', 'updated_at'])
    messages.warning(
        request,
        f"Seller '{seller_profile.store_name}' status set to unapproved/pending."
    )
    return redirect('admin_dashboard')
