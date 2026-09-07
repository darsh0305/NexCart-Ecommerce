import json
from decimal import Decimal
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order, OrderItem
from products.models import (
    Category,
    Product,
    ProductImage,
    ProductSizeVariant,
)


def seller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.role != 'seller' and not hasattr(request.user, 'seller_profile'):
            messages.error(
                request,
                'Seller access required. Customer accounts cannot access the seller dashboard.'
            )
            return redirect('home')

        if not hasattr(request.user, 'seller_profile'):
            from .models import SellerProfile
            SellerProfile.objects.create(
                user=request.user,
                store_name=f"{request.user.first_name or request.user.username}'s Store",
                phone=getattr(request.user, 'phone_number', ''),
                is_approved=True
            )

        if not request.user.seller_profile.is_approved:
            messages.error(
                request,
                'Your seller account is awaiting approval.'
            )
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper


# ==========================================
# SELLER DASHBOARD
# ==========================================

@login_required
@seller_required
def seller_dashboard(request):
    seller = request.user

    products = Product.objects.filter(seller=seller)

    total_products = products.count()

    low_stock_products = products.filter(
        stock__gt=0,
        stock__lte=5
    ).count()

    out_of_stock_products = products.filter(
        stock=0
    ).count()

    seller_orders = Order.objects.filter(
        items__product__seller=seller
    ).distinct()

    total_orders = seller_orders.count()

    # Calculate total revenue
    paid_items = OrderItem.objects.filter(
        product__seller=seller,
        order__payment_status='paid'
    )
    total_sales = paid_items.aggregate(total=Sum('total_price'))['total'] or 0

    recent_orders = seller_orders.order_by('-created_at')[:5]

    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'recent_orders': recent_orders,
    }

    return render(request, 'sellers/dashboard.html', context)


# ==========================================
# SELLER PRODUCTS
# ==========================================

@login_required
@seller_required
def seller_products(request):
    products = Product.objects.filter(
        seller=request.user
    ).select_related(
        'category'
    ).prefetch_related(
        'images'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'sellers/products.html',
        {
            'products': products
        }
    )


# ==========================================
# ADD PRODUCT
# ==========================================

@login_required
@seller_required
def seller_product_add(request):
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        discount_percentage = request.POST.get('discount_percentage', 0) or 0
        stock = request.POST.get('stock', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 5) or 5
        brand = request.POST.get('brand', '')
        author = request.POST.get('author', '')
        status = request.POST.get('status', 'active')
        if status not in ['active', 'inactive', 'out_of_stock', 'draft']:
            status = 'active'
        image = request.FILES.get('image')

        category = get_object_or_404(
            Category,
            id=category_id,
            is_active=True
        )

        is_fashion = category and 'fashion' in category.name.lower()
        size_stocks = {}
        if is_fashion:
            size_stocks = {
                'S': int(request.POST.get('size_stock_s', 0) or 0),
                'M': int(request.POST.get('size_stock_m', 0) or 0),
                'L': int(request.POST.get('size_stock_l', 0) or 0),
                'XL': int(request.POST.get('size_stock_xl', 0) or 0),
                'XXL': int(request.POST.get('size_stock_xxl', 0) or 0),
            }
            if any(k in request.POST for k in ['size_stock_s', 'size_stock_m', 'size_stock_l', 'size_stock_xl', 'size_stock_xxl']):
                stock = sum(size_stocks.values())

        size = request.POST.get('size', '').strip() or None
        if is_fashion:
            if size not in ['S', 'M', 'L', 'XL', 'XXL']:
                size = None
        else:
            size = None

        product = Product.objects.create(
            seller=request.user,
            category=category,
            name=name,
            description=description,
            price=price,
            discount_percentage=discount_percentage,
            stock=stock,
            low_stock_threshold=low_stock_threshold,
            brand=brand,
            author=author,
            size=size,
            image=image,
            status=status,
            is_active=(status == 'active')
        )

        # Create size variants for Fashion products
        if is_fashion and size_stocks:
            for sz, sz_stock in size_stocks.items():
                ProductSizeVariant.objects.create(
                    product=product,
                    size=sz,
                    stock=sz_stock
                )

        # Additional Images
        additional_images = request.FILES.getlist('additional_images')
        for image_file in additional_images:
            ProductImage.objects.create(
                product=product,
                image=image_file
            )

        messages.success(request, 'Product added successfully.')
        return redirect('seller_products')

    return render(
        request,
        'sellers/product_form.html',
        {
            'categories': categories
        }
    )


# ==========================================
# EDIT PRODUCT
# ==========================================

@login_required
@seller_required
def seller_product_edit(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        seller=request.user
    )
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price = request.POST.get('price', product.price)
        product.discount_percentage = request.POST.get('discount_percentage', product.discount_percentage) or 0
        product.stock = request.POST.get('stock', product.stock)
        product.low_stock_threshold = request.POST.get('low_stock_threshold', product.low_stock_threshold) or 5
        product.brand = request.POST.get('brand', product.brand)
        product.author = request.POST.get('author', product.author)

        status = request.POST.get('status')
        if status in ['active', 'inactive', 'out_of_stock', 'draft']:
            product.status = status
            product.is_active = (status == 'active')

        category_id = request.POST.get('category')
        if category_id:
            product.category = get_object_or_404(
                Category,
                id=category_id,
                is_active=True
            )

        is_fashion = product.category and 'fashion' in product.category.name.lower()
        if is_fashion:
            size_stocks = {
                'S': int(request.POST.get('size_stock_s', 0) or 0),
                'M': int(request.POST.get('size_stock_m', 0) or 0),
                'L': int(request.POST.get('size_stock_l', 0) or 0),
                'XL': int(request.POST.get('size_stock_xl', 0) or 0),
                'XXL': int(request.POST.get('size_stock_xxl', 0) or 0),
            }
            if any(k in request.POST for k in ['size_stock_s', 'size_stock_m', 'size_stock_l', 'size_stock_xl', 'size_stock_xxl']):
                product.stock = sum(size_stocks.values())
                for sz, sz_stock in size_stocks.items():
                    ProductSizeVariant.objects.update_or_create(
                        product=product,
                        size=sz,
                        defaults={'stock': sz_stock}
                    )

        size = request.POST.get('size', '').strip() or None
        if is_fashion:
            if size in ['S', 'M', 'L', 'XL', 'XXL']:
                product.size = size
            else:
                product.size = None
        else:
            product.size = None

        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        product.save()

        # Additional Images
        additional_images = request.FILES.getlist('additional_images')
        for image_file in additional_images:
            ProductImage.objects.create(
                product=product,
                image=image_file
            )

        messages.success(request, 'Product updated successfully.')
        return redirect('seller_products')

    size_variant_map = {v.size: v.stock for v in product.size_variants.all()}

    return render(
        request,
        'sellers/product_edit.html',
        {
            'product': product,
            'categories': categories,
            'size_variant_map': size_variant_map,
        }
    )


# ==========================================
# UPDATE PRODUCT STATUS
# ==========================================

@login_required
@seller_required
def update_product_status(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        seller=request.user
    )

    if request.method == 'POST':
        status = request.POST.get('status')
        allowed_statuses = [
            'active',
            'inactive',
            'out_of_stock',
            'draft',
        ]

        if status not in allowed_statuses:
            messages.error(
                request,
                'Invalid product status.'
            )
            return redirect('seller_products')

        product.status = status
        product.is_active = (status == 'active')
        product.save(
            update_fields=[
                'status',
                'is_active',
                'updated_at'
            ]
        )

        messages.success(
            request,
            f"'{product.name}' status updated to {product.get_status_display()} successfully."
        )

    return redirect('seller_products')


# ==========================================
# DELETE PRODUCT
# ==========================================

@login_required
@seller_required
def seller_product_delete(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        seller=request.user
    )

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('seller_products')

    return render(
        request,
        'sellers/product_delete.html',
        {
            'product': product
        }
    )


# ==========================================
# SELLER ORDERS
# ==========================================

@login_required
@seller_required
def seller_orders(request):
    seller = request.user

    orders = Order.objects.filter(
        items__product__seller=seller
    ).distinct().prefetch_related('items', 'items__product').order_by('-created_at')

    orders_data = []
    for order in orders:
        seller_items = order.items.filter(product__seller=seller)
        seller_subtotal = sum(item.total_price for item in seller_items)
        orders_data.append({
            'order': order,
            'seller_items': seller_items,
            'seller_subtotal': seller_subtotal,
        })

    return render(
        request,
        'sellers/orders.html',
        {
            'orders': orders,
            'orders_data': orders_data,
        }
    )


# ==========================================
# UPDATE ORDER STATUS (DELIVERY STATUS)
# ==========================================

@login_required
@seller_required
def update_order_status(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        items__product__seller=request.user
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
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
            return redirect('seller_orders')

        order.status = new_status
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
                f'Order #{order.order_number} marked as Delivered and Cash on Delivery payment updated to Paid.'
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
                f'Order #{order.order_number} status updated to {order.get_status_display()} successfully.'
            )

    return redirect('seller_orders')


# ==========================================
# SALES REPORTS
# ==========================================

@login_required
@seller_required
def seller_sales_report(request):
    seller = request.user

    # Multi-seller safe items filter: only calculate revenue and items for this seller
    seller_items = OrderItem.objects.filter(
        product__seller=seller
    ).exclude(
        order__status='cancelled'
    )

    revenue_expression = ExpressionWrapper(
        F('quantity') * F('price'),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    total_revenue = (
        seller_items.aggregate(
            total=Sum(revenue_expression)
        )['total'] or Decimal('0.00')
    )

    total_products_sold = (
        seller_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
    )

    total_orders = seller_items.values(
        'order'
    ).distinct().count()

    average_order_value = Decimal('0.00')
    if total_orders:
        average_order_value = (
            total_revenue / total_orders
        )

    daily_sales = (
        seller_items
        .annotate(
            sale_date=TruncDate(
                'order__created_at'
            )
        )
        .values(
            'sale_date'
        )
        .annotate(
            revenue=Sum(
                revenue_expression
            ),
            products=Sum(
                'quantity'
            )
        )
        .order_by(
            '-sale_date'
        )[:30]
    )

    recent_orders = (
        Order.objects
        .filter(
            items__product__seller=seller
        )
        .exclude(
            status='cancelled'
        )
        .distinct()
        .prefetch_related('items', 'items__product')
        .order_by(
            '-created_at'
        )[:10]
    )

    recent_orders_data = []
    for ro in recent_orders:
        s_items = ro.items.filter(product__seller=seller)
        subtotal = sum(i.total_price for i in s_items)
        qty = sum(i.quantity for i in s_items)
        recent_orders_data.append({
            'order': ro,
            'seller_subtotal': subtotal,
            'products_count': qty,
            'items': s_items,
        })

    # Catalog & inventory stats
    total_products = Product.objects.filter(seller=seller).count()
    low_stock_products = Product.objects.filter(seller=seller, stock__gt=0, stock__lte=5).count()
    out_of_stock_products = Product.objects.filter(seller=seller, stock=0).count()

    # Top products by revenue
    top_products = (
        seller_items
        .values('product_name')
        .annotate(
            revenue=Sum(revenue_expression),
            units=Sum('quantity')
        )
        .order_by('-revenue')[:6]
    )

    # Chart data serialization (chronological order)
    daily_sales_list = list(reversed(list(daily_sales)))
    chart_labels = [day['sale_date'].strftime('%d %b') for day in daily_sales_list if day['sale_date']]
    chart_revenue = [float(day['revenue'] or 0) for day in daily_sales_list]
    chart_units = [int(day['products'] or 0) for day in daily_sales_list]

    top_product_labels = [p['product_name'][:25] for p in top_products]
    top_product_revenue = [float(p['revenue'] or 0) for p in top_products]

    # Order Status Distribution
    seller_orders_all = Order.objects.filter(items__product__seller=seller).distinct()
    status_summary = {
        'Delivered': seller_orders_all.filter(status='delivered').count(),
        'Shipped / Out': seller_orders_all.filter(status__in=['shipped', 'out_for_delivery']).count(),
        'Confirmed / Processing': seller_orders_all.filter(status__in=['confirmed', 'processing']).count(),
        'Pending': seller_orders_all.filter(status='pending').count(),
    }
    # Filter out 0 count keys if empty
    status_labels = [k for k, v in status_summary.items() if v > 0]
    status_data = [v for k, v in status_summary.items() if v > 0]

    # Recent sold items ledger
    recent_sold_items = seller_items.select_related(
        'order',
        'product'
    ).order_by(
        '-order__created_at'
    )[:10]

    context = {
        'total_revenue': total_revenue,
        'total_sales': total_revenue,
        'total_products_sold': total_products_sold,
        'total_quantity_sold': total_products_sold,
        'total_orders': total_orders,
        'average_order_value': average_order_value,
        'daily_sales': daily_sales,
        'recent_orders': recent_orders,
        'recent_orders_data': recent_orders_data,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'recent_sold_items': recent_sold_items,
        'top_products': top_products,
        # Chart JSON series
        'chart_labels_json': json.dumps(chart_labels),
        'chart_revenue_json': json.dumps(chart_revenue),
        'chart_units_json': json.dumps(chart_units),
        'top_product_labels_json': json.dumps(top_product_labels),
        'top_product_revenue_json': json.dumps(top_product_revenue),
        'status_labels_json': json.dumps(status_labels),
        'status_data_json': json.dumps(status_data),
    }

    return render(
        request,
        'sellers/sales_report.html',
        context
    )


