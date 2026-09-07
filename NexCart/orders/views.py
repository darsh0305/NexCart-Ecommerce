import os
import uuid
import razorpay
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image,
)

from cart.models import Cart, CartItem
from accounts.models import Address
from .models import Order, OrderItem

# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


# ============================================================
# CHECKOUT
# ============================================================

@login_required
def checkout(request):

    # Get current user's cart
    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    # Get all cart items
    cart_items = cart.items.select_related(
        'product'
    )

    # Check if cart is empty
    if not cart_items.exists():

        messages.warning(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'cart_detail'
        )

    # Get user's saved addresses
    addresses = Address.objects.filter(
        user=request.user
    )

    # When user selects an address
    if request.method == 'POST':

        address_id = request.POST.get(
            'address_id'
        )

        # Address not selected
        if not address_id:

            messages.error(
                request,
                'Please select a delivery address.'
            )

            return redirect(
                'checkout'
            )

        # Make sure address belongs to current user
        address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user
        )

        # Show order confirmation page
        return render(
            request,
            'orders/place_order.html',
            {
                'cart': cart,
                'cart_items': cart_items,
                'address': address,
            }
        )

    # Display checkout page
    return render(
        request,
        'orders/checkout.html',
        {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
        }
    )


# ============================================================
# PLACE ORDER
# ============================================================

@login_required
@transaction.atomic
def place_order(
    request,
    address_id
):

    # Only allow POST request
    if request.method != 'POST':

        return redirect(
            'checkout'
        )

    # Get current user's cart
    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    # Get cart items
    cart_items = list(
        cart.items.select_related(
            'product'
        )
    )

    # Check empty cart
    if not cart_items:

        messages.warning(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'cart_detail'
        )

    # Get selected address
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # ========================================================
    # CHECK STOCK
    # ========================================================

    for item in cart_items:

        if item.quantity > item.product.stock:

            messages.error(
                request,
                f'Not enough stock for {item.product.name}.'
            )

            return redirect(
                'cart_detail'
            )

    # ========================================================
    # CALCULATE TOTAL
    # ========================================================

    subtotal = sum(
        item.total_price
        for item in cart_items
    )

    delivery_charge = cart.delivery_charge
    total_amount = cart.total_with_delivery

    # ========================================================
    # GENERATE ORDER NUMBER
    # ========================================================

    order_number = (
        'NC-' +
        uuid.uuid4().hex[:10].upper()
    )

    # ========================================================
    # CREATE ORDER WITH ADDRESS SNAPSHOT
    # ========================================================

    shipping_address_str = f"{address.address_line_1} {address.address_line_2}".strip()
    if address.landmark:
        shipping_address_str = f"{shipping_address_str} (Landmark: {address.landmark})"

    order = Order.objects.create(

        user=request.user,

        address=address,

        shipping_name=address.full_name,

        shipping_phone=address.phone,

        shipping_address=shipping_address_str,

        shipping_city=address.city,

        shipping_state=address.state,

        shipping_pincode=address.pincode,

        order_number=order_number,

        subtotal=subtotal,

        delivery_charge=delivery_charge,

        total_amount=total_amount,

        payment_method='cod',

        payment_status='pending',

        status='pending',

    )


    # ========================================================
    # CREATE ORDER ITEMS
    # ========================================================

    for item in cart_items:

        OrderItem.objects.create(

            order=order,

            product=item.product,

            product_name=item.product.name,

            price=item.product.discounted_price,

            quantity=item.quantity,

            size=item.size,

            total_price=item.total_price,

        )

        # Reduce product stock
        if item.size and item.product.has_size_variants:
            variant = item.product.size_variants.filter(size=item.size).first()
            if variant:
                variant.stock = max(0, variant.stock - item.quantity)
                variant.save(update_fields=['stock'])
            item.product.stock = sum(v.stock for v in item.product.size_variants.all())
        else:
            item.product.stock -= item.quantity

        if item.product.stock <= 0:
            item.product.stock = 0
            item.product.status = 'out_of_stock'
            item.product.is_active = False

        item.product.save(
            update_fields=[
                'stock',
                'status',
                'is_active',
                'updated_at',
            ]
        )

    # ========================================================
    # CLEAR CART
    # ========================================================

    cart.items.all().delete()

    # ========================================================
    # ORDER SUCCESS PAGE
    # ========================================================

    return redirect(
        'order_success',
        order_number=order.order_number
    )


# ============================================================
# CREATE RAZORPAY ORDER
# ============================================================

@login_required
def create_razorpay_order(request):

    if request.method != 'POST':

        return redirect(
            'checkout'
        )

    # --------------------------------------------------------
    # GET CART
    # --------------------------------------------------------

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    cart_items = list(
        cart.items.select_related(
            'product'
        )
    )

    # --------------------------------------------------------
    # CHECK EMPTY CART
    # --------------------------------------------------------

    if not cart_items:

        messages.warning(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'cart_detail'
        )

    # --------------------------------------------------------
    # GET ADDRESS
    # --------------------------------------------------------

    address_id = request.POST.get(
        'address_id'
    )

    if not address_id:

        messages.error(
            request,
            'Please select a shipping address.'
        )

        return redirect(
            'checkout'
        )

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # --------------------------------------------------------
    # CHECK STOCK
    # --------------------------------------------------------

    for item in cart_items:

        if item.quantity > item.product.stock:

            messages.error(
                request,
                f'Not enough stock for {item.product.name}.'
            )

            return redirect(
                'cart_detail'
            )

    # --------------------------------------------------------
    # CALCULATE TOTAL
    # --------------------------------------------------------

    subtotal = sum(
        item.total_price
        for item in cart_items
    )

    delivery_charge = cart.delivery_charge
    total_amount = cart.total_with_delivery

    # --------------------------------------------------------
    # CONVERT RUPEES TO PAISE
    # --------------------------------------------------------

    amount_in_paise = int(
        total_amount * 100
    )

    # Razorpay requires at least ₹1
    if amount_in_paise < 100:

        messages.error(
            request,
            'Order amount must be at least ₹1.'
        )

        return redirect(
            'checkout'
        )

    # --------------------------------------------------------
    # GENERATE NEXCART ORDER NUMBER
    # --------------------------------------------------------

    order_number = (
        'NC-' +
        uuid.uuid4().hex[:10].upper()
    )

    # --------------------------------------------------------
    # CREATE RAZORPAY ORDER
    # --------------------------------------------------------

    razorpay_data = {

        'amount': amount_in_paise,

        'currency': 'INR',

        'receipt': order_number,

        'notes': {

            'user_id': str(
                request.user.id
            ),

            'order_number': order_number,

        }

    }

    try:

        razorpay_order = razorpay_client.order.create(
            data=razorpay_data
        )

    except Exception as e:

        messages.error(
            request,
            'Unable to create Razorpay order. Please try again.'
        )

        print(
            'Razorpay Error:',
            e
        )

        return redirect(
            'checkout'
        )

    # --------------------------------------------------------
    # CREATE NEXCART ORDER
    # --------------------------------------------------------

    shipping_address_str = f"{address.address_line_1} {address.address_line_2}".strip()
    if address.landmark:
        shipping_address_str = f"{shipping_address_str} (Landmark: {address.landmark})"

    order = Order.objects.create(

        user=request.user,

        address=address,

        shipping_name=address.full_name,

        shipping_phone=address.phone,

        shipping_address=shipping_address_str,

        shipping_city=address.city,

        shipping_state=address.state,

        shipping_pincode=address.pincode,

        order_number=order_number,

        subtotal=subtotal,

        delivery_charge=delivery_charge,

        total_amount=total_amount,

        payment_method='razorpay',

        payment_status='pending',

        razorpay_order_id=razorpay_order['id'],

        status='pending',

    )


    # --------------------------------------------------------
    # CREATE ORDER ITEMS
    # --------------------------------------------------------

    for item in cart_items:

        OrderItem.objects.create(

            order=order,

            product=item.product,

            product_name=item.product.name,

            price=item.product.discounted_price,

            quantity=item.quantity,

            size=item.size,

            total_price=item.total_price,

        )

    # --------------------------------------------------------
    # SHOW RAZORPAY CHECKOUT PAGE
    # --------------------------------------------------------

    return render(
        request,
        'orders/razorpay_checkout.html',
        {
            'order': order,

            'razorpay_order_id':
                razorpay_order['id'],

            'razorpay_key_id':
                settings.RAZORPAY_KEY_ID,

            'amount':
                amount_in_paise,

            'amount_in_rupees':
                total_amount,

            'currency':
                'INR',

            'user':
                request.user,

        }
    )


# ============================================================
# VERIFY RAZORPAY PAYMENT
# ============================================================

@login_required
@transaction.atomic
def verify_razorpay_payment(request):

    if request.method != 'POST':

        return redirect(
            'checkout'
        )

    razorpay_order_id = request.POST.get(
        'razorpay_order_id'
    )

    razorpay_payment_id = request.POST.get(
        'razorpay_payment_id'
    )

    razorpay_signature = request.POST.get(
        'razorpay_signature'
    )

    # --------------------------------------------------------
    # CHECK DATA
    # --------------------------------------------------------

    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
    ]):

        messages.error(
            request,
            'Payment information is incomplete.'
        )

        return redirect(
            'checkout'
        )

    # --------------------------------------------------------
    # GET ORDER
    # --------------------------------------------------------

    order = get_object_or_404(
        Order,
        razorpay_order_id=razorpay_order_id,
        user=request.user
    )

    # --------------------------------------------------------
    # VERIFY SIGNATURE
    # --------------------------------------------------------

    try:

        razorpay_client.utility.verify_payment_signature({

            'razorpay_order_id':
                razorpay_order_id,

            'razorpay_payment_id':
                razorpay_payment_id,

            'razorpay_signature':
                razorpay_signature,

        })

    except razorpay.errors.SignatureVerificationError:

        order.payment_status = 'failed'

        order.save(
            update_fields=[
                'payment_status',
                'updated_at',
            ]
        )

        messages.error(
            request,
            'Payment verification failed.'
        )

        return redirect(
            'checkout'
        )

    except Exception as e:

        print(
            'Payment Verification Error:',
            e
        )

        messages.error(
            request,
            'Unable to verify payment.'
        )

        return redirect(
            'checkout'
        )

    # --------------------------------------------------------
    # PAYMENT VERIFIED
    # --------------------------------------------------------

    order.razorpay_payment_id = (
        razorpay_payment_id
    )

    order.razorpay_signature = (
        razorpay_signature
    )

    order.payment_status = 'paid'

    order.status = 'confirmed'

    order.save()

    # --------------------------------------------------------
    # REDUCE STOCK
    # --------------------------------------------------------

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    cart_items = list(
        cart.items.select_related(
            'product'
        )
    )

    for item in cart_items:

        if item.quantity > item.product.stock:

            order.payment_status = 'failed'

            order.status = 'cancelled'

            order.save()

            messages.error(
                request,
                f'Not enough stock for {item.product.name}.'
            )

            return redirect(
                'cart_detail'
            )

    for item in cart_items:
        if item.size and item.product.has_size_variants:
            variant = item.product.size_variants.filter(size=item.size).first()
            if variant:
                variant.stock = max(0, variant.stock - item.quantity)
                variant.save(update_fields=['stock'])
            item.product.stock = sum(v.stock for v in item.product.size_variants.all())
        else:
            item.product.stock -= item.quantity

        if item.product.stock <= 0:
            item.product.stock = 0
            item.product.status = 'out_of_stock'
            item.product.is_active = False

        item.product.save(
            update_fields=[
                'stock',
                'status',
                'is_active',
                'updated_at',
            ]
        )

    # --------------------------------------------------------
    # CLEAR CART
    # --------------------------------------------------------

    cart.items.all().delete()

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return redirect(
        'order_success',
        order_number=order.order_number
    )




@login_required
def order_success(
    request,
    order_number
):

    # Get order belonging to current user
    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user
    )

    # Get order items with related product
    order_items = order.items.select_related(
        'product'
    )

    return render(
        request,
        'orders/order_success.html',
        {
            'order': order,
            'order_items': order_items,
        }
    )


# ============================================================
# CUSTOMER ORDERS / MY ORDERS
# ============================================================

@login_required
def my_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).select_related(
        'address'
    ).prefetch_related(
        'items__product__seller__seller_profile'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'orders/my_orders.html',
        {
            'orders': orders,
        }
    )


@login_required
def order_list(request):
    return my_orders(request)


# ============================================================
# ORDER DETAIL
# ============================================================

@login_required
def order_detail(
    request,
    order_id=None,
    order_number=None
):
    query_kwargs = {'user': request.user}
    if order_id is not None:
        query_kwargs['id'] = order_id
    elif order_number is not None:
        if str(order_number).isdigit():
            query_kwargs['id'] = int(order_number)
        else:
            query_kwargs['order_number'] = order_number
    else:
        return redirect('my_orders')

    order = get_object_or_404(
        Order.objects.select_related(
            'address',
            'user'
        ).prefetch_related(
            'items__product__seller__seller_profile'
        ),
        **query_kwargs
    )

    can_cancel = order.status in ['pending', 'confirmed', 'processing']

    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order,
            'can_cancel': can_cancel,
        }
    )


# ============================================================
# REORDER
# ============================================================

@login_required
def reorder_order(
    request,
    order_id
):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    cart, _ = Cart.objects.get_or_create(
        user=request.user
    )

    added_count = 0
    unavailable_items = []

    for item in order.items.select_related('product'):
        product = item.product
        if not product or product.status != 'active' or product.stock <= 0:
            unavailable_items.append(item.product_name)
            continue

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            new_qty = min(cart_item.quantity + item.quantity, product.stock)
            cart_item.quantity = new_qty
            cart_item.save()
        else:
            cart_item.quantity = min(item.quantity, product.stock)
            cart_item.save()

        added_count += 1

    if added_count > 0:
        messages.success(
            request,
            f"Items from Order #{order.order_number} added to your cart."
        )

    if unavailable_items:
        messages.warning(
            request,
            f"The following item(s) are currently unavailable or out of stock: {', '.join(unavailable_items)}."
        )

    if added_count == 0 and unavailable_items:
        return redirect('order_detail', order_id=order.id)

    return redirect('cart_detail')


# ============================================================
# CANCEL ORDER
# ============================================================

@login_required
@transaction.atomic
def cancel_order(
    request,
    order_id
):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if request.method == 'POST':
        if order.status in ['pending', 'confirmed', 'processing']:
            # Restore stock for ordered items
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

            order.status = 'cancelled'
            order.save(
                update_fields=[
                    'status',
                    'updated_at'
                ]
            )

            messages.success(
                request,
                f"Order #{order.order_number} has been cancelled successfully."
            )
        else:
            messages.error(
                request,
                f"Order #{order.order_number} cannot be cancelled because it is already {order.get_status_display().lower()}."
            )

    return redirect('order_detail', order_id=order.id)


# ============================================================
# VIEW INVOICE (HTML PREVIEW)
# ============================================================

@login_required
def view_invoice(
    request,
    order_id
):
    # Support direct download query param (?download=pdf or ?download=1)
    if request.GET.get('download') in ['pdf', '1', 'true']:
        return download_invoice(request, order_id)

    # Ensure customer can only view their own invoice (staff can view any)
    if request.user.is_staff:
        order = get_object_or_404(
            Order.objects.select_related(
                'address',
                'user'
            ).prefetch_related(
                'items__product__category'
            ),
            id=order_id
        )
    else:
        order = get_object_or_404(
            Order.objects.select_related(
                'address',
                'user'
            ).prefetch_related(
                'items__product__category'
            ),
            id=order_id,
            user=request.user
        )

    # Check if any item in the order is a fashion product or has size
    has_fashion = any(
        (item.product and item.product.category and 'fashion' in item.product.category.name.lower()) or bool(item.size)
        for item in order.items.all()
    )

    items_with_details = []
    total_mrp = Decimal('0.00')
    total_savings = Decimal('0.00')

    for item in order.items.all():
        orig_price = item.product.price if (item.product and item.product.price) else item.price
        item_mrp_total = orig_price * item.quantity
        item_discount = max(Decimal('0.00'), (orig_price - item.price) * item.quantity)

        total_mrp += item_mrp_total
        total_savings += item_discount

        items_with_details.append({
            'item': item,
            'product_name': item.product_name,
            'product': item.product,
            'size': item.size,
            'quantity': item.quantity,
            'price': item.price,
            'orig_price': orig_price,
            'discount': item_discount,
            'total_price': item.total_price,
        })

    invoice_number = f"INV-{order.id:06d}"

    customer_name = order.shipping_name or (order.address.full_name if order.address else (order.user.get_full_name() or order.user.username))
    customer_phone = order.shipping_phone or (order.address.phone if order.address else "N/A")

    if order.shipping_address:
        address_line = order.shipping_address
        city_state_pin = f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}".strip(', -')
        landmark = ""
    elif order.address:
        address_line = f"{order.address.address_line_1} {order.address.address_line_2}".strip()
        city_state_pin = f"{order.address.city}, {order.address.state} - {order.address.pincode}"
        landmark = f"Landmark: {order.address.landmark}" if order.address.landmark else ""
    else:
        address_line = "No address specified"
        city_state_pin = ""
        landmark = ""

    if order.payment_method == 'razorpay':
        payment_method_display = "Online Razorpay"
    elif order.payment_method == 'cod':
        payment_method_display = "Cash on Delivery"
    else:
        payment_method_display = order.get_payment_method_display()

    # Use current local date and time for the invoice
    now = timezone.localtime(timezone.now()) if timezone.is_aware(timezone.now()) else timezone.now()
    invoice_date_display = now.strftime('%d %b %Y, %I:%M %p')

    context = {
        'order': order,
        'has_fashion': has_fashion,
        'items_with_details': items_with_details,
        'total_mrp': total_mrp,
        'total_savings': total_savings,
        'invoice_number': invoice_number,
        'invoice_date_display': invoice_date_display,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'address_line': address_line,
        'city_state_pin': city_state_pin,
        'landmark': landmark,
        'payment_method_display': payment_method_display,
    }

    return render(request, 'orders/invoice.html', context)


# ============================================================
# DOWNLOAD INVOICE PDF
# ============================================================

@login_required
def download_invoice(
    request,
    order_id
):
    # Ensure customer can only download their own invoice (staff can view any)
    if request.user.is_staff:
        order = get_object_or_404(
            Order.objects.select_related(
                'address',
                'user'
            ).prefetch_related(
                'items__product__category'
            ),
            id=order_id
        )
    else:
        order = get_object_or_404(
            Order.objects.select_related(
                'address',
                'user'
            ).prefetch_related(
                'items__product__category'
            ),
            id=order_id,
            user=request.user
        )

    # Check if any item in the order is a fashion product or has size
    has_fashion = any(
        (item.product and item.product.category and 'fashion' in item.product.category.name.lower()) or bool(item.size)
        for item in order.items.all()
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    header_title = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0B2A4A')
    )

    header_subtitle = ParagraphStyle(
        'HeaderSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#5B6B82')
    )

    invoice_title = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=2,
        textColor=colors.HexColor('#2563EB')
    )

    invoice_meta = ParagraphStyle(
        'InvoiceMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=2,
        textColor=colors.HexColor('#0F172A')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0B2A4A')
    )

    section_content = ParagraphStyle(
        'SectionContent',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#0F172A')
    )

    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#0F172A')
    )

    table_cell_discount = ParagraphStyle(
        'TableCellDiscount',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#059669')
    )

    table_cell_bold_right = ParagraphStyle(
        'TableCellBoldRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#0B2A4A')
    )

    elements = []

    # --------------------------------------------------------
    # HEADER SECTION WITH NEXCART LOGO
    # --------------------------------------------------------

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpeg')
    brand_text = [
        Paragraph('<b>NexCart</b>', header_title),
        Spacer(1, 2),
        Paragraph('Official Retail & Tax Invoice', header_subtitle),
        Paragraph('www.nexcart.com', header_subtitle)
    ]

    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=46, height=46)
        brand_table = Table([[logo_img, brand_text]], colWidths=[52, 218])
        brand_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        header_left = brand_table
    else:
        header_left = brand_text

    invoice_number_display = f"INV-{order.id:06d}"
    now = timezone.localtime(timezone.now()) if timezone.is_aware(timezone.now()) else timezone.now()
    invoice_date_str = now.strftime('%d %b %Y, %I:%M %p')

    header_right = [
        Paragraph('TAX INVOICE', invoice_title),
        Spacer(1, 2),
        Paragraph(f'<b>Invoice No:</b> {invoice_number_display}', invoice_meta),
        Paragraph(f'<b>Order ID:</b> {order.order_number}', invoice_meta),
        Paragraph(f'<b>Date:</b> {invoice_date_str}', invoice_meta),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[270, 253])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # Divider bar
    elements.append(
        HRFlowable(
            width='100%',
            thickness=1.5,
            color=colors.HexColor('#2563EB'),
            spaceAfter=12
        )
    )

    # --------------------------------------------------------
    # CUSTOMER & DELIVERY & PAYMENT INFO
    # --------------------------------------------------------

    customer_name = order.shipping_name or (order.address.full_name if order.address else (order.user.get_full_name() or order.user.username))
    customer_phone = order.shipping_phone or (order.address.phone if order.address else "N/A")

    bill_to_content = [
        Paragraph('<b>CUSTOMER INFORMATION</b>', section_heading),
        Spacer(1, 3),
        Paragraph(f'<b>{customer_name}</b>', section_content),
        Paragraph(f'Phone: {customer_phone}', section_content),
    ]

    if order.shipping_address:
        address_line = order.shipping_address
        city_state_pin = f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}".strip(', -')
        landmark = ""
    elif order.address:
        address_line = f"{order.address.address_line_1} {order.address.address_line_2}".strip()
        city_state_pin = f"{order.address.city}, {order.address.state} - {order.address.pincode}"
        landmark = f"Landmark: {order.address.landmark}" if order.address.landmark else ""
    else:
        address_line = "No address specified"
        city_state_pin = ""
        landmark = ""

    ship_to_content = [
        Paragraph('<b>DELIVERY ADDRESS</b>', section_heading),
        Spacer(1, 3),
        Paragraph(address_line, section_content),
        Paragraph(city_state_pin, section_content),
    ]
    if landmark:
        ship_to_content.append(
            Paragraph(landmark, section_content)
        )

    # Format payment method display
    if order.payment_method == 'razorpay':
        payment_method_display = "Online Razorpay"
    elif order.payment_method == 'cod':
        payment_method_display = "Cash on Delivery"
    else:
        payment_method_display = order.get_payment_method_display()

    payment_status_text = order.get_payment_status_display().upper()
    status_color = "#059669" if order.payment_status == "paid" else "#B45309"

    payment_content = [
        Paragraph('<b>PAYMENT INFORMATION</b>', section_heading),
        Spacer(1, 3),
        Paragraph(f'<b>Payment Method:</b> {payment_method_display}', section_content),
        Paragraph(f'<b>Payment Status:</b> <font color="{status_color}"><b>{payment_status_text}</b></font>', section_content),
    ]

    info_table = Table([[bill_to_content, ship_to_content, payment_content]], colWidths=[175, 175, 173])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # --------------------------------------------------------
    # PURCHASED ITEMS TABLE
    # --------------------------------------------------------

    if has_fashion:
        table_headers = [
            Paragraph('#', table_header_style),
            Paragraph('Purchased Product', table_header_style),
            Paragraph('Size', ParagraphStyle('THC_Size', parent=table_header_style, alignment=1)),
            Paragraph('Qty', ParagraphStyle('THC', parent=table_header_style, alignment=1)),
            Paragraph('Original Price', ParagraphStyle('THR1', parent=table_header_style, alignment=2)),
            Paragraph('Discount', ParagraphStyle('THR2', parent=table_header_style, alignment=2)),
            Paragraph('Total Amount', ParagraphStyle('THR3', parent=table_header_style, alignment=2)),
        ]
        col_widths = [20, 175, 38, 30, 80, 90, 90]
    else:
        table_headers = [
            Paragraph('#', table_header_style),
            Paragraph('Purchased Product', table_header_style),
            Paragraph('Qty', ParagraphStyle('THC', parent=table_header_style, alignment=1)),
            Paragraph('Original Price', ParagraphStyle('THR1', parent=table_header_style, alignment=2)),
            Paragraph('Discount', ParagraphStyle('THR2', parent=table_header_style, alignment=2)),
            Paragraph('Total Amount', ParagraphStyle('THR3', parent=table_header_style, alignment=2)),
        ]
        col_widths = [25, 208, 30, 80, 90, 90]

    items_data = [table_headers]

    total_mrp = Decimal('0.00')
    total_savings = Decimal('0.00')

    for idx, item in enumerate(order.items.all(), 1):
        orig_price = item.product.price if (item.product and item.product.price) else item.price
        item_mrp_total = orig_price * item.quantity
        item_discount = max(Decimal('0.00'), (orig_price - item.price) * item.quantity)

        total_mrp += item_mrp_total
        total_savings += item_discount

        discount_text = f"- Rs. {item_discount:,.2f}" if item_discount > 0 else "Rs. 0.00"

        if has_fashion:
            size_text = item.size if item.size else "-"
            items_data.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(item.product_name, table_cell_style),
                Paragraph(size_text, table_cell_center),
                Paragraph(str(item.quantity), table_cell_center),
                Paragraph(f'Rs. {orig_price:,.2f}', table_cell_right),
                Paragraph(discount_text, table_cell_discount if item_discount > 0 else table_cell_right),
                Paragraph(f'Rs. {item.total_price:,.2f}', table_cell_bold_right),
            ])
        else:
            items_data.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(item.product_name, table_cell_style),
                Paragraph(str(item.quantity), table_cell_center),
                Paragraph(f'Rs. {orig_price:,.2f}', table_cell_right),
                Paragraph(discount_text, table_cell_discount if item_discount > 0 else table_cell_right),
                Paragraph(f'Rs. {item.total_price:,.2f}', table_cell_bold_right),
            ])

    items_table = Table(items_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2A4A')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # --------------------------------------------------------
    # FINANCIAL SUMMARY TABLE
    # --------------------------------------------------------

    delivery_display = "FREE" if order.delivery_charge == 0 else f"Rs. {order.delivery_charge:,.2f}"
    summary_data = []

    if total_savings > 0:
        summary_data.append([
            Paragraph('Total MRP (Original):', table_cell_bold_right),
            Paragraph(f'Rs. {total_mrp:,.2f}', table_cell_right)
        ])
        summary_data.append([
            Paragraph('Total Discount Savings:', table_cell_bold_right),
            Paragraph(f'- Rs. {total_savings:,.2f}', table_cell_discount)
        ])
        summary_data.append([
            Paragraph('Subtotal (After Discount):', table_cell_bold_right),
            Paragraph(f'Rs. {order.subtotal:,.2f}', table_cell_right)
        ])
    else:
        summary_data.append([
            Paragraph('Subtotal:', table_cell_bold_right),
            Paragraph(f'Rs. {order.subtotal:,.2f}', table_cell_right)
        ])

    summary_data.append([
        Paragraph('Delivery Charges:', table_cell_bold_right),
        Paragraph(delivery_display, table_cell_right)
    ])
    summary_data.append([
        Paragraph('<b>Grand Total:</b>', ParagraphStyle('GT', parent=table_cell_bold_right, fontSize=10, textColor=colors.HexColor('#0B2A4A'))),
        Paragraph(f'<b>Rs. {order.total_amount:,.2f}</b>', ParagraphStyle('GTR', parent=table_cell_bold_right, fontSize=10, textColor=colors.HexColor('#2563EB')))
    ])

    last_row_idx = len(summary_data) - 1
    summary_table = Table(summary_data, colWidths=[150, 100], hAlign='RIGHT')
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, last_row_idx), (-1, last_row_idx), colors.HexColor('#EFF6FF')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 25))

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#64748B')
    )
    elements.append(
        HRFlowable(
            width='100%',
            thickness=0.5,
            color=colors.HexColor('#E2E8F0'),
            spaceAfter=10
        )
    )
    elements.append(
        Paragraph(
            '<b>Thank you for shopping with NexCart!</b>',
            ParagraphStyle(
                'FTB',
                parent=footer_style,
                fontName='Helvetica-Bold',
                fontSize=9.5,
                textColor=colors.HexColor('#0B2A4A')
            )
        )
    )
    elements.append(
        Paragraph(
            'This is a computer-generated invoice and does not require a physical signature.',
            footer_style
        )
    )
    elements.append(
        Paragraph(
            'NexCart E-Commerce Platform &bull; Customer Care: support@nexcart.com',
            footer_style
        )
    )

    # --------------------------------------------------------
    # GENERATE PDF & RETURN RESPONSE
    # --------------------------------------------------------

    doc.build(elements)
    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"NexCart_Invoice_{order.order_number}.pdf",
        content_type="application/pdf"
    )


# ============================================================
# STEP 29: ORDER TRACKING & DELIVERY TIMELINE
# ============================================================

@login_required(login_url='login')
def order_tracking(request, order_id):

    if str(order_id).isdigit():
        order_query = Q(id=int(order_id))
    else:
        order_query = Q(order_number=order_id)

    # Customer can only track their own order, staff can track any
    if request.user.is_staff or request.user.is_superuser:
        order = get_object_or_404(
            Order.objects.select_related('user', 'address').prefetch_related('items__product'),
            order_query
        )
    else:
        order = get_object_or_404(
            Order.objects.select_related('user', 'address').prefetch_related('items__product'),
            order_query,
            user=request.user
        )

    tracking_steps = [
        {
            'key': 'pending',
            'title': 'Order Placed',
            'desc': 'Your order has been placed and received by NexCart.',
            'icon': '📝',
            'time': order.created_at,
        },
        {
            'key': 'confirmed',
            'title': 'Order Confirmed',
            'desc': 'The seller has confirmed your order and accepted fulfillment.',
            'icon': '✓',
            'time': None,
        },
        {
            'key': 'processing',
            'title': 'Processing & Packaging',
            'desc': 'Your items are packed and undergoing dispatch inspection.',
            'icon': '📦',
            'time': None,
        },
        {
            'key': 'shipped',
            'title': 'Shipped',
            'desc': 'Package dispatched via logistics courier partner.',
            'icon': '🚚',
            'time': None,
        },
        {
            'key': 'out_for_delivery',
            'title': 'Out for Delivery',
            'desc': 'Delivery executive is on the way to your delivery address.',
            'icon': '🛵',
            'time': None,
        },
        {
            'key': 'delivered',
            'title': 'Delivered',
            'desc': 'Package handed over safely at the delivery address.',
            'icon': '🎉',
            'time': order.updated_at if order.status == 'delivered' else None,
        },
    ]

    status_order = [
        'pending',
        'confirmed',
        'processing',
        'shipped',
        'out_for_delivery',
        'delivered',
    ]

    current_status = order.status.lower() if order.status else 'pending'

    if current_status in status_order:
        current_index = status_order.index(current_status)
    else:
        current_index = -1

    context = {
        'order': order,
        'tracking_steps': tracking_steps,
        'status_order': status_order,
        'current_status': current_status,
        'current_index': current_index,
        'is_cancelled': (current_status == 'cancelled'),
    }

    return render(
        request,
        'orders/order_tracking.html',
        context
    )


@login_required(login_url='login')
def update_delivery_status(request, order_id):

    if request.method != 'POST':
        return redirect('my_orders')

    if str(order_id).isdigit():
        order = get_object_or_404(Order, id=int(order_id))
    else:
        order = get_object_or_404(Order, order_number=order_id)

    # Authorization check: seller of order items OR admin/staff
    is_seller = order.items.filter(product__seller=request.user).exists()
    if not (request.user.is_staff or request.user.is_superuser or is_seller):
        messages.error(request, "You do not have permission to update this order's status.")
        return redirect('seller_orders' if getattr(request.user, 'role', '') == 'seller' else 'home')

    new_status = request.POST.get('delivery_status') or request.POST.get('status')

    if new_status:
        status_map = {
            'placed': 'pending',
            'pending': 'pending',
            'confirmed': 'confirmed',
            'processing': 'processing',
            'shipped': 'shipped',
            'out_for_delivery': 'out_for_delivery',
            'delivered': 'delivered',
            'cancelled': 'cancelled',
        }
        normalized = status_map.get(new_status.lower(), new_status.lower())
        allowed = [c[0] for c in Order.ORDER_STATUS_CHOICES]

        if normalized in allowed:
            old_status = order.status
            order.status = normalized

            # If cancelled, restore stock
            if normalized == 'cancelled' and old_status != 'cancelled':
                for item in order.items.select_related('product'):
                    if item.product:
                        item.product.stock += item.quantity
                        if item.product.stock > 0 and item.product.status == 'out_of_stock':
                            item.product.status = 'active'
                            item.product.is_active = True
                        item.product.save(update_fields=['stock', 'status', 'is_active', 'updated_at'])

            # If COD marked delivered, mark payment paid
            if normalized == 'delivered' and order.payment_method == 'cod' and order.payment_status == 'pending':
                order.payment_status = 'paid'
                order.save(update_fields=['status', 'payment_status', 'updated_at'])
            else:
                order.save(update_fields=['status', 'updated_at'])

            messages.success(request, f"Order #{order.order_number} status updated to {order.get_status_display()}.")

    if getattr(request.user, 'role', '') == 'seller':
        return redirect('seller_orders')
    elif request.user.is_staff:
        return redirect('admin_order_detail', order_id=order.id)
    return redirect('order_tracking', order_id=order.id)


# Re-export seller_sales_report for modular access
from sellers.views import seller_sales_report

