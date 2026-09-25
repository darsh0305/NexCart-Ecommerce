import re
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate

from accounts.models import Address
from cart.models import Cart
from orders.models import Order, OrderItem
from products.models import Category, Product, ProductFeedback


STOP_WORDS = {
    'the', 'a', 'an', 'show', 'me', 'find', 'what', 'is', 'are', 'for', 'my', 'i', 'want',
    'buy', 'price', 'of', 'and', 'in', 'on', 'to', 'do', 'can', 'you', 'please', 'tell',
    'with', 'from', 'latest', 'best', 'top', 'trending', 'available', 'stock', 'order', 'track',
    'products', 'product'
}


def _price_value_from_text(message):
    match = re.search(
        r'(?:under|below|less than|upto|up to|below|maximum|max|<=|<)\s*₹?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        message,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r'₹\s*(\d+(?:,\d{3})*(?:\.\d+)?)', message)
    if not match:
        return None

    raw = match.group(1).replace(',', '')
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _normalize_query(message):
    return re.sub(r'[^a-zA-Z0-9\s]', ' ', (message or '').lower()).strip()


def _extract_category_filter(message):
    message_tokens = set(_normalize_query(message).split())
    categories = list(Category.objects.filter(is_active=True).values_list('name', flat=True))
    best_match = None
    best_score = (-1, -1)

    for category in categories:
        category_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', category.lower())
        category_tokens = set(category_text.split())
        overlap = category_tokens & message_tokens
        if not overlap:
            continue

        score = (len(overlap), len(category_text))
        if score > best_score:
            best_score = score
            best_match = category

    return best_match


def get_category_context():
    """Returns a list of all active categories in the database."""
    categories = Category.objects.filter(is_active=True).order_by('name')
    if not categories.exists():
        return "No categories currently available."
    
    rows = ["Available Categories:"]
    for cat in categories:
        desc = f" - {cat.description}" if cat.description else ""
        rows.append(f"- {cat.name}{desc}")
    
    return "\n".join(rows)


def get_trending_context(limit=5):
    """
    Returns trending products based on actual delivered order quantities.
    Falls back to most featured/discounted if no order data exists.
    """
    # Find most sold products from delivered orders
    top_items = (
        OrderItem.objects.filter(order__status='delivered')
        .values('product_id')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:limit]
    )

    if top_items:
        product_ids = [item['product_id'] for item in top_items]
        # Preserve the order from the annotation
        products = sorted(
            Product.objects.filter(id__in=product_ids, is_active=True, status='active').select_related('category'),
            key=lambda p: product_ids.index(p.id)
        )
        if products:
            rows = ["Based on recent orders, these products are currently trending:"]
            for product in products:
                cat_name = product.category.name if product.category else 'Uncategorized'
                rows.append(f"- {product.name} ({cat_name}) - ₹{product.price} (Stock: {product.stock})")
            return "\n".join(rows)

    # Fallback: featured products if no sales data
    featured = Product.objects.filter(
        is_active=True, status='active'
    ).select_related('category').order_by('-is_featured', '-discount_percentage')[:limit]
    
    if featured:
        rows = ["Here are some of our featured products:"]
        for product in featured:
            cat_name = product.category.name if product.category else 'Uncategorized'
            rows.append(f"- {product.name} ({cat_name}) - ₹{product.price} (Stock: {product.stock})")
        return "\n".join(rows)

    return "No trending products available at the moment."


def product_rows_for_query(message, limit=10):
    query = (message or '').strip()
    qs = Product.objects.filter(is_active=True, status='active').select_related('category')

    category_name = _extract_category_filter(query)
    if category_name:
        qs = qs.filter(category__name__icontains=category_name)

    price_cap = _price_value_from_text(query)
    if price_cap is not None:
        qs = qs.filter(price__lte=price_cap)

    category_tokens = set()
    if category_name:
        category_tokens = set(re.sub(r'[^a-zA-Z0-9\s]', ' ', category_name.lower()).split())

    price_tokens = {'under', 'below', 'less', 'than', 'upto', 'up', 'to', 'maximum', 'max'}
    tokens = [
        word for word in _normalize_query(query).split()
        if word
        and word not in STOP_WORDS
        and word not in category_tokens
        and word not in price_tokens
        and not word.isdigit()
    ]
    if tokens:
        text_q = Q()
        for token in tokens:
            text_q &= (Q(name__icontains=token) | Q(description__icontains=token) | Q(category__name__icontains=token))
        qs = qs.filter(text_q)

    # Note: If qs is empty, we return an empty list rather than just throwing random products at them.
    # The chatbot should say "I couldn't find any products..." rather than showing unrelated items.
    return qs[:limit]


def get_product_context(message=None, limit=20):
    if not message:
        products = Product.objects.filter(is_active=True, status='active').select_related('category')[:limit]
    else:
        products = product_rows_for_query(message, limit=limit)
        
    if not products:
        return 'No matching products found in the NexCart catalog for your search.'

    rows = []
    for product in products:
        category_name = product.category.name if product.category else 'Uncategorized'
        size_info = product.size if product.size else 'Not specified'
        if product.has_size_variants:
            size_info = ', '.join(
                f'{variant.size}:{variant.stock}' for variant in product.size_variants.all()
            )

        rows.append(
            f"""
Product ID: {product.id}
Product Name: {product.name}
Category: {category_name}
Price: ₹{product.price}
Discount: {product.discount_percentage}%
Stock: {product.stock}
Size: {size_info}
Status: {product.status}
"""
        )

    return '\n'.join(rows)


def get_customer_context(user):
    if not user or not user.is_authenticated:
        return 'Customer is not logged in.'

    # ── Addresses ──
    addresses = Address.objects.filter(user=user).order_by('-is_default', '-created_at')[:5]
    if addresses:
        address_rows = []
        for address in addresses:
            address_rows.append(
                f"Address: {address.full_name}, {address.address_line_1}, "
                f"{address.city}, {address.state} - {address.pincode}, Phone: {address.phone}"
            )
    else:
        address_rows = ['No saved addresses.']

    # ── Orders with items ──
    orders = (
        Order.objects
        .filter(user=user)
        .select_related('address')
        .prefetch_related('items__product')
        .order_by('-created_at')[:5]
    )
    order_rows = []
    for order in orders:
        item_rows = []
        for item in order.items.all()[:10]:
            item_rows.append(
                f"  - {item.product_name} x {item.quantity} @ ₹{item.price}"
                f" ({item.size or 'No size'})"
            )

        order_rows.append(
            f"""
Order ID: {order.id}
Order Number: {order.order_number}
Order Date: {order.created_at}
Status: {order.get_status_display()}
Payment Method: {order.get_payment_method_display()}
Payment Status: {order.get_payment_status_display()}
Total Amount: ₹{order.total_amount}
Items:
{chr(10).join(item_rows) if item_rows else 'No items'}
"""
        )

    return (
        f"Addresses:\n{chr(10).join(address_rows)}\n\n"
        f"Recent Orders:\n{chr(10).join(order_rows) if order_rows else 'No recent orders.'}"
    )


def get_cart_context(user):
    """Retrieve the authenticated customer's current cart contents."""
    if not user or not user.is_authenticated:
        return 'Customer is not logged in.'

    try:
        cart = Cart.objects.get(user=user)
    except Cart.DoesNotExist:
        return 'The customer has no items in their cart.'

    items = cart.items.select_related('product')
    if not items.exists():
        return 'The customer has no items in their cart.'

    rows = []
    for item in items:
        size_str = f" (Size: {item.size})" if item.size else ''
        rows.append(
            f"  - {item.product.name}{size_str} x {item.quantity}"
            f" @ ₹{item.product.discounted_price} each"
            f" = ₹{item.total_price}"
        )

    return (
        f"Cart Items:\n{chr(10).join(rows)}\n"
        f"Subtotal: ₹{cart.subtotal}\n"
        f"Delivery Charge: ₹{cart.delivery_charge}\n"
        f"Total: ₹{cart.total_with_delivery}"
    )


def get_feedback_context(message=None):
    """Retrieve feedback context. Optionally filter by message search."""
    products = Product.objects.filter(is_active=True).prefetch_related('feedbacks')
    
    if message:
        # Attempt to filter products by search query if a specific product was mentioned
        filtered = product_rows_for_query(message, limit=5)
        if filtered:
            products = filtered.prefetch_related('feedbacks')

    rows = []
    for product in products[:10]:  # Limit to avoid huge context
        stats = product.feedbacks.aggregate(
            avg_rating=Avg('rating'),
            total_feedback=Count('id'),
        )
        avg = stats['avg_rating']
        total = stats['total_feedback'] or 0

        if total > 0:
            rows.append(
                f"Product: {product.name}\n"
                f"Average Rating: {avg:.1f}/5\n"
                f"Total Feedback: {total}\n"
            )

    return '\n'.join(rows) if rows else 'No product feedback available.'


def determine_intent(message):
    """
    Very simple, lightweight keyword-based intent router.
    Returns a set of intents (e.g. {'product_search', 'order_tracking'}).
    """
    query = (message or '').strip().lower()
    intents = set()
    
    # 1. Greetings / General Chat (no DB needed)
    if query in ['hi', 'hello', 'hey', 'help', 'who are you']:
        intents.add('greeting')
        return intents
        
    # 2. Categories
    if 'category' in query or 'categories' in query:
        intents.add('category_list')
        
    # 3. Trending
    if any(word in query for word in ['trending', 'popular', 'best', 'top']):
        intents.add('trending')
        
    # 4. Orders / Tracking
    if any(word in query for word in ['order', 'orders', 'track', 'tracking', 'delivery', 'invoice']):
        intents.add('order_tracking')
        
    # 5. Cart
    if any(word in query for word in ['cart', 'basket', 'checkout', 'bag']):
        intents.add('cart')
        
    # 6. Feedback
    if any(word in query for word in ['feedback', 'rating', 'review', 'reviews']):
        intents.add('feedback')

    # 7. General Questions
    if any(word in query for word in ['nexcart', 'how to', 'cod', 'razorpay', 'return']):
        intents.add('general')

    # If no specific intent found, assume product search
    if not intents:
        intents.add('product_search')
        
    return intents


def build_nexcart_context(user, message=None):
    """
    Build the complete live NexCart context that is injected into the
    Gemini prompt so the AI answers from real data rather than guessing.
    Only queries the database for sections relevant to the user's intent.
    """
    query = (message or '').strip()
    intents = determine_intent(query)
    
    sections = []

    if 'greeting' in intents:
        return 'Customer is greeting you. No database context needed.'

    # Always include customer context when logged in, or if explicitly asked for orders
    if (user and user.is_authenticated) or 'order_tracking' in intents or 'cart' in intents:
        customer_ctx = get_customer_context(user)
        sections += [
            '==================== CUSTOMER DATA ====================',
            customer_ctx,
            ''
        ]

    if 'cart' in intents and user and user.is_authenticated:
        sections += [
            '==================== CART DATA ====================',
            get_cart_context(user),
            ''
        ]

    if 'category_list' in intents:
        sections += [
            '==================== CATEGORIES ====================',
            get_category_context(),
            ''
        ]
        
    if 'trending' in intents:
        sections += [
            '==================== TRENDING PRODUCTS ====================',
            get_trending_context(),
            ''
        ]

    # Only do a product search if explicitly requested or if it's a general product question
    if 'product_search' in intents or 'category_list' in intents or 'trending' in intents or 'feedback' in intents:
         sections += [
            '==================== LIVE PRODUCT DATA ====================',
            get_product_context(query, limit=10),
            ''
        ]

    if 'feedback' in intents:
        sections += [
            '==================== PRODUCT FEEDBACK ====================',
            get_feedback_context(query),
            ''
        ]
        
    if not sections:
        # Fallback if no sections matched but we didn't return early
        sections += [
            '==================== LIVE PRODUCT DATA ====================',
            get_product_context(query, limit=10)
        ]

    return '\n'.join(sections).strip()


# =============================================================================
# SELLER CONTEXT BUILDER
# =============================================================================

def get_seller_store_context(seller):
    """Returns basic store info and inventory summary for the seller."""
    try:
        profile = seller.seller_profile
        store_name = profile.store_name
        store_desc = profile.store_description or 'N/A'
    except Exception:
        store_name = seller.get_full_name() or seller.username
        store_desc = 'N/A'

    products = Product.objects.filter(seller=seller)
    total = products.count()
    active = products.filter(status='active', is_active=True).count()
    low_stock = products.filter(stock__gt=0, stock__lte=5).count()
    out_of_stock = products.filter(stock=0).count()
    draft = products.filter(status='draft').count()

    return (
        f"Store Name: {store_name}\n"
        f"Store Description: {store_desc}\n"
        f"Seller Username: {seller.username}\n"
        f"Seller Email: {seller.email}\n\n"
        f"=== Inventory Summary ===\n"
        f"Total Products: {total}\n"
        f"Active Products: {active}\n"
        f"Low Stock (1-5 units): {low_stock}\n"
        f"Out of Stock: {out_of_stock}\n"
        f"Draft Products: {draft}"
    )


def get_seller_products_context(seller, message=None):
    """Returns the seller's own product catalog."""
    qs = Product.objects.filter(seller=seller).select_related('category').order_by('-created_at')

    # Optional search filter
    if message:
        normalized = _normalize_query(message)
        tokens = [
            w for w in normalized.split()
            if w and w not in STOP_WORDS and not w.isdigit()
        ]
        if tokens:
            q = Q()
            for token in tokens:
                q &= (Q(name__icontains=token) | Q(category__name__icontains=token))
            qs = qs.filter(q)

    if not qs.exists():
        return 'No products found in your store catalog.'

    rows = []
    for p in qs[:15]:
        cat = p.category.name if p.category else 'Uncategorized'
        rows.append(
            f"Product: {p.name} | Category: {cat} | Price: ₹{p.price} "
            f"| Discount: {p.discount_percentage}% | Stock: {p.stock} | Status: {p.status}"
        )
    return '\n'.join(rows)


def get_seller_orders_context(seller):
    """Returns the seller's recent orders."""
    orders = (
        Order.objects
        .filter(items__product__seller=seller)
        .distinct()
        .prefetch_related('items', 'items__product')
        .order_by('-created_at')[:10]
    )

    if not orders.exists():
        return 'No orders found for your store.'

    rows = []
    for order in orders:
        seller_items = order.items.filter(product__seller=seller)
        seller_subtotal = sum(item.total_price for item in seller_items)
        item_names = ', '.join(
            f"{item.product_name} x{item.quantity}" for item in seller_items
        )
        rows.append(
            f"Order #{order.order_number} | Date: {order.created_at.strftime('%d %b %Y')} "
            f"| Status: {order.get_status_display()} | Payment: {order.get_payment_status_display()} "
            f"| Your Revenue: ₹{seller_subtotal} | Items: {item_names}"
        )
    return '\n'.join(rows)


def get_seller_revenue_context(seller):
    """Returns revenue and sales summary for the seller."""
    revenue_expr = ExpressionWrapper(
        F('quantity') * F('price'),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    seller_items = OrderItem.objects.filter(
        product__seller=seller
    ).exclude(order__status='cancelled')

    total_revenue = seller_items.aggregate(
        total=Sum(revenue_expr)
    )['total'] or Decimal('0.00')

    total_units = seller_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    total_orders = seller_items.values('order').distinct().count()

    avg_order_value = (
        total_revenue / total_orders if total_orders else Decimal('0.00')
    )

    # Paid revenue only
    paid_revenue = OrderItem.objects.filter(
        product__seller=seller,
        order__payment_status='paid'
    ).aggregate(total=Sum(revenue_expr))['total'] or Decimal('0.00')

    # Top 5 products by revenue
    top_products = (
        seller_items
        .values('product_name')
        .annotate(revenue=Sum(revenue_expr), units=Sum('quantity'))
        .order_by('-revenue')[:5]
    )

    # Daily sales (last 7 days)
    daily = (
        seller_items
        .annotate(sale_date=TruncDate('order__created_at'))
        .values('sale_date')
        .annotate(revenue=Sum(revenue_expr), units=Sum('quantity'))
        .order_by('-sale_date')[:7]
    )

    rows = [
        f"Total Revenue (excl. cancelled): ₹{total_revenue:.2f}",
        f"Confirmed/Paid Revenue: ₹{paid_revenue:.2f}",
        f"Total Units Sold: {total_units}",
        f"Total Orders: {total_orders}",
        f"Average Order Value: ₹{avg_order_value:.2f}",
        "",
        "Top Products by Revenue:",
    ]
    for p in top_products:
        rows.append(f"  - {p['product_name']}: ₹{p['revenue']:.2f} ({p['units']} units)")

    rows.append("")
    rows.append("Recent Daily Sales (last 7 days):")
    for day in daily:
        if day['sale_date']:
            rows.append(
                f"  - {day['sale_date'].strftime('%d %b %Y')}: "
                f"₹{day['revenue']:.2f} ({day['units']} units)"
            )

    return '\n'.join(rows)


def determine_seller_intent(message):
    """
    Keyword-based intent router for the seller chatbot.
    Returns a set of intents.
    """
    query = (message or '').strip().lower()
    intents = set()

    if query in ['hi', 'hello', 'hey', 'help', 'who are you']:
        intents.add('greeting')
        return intents

    # Revenue / Sales reports
    if any(w in query for w in ['revenue', 'sales', 'earning', 'income', 'profit', 'report', 'daily', 'monthly']):
        intents.add('revenue')

    # Orders
    if any(w in query for w in ['order', 'orders', 'customer order', 'pending', 'shipped', 'delivered', 'cancelled']):
        intents.add('orders')

    # Inventory / Products
    if any(w in query for w in ['product', 'products', 'stock', 'inventory', 'catalog', 'low stock', 'out of stock', 'add product', 'edit product']):
        intents.add('inventory')

    # Store info
    if any(w in query for w in ['store', 'shop', 'profile', 'account', 'settings']):
        intents.add('store')

    # If no specific intent, default to store + inventory
    if not intents:
        intents.add('store')
        intents.add('inventory')

    return intents


def build_seller_context(seller, message=None):
    """
    Build the complete live seller context injected into the Gemini prompt.
    Only fetches data relevant to the seller's question.
    """
    query = (message or '').strip()
    intents = determine_seller_intent(query)

    sections = []

    if 'greeting' in intents:
        return 'Seller is greeting you. Provide a helpful welcome message about the seller dashboard.'

    # Always include basic store info
    sections += [
        '==================== SELLER STORE INFO ====================',
        get_seller_store_context(seller),
        ''
    ]

    if 'inventory' in intents:
        sections += [
            '==================== SELLER PRODUCTS / INVENTORY ====================',
            get_seller_products_context(seller, message),
            ''
        ]

    if 'orders' in intents:
        sections += [
            '==================== SELLER ORDERS ====================',
            get_seller_orders_context(seller),
            ''
        ]

    if 'revenue' in intents:
        sections += [
            '==================== SELLER REVENUE & SALES ====================',
            get_seller_revenue_context(seller),
            ''
        ]

    if 'store' in intents and 'inventory' not in intents:
        sections += [
            '==================== SELLER PRODUCTS / INVENTORY ====================',
            get_seller_products_context(seller),
            ''
        ]

    return '\n'.join(sections).strip()
