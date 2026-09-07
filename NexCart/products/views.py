import json
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.utils import timezone

from .models import (
    Category,
    Product,
)


def home(request):

    featured_products = Product.objects.filter(
        status='active',
        is_featured=True
    ).select_related(
        'category'
    )[:8]

    if not featured_products:
        featured_products = Product.objects.filter(
            status='active'
        ).select_related(
            'category'
        )[:8]

    categories = Category.objects.filter(
        is_active=True
    )

    return render(
        request,
        'home/home.html',
        {
            'featured_products':
            featured_products,

            'categories':
            categories,
        }
    )


def product_list(request):

    products = Product.objects.filter(
        status__in=['active', 'out_of_stock']
    ).select_related(
        'category'
    )

    # Search
    query = request.GET.get('q', '').strip()
    if not query:
        query = request.GET.get('search', '').strip()

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
        )

    # Category filter
    category = request.GET.get(
        'category',
        ''
    ).strip()

    if category:
        products = products.filter(
            category__slug=category
        )

    # Price range
    min_price = request.GET.get(
        'min_price',
        ''
    ).strip()

    max_price = request.GET.get(
        'max_price',
        ''
    ).strip()

    if min_price:
        try:
            products = products.filter(
                price__gte=float(min_price)
            )
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(
                price__lte=float(max_price)
            )
        except ValueError:
            pass

    # Availability
    availability = request.GET.get(
        'availability',
        ''
    ).strip()

    if availability == 'in_stock':
        products = products.filter(
            stock__gt=0
        )

    # Sorting
    sort = request.GET.get(
        'sort',
        ''
    ).strip()

    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'name_az':
        products = products.order_by('name')
    elif sort == 'name_za':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(
        products,
        12
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    categories = Category.objects.filter(
        is_active=True
    ).order_by(
        'name'
    )

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'search_query': query,
        'selected_category': category,
        'min_price': min_price,
        'max_price': max_price,
        'availability': availability,
        'selected_sort': sort,
    }

    return render(
        request,
        'products/product_list.html',
        context
    )


def calculate_delivery_for_pincode(pincode_str, base_date=None):
    """
    Calculates expected delivery timeline based on postal pincode proximity.
    Nearby/same-region pincodes share the exact same expected delivery date,
    while further postal circles receive different dates according to distance.
    """
    if base_date is None:
        base_date = timezone.now()

    pin_clean = str(pincode_str).strip() if pincode_str else ''
    if not pin_clean.isdigit() or len(pin_clean) != 6:
        # Fallback default: 4 days standard delivery
        exp = base_date + timedelta(days=4)
        return {
            'pincode': pin_clean,
            'days': 4,
            'location': 'Your Location',
            'expected_date': exp,
            'start_date': base_date + timedelta(days=3),
            'end_date': base_date + timedelta(days=5),
            'zone': 'Standard National Delivery',
        }

    prefix2 = int(pin_clean[:2])
    prefix1 = int(pin_clean[0])

    # Postal circle mapping with proximity transit days
    circle_map = {
        11: ('Delhi NCR', 3),
        12: ('Haryana', 3), 13: ('Haryana', 3),
        14: ('Punjab', 4), 15: ('Punjab', 4), 16: ('Chandigarh / Punjab', 4),
        17: ('Himachal Pradesh', 5),
        18: ('Jammu & Kashmir', 5), 19: ('Jammu & Kashmir', 6),
        20: ('Uttar Pradesh West', 4), 21: ('Uttar Pradesh Central', 4),
        22: ('Uttar Pradesh East', 4), 23: ('Uttar Pradesh', 4),
        24: ('Uttarakhand', 4), 25: ('Uttar Pradesh', 4),
        26: ('Uttarakhand', 5), 27: ('Uttar Pradesh', 4), 28: ('Uttar Pradesh', 4),
        30: ('Jaipur / Rajasthan', 3), 31: ('Rajasthan', 3), 32: ('Rajasthan', 3),
        33: ('Rajasthan', 4), 34: ('Jodhpur / Rajasthan', 3),
        36: ('Saurashtra / Gujarat', 2), 37: ('Kutch / Gujarat', 2),
        38: ('Ahmedabad / Gujarat', 2), 39: ('Surat / Gujarat', 2),
        40: ('Mumbai / MMR', 1), 41: ('Pune / Maharashtra', 2),
        42: ('Nashik / Maharashtra', 2), 43: ('Aurangabad / Maharashtra', 2),
        44: ('Nagpur / Maharashtra', 3),
        45: ('Indore / MP', 3), 46: ('Bhopal / MP', 3),
        47: ('Gwalior / MP', 3), 48: ('Jabalpur / MP', 4), 49: ('Chhattisgarh', 4),
        50: ('Hyderabad / Telangana', 3), 51: ('Rayalaseema / AP', 3),
        52: ('Vijayawada / AP', 3), 53: ('Visakhapatnam / AP', 4),
        56: ('Bengaluru / Karnataka', 3), 57: ('Mangalore / Karnataka', 3),
        58: ('Hubli / Karnataka', 3), 59: ('Belgaum / Karnataka', 3),
        60: ('Chennai / Tamil Nadu', 3), 61: ('Tamil Nadu Central', 4),
        62: ('Madurai / Tamil Nadu', 4), 63: ('Coimbatore / Tamil Nadu', 3),
        64: ('Coimbatore / Tamil Nadu', 4),
        67: ('Calicut / North Kerala', 4), 68: ('Kochi / Central Kerala', 4), 69: ('Trivandrum / South Kerala', 4),
        70: ('Kolkata / West Bengal', 4), 71: ('West Bengal Central', 4),
        72: ('West Bengal South', 5), 73: ('North Bengal / Sikkim', 5), 74: ('West Bengal', 5),
        75: ('Bhubaneswar / Odisha', 4), 76: ('Odisha South', 5), 77: ('Odisha West', 5),
        78: ('Guwahati / Assam', 6), 79: ('North-East Region', 7),
        80: ('Patna / Bihar', 4), 81: ('Bihar South', 5), 82: ('Gaya / Bihar', 5),
        83: ('Ranchi / Jharkhand', 4), 84: ('Muzaffarpur / Bihar', 5), 85: ('Bhagalpur / Bihar', 5),
    }

    if prefix2 in circle_map:
        location, days = circle_map[prefix2]
    else:
        # Fallback zone calculation based on regional postal circle digit
        zone_diff = abs(prefix1 - 4)
        if zone_diff == 0:
            days = 2
            location = 'Western Postal Zone'
        elif zone_diff == 1:
            days = 3
            location = 'Central / Northern Postal Zone'
        elif zone_diff == 2:
            days = 4
            location = 'Southern / Eastern Postal Zone'
        else:
            days = 5 + (zone_diff - 3)
            location = 'Special Remote Postal Zone'

    start_days = max(1, days - 1)
    end_days = days + 1
    exp = base_date + timedelta(days=days)

    return {
        'pincode': pin_clean,
        'days': days,
        'location': location,
        'expected_date': exp,
        'start_date': base_date + timedelta(days=start_days),
        'end_date': base_date + timedelta(days=end_days),
        'zone': f'{location} ({days} days)',
    }


def resolve_coordinates_to_pincode(lat, lng):
    """
    Resolves geographic GPS coordinates (latitude, longitude) to an approximate
    Indian postal zone/pincode for delivery timeline estimation.
    """
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return '400001'

    # Geographic coordinate zone mapping for India
    if lng > 89.0 and lat > 22.0:
        return '781001'  # North-East / Assam
    elif lat > 32.0:
        return '190001'  # Jammu & Kashmir / HP
    elif lat > 27.5 and lng < 78.5:
        return '110001'  # Delhi NCR / Haryana / Punjab
    elif lat > 24.5 and lng < 76.0:
        return '302001'  # Rajasthan (Jaipur)
    elif lat > 24.0 and lng > 83.0:
        return '800001'  # Bihar / Jharkhand
    elif lat > 21.0 and lng > 85.0:
        return '700001'  # Kolkata / West Bengal
    elif 20.0 <= lat <= 24.5 and 68.0 <= lng <= 74.5:
        return '380001'  # Gujarat (Ahmedabad)
    elif 18.0 <= lat <= 20.5 and 72.0 <= lng <= 74.0:
        return '400001'  # Mumbai / MMR
    elif 17.5 <= lat <= 20.0 and 73.5 <= lng <= 76.0:
        return '411001'  # Pune / Maharashtra
    elif 16.5 <= lat <= 19.0 and 77.0 <= lng <= 80.5:
        return '500001'  # Hyderabad / Telangana
    elif 11.5 <= lat <= 15.0 and 74.5 <= lng <= 78.5:
        return '560001'  # Bengaluru / Karnataka
    elif 11.0 <= lat <= 14.0 and 79.0 <= lng <= 81.0:
        return '600001'  # Chennai / Tamil Nadu
    elif 8.0 <= lat <= 12.0 and 75.5 <= lng <= 77.5:
        return '682001'  # Kerala (Kochi)
    else:
        return '400001'


def check_pincode_delivery(request):
    """
    AJAX view to look up expected delivery day, date, and serviceability for a pincode or GPS coordinates.
    """
    pincode = request.GET.get('pincode', '').strip()
    lat = request.GET.get('lat', '').strip()
    lng = request.GET.get('lng', '').strip()

    if not pincode and lat and lng:
        pincode = resolve_coordinates_to_pincode(lat, lng)

    if not pincode or not pincode.isdigit() or len(pincode) != 6:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid 6-digit postal pincode.',
        }, status=400)

    delivery_info = calculate_delivery_for_pincode(pincode)
    exp_date = delivery_info['expected_date']
    start_date = delivery_info['start_date']
    end_date = delivery_info['end_date']
    days = delivery_info['days']

    day_word = 'day' if days == 1 else 'days'

    return JsonResponse({
        'success': True,
        'pincode': delivery_info['pincode'],
        'location': delivery_info['location'],
        'delivery_days': days,
        'expected_delivery_date': exp_date.strftime('%A, %d %B'),
        'expected_delivery_day': exp_date.strftime('%A'),
        'expected_delivery_short': exp_date.strftime('%a, %d %b'),
        'delivery_start_date': start_date.strftime('%a, %d %b'),
        'delivery_end_date': end_date.strftime('%a, %d %b'),
        'delivery_window': f"{start_date.strftime('%a, %d %b')} – {end_date.strftime('%a, %d %b')}",
        'zone_label': delivery_info['zone'],
        'message': f"Delivery available to {delivery_info['location']} (PIN {delivery_info['pincode']}) by {exp_date.strftime('%A, %d %b')} ({days} business {day_word}). Cash on Delivery & Free Shipping eligible!",
    })


def product_detail(
    request,
    slug
):

    if str(slug).isdigit():
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('images', 'size_variants'),
            Q(id=int(slug)) | Q(slug=slug),
            status__in=['active', 'out_of_stock']
        )
    else:
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('images', 'size_variants'),
            slug=slug,
            status__in=['active', 'out_of_stock']
        )

    gallery_images = []
    if product.image:
        gallery_images.append(product.image.url)

    additional_images = [img.image.url for img in product.images.all()]
    for image_url in additional_images:
        if image_url not in gallery_images:
            gallery_images.append(image_url)

    if not gallery_images and product.image:
        gallery_images.append(product.image.url)

    gallery_images_json = json.dumps(gallery_images)

    now = timezone.now()
    user_address = None
    initial_pincode = '400001'

    if request.user.is_authenticated:
        user_address = request.user.addresses.filter(is_default=True).first()
        if not user_address:
            user_address = request.user.addresses.first()
        if user_address and user_address.pincode:
            initial_pincode = user_address.pincode

    delivery_info = calculate_delivery_for_pincode(initial_pincode, now)

    size_stock_map = {v.size: v.stock for v in product.size_variants.all()}
    has_variants = product.size_variants.exists()

    context = {
        'product': product,
        'gallery_images': gallery_images,
        'gallery_images_json': gallery_images_json,
        'expected_delivery_date': delivery_info['expected_date'],
        'delivery_start_date': delivery_info['start_date'],
        'delivery_end_date': delivery_info['end_date'],
        'delivery_days': delivery_info['days'],
        'delivery_location': delivery_info['location'],
        'user_address': user_address,
        'initial_pincode': initial_pincode if user_address else '',
        'size_stock_map': size_stock_map,
        'has_variants': has_variants,
    }

    return render(
        request,
        'products/product_detail.html',
        context
    )