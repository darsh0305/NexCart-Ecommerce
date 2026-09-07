from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from products.models import Product

from .models import Cart, CartItem


@login_required
def add_to_cart(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id,
        status='active'
    )

    # Check stock

    if product.stock <= 0 or product.status != 'active':

        messages.error(
            request,
            'This product is currently out of stock or unavailable.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    # Receive size
    size = request.POST.get('size') if request.method == 'POST' else request.GET.get('size')
    if size:
        size = size.strip().upper()

    # Validate Fashion product size
    if product.category and 'fashion' in product.category.name.lower():
        if size not in ['S', 'M', 'L', 'XL', 'XXL']:
            messages.error(
                request,
                'Please select a size.'
            )
            return redirect(
                'product_detail',
                slug=product.slug
            )
    else:
        size = None

    # Get or create cart

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    # Get or create cart item by product and size
    if size:
        cart_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            size=size
        ).first()
    else:
        cart_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            size__isnull=True
        ).first()

    available_stock = product.get_stock_for_size(size) if (size and product.has_size_variants) else product.stock
    if available_stock <= 0:
        size_msg = f" in size {size}" if size else ""
        messages.error(
            request,
            f"{product.name}{size_msg} is currently out of stock."
        )
        return redirect(
            'product_detail',
            slug=product.slug
        )

    if cart_item:
        if cart_item.quantity < available_stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(
                request,
                f'You cannot add more than the available stock ({available_stock}).'
            )
            return redirect(
                'cart_detail'
            )
    else:
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
            size=size
        )

    size_display = f" (Size: {size})" if size else ""
    messages.success(
        request,
        f'{product.name}{size_display} added to your cart.'
    )

    return redirect(
        'cart_detail'
    )


@login_required
def cart_detail(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_items = cart.items.select_related(
        'product'
    )

    return render(
        request,
        'cart/cart_detail.html',
        {
            'cart': cart,
            'cart_items': cart_items,
        }
    )


@login_required
def increase_quantity(
    request,
    item_id
):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    max_stock = cart_item.product.get_stock_for_size(cart_item.size) if (cart_item.size and cart_item.product.has_size_variants) else cart_item.product.stock

    if cart_item.quantity < max_stock:
        cart_item.quantity += 1
        cart_item.save()
    else:
        messages.warning(
            request,
            f'Maximum available stock ({max_stock}) reached.'
        )

    return redirect(
        'cart_detail'
    )


@login_required
def decrease_quantity(
    request,
    item_id
):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if cart_item.quantity > 1:

        cart_item.quantity -= 1

        cart_item.save()

    else:

        cart_item.delete()

    return redirect(
        'cart_detail'
    )


@login_required
def remove_from_cart(
    request,
    item_id
):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.delete()

    messages.success(
        request,
        'Product removed from your cart.'
    )

    return redirect(
        'cart_detail'
    )