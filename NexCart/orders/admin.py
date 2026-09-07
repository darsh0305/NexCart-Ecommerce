from django.contrib import admin

from .models import (
    Order,
    OrderItem,
)


# ============================================================
# ORDER ITEM INLINE
# ============================================================

class OrderItemInline(
    admin.TabularInline
):

    model = OrderItem

    extra = 0

    readonly_fields = (

        'product',

        'product_name',

        'size',

        'price',

        'quantity',

        'total_price',

    )

# ============================================================
# ORDER ADMIN
# ============================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (

        'order_number',

        'user',

        'total_amount',

        'payment_method',

        'payment_status',

        'status',

        'created_at',

    )

    list_filter = (

        'payment_method',

        'payment_status',

        'status',

        'created_at',

    )

    search_fields = (

        'order_number',

        'user__username',

        'user__email',

        'razorpay_order_id',

        'razorpay_payment_id',

    )

    readonly_fields = (

        'order_number',

        'user',

        'address',

        'subtotal',

        'delivery_charge',

        'total_amount',

        'payment_method',

        'payment_status',

        'razorpay_order_id',

        'razorpay_payment_id',

        'razorpay_signature',

        'created_at',

        'updated_at',

    )

    fieldsets = (

        (
            'Order Information',
            {
                'fields': (

                    'order_number',

                    'user',

                    'address',

                    'status',

                )
            }
        ),

        (
            'Price Information',
            {
                'fields': (

                    'subtotal',

                    'delivery_charge',

                    'total_amount',

                )
            }
        ),

        (
            'Payment Information',
            {
                'fields': (

                    'payment_method',

                    'payment_status',

                    'razorpay_order_id',

                    'razorpay_payment_id',

                    'razorpay_signature',

                )
            }
        ),

        (
            'Timestamps',
            {
                'fields': (

                    'created_at',

                    'updated_at',

                )
            }
        ),

    )

    inlines = [
        OrderItemInline
    ]

# ============================================================
# ORDER ITEM ADMIN
# ============================================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (

        'order',

        'product_name',

        'size',

        'price',

        'quantity',

        'total_price',

    )

    search_fields = (

        'product_name',

        'order__order_number',

        'size',

    )