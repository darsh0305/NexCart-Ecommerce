from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(
    admin.TabularInline
):

    model = CartItem
    fields = ('product', 'size', 'quantity', 'added_at')
    readonly_fields = ('added_at',)
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'user__email',
        'user__username',
    )

    inlines = [
        CartItemInline
    ]