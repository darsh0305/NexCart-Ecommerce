from django.contrib import admin

from .models import (
    Category,
    Product,
    ProductImage,
    ProductSizeVariant,
)


class ProductSizeVariantInline(
    admin.TabularInline
):
    model = ProductSizeVariant
    extra = 5


class ProductImageInline(
    admin.TabularInline
):

    model = ProductImage
    extra = 3
    fields = (
        'image',
        'alt_text',
        'is_main',
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
    )

    prepopulated_fields = {
        'slug': (
            'name',
        )
    }

    ordering = (
        'name',
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    inlines = [
        ProductSizeVariantInline,
        ProductImageInline,
    ]

    list_display = (
        'name',
        'category',
        'seller',
        'brand',
        'author',
        'size',
        'price',
        'discount_percentage',
        'get_discounted_price',
        'stock',
        'low_stock',
        'is_active',
        'is_featured',
        'created_at',
    )

    list_filter = (
        'category',
        'size',
        'is_active',
        'is_featured',
        'created_at',
    )

    search_fields = (
        'name',
        'author',
        'brand',
        'description',
    )

    prepopulated_fields = {
        'slug': (
            'name',
        )
    }

    list_editable = (
        'price',
        'discount_percentage',
        'stock',
        'is_active',
        'is_featured',
    )

    ordering = (
        '-created_at',
    )

    def get_discounted_price(self, obj):

        return obj.discounted_price

    get_discounted_price.short_description = (
        'Discounted Price'
    )

    def low_stock(self, obj):

        return obj.stock <= 5

    low_stock.boolean = True
    low_stock.short_description = 'Low Stock'