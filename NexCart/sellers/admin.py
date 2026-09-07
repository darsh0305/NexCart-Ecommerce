from django.contrib import admin
from .models import SellerProfile


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'store_name',
        'user',
        'city',
        'is_approved',
        'created_at',
    )
    list_filter = (
        'is_approved',
        'created_at',
    )
    search_fields = (
        'store_name',
        'user__username',
        'user__email',
    )
    list_editable = (
        'is_approved',
    )
    ordering = (
        '-created_at',
    )

