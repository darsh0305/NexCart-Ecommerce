from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Address


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_email_verified',
        'is_active',
        'created_at',
    )

    list_filter = (
        'role',
        'is_email_verified',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = (
        '-created_at',
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = (
        'full_name',
        'user',
        'phone',
        'address_type',
        'city',
        'state',
        'pincode',
        'is_default',
        'created_at',
    )

    list_filter = (
        'address_type',
        'is_default',
        'state',
        'city',
        'created_at',
    )

    search_fields = (
        'full_name',
        'phone',
        'user__username',
        'user__email',
        'city',
        'pincode',
    )