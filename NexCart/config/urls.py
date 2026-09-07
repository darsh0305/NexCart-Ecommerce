from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from products.views import home, product_list


urlpatterns = [

    # Admin
    path(
        'admin/',
        admin.site.urls
    ),

    # Admin Dashboard
    path(
        'dashboard/',
        include('dashboard.urls')
    ),
    path(
        'admin-dashboard/',
        include('dashboard.urls')
    ),

    # Home Page
    path(
        '',
        home,
        name='home'
    ),

    # Product aliases: keep both singular and plural storefront URLs working.
    path(
        'product',
        product_list,
        name='product_list_no_slash'
    ),
    # Accounts
    path(
        'accounts/',
        include('accounts.urls')
    ),

    # Products
    path(
        'products/',
        include('products.urls')
    ),
    path(
        'product/',
        include('products.urls')
    ),
    path(
        'cart/',
        include('cart.urls')
    ),
    path(
        'orders/',
        include('orders.urls')
    ),
    path(
        'seller/',
        include('sellers.urls')
    ),
]


if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )