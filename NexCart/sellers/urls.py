from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path(
        '',
        views.seller_dashboard,
        name='seller_dashboard'
    ),

    # Products
    path(
        'products/',
        views.seller_products,
        name='seller_products'
    ),
    path(
        'products/add/',
        views.seller_product_add,
        name='seller_product_add'
    ),
    path(
        'products/<int:product_id>/edit/',
        views.seller_product_edit,
        name='seller_product_edit'
    ),
    path(
        'products/<int:product_id>/delete/',
        views.seller_product_delete,
        name='seller_product_delete'
    ),
    path(
        'products/<int:product_id>/status/',
        views.update_product_status,
        name='update_product_status'
    ),

    # Orders
    path(
        'orders/',
        views.seller_orders,
        name='seller_orders'
    ),
    path(
        'orders/<int:order_id>/status/',
        views.update_order_status,
        name='update_order_status'
    ),

    # Sales Reports
    path(
        'sales/',
        views.seller_sales_report,
        name='seller_sales_report'
    ),
    path(
        'sales-report/',
        views.seller_sales_report,
        name='seller_sales_report_alt'
    ),
]
