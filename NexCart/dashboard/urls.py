from django.urls import path

from . import views


urlpatterns = [

    path(
        '',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'orders/',
        views.admin_orders,
        name='admin_orders'
    ),

    path(
        'orders/<int:order_id>/',
        views.admin_order_detail,
        name='admin_order_detail'
    ),

    path(
        'orders/<int:order_id>/status/',
        views.admin_update_order_status,
        name='admin_update_order_status'
    ),

    path(
        'seller/<int:seller_id>/approve/',
        views.approve_seller_quick,
        name='admin_approve_seller'
    ),

    path(
        'seller/<int:seller_id>/reject/',
        views.reject_seller_quick,
        name='admin_reject_seller'
    ),

]
