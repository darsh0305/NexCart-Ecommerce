from django.urls import path

from .views import (
    cancel_order,
    checkout,
    create_razorpay_order,
    download_invoice,
    my_orders,
    order_detail,
    order_list,
    order_success,
    order_tracking,
    place_order,
    reorder_order,
    seller_sales_report,
    update_delivery_status,
    verify_razorpay_payment,
    view_invoice,
)

urlpatterns = [

    path(
        'checkout/',
        checkout,
        name='checkout'
    ),


    path(
        'razorpay/create/',
        create_razorpay_order,
        name='create_razorpay_order'
    ),

    path(
        'razorpay/verify/',
        verify_razorpay_payment,
        name='verify_razorpay_payment'
    ),

    path(
        'place/<int:address_id>/',
        place_order,
        name='place_order'
    ),

    path(
        'success/<str:order_number>/',
        order_success,
        name='order_success'
    ),

    path(
        'my-orders/',
        my_orders,
        name='my_orders'
    ),

    path(
        'orders/',
        order_list,
        name='order_list'
    ),

    path(
        'my-orders/<int:order_id>/',
        order_detail,
        name='order_detail'
    ),

    path(
        'my-orders/<str:order_number>/',
        order_detail,
        name='order_detail_number'
    ),

    path(
        '<int:order_id>/',
        order_detail,
        name='order_detail_direct'
    ),


    # Step 29: Order Tracking & Timeline
    path(
        'tracking/<int:order_id>/',
        order_tracking,
        name='order_tracking'
    ),

    path(
        'tracking/<str:order_id>/',
        order_tracking,
        name='order_tracking_number'
    ),

    path(
        'order/<int:order_id>/status/',
        update_delivery_status,
        name='update_delivery_status'
    ),

    path(
        'order/<int:order_id>/cancel/',
        cancel_order,
        name='cancel_order'
    ),

    path(
        'order/<int:order_id>/reorder/',
        reorder_order,
        name='reorder_order'
    ),

    path(
        'invoice/<int:order_id>/',
        view_invoice,
        name='view_invoice'
    ),

    path(
        'invoice/<int:order_id>/pdf/',
        download_invoice,
        name='download_invoice'
    ),

    path(
        'sales-report/',
        seller_sales_report,
        name='order_sales_report'
    ),

]