from django.urls import path

from .views import (
    check_pincode_delivery,
    product_detail,
    product_list,
    submit_product_feedback,
)

urlpatterns = [

    path(
        '',
        product_list,
        name='product_list'
    ),

    path(
        'check-delivery-pincode/',
        check_pincode_delivery,
        name='check_pincode_delivery'
    ),

    path(
        'feedback/<int:order_item_id>/',
        submit_product_feedback,
        name='submit_product_feedback'
    ),

    path(
        '<slug:slug>/',
        product_detail,
        name='product_detail'
    ),

]