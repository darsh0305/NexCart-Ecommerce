from django.urls import path

from .views import (
    add_to_cart,
    cart_detail,
    decrease_quantity,
    increase_quantity,
    remove_from_cart,
)


urlpatterns = [

    path(
        '',
        cart_detail,
        name='cart_detail'
    ),

    path(
        'add/<int:product_id>/',
        add_to_cart,
        name='add_to_cart'
    ),

    path(
        'increase/<int:item_id>/',
        increase_quantity,
        name='increase_quantity'
    ),

    path(
        'decrease/<int:item_id>/',
        decrease_quantity,
        name='decrease_quantity'
    ),

    path(
        'remove/<int:item_id>/',
        remove_from_cart,
        name='remove_from_cart'
    ),

]