from django.conf import settings
from django.db import models

from products.models import Product


class Cart(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def total_items(self):

        return sum(
            item.quantity
            for item in self.items.all()
        )

    @property
    def subtotal(self):

        return sum(
            item.total_price
            for item in self.items.all()
        )

    @property
    def delivery_charge(self):

        if self.subtotal >= 499:
            return 0

        if self.subtotal > 0:
            return 30

        return 0

    @property
    def total_with_delivery(self):

        return self.subtotal + self.delivery_charge

    def __str__(self):

        return f"{self.user}'s Cart"


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    size = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )

    added_at = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def total_price(self):

        return (
            self.product.discounted_price
            * self.quantity
        )

    def __str__(self):

        size_str = f" ({self.size})" if self.size else ""
        return (
            f"{self.product.name}{size_str} "
            f"x {self.quantity}"
        )