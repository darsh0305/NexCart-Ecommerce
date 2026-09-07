from django.conf import settings
from django.db import models

from products.models import Product


# ============================================================
# ORDER
# ============================================================

class Order(models.Model):

    # --------------------------------------------------------
    # ORDER STATUS
    # --------------------------------------------------------

    ORDER_STATUS_CHOICES = [

        ('pending', 'Pending'),

        ('confirmed', 'Confirmed'),

        ('processing', 'Processing'),

        ('shipped', 'Shipped'),

        ('out_for_delivery', 'Out for Delivery'),

        ('delivered', 'Delivered'),

        ('cancelled', 'Cancelled'),

    ]


    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    PAYMENT_METHOD_CHOICES = [

        ('cod', 'Cash on Delivery'),

        ('razorpay', 'Razorpay'),

    ]


    # --------------------------------------------------------
    # PAYMENT STATUS
    # --------------------------------------------------------

    PAYMENT_STATUS_CHOICES = [

        ('pending', 'Pending'),

        ('paid', 'Paid'),

        ('failed', 'Failed'),

        ('refunded', 'Refunded'),

    ]


    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )


    # --------------------------------------------------------
    # SHIPPING ADDRESS SNAPSHOT
    # --------------------------------------------------------

    address = models.ForeignKey(
        'accounts.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    shipping_name = models.CharField(
        max_length=150,
        blank=True
    )

    shipping_phone = models.CharField(
        max_length=15,
        blank=True
    )

    shipping_address = models.TextField(
        blank=True
    )

    shipping_city = models.CharField(
        max_length=100,
        blank=True
    )

    shipping_state = models.CharField(
        max_length=100,
        blank=True
    )

    shipping_pincode = models.CharField(
        max_length=10,
        blank=True
    )



    # --------------------------------------------------------
    # NEXCART ORDER NUMBER
    # --------------------------------------------------------

    order_number = models.CharField(
        max_length=30,
        unique=True
    )


    # --------------------------------------------------------
    # PRICE INFORMATION
    # --------------------------------------------------------

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    delivery_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'
    )


    # --------------------------------------------------------
    # PAYMENT STATUS
    # --------------------------------------------------------

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )


    # ========================================================
    # RAZORPAY INFORMATION
    # ========================================================

    # Razorpay Order ID
    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )


    # Razorpay Payment ID
    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )


    # Razorpay Signature
    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )


    # --------------------------------------------------------
    # ORDER STATUS
    # --------------------------------------------------------

    status = models.CharField(
        max_length=30,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )


    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def save(self, *args, **kwargs):
        # Automatically mark COD orders as paid when delivery status is set to delivered
        if self.status == 'delivered' and self.payment_method == 'cod' and self.payment_status == 'pending':
            self.payment_status = 'paid'
            if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
                kwargs['update_fields'] = list(set(kwargs['update_fields']) | {'payment_status'})

        super().save(*args, **kwargs)

    @property
    def delivery_status(self):
        return self.status

    @delivery_status.setter
    def delivery_status(self, value):
        self.status = value

    def get_delivery_status_display(self):
        return self.get_status_display()

    def __str__(self):

        return self.order_number



# ============================================================
# ORDER ITEM
# ============================================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    # Store product name at the time of purchase
    product_name = models.CharField(
        max_length=255
    )

    # Store product price at the time of purchase
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField()

    size = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    def __str__(self):

        size_str = f" ({self.size})" if self.size else ""
        return (
            f"{self.product_name}{size_str} "
            f"x {self.quantity}"
        )