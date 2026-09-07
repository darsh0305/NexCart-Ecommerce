from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(
        self,
        *args,
        **kwargs
    ):

        if not self.slug:

            self.slug = slugify(
                self.name
            )

        super().save(
            *args,
            **kwargs
        )

    def __str__(self):

        return self.name


class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_products',
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True
    )

    brand = models.CharField(
        max_length=100,
        blank=True
    )

    author = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    stock = models.PositiveIntegerField(
        default=0
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5
    )

    image = models.ImageField(
        upload_to='products/'
    )

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('out_of_stock', 'Out of Stock'),
        ('draft', 'Draft'),
    ]

    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    size = models.CharField(
        max_length=5,
        choices=SIZE_CHOICES,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    is_featured = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(
        self,
        *args,
        **kwargs
    ):

        if not self.slug:

            self.slug = slugify(
                self.name
            )

        if self.stock <= 0 and self.status == 'active':
            self.status = 'out_of_stock'

        self.is_active = (self.status == 'active')

        super().save(
            *args,
            **kwargs
        )

    @property
    def author_or_brand_label(self):
        if self.category and self.category.name == 'Books & Education':
            return 'Author'
        return 'Brand'

    @property
    def author_or_brand_value(self):
        if self.category and self.category.name == 'Books & Education':
            return self.author
        return self.brand

    @property
    def discounted_price(self):

        discount_amount = (
            self.price
            * self.discount_percentage
            / 100
        )

        return (
            self.price
            - discount_amount
        )

    @property
    def selling_price(self):
        return self.discounted_price

    @property
    def is_in_stock(self):

        return self.stock > 0 and self.status == 'active'

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.low_stock_threshold

    def get_stock_for_size(self, size_code):
        if not size_code:
            return self.stock
        variant = self.size_variants.filter(size=size_code).first()
        return variant.stock if variant else 0

    @property
    def has_size_variants(self):
        return self.size_variants.exists()

    @property
    def total_size_stock(self):
        if self.has_size_variants:
            return sum(v.stock for v in self.size_variants.all())
        return self.stock

    def __str__(self):

        return self.name


class ProductSizeVariant(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='size_variants'
    )

    size = models.CharField(
        max_length=5,
        choices=Product.SIZE_CHOICES
    )

    stock = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        unique_together = ('product', 'size')
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} - Size {self.size} (Stock: {self.stock})"


class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(
        upload_to='products/gallery/'
    )

    alt_text = models.CharField(
        max_length=200,
        blank=True
    )

    is_main = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.product.name} - Image"
