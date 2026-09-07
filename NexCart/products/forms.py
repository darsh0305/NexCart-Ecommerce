from django import forms
from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'price',
            'discount_percentage',
            'stock',
            'low_stock_threshold',
            'category',
            'brand',
            'author',
            'size',
            'image',
            'status',
        ]
