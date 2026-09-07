
from django.db import migrations
from django.utils.text import slugify


def create_categories(apps, schema_editor):
    Category = apps.get_model('products', 'Category')

    categories = [
        {
            'name': 'Electronics',
            'description': 'Discover the latest electronics and gadgets.',
        },
        {
            'name': 'Fashion',
            'description': 'Explore trending fashion and apparel.',
        },
        {
            'name': 'Books & Education',
            'description': 'Learn and grow with our book collection.',
        },
        {
            'name': 'Sports & Fitness',
            'description': 'Everything you need for your fitness journey.',
        },
    ]

    for cat in categories:
        name = cat['name']
        description = cat['description']

        # build a unique slug (avoid collisions)
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        Category.objects.update_or_create(
            name=name,
            defaults={
                'description': description,
                'slug': slug,
            }
        )


def remove_categories(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    names = ['Electronics', 'Fashion', 'Books & Education', 'Sports & Fitness']
    Category.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_alter_productimage_options'),
    ]

    operations = [
        migrations.RunPython(create_categories, remove_categories),
    ]
