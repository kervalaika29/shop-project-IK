from .models import Product
from .views import get_categories_with_products


def shop_sidebar(request):
    """
    ეს მონაცემები საჭიროა თითქმის ყველა გვერდზე (ზედა მენიუს "All Categories",
    საძიებო ველის სია, გვერდითი პანელი, footer), ამიტომ ყოველ view-ში
    ხელით არ ვაწვდით: context processor მათ ყველა შაბლონს ავტომატურად აძლევს.
    """
    return {
        "categories": get_categories_with_products(),
        "sale_products": (
            Product.objects.filter(has_discount=True)
            .select_related("category")
            .order_by("price")[:3]
        ),
    }
