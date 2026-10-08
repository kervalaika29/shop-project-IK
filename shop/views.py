from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def get_categories_with_products():
    """
    კატეგორიების ჩამონათვალი: მხოლოდ ის კატეგორიები, რომლებშიც მინიმუმ
    ერთი პროდუქტია. annotate-ით ვითვლით თითოეული კატეგორიის პროდუქტების
    რაოდენობას (product_count), შემდეგ filter-ით ვტოვებთ არაცარიელებს.
    """
    return (
        Category.objects.annotate(product_count=Count("products"))
        .filter(product_count__gt=0)
        .order_by("name")
    )


def home(request):
    """მთავარი გვერდი: ყველა პროდუქტი ფასის ზრდადობით + კატეგორიების სია."""
    products = Product.objects.select_related("category").order_by("price")
    context = {
        "products": products,
        "categories": get_categories_with_products(),
    }
    return render(request, "shop/home.html", context)


def category_detail(request, pk):
    """კონკრეტული კატეგორიის გვერდი: მხოლოდ ამ კატეგორიის პროდუქტები."""
    category = get_object_or_404(
        Category.objects.annotate(product_count=Count("products")), pk=pk
    )
    products = category.products.select_related("category").order_by("price")
    context = {
        "category": category,
        "category_pk_active": category.pk,
        "products": products,
        "categories": get_categories_with_products(),
    }
    return render(request, "shop/category_detail.html", context)


def sale(request):
    """ფასდაკლებული პროდუქტების გვერდი."""
    products = (
        Product.objects.filter(has_discount=True)
        .select_related("category")
        .order_by("price")
    )
    context = {
        "products": products,
        "categories": get_categories_with_products(),
    }
    return render(request, "shop/sale.html", context)


def product_detail(request, pk):
    """პროდუქტის დეტალური გვერდი."""
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    context = {
        "product": product,
        "categories": get_categories_with_products(),
    }
    return render(request, "shop/product_detail.html", context)
