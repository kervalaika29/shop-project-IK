from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
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


# ---------------------------------------------------------------------------
# გვერდები: ჩამონათვალი და დეტალები
# ---------------------------------------------------------------------------

def home(request):
    """
    მთავარი გვერდი: ყველა პროდუქტი ფასის ზრდადობით.
    საძიებო ველიდან მოსულ ?q=... (სახელი) და ?category=... (კატეგორიის id)
    პარამეტრებით სია იფილტრება.
    """
    products = Product.objects.select_related("category").order_by("price")

    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    if query:
        products = products.filter(name__icontains=query)
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    # ფასდაკლებული პროდუქტები მთავარი გვერდის სარეკლამო ბლოკებისთვის
    on_sale = Product.objects.filter(has_discount=True).select_related("category")
    context = {
        "products": products,
        "query": query,
        "selected_category": int(category_id) if category_id.isdigit() else None,
        "search_active": bool(query or category_id.isdigit()),
        "featured_product": on_sale.order_by("-price").first(),
        "offer_products": on_sale.order_by("price")[:2],
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
    }
    return render(request, "shop/category_detail.html", context)


def sale(request):
    """ფასდაკლებული პროდუქტების გვერდი."""
    products = (
        Product.objects.filter(has_discount=True)
        .select_related("category")
        .order_by("price")
    )
    return render(request, "shop/sale.html", {"products": products})


def product_detail(request, pk):
    """პროდუქტის დეტალური გვერდი + იმავე კატეგორიის სხვა პროდუქტები."""
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    related_products = (
        Product.objects.filter(category=product.category)
        .exclude(pk=product.pk)
        .select_related("category")
        .order_by("price")[:4]
    )
    context = {
        "product": product,
        "category_pk_active": product.category_id,
        "related_products": related_products,
    }
    return render(request, "shop/product_detail.html", context)


# ---------------------------------------------------------------------------
# პროდუქტის დამატება / განახლება / წაშლა (CRUD)
# ---------------------------------------------------------------------------

def product_create(request):
    """
    პროდუქტის დამატება.
    GET  - ცარიელი ფორმის ჩვენება.
    POST - მონაცემების შემოწმება; თუ სწორია, ვინახავთ და პროდუქტის გვერდზე გადავდივართ,
           თუ არა და ფორმა შეცდომებით ისევ გამოჩნდება.
    """
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product “{product.name}” was added.")
            return redirect(product)  # product.get_absolute_url()
    else:
        form = ProductForm()
    context = {"form": form, "is_edit": False}
    return render(request, "shop/product_form.html", context)


def product_update(request, pk):
    """
    პროდუქტის განახლება. ფორმა არსებული პროდუქტის მონაცემებით ივსება (instance=product),
    შენახვისას კი ახალი პროდუქტი არ იქმნება, არამედ ეს იგივე ჩანაწერი განახლდება.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product “{product.name}” was updated.")
            return redirect(product)
    else:
        form = ProductForm(instance=product)
    context = {"form": form, "product": product, "is_edit": True}
    return render(request, "shop/product_form.html", context)


def product_delete(request, pk):
    """
    პროდუქტის წაშლა.
    GET  - დადასტურების გვერდი ("ნამდვილად გსურთ წაშლა?"), არაფერი იშლება.
    POST - პროდუქტი იშლება მხოლოდ დადასტურების ღილაკზე დაჭერისას.
    წაშლა მხოლოდ POST-ით ხდება, რომ მისამართზე შემთხვევით გადასვლამ ან ბმულის
    გახსნამ ჩანაწერი არ წაშალოს.
    """
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f"Product “{name}” was deleted.")
        return redirect("home")
    context = {"product": product, "category_pk_active": product.category_id}
    return render(request, "shop/product_confirm_delete.html", context)


# ---------------------------------------------------------------------------
# შაბლონის დანარჩენი გვერდები (ლოგიკის გარეშე, მხოლოდ დიზაინი)
# ---------------------------------------------------------------------------

def cart(request):
    return render(request, "shop/cart.html")


def checkout(request):
    return render(request, "shop/checkout.html")


def contact(request):
    return render(request, "shop/contact.html")
