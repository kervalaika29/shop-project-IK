from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView

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
# გვერდები: ჩამონათვალი და დეტალები (Class-Based Views, HW39)
# ---------------------------------------------------------------------------

class HomeView(ListView):
    """
    მთავარი გვერდი: ყველა პროდუქტი ფასის ზრდადობით.
    საძიებო ველიდან მოსულ ?q=... (სახელი) და ?category=... (კატეგორიის id)
    პარამეტრებით სია იფილტრება.

    ListView თვითონ იღებს queryset-ს და შაბლონს აწვდის context_object_name-ით
    ("products"). ფილტრაცია get_queryset-შია, დამატებითი მონაცემები კი
    get_context_data-ში.
    """

    queryset = Product.objects.select_related("category").order_by("price")
    template_name = "shop/home.html"
    context_object_name = "products"

    def get_query(self):
        """საძიებო ტექსტი (?q=...), ზედმეტი გამოტოვებების გარეშე."""
        return self.request.GET.get("q", "").strip()

    def get_category_id(self):
        """არჩეული კატეგორიის id (?category=...) ან None, თუ ციფრი არ არის."""
        category_id = self.request.GET.get("category", "")
        return int(category_id) if category_id.isdecimal() else None

    def get_queryset(self):
        products = super().get_queryset()
        query = self.get_query()
        category_id = self.get_category_id()
        if query:
            products = products.filter(name__icontains=query)
        if category_id is not None:
            products = products.filter(category_id=category_id)
        return products

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.get_query()
        category_id = self.get_category_id()
        # ფასდაკლებული პროდუქტები მთავარი გვერდის სარეკლამო ბლოკებისთვის
        on_sale = Product.objects.filter(has_discount=True).select_related("category")
        context.update(
            {
                "query": query,
                "selected_category": category_id,
                "search_active": bool(query) or category_id is not None,
                "featured_product": on_sale.order_by("-price").first(),
                "offer_products": on_sale.order_by("price")[:2],
            }
        )
        return context


class CategoryDetailView(DetailView):
    """კონკრეტული კატეგორიის გვერდი: მხოლოდ ამ კატეგორიის პროდუქტები."""

    queryset = Category.objects.annotate(product_count=Count("products"))
    template_name = "shop/category_detail.html"
    context_object_name = "category"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_pk_active"] = self.object.pk
        context["products"] = self.object.products.select_related("category").order_by(
            "price"
        )
        return context


class SaleView(ListView):
    """ფასდაკლებული პროდუქტების გვერდი."""

    queryset = (
        Product.objects.filter(has_discount=True)
        .select_related("category")
        .order_by("price")
    )
    template_name = "shop/sale.html"
    context_object_name = "products"


class ProductDetailView(DetailView):
    """პროდუქტის დეტალური გვერდი + იმავე კატეგორიის სხვა პროდუქტები."""

    queryset = Product.objects.select_related("category")
    template_name = "shop/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["category_pk_active"] = product.category_id
        context["related_products"] = (
            Product.objects.filter(category=product.category)
            .exclude(pk=product.pk)
            .select_related("category")
            .order_by("price")[:4]
        )
        return context


# ---------------------------------------------------------------------------
# პროდუქტის დამატება / განახლება / წაშლა (CRUD)
# ---------------------------------------------------------------------------

class ProductCreateView(CreateView):
    """
    პროდუქტის დამატება.
    GET  - ცარიელი ფორმის ჩვენება.
    POST - მონაცემების შემოწმება; თუ სწორია, CreateView ინახავს და პროდუქტის
           გვერდზე გადადის (მისამართს იღებს product.get_absolute_url()-იდან),
           თუ არა და ფორმა შეცდომებით ისევ გამოჩნდება.
    """

    model = Product
    form_class = ProductForm
    template_name = "shop/product_form.html"
    extra_context = {"is_edit": False}

    def form_valid(self, form):
        response = super().form_valid(form)  # აქ შეინახა და self.object შეიქმნა
        messages.success(self.request, f"Product “{self.object.name}” was added.")
        return response


# დავალების პირობით update და delete კვლავ ჩვეულებრივი (function-based) view-ებია.

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

class CartView(TemplateView):
    template_name = "shop/cart.html"


class CheckoutView(TemplateView):
    template_name = "shop/checkout.html"


class ContactView(TemplateView):
    template_name = "shop/contact.html"
