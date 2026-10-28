from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.http import Http404
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

    პაგინაცია (HW42): paginate_by = 8 ნიშნავს, რომ გვერდზე 8 პროდუქტია (ბადეში 4 სვეტია,
    ე.ი. 2 სრული რიგი). ListView გვერდებად თვითონ ჭრის queryset-ს (?page=2) და შაბლონს
    აძლევს page_obj-ს; "products" ახლა მხოლოდ მიმდინარე გვერდის პროდუქტებია.
    არარსებულ გვერდზე (?page=99 ან ?page=abc) Django 404-ს აბრუნებს.
    """

    queryset = Product.objects.select_related("category").order_by("price")
    template_name = "shop/home.html"
    context_object_name = "products"
    paginate_by = 8

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
    """
    კონკრეტული კატეგორიის გვერდი: მხოლოდ ამ კატეგორიის პროდუქტები.

    DetailView-ს ჩაშენებული პაგინაცია არ აქვს (ის ერთ ობიექტს აჩვენებს, სიას კი არა),
    ამიტომ აქ Paginator-ს ხელით ვიყენებთ. შაბლონს იგივე ცვლადებს ვაწვდით, რასაც ListView
    (page_obj, paginator, is_paginated), ამიტომ შაბლონი იგივეა, რაც SaleView-სთვის.
    """

    queryset = Category.objects.annotate(product_count=Count("products"))
    template_name = "shop/category_detail.html"
    context_object_name = "category"
    paginate_by = 6  # ბადეში 3 სვეტია, ე.ი. 2 სრული რიგი

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_pk_active"] = self.object.pk
        products = self.object.products.select_related("category").order_by("price")

        paginator = Paginator(products, self.paginate_by)
        try:
            page_obj = paginator.page(self.request.GET.get("page") or 1)
        except (PageNotAnInteger, EmptyPage):
            # ListView-ს მსგავსად: არარსებულ გვერდზე 404
            raise Http404("Invalid page.")
        context.update(
            {
                "products": page_obj.object_list,  # მხოლოდ მიმდინარე გვერდის პროდუქტები
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": page_obj.has_other_pages(),
            }
        )
        return context


class SaleView(ListView):
    """ფასდაკლებული პროდუქტების გვერდი (პაგინაციით: გვერდზე 6 პროდუქტი)."""

    queryset = (
        Product.objects.filter(has_discount=True)
        .select_related("category")
        .order_by("price")
    )
    template_name = "shop/sale.html"
    context_object_name = "products"
    paginate_by = 6


class ProductDetailView(DetailView):
    """პროდუქტის დეტალური გვერდი + იმავე კატეგორიის სხვა პროდუქტები."""

    queryset = Product.objects.select_related("category", "user")
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

class ProductCreateView(LoginRequiredMixin, CreateView):
    """
    პროდუქტის დამატება. მხოლოდ სისტემაში შესული მომხმარებლისთვის (LoginRequiredMixin):
    ანონიმური მომხმარებელი შესვლის გვერდზე გადადის (LOGIN_URL), შესვლის შემდეგ კი
    ?next=... მისამართით ისევ დამატების გვერდზე ბრუნდება.

    GET  - ცარიელი ფორმის ჩვენება.
    POST - მონაცემების შემოწმება; თუ სწორია, CreateView ინახავს და პროდუქტის
           გვერდზე გადადის (მისამართს იღებს product.get_absolute_url()-იდან),
           თუ არა და ფორმა შეცდომებით ისევ გამოჩნდება.
    ატვირთული სურათი request.FILES-შია; CreateView ფორმას მას თვითონ გადასცემს.
    """

    model = Product
    form_class = ProductForm
    template_name = "shop/product_form.html"
    extra_context = {"is_edit": False}

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.info(self.request, "Please log in to add a product.")
        return super().handle_no_permission()

    def form_valid(self, form):
        # მფლობელს ფორმიდან არ ვიღებთ: ვწერთ იმ მომხმარებელს, ვინც ახლა შესულია სისტემაში
        form.instance.user = self.request.user
        response = super().form_valid(form)  # აქ შეინახა და self.object შეიქმნა
        messages.success(self.request, f"Product “{self.object.name}” was added.")
        return response


# დავალების პირობით update და delete კვლავ ჩვეულებრივი (function-based) view-ებია.

def get_product_for_owner(request, pk):
    """
    პროდუქტს იღებს განახლებისთვის ან წაშლისთვის და ამოწმებს, რომ ის ამ მომხმარებელს ეკუთვნის.
    არარსებულ პროდუქტზე 404, სხვისზე (ან უმფლობელო პროდუქტზე) კი 403 (PermissionDenied).
    ფუნქცია მხოლოდ @login_required view-ებიდან გამოიძახება, ამიტომ request.user ყოველთვის შესულია.
    """
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    if not product.is_owned_by(request.user):
        raise PermissionDenied("Only the user who added a product can change or delete it.")
    return product


@login_required
def product_update(request, pk):
    """
    პროდუქტის განახლება (მხოლოდ მფლობელისთვის). ფორმა არსებული პროდუქტის მონაცემებით ივსება
    (instance=product), შენახვისას კი ახალი პროდუქტი არ იქმნება, არამედ ეს იგივე ჩანაწერი
    განახლდება. request.FILES-ით ახალი სურათიც მოდის (სურათის შეცვლა/წაშლა).
    user ველი ფორმაში არ არის, ამიტომ მფლობელი განახლებისას არ იცვლება.
    """
    product = get_product_for_owner(request, pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product “{product.name}” was updated.")
            return redirect(product)
    else:
        form = ProductForm(instance=product)
    context = {"form": form, "product": product, "is_edit": True}
    return render(request, "shop/product_form.html", context)


@login_required
def product_delete(request, pk):
    """
    პროდუქტის წაშლა (მხოლოდ მფლობელისთვის).
    GET  - დადასტურების გვერდი ("ნამდვილად გსურთ წაშლა?"), არაფერი იშლება.
    POST - პროდუქტი იშლება მხოლოდ დადასტურების ღილაკზე დაჭერისას.
    წაშლა მხოლოდ POST-ით ხდება, რომ მისამართზე შემთხვევით გადასვლამ ან ბმულის
    გახსნამ ჩანაწერი არ წაშალოს.
    """
    product = get_product_for_owner(request, pk)
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
