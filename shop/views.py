from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from .forms import DEFAULT_SORT, FILTER_FIELDS, SORT_OPTIONS, ProductFilterForm, ProductForm
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
# HW43: ძებნა + ფილტრაცია + სორტირება (ერთი საერთო ლოგიკა სამი სიისთვის)
# ---------------------------------------------------------------------------

def format_price(value):
    """Decimal("100.00") -> "100", Decimal("99.50") -> "99.5" (ჩიპზე ზედმეტი ნულების გარეშე)."""
    return format(value.normalize(), "f")


class ProductFilterMixin:
    """
    ძებნა, ფილტრაცია და სორტირება პროდუქტების სიაზე. mixin-ს იყენებს სამივე სია: მთავარი,
    კატეგორიის და sale გვერდი, ამიტომ ლოგიკა ერთხელ წერია და ყველგან ერთნაირად მუშაობს.

    როგორ მუშაობს "ერთად": ყველაფერი ერთ ?...-ში წერია, მაგ.
        /?q=laptop&category=2&min_price=500&max_price=2000&sale=on&sort=price_desc&page=2
    ProductFilterForm ამ პარამეტრებს ამოწმებს, filter_products კი მათ ერთმანეთის მიყოლებით
    ადებს ერთსა და იმავე queryset-ს: ჯერ ძებნა, მერე ფილტრები (ყოველი ფილტრი წინა შედეგს
    კიდევ უფრო ავიწროვებს), ბოლოს სორტირება. ამიტომ სორტირება ფილტრს არ აუქმებს, ფილტრი -
    სორტირებას, გვერდების ნომრები (page) კი ორივეს ინახავს (იხ. pagination ტეგი).

    fixed_filters: ველები, რომლებიც ამ გვერდზე უკვე დაფიქსირებულია (კატეგორიის გვერდზე
    "category", sale-ის გვერდზე "sale"). ფორმაში ისინი აღარ ჩანს და ?category=... იგნორირდება.
    """

    fixed_filters = ()

    # --- ფორმა -------------------------------------------------------------

    def get_filter_form(self):
        """ფორმა ერთხელ იქმნება და ერთხელვე მოწმდება (მერე იგივე ობიექტი ბრუნდება)."""
        if not hasattr(self, "_filter_form"):
            form = ProductFilterForm(self.request.GET, fixed=self.fixed_filters)
            if "category" in form.fields:
                # select-ში მხოლოდ არაცარიელი კატეგორიებია, ისევე როგორც ზედა მენიუში
                form.fields["category"].queryset = get_categories_with_products()
            # is_valid() სწორედ cleaned_data-ს ავსებს: არასწორი ველი მასში უბრალოდ არ არის
            form.is_valid()
            self._filter_form = form
        return self._filter_form

    def get_sort(self):
        """მიმდინარე სორტირების გასაღები (არასწორი ან არარსებული ?sort=-ის დროს სტანდარტული)."""
        return self.get_filter_form().cleaned_data.get("sort") or DEFAULT_SORT

    # --- queryset ----------------------------------------------------------

    def filter_products(self, products):
        """პროდუქტებს ადებს ძებნას, ფილტრებს და სორტირებას (ზუსტად ამ თანმიმდევრობით)."""
        data = self.get_filter_form().cleaned_data

        # 1) ძებნა: ყოველი სიტყვა უნდა იყოს სახელში ან აღწერაში. "asus laptop" და "laptop asus"
        #    ერთსა და იმავეს პოულობს. Q-ს "|" ნიშნავს "ან"-ს, ზედიზედ filter-ები კი "და"-ს.
        for word in data.get("q", "").split():
            products = products.filter(Q(name__icontains=word) | Q(description__icontains=word))

        # 2) ფილტრები (თითოეული მხოლოდ მაშინ, როცა მითითებულია)
        if data.get("category"):
            products = products.filter(category=data["category"])
        if data.get("min_price") is not None:
            products = products.filter(price__gte=data["min_price"])
        if data.get("max_price") is not None:
            products = products.filter(price__lte=data["max_price"])
        if data.get("sale"):
            products = products.filter(has_discount=True)

        # 3) სორტირება
        return products.order_by(*SORT_OPTIONS[self.get_sort()][2])

    # --- ბმულები და შაბლონის მონაცემები -----------------------------------

    def url_with(self, remove=(), **changes):
        """
        მიმდინარე მისამართი "?..." სახით ცვლილებებით: remove-ში მითითებული პარამეტრები იშლება,
        changes-ში მითითებული იცვლება, დანარჩენი ინახება. page ყოველთვის იშლება: ფილტრის ან
        სორტირების შეცვლის შემდეგ პირველ გვერდზე ვბრუნდებით (მესამე გვერდი შეიძლება აღარ არსებობდეს).
        """
        params = self.request.GET.copy()
        for name in (*remove, "page"):
            params.pop(name, None)
        for name, value in changes.items():
            params[name] = value
        return "?" + params.urlencode()

    def get_active_filters(self):
        """
        ჩართული ფილტრები "ჩიპებისთვის" ("Category: Laptops ✕"). ჩიპზე დაჭერა მხოლოდ ამ ფილტრს
        ხსნის, დანარჩენი (და სორტირებაც) რჩება.
        """
        data = self.get_filter_form().cleaned_data
        chips = []
        if data.get("q"):
            chips.append({"label": f"Search: “{data['q']}”", "url": self.url_with(remove=["q"])})
        if data.get("category"):
            chips.append({"label": f"Category: {data['category'].name}", "url": self.url_with(remove=["category"])})
        low, high = data.get("min_price"), data.get("max_price")
        if low is not None or high is not None:
            if low is not None and high is not None:
                label = f"Price: {format_price(low)} – {format_price(high)} ₾"
            elif low is not None:
                label = f"Price: from {format_price(low)} ₾"
            else:
                label = f"Price: up to {format_price(high)} ₾"
            chips.append({"label": label, "url": self.url_with(remove=["min_price", "max_price"])})
        if data.get("sale"):
            chips.append({"label": "On sale only", "url": self.url_with(remove=["sale"])})
        return chips

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = self.get_sort()
        active_filters = self.get_active_filters()
        context.update(
            {
                "filter_form": self.get_filter_form(),
                "active_filters": active_filters,
                "filters_active": bool(active_filters),
                # ფილტრების გასუფთავება: სორტირება რჩება
                "clear_filters_url": self.url_with(remove=FILTER_FIELDS),
                "sort": sort,
                "sort_label": SORT_OPTIONS[sort][0],
                "sort_text": SORT_OPTIONS[sort][1],
                # ფორმის დამალული ველისთვის: სტანდარტული სორტირების დროს არაფერი იწერება
                "sort_param": "" if sort == DEFAULT_SORT else sort,
                # სორტირების ღილაკები: ყოველი ღილაკი ინახავს მიმდინარე ძებნას და ფილტრებს
                "sort_options": [
                    {
                        "key": key,
                        "label": option[0],
                        "active": key == sort,
                        "url": self.url_with(remove=["sort"]) if key == DEFAULT_SORT else self.url_with(sort=key),
                    }
                    for key, option in SORT_OPTIONS.items()
                ],
            }
        )
        return context


# ---------------------------------------------------------------------------
# გვერდები: ჩამონათვალი და დეტალები (Class-Based Views, HW39)
# ---------------------------------------------------------------------------

class HomeView(ProductFilterMixin, ListView):
    """
    მთავარი გვერდი: ყველა პროდუქტი. ძებნა, ფილტრები და სორტირება (HW43) ProductFilterMixin-შია:
    ?q=... (სახელი/აღწერა), ?category=... (კატეგორიის id), ?min_price=... & ?max_price=...,
    ?sale=on და ?sort=... (იხ. ProductFilterForm). სტანდარტულად პროდუქტები ფასის ზრდადობითაა.

    ListView თვითონ იღებს queryset-ს და შაბლონს აწვდის context_object_name-ით
    ("products"). ფილტრაცია get_queryset-შია, დამატებითი მონაცემები კი
    get_context_data-ში.

    პაგინაცია (HW42): paginate_by = 8 ნიშნავს, რომ გვერდზე 8 პროდუქტია (ბადეში 4 სვეტია,
    ე.ი. 2 სრული რიგი). ListView გვერდებად თვითონ ჭრის queryset-ს (?page=2) და შაბლონს
    აძლევს page_obj-ს; "products" ახლა მხოლოდ მიმდინარე გვერდის პროდუქტებია.
    არარსებულ გვერდზე (?page=99 ან ?page=abc) Django 404-ს აბრუნებს.
    """

    queryset = Product.objects.select_related("category")
    template_name = "shop/home.html"
    context_object_name = "products"
    paginate_by = 8

    def get_queryset(self):
        return self.filter_products(super().get_queryset())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_filter_form().cleaned_data
        category = data.get("category")
        # ფასდაკლებული პროდუქტები მთავარი გვერდის სარეკლამო ბლოკებისთვის
        on_sale = Product.objects.filter(has_discount=True).select_related("category")
        context.update(
            {
                # ზედა ზოლის საძიებო ფორმა ამ ორს იყენებს (ტექსტი და არჩეული კატეგორია)
                "query": data.get("q", ""),
                "selected_category": category.pk if category else None,
                "search_active": context["filters_active"],
                "featured_product": on_sale.order_by("-price").first(),
                "offer_products": on_sale.order_by("price")[:2],
            }
        )
        return context


class CategoryDetailView(ProductFilterMixin, DetailView):
    """
    კონკრეტული კატეგორიის გვერდი: მხოლოდ ამ კატეგორიის პროდუქტები. ამ კატეგორიის შიგნით ძებნა,
    ფასის ფილტრი, "მხოლოდ ფასდაკლებული" და სორტირება (HW43) ProductFilterMixin-ით მუშაობს.
    კატეგორია უკვე არჩეულია, ამიტომ "category" ფილტრი აქ არ არის (fixed_filters).

    DetailView-ს ჩაშენებული პაგინაცია არ აქვს (ის ერთ ობიექტს აჩვენებს, სიას კი არა),
    ამიტომ აქ Paginator-ს ხელით ვიყენებთ. შაბლონს იგივე ცვლადებს ვაწვდით, რასაც ListView
    (page_obj, paginator, is_paginated), ამიტომ შაბლონი იგივეა, რაც SaleView-სთვის.
    """

    queryset = Category.objects.annotate(product_count=Count("products"))
    template_name = "shop/category_detail.html"
    context_object_name = "category"
    paginate_by = 6  # ბადეში 3 სვეტია, ე.ი. 2 სრული რიგი
    fixed_filters = ("category",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_pk_active"] = self.object.pk
        products = self.filter_products(self.object.products.select_related("category"))

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


class SaleView(ProductFilterMixin, ListView):
    """
    ფასდაკლებული პროდუქტების გვერდი (პაგინაციით: გვერდზე 6 პროდუქტი).
    აქაც მუშაობს ძებნა, კატეგორიისა და ფასის ფილტრი და სორტირება (HW43). "sale" ფილტრი აქ არ არის:
    გვერდზე ისედაც მხოლოდ ფასდაკლებული პროდუქტებია (fixed_filters).
    """

    queryset = Product.objects.filter(has_discount=True).select_related("category")
    template_name = "shop/sale.html"
    context_object_name = "products"
    paginate_by = 6
    fixed_filters = ("sale",)

    def get_queryset(self):
        return self.filter_products(super().get_queryset())


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
