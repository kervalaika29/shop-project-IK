# Mini Shop — Django Homework 45

Django პროექტი პროდუქტებითა და კატეგორიებით (ბაზა: **sqlite3**).

- დავალება 37: პროდუქტის **დამატების, განახლების და წაშლის** ლოგიკა + **Electro HTML შაბლონების** მორგება პროექტზე.
- დავალება 39: აქამდე არსებული ყველა view გადაკეთებულია Class-Based-View-ებად (update-ისა და delete-ის გარდა).
- დავალება 41: ახალი `users` აპლიკაცია (Django-ს `User` მოდელი): რეგისტრაცია, შესვლა, გასვლა; პროდუქტს დაემატა სურათი და მფლობელი (`user`); პროდუქტის დამატება მხოლოდ შესულ მომხმარებელს შეუძლია, განახლება და წაშლა კი მხოლოდ იმას, ვინც პროდუქტი დაამატა.
- დავალება 42: (1) პაგინაცია მთავარ, კატეგორიის და sale გვერდებზე; (2) `MAINTENANCE_MODE` middleware: `True`-ზე ყველა გვერდზე ჩანს "Site is under maintenance", `/admin/` კი ჩვეულებრივ მუშაობს; (3) signal, რომელიც პროდუქტის განახლებისას ტერმინალში ბეჭდავს `Product "Asus Laptop" was updated.`
- დავალება 43: პროდუქტების სიებს დაემატა ძებნა, ფილტრაცია (კატეგორია, ფასი, მხოლოდ ფასდაკლებული) და სორტირება (ფასი, სახელი, ახალი). სამივე ერთად მუშაობს: ერთ მისამართში ინახება და პაგინაციასაც არ ეშლება (იხ. [დავალება 43](#დავალება-43-ძებნა-ფილტრაცია-და-სორტირება)).
- დავალება 44: დაემატა მომხმარებლის პაროლის აღდგენა ("Forgot your password?"): email-ზე მოდის ერთჯერადი ბმული, რომლითაც მომხმარებელი ახალ პაროლს აყენებს (იხ. [დავალება 44](#დავალება-44-პაროლის-აღდგენა)).
- **დავალება 45: დაემატა REST API (Django REST Framework, ახალი `api` აპლიკაცია): კატეგორიებისა და პროდუქტების სია, პროდუქტის დეტალური ინფორმაცია და პროდუქტის შექმნა, თითოეულს თავისი სერიალიზატორით (იხ. [დავალება 45](#დავალება-45-rest-api-django-rest-framework)).**

## გაშვება (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

`requirements.txt`-ში ახლა `Pillow`-იც არის: Django-ს `ImageField` მის გარეშე არ მუშაობს.

HW45-დან `requirements.txt`-ში `djangorestframework`-იც არის (REST API). თუ პროექტი უკვე დაყენებული გაქვთ, ერთხელ ისევ გაუშვით `pip install -r requirements.txt`.

შემდეგ ბრაუზერში გახსენით <http://127.0.0.1:8000/>.

ბაზა (`db.sqlite3`) უკვე შევსებულია: 5 კატეგორია, 14 პროდუქტი, HW41-ის მიგრაცია (`0002`) უკვე გაშვებულია. HW42-ს და HW45-ს ახალი მიგრაცია არ სჭირდება.
თუ სხვა (ძველი) ბაზით მუშაობთ, საკმარისია `python manage.py migrate`.
თუ ბაზა თავიდან გინდათ შევსება:

```
python manage.py migrate
python manage.py loaddata initial_data
```

ადმინისტრატორის შესაქმნელად: `python manage.py createsuperuser` (მისამართი: `/admin/`).

> შაბლონის შრიფტები და ხატულები (Font Awesome, Bootstrap JS, jQuery) CDN-იდან იტვირთება, ამიტომ გვერდის სრულყოფილად საჩვენებლად ინტერნეტი სჭირდება.

## გვერდები

| მისამართი | აღწერა |
|---|---|
| `/` | მთავარი: ყველა პროდუქტი (სტანდარტულად ფასის ზრდადობით) + კატეგორიების სია (რაოდენობა ფრჩხილებში), გვერდზე 8 პროდუქტი: `/?page=2`. ძებნა, ფილტრები და სორტირება ერთად: `/?q=laptop&category=1&min_price=500&max_price=2000&sale=on&sort=price_desc` (გვერდებთან ერთად: `...&page=2`) |
| `/category/<id>/` | კონკრეტული კატეგორიის პროდუქტები, გვერდზე 6 პროდუქტი (`?page=2`); აქაც მუშაობს ძებნა, ფასი, sale და სორტირება |
| `/sale/` | ფასდაკლებული პროდუქტები, გვერდზე 6 პროდუქტი (`?page=2`); აქაც მუშაობს ძებნა, კატეგორია, ფასი და სორტირება |
| `/product/<id>/` | პროდუქტის დეტალური გვერდი |
| `/product/add/` | **პროდუქტის დამატება** (`ProductCreateView`), მხოლოდ შესული მომხმარებლისთვის |
| `/product/<id>/edit/` | **პროდუქტის განახლება**, მხოლოდ მფლობელისთვის |
| `/product/<id>/delete/` | **პროდუქტის წაშლა** (ჯერ დადასტურების გვერდი), მხოლოდ მფლობელისთვის |
| `/users/register/` | **რეგისტრაცია** |
| `/users/login/` | **შესვლა** |
| `/users/logout/` | **გასვლა** (მხოლოდ POST, ღილაკი მენიუშია) |
| `/users/password-reset/` | **პაროლის აღდგენა**, 1-ლი ნაბიჯი: email-ის შეყვანა (ბმული შესვლის გვერდზე: "Forgot your password?") |
| `/users/password-reset/done/` | აღდგენა, მე-2 ნაბიჯი: "Check your email" |
| `/users/reset/<uidb64>/<token>/` | აღდგენა, მე-3 ნაბიჯი: ბმული email-იდან, ახალი პაროლის ფორმა |
| `/users/reset/done/` | აღდგენა, მე-4 ნაბიჯი: "პაროლი შეიცვალა" |
| `/api/` | **REST API** (HW45): ყველა endpoint-ის ბმული ერთ ადგილას |
| `/api/categories/` | API: **კატეგორიების სია** (JSON) |
| `/api/products/` | API: **პროდუქტების სია** (JSON) |
| `/api/products/<id>/` | API: **პროდუქტის დეტალური ინფორმაცია** (JSON) |
| `/api/products/create/` | API: **პროდუქტის შექმნა** (POST), მხოლოდ ავტორიზებულისთვის |
| `/api-auth/login/` | DRF-ის შესვლის გვერდი ბრაუზერული API-ისთვის (იგივე მომხმარებლით, რაც საიტზე) |
| `/cart/`, `/checkout/`, `/contact/` | Electro შაბლონის დანარჩენი გვერდები (დემო, ლოგიკის გარეშე) |

## Class-Based Views (HW39)

`shop/views.py`-ში ყველა view კლასია, გარდა `product_update`-ისა და `product_delete`-ისა (დავალების პირობით ისინი ჩვეულებრივი function-based view-ები რჩება). `shop/urls.py`-ში კლასები `.as_view()`-ით ერთვება. URL-ების სახელები (`name=...`) არ შეცვლილა, ამიტომ შაბლონებს არაფერი შეცვლია.

| ძველი view (ფუნქცია) | ახალი view (კლასი) | საბაზო კლასი | რას აკეთებს |
|---|---|---|---|
| `home` | `HomeView` | `ListView` | პროდუქტების სია; ძებნა, ფილტრები და სორტირება `ProductFilterMixin`-ში (HW43), `get_context_data`-ში სარეკლამო ბლოკები |
| `category_detail` | `CategoryDetailView` | `DetailView` | კატეგორია (`product_count`-ით) + მისი პროდუქტები |
| `sale` | `SaleView` | `ListView` | მხოლოდ ფასდაკლებული პროდუქტები |
| `product_detail` | `ProductDetailView` | `DetailView` | პროდუქტი + იმავე კატეგორიის სხვა პროდუქტები (`related_products`) |
| `product_create` | `ProductCreateView` | `CreateView` | დამატების ფორმა (`ProductForm`), შენახვის შემდეგ გადადის პროდუქტის გვერდზე + შეტყობინება `form_valid`-ში |
| `cart` | `CartView` | `TemplateView` | დემო გვერდი |
| `checkout` | `CheckoutView` | `TemplateView` | დემო გვერდი |
| `contact` | `ContactView` | `TemplateView` | დემო გვერდი |
| `product_update` | *უცვლელია (function-based)* | — | განახლება |
| `product_delete` | *უცვლელია (function-based)* | — | წაშლა |

## მომხმარებლები და უფლებები (HW41)

### `users` აპლიკაცია (რეგისტრაცია, შესვლა, გასვლა)

ვიყენებთ Django-ს ჩაშენებულ `User` მოდელს (`django.contrib.auth.models.User`), ამიტომ ახალი მოდელი და მიგრაცია არ გვჭირდება. აპლიკაცია დარეგისტრირებულია `INSTALLED_APPS`-ში, მისამართები `config/urls.py`-შია (`/users/...`).

| რა | სად | როგორ მუშაობს |
|---|---|---|
| რეგისტრაცია | `users.views.RegisterView` (`CreateView`) + `users.forms.RegisterForm` | `UserCreationForm` + სავალდებულო და უნიკალური email. Django ამოწმებს, რომ username თავისუფალია, პაროლები ემთხვევა და პაროლი საკმარისად ძლიერია; პაროლი ინახება დაჰეშილი სახით. წარმატების შემდეგ მომხმარებელი ავტომატურად შედის სისტემაში და მთავარ გვერდზე გადადის |
| შესვლა | `users.views.UserLoginView` (`LoginView`) + `LoginForm` | არასწორი username/პაროლისას ფორმა შეცდომას აჩვენებს. თუ მომხმარებელი დაცული გვერდიდან მოვიდა, შესვლის შემდეგ იქ ბრუნდება (`?next=`), სხვა შემთხვევაში მთავარ გვერდზე გადადის. უკვე შესულს შესვლის და რეგისტრაციის გვერდები მთავარზე გადაჰყავს |
| გასვლა | `users.views.UserLogoutView` (`LogoutView`) | Django 5+ -ში გასვლა მხოლოდ **POST**-ით ხდება (CSRF დაცვა), ამიტომ მენიუში "Logout" ფორმის ღილაკია, ბმული კი არა |

`config/settings.py`-ში: `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "home"`.
მენიუში (`includes/navbar.html`) ანონიმურს ჩანს **Login / Register**, შესულს კი მისი სახელი და **Logout**.

### Product: სურათი და მფლობელი

`shop/models.py`:

- `image = ImageField(upload_to="products/", blank=True)`: სურათი სავალდებულო არ არის (არსებულ 14 პროდუქტს არ აქვს), ამიტომ თუ არ არის ატვირთული, ისევ შაბლონის მზა სურათი ჩანს (`Product.image_url`).
- `user = ForeignKey(User, on_delete=CASCADE, related_name="products", null=True, blank=True)`: პროდუქტის მფლობელი. `null=True` მხოლოდ HW41-მდე არსებული პროდუქტებისთვისაა (მათ მფლობელი არ ჰყავთ, საიტიდან ვერავინ შეცვლის/წაშლის, admin-იდან კი იმართება). საიტიდან დამატებულ პროდუქტს მფლობელი ყოველთვის ეწერება. მიგრაცია: `shop/migrations/0002_product_image_product_user.py`.

სურათის დამუშავება:

- **ფაილის ატვირთვა**: `settings.py`-ში `MEDIA_URL`/`MEDIA_ROOT` (`media/products/`), `config/urls.py`-ში `static(MEDIA_URL, ...)` (მუშაობს `DEBUG=True`-ზე), ფორმას `enctype="multipart/form-data"` აქვს, view-ები `request.FILES`-ს იღებენ.
- **შემოწმება** (`ProductForm.clean_image`): ფაილი მართლა სურათი უნდა იყოს (Pillow), ფორმატი JPG/PNG/GIF/WEBP და ზომა მაქსიმუმ 5 MB.
- **რედაქტირება**: ფორმაში მიმდინარე სურათი ჩანს; ახალი ფაილი ძველს ანაცვლებს, "Clear" ჩეკბოქსი სურათს შლის.
- **გასუფთავება** (`shop/signals.py`): პროდუქტის წაშლისას ან სურათის შეცვლისას ძველი ფაილი დისკიდანაც იშლება.
- `media/` განზრახ არ არის `.gitignore`-ში, როგორც `db.sqlite3`, რომ ბაზაში ჩაწერილ სურათებს ფაილებიც გაჰყვეს GitHub-ზე.

### უფლებები

| მოქმედება | ანონიმური | შესული, სხვისი პროდუქტი | მფლობელი |
|---|---|---|---|
| პროდუქტის ნახვა | კი | კი | კი |
| დამატება | გადადის შესვლის გვერდზე (`?next=/product/add/`) | კი | კი |
| განახლება / წაშლა | გადადის შესვლის გვერდზე | **403** (ჩვენი `403.html` გვერდი) | კი |

- **დამატება**: `ProductCreateView(LoginRequiredMixin, CreateView)`. `user` ველი ფორმაში **არ არის**; `form_valid`-ში ვწერთ `form.instance.user = self.request.user`, ე.ი. მფლობელი ის მომხმარებელია, ვინც ამ მომენტში შესულია. ხელით გაგზავნილი `user=...` უბრალოდ იგნორირდება.
- **განახლება და წაშლა**: დავალება 39-ის პირობით ისევ function-based view-ებია, ახლა `@login_required`-ით. ორივე იყენებს `get_product_for_owner()` ფუნქციას: არარსებულ პროდუქტზე 404, სხვისზე (ან უმფლობელოზე) 403 (`PermissionDenied`). ამიტომ დაცულია პირდაპირი მისამართიც და ხელით გაგზავნილი POST-იც.
- **ღილაკები**: Edit/Delete ჩანს მხოლოდ მფლობელისთვის (`{% if product|is_owned_by:user %}`; ფილტრი `shop/templatetags/shop_tags.py`-შია). პროდუქტის გვერდზე ჩანს "Added by".
- "Add Product" ღილაკი ყველას ჩანს: ანონიმურს შესვლის გვერდზე გადაიყვანს, შესვლის შემდეგ კი დამატების ფორმაზე დააბრუნებს.

## დავალება 42

### 1. პაგინაცია

პროდუქტების სია გვერდებად იყოფა, რომ ყველა პროდუქტი ერთ გრძელ გვერდზე არ ჩანდეს.

| გვერდი | view | გვერდზე | რატომ ამდენი |
|---|---|---|---|
| `/` | `HomeView` (`ListView`) | 8 | ბადეში 4 სვეტია: 2 სრული რიგი |
| `/sale/` | `SaleView` (`ListView`) | 6 | ბადეში 3 სვეტია: 2 სრული რიგი |
| `/category/<id>/` | `CategoryDetailView` (`DetailView`) | 6 | იგივე |

- `ListView`-ებში საკმარისი იყო `paginate_by = 8` (ან `6`): Django თვითონ ჭრის queryset-ს `?page=N`-ის მიხედვით და შაბლონს აძლევს `page_obj`-ს, `paginator`-ს და `is_paginated`-ს. `products` ახლა მხოლოდ **მიმდინარე გვერდის** პროდუქტებია.
- `CategoryDetailView` `DetailView`-ია (ერთ კატეგორიას აჩვენებს) და ჩაშენებული პაგინაცია არ აქვს, ამიტომ მის `get_context_data`-ში `Paginator` ხელით ვიყენებთ და შაბლონს იგივე ცვლადებს (`page_obj`, `paginator`, `is_paginated`) ვაწვდით. ასე ერთი და იგივე შაბლონი (`shop_layout.html`) ორივე გვერდს ემსახურება.
- **ნავიგაცია** (`« 1 2 3 … 9 »` და "Showing 9–14 of 14 products") ერთ ადგილას არის: `{% pagination page_obj %}` ტეგი (`shop/templatetags/shop_tags.py`) + `includes/pagination.html`. მხოლოდ ერთი გვერდის შემთხვევაში არაფერი ჩანს. ბევრი გვერდის დროს ნომრები შემოკლებულია (`1 … 11 12 13 14 15 … 25`).
- **ძიება არ იკარგება**: ტეგი მიმდინარე `?q=...&category=...` პარამეტრებს გვერდის ბმულებში ინახავს (`/?q=sony&page=2`).
- **ჯამური რაოდენობა**: სათაურში ("14 products") ჩანს **ყველა** პროდუქტის რაოდენობა (`paginator.count`) და არა მიმდინარე გვერდისა.
- არარსებულ გვერდზე (`?page=99`, `?page=0`, `?page=abc`) 404 ბრუნდება, სამივე გვერდზე ერთნაირად.
- მიმდინარე 14 პროდუქტით მთავარი გვერდი 2 გვერდია (8 + 6). კატეგორიებსა და sale-ში ახლა 6 პროდუქტზე ნაკლებია, ამიტომ იქ ნავიგაცია მხოლოდ მაშინ გამოჩნდება, როცა 6-ზე მეტი პროდუქტი იქნება.

### 2. Maintenance middleware

`config/settings.py`-ში ახალი პარამეტრია:

```python
MAINTENANCE_MODE = False   # True-ზე საიტი "ტექნიკურ სამუშაოებზეა"
```

`MAINTENANCE_MODE = True`-ზე `shop/middleware.py`-ის `MaintenanceModeMiddleware` ყველა request-ზე (ნებისმიერი გვერდი, ფორმა, POST) აბრუნებს გვერდს **"Site is under maintenance"** (`shop/templates/shop/maintenance.html`). გამონაკლისია მხოლოდ **`/admin/`**: ადმინისტრატორი შედის და მუშაობს ჩვეულებრივ.

**როგორ გამოვცადოთ**: `settings.py`-ში ჩაწერეთ `MAINTENANCE_MODE = True`, შეინახეთ (`runserver` თავისით გადაიტვირთება) და გახსენით <http://127.0.0.1:8000/> (ჩანს "Site is under maintenance"), შემდეგ <http://127.0.0.1:8000/admin/> (მუშაობს). გამოსართავად დააბრუნეთ `False`.

როგორ მუშაობს:

- middleware კლასს `__init__(self, get_response)` და `__call__(self, request)` აქვს. `__call__`-ში ვამოწმებთ: თუ რეჟიმი ჩართულია და მისამართი `/admin/`-ით არ იწყება, თვითონ ვაბრუნებთ პასუხს (view საერთოდ არ სრულდება), წინააღმდეგ შემთხვევაში `get_response(request)`-ით request შემდეგ ფენას გადაეცემა.
- პარამეტრს **ყოველ request-ზე** ვკითხულობთ (`getattr(settings, "MAINTENANCE_MODE", False)`), ამიტომ ცვლილება მაშინვე მოქმედებს; თუ პარამეტრი საერთოდ არ არის, საიტი ჩვეულებრივ მუშაობს.
- `/admin/`-ის მისამართს `reverse("admin:index")`-ით ვიღებთ (ხელით ორჯერ არ ვწერთ). `/admin` (ხაზის გარეშე) ჩვეულებრივ `/admin/`-ზე გადადის, `/administrator/` კი **არ** არის admin და იკეტება.
- პასუხის სტატუსი **503 Service Unavailable** ("დროებით მიუწვდომელია") და არა 200: ბრაუზერში ეს არ ჩანს, მაგრამ საძიებო სისტემებს ეუბნება, რომ ეს გვერდის რეალური შიგთავსი არ არის.
- გვერდი request-ის გარეშე რენდერდება და static/CDN-ს არ იყენებს, ამიტომ **ბაზას არ ეხება** (ტექნიკური სამუშაოებისას ბაზა შეიძლება მიუწვდომელი იყოს).
- `MIDDLEWARE` სიაში `CommonMiddleware`-ის შემდეგაა (`/admin` → `/admin/` გადამისამართებისთვის) და CSRF/Auth/Messages-მდე (სესია და ბაზა არ გვჭირდება).

### 3. Signal: პროდუქტის განახლება

`shop/signals.py`:

```python
@receiver(post_save, sender=Product)
def print_product_updated(sender, instance, created, **kwargs):
    if not created:
        print(f'Product "{instance.name}" was updated.', flush=True)
```

პროდუქტის განახლებისას იმ ტერმინალში, სადაც `runserver` გაშვებულია, ჩნდება:

```
Product "Asus Laptop" was updated.
```

- `post_save` ყოველი `.save()`-ის შემდეგ სრულდება. `created=True` ახალი პროდუქტის შექმნაა, ამიტომ მხოლოდ **განახლებისას** ვბეჭდავთ (დამატებისას და წაშლისას არაფერი იბეჭდება).
- მუშაობს ყველგან, სადაც პროდუქტი ინახება: საიტიდან (Edit), admin-იდან და კოდიდან (`product.save()`). view-ებში და admin-ში არაფერი შეცვლილა.
- signal-ი უკვე არსებულ `shop/signals.py`-შია და `ShopConfig.ready()`-ით რეგისტრირდება (როგორც სურათის გასუფთავების signal-ები).
- ყურადღება: `Product.objects.filter(...).update(...)` signal-ს **არ** იძახებს (Django-ში მასობრივი `update()` `save()`-ს არ ეშვება), ამიტომ ასეთ განახლებაზე ტექსტი არ დაიბეჭდება.

## დავალება 43: ძებნა, ფილტრაცია და სორტირება

პროდუქტების სიას (მთავარი, კატეგორიის და sale გვერდი) დაემატა ძებნა, ფილტრაცია და სორტირება. მთავარი მოთხოვნა: **სამივე ერთმანეთთან გადაბმულად მუშაობს**: ძებნის შემდეგ ფილტრის ან სორტირების შეცვლა ძებნას არ ანადგურებს, პაგინაცია კი სამივეს ინახავს.

### პარამეტრები (ყველა მისამართში, `?...`)

| პარამეტრი | სახე | რას აკეთებს | მაგალითი |
|---|---|---|---|
| `q` | ძებნა | პროდუქტის **სახელში ან აღწერაში**; ყოველი სიტყვა უნდა მოიძებნოს, რიგს მნიშვნელობა არ აქვს, დიდი/პატარა ასო არ ითვლება | `?q=asus laptop` |
| `category` | ფილტრი | კატეგორია (id) | `?category=3` |
| `min_price`, `max_price` | ფილტრი | ფასი "დან" და "მდე" (ზღვრები ჩართულია) | `?min_price=500&max_price=2000` |
| `sale` | ფილტრი | მხოლოდ ფასდაკლებული პროდუქტები | `?sale=on` |
| `sort` | სორტირება | `price_asc` (სტანდარტული), `price_desc`, `name_asc`, `name_desc`, `newest` | `?sort=price_desc` |
| `page` | პაგინაცია (HW42) | გვერდის ნომერი | `?page=2` |

ყველაფერი ერთად: `/?q=laptop&category=1&min_price=500&max_price=2000&sale=on&sort=price_desc&page=1`

### როგორ მუშაობს

- **`ProductFilterForm`** (`shop/forms.py`) ჩვეულებრივი `forms.Form`-ია, მაგრამ მონაცემებს POST-ით კი არა, მისამართიდან (`request.GET`) იღებს და არაფერს ინახავს. ის ამოწმებს პარამეტრებს: ფასი რიცხვი უნდა იყოს (`DecimalField` იგივე 10/2 შეზღუდვით, რაც `Product.price`-ს აქვს), `min_price` არ უნდა აღემატებოდეს `max_price`-ს, `sort` უნდა იყოს ცნობილი ვარიანტი, `category` უნდა არსებობდეს.
- **`ProductFilterMixin`** (`shop/views.py`) ერთი საერთო ლოგიკაა სამი სიისთვის. `HomeView`, `CategoryDetailView` და `SaleView` მას იყენებენ, ამიტომ ლოგიკა ერთხელ წერია. `filter_products(queryset)` ზედიზედ ადებს: **1) ძებნას** (ყოველი სიტყვისთვის `filter(Q(name__icontains=...) | Q(description__icontains=...))`), **2) ფილტრებს** (თითოეული queryset-ს კიდევ უფრო ავიწროვებს) და **3) სორტირებას** (`order_by`). ამიტომ ერთი მეორეს ვერ აუქმებს.
- **სორტირება ორ დეტალზეა აგებული** (`SORT_OPTIONS`, `shop/forms.py`): (1) ბოლო ველი ყოველთვის `pk`-ია, ამიტომ თანაბარი ფასის ან სახელის შემთხვევაში რიგი მაინც ერთნაირია და პაგინაციისას პროდუქტი არ იკარგება და არ მეორდება; (2) სახელებს `Lower("name")`-ით ვადარებთ, ამიტომ `apple` `Zebra`-ს წინ დგას.
- **არასწორი მნიშვნელობა საიტს არ აფუჭებს**: `?min_price=abc`, `?sort=zzz`, `?category=9999` ან `?min_price=1e30` გამოტოვდება, დანარჩენი ფილტრები კი მუშაობს. ფორმის ქვეშ ჩანს ყვითელი შეტყობინება "Some values were ignored".
- **კატეგორიისა და sale-ის გვერდზე** ის ფილტრი, რომელიც გვერდზე უკვე არჩეულია, ფორმაში აღარ ჩანს (`fixed_filters`): კატეგორიის გვერდზე არ არის კატეგორიის არჩევა, sale-ზე კი "On sale only".

### ინტერფეისი (`includes/filter_bar.html`)

1. **ფორმა** (GET): ძებნა, კატეგორია, ფასი "დან/მდე", "On sale only" და ღილაკები "Apply" და "Clear filters". გვერდი ფორმის გაგზავნისას თავიდან (პირველი გვერდიდან) იწყება.
2. **აქტიური ფილტრების ჩიპები** ("Search: “laptop” ✕", "Category: Laptops ✕", ...): ჩიპზე დაჭერა მხოლოდ ამ ფილტრს ხსნის, დანარჩენი და სორტირება რჩება.
3. **სორტირების ღილაკები** ("Price: low to high", "Name: A to Z", "Newest first", ...): ბმულებია, რომლებიც მიმდინარე ძებნასა და ფილტრებს ინახავენ და პირველ გვერდზე აბრუნებენ.
4. ფორმა მიმდინარე სორტირებას დამალული ველით (`<input type="hidden" name="sort">`) გადასცემს, ზედა ზოლის საძიებო ფორმა კი სორტირებასა და ფასის/sale ფილტრებს ინახავს: ახალი ძებნა მათ არ აუქმებს.
5. ბმულებს `ProductFilterMixin.url_with()` აგებს (მიმდინარე `?...`-დან იღებს ან შლის პარამეტრს), ამიტომ შაბლონი ლოგიკის გარეშეა. გვერდების ნავიგაცია (`{% pagination page_obj %}`, HW42) უკვე ინახავდა მთელ `?...`-ს და ახალი პარამეტრებიც ავტომატურად გადადის.
6. ზედა ზოლის საძიებო ველი მხოლოდ დიდ ეკრანზე ჩანს (`d-lg-block`), ხოლო ფილტრის პანელი ყველა ზომაზე მუშაობს, ამიტომ ძებნა ტელეფონზეც შესაძლებელია.

### სცადეთ

- `/?q=laptop`: 3 პროდუქტი, მერე დააჭირეთ "Price: high to low": ძებნა რჩება.
- `/?q=laptop&sale=on`: მხოლოდ ფასდაკლებული ლეპტოპები.
- `/?category=3&min_price=800&max_price=1000&sort=price_desc`: ყურსასმენები 800–1000 ₾ ფასში, ძვირიდან იაფისკენ.
- `/?min_price=abc&q=sony`: `min_price` გამოტოვდება, ძებნა კი მუშაობს (ყვითელი შეტყობინებით).
- `/sale/?category=2&sort=price_desc` და `/category/1/?q=asus`: იგივე პანელი სხვა გვერდებზეც.

## დავალება 44: პაროლის აღდგენა

მომხმარებელს, რომელსაც პაროლი დაავიწყდა, შეუძლია თავისით დააყენოს ახალი: შესვლის გვერდზე ბმული **"Forgot your password?"** → email-ის შეყვანა → წერილი ბმულით → ახალი პაროლი → შესვლა. ახალი მოდელი და მიგრაცია არ გვჭირდება: ვიყენებთ Django-ს ჩაშენებულ `User` მოდელს და მის მზა view-ებს (`django.contrib.auth.views`).

### ოთხი ნაბიჯი

| # | მისამართი (`name=`) | view (`users/views.py`) | რას აკეთებს |
|---|---|---|---|
| 1 | `/users/password-reset/` (`password_reset`) | `UserPasswordResetView` (`PasswordResetView`) | ფორმა: email. სწორი ფორმის შემდეგ Django ქმნის ერთჯერად ბმულს და აგზავნის წერილს |
| 2 | `/users/password-reset/done/` (`password_reset_done`) | `UserPasswordResetDoneView` | "Check your email": წერილი გაგზავნილია |
| 3 | `/users/reset/<uidb64>/<token>/` (`password_reset_confirm`) | `UserPasswordResetConfirmView` | ბმული წერილიდან. სწორი ბმულისას ჩანს ახალი პაროლის ფორმა (პაროლი ორჯერ), არასწორისას "Reset link is invalid" |
| 4 | `/users/reset/done/` (`password_reset_complete`) | `UserPasswordResetCompleteView` | "Your password has been changed" + ღილაკი შესვლის გვერდზე |

URL-ების სახელები Django-ს სტანდარტულია (`password_reset`, `password_reset_done`, `password_reset_confirm`, `password_reset_complete`), ამიტომ წერილის შაბლონში `{% url 'password_reset_confirm' uidb64=uid token=token %}` მათ პირდაპირ პოულობს.

### როგორ გამოვცადოთ

1. `python manage.py runserver`, შემდეგ <http://127.0.0.1:8000/users/register/>-ზე დარეგისტრირდით (**email აუცილებელია**: აღდგენა მისით ხდება) და გამოდით (Logout).
2. გახსენით <http://127.0.0.1:8000/users/login/> და დააჭირეთ **"Forgot your password?"**.
3. ჩაწერეთ იგივე email და დააჭირეთ **"Send reset link"**: გამოვა "Check your email".
4. **წერილი რეალურად არ იგზავნება, ის ტერმინალში იბეჭდება**: იმ ფანჯარაში, სადაც `runserver` გაშვებულია, ჩანს წერილი ბმულით:

   ```
   Subject: Password reset on Mini Shop
   From: Mini Shop <noreply@minishop.local>
   To: tester@example.com
   ...
   http://127.0.0.1:8000/users/reset/MQ/dhjgbs-e911294c61dbbab7a64a9b6c061935a5/
   ```

5. დააკოპირეთ ეს ბმული ბრაუზერის მისამართის ველში: გაიხსნება ახალი პაროლის ფორმა. ჩაწერეთ პაროლი ორჯერ, დააჭირეთ **"Change password"**, შემდეგ **"Login"** და შედით ახალი პაროლით.

### როგორ მუშაობს

- **ფორმები** (`users/forms.py`): `UserPasswordResetForm` (`PasswordResetForm`) და `UserSetPasswordForm` (`SetPasswordForm`). ლოგიკა Django-სია, ჩვენ მხოლოდ Bootstrap-ის სტილს ვამატებთ (როგორც `LoginForm`-ში). `SetPasswordForm` ამოწმებს, რომ ორი პაროლი ერთმანეთს ემთხვევა და პაროლი `AUTH_PASSWORD_VALIDATORS`-ის წესებს აკმაყოფილებს; ინახება დაჰეშილი სახით.
- **შაბლონები** (`users/templates/users/`): `password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html` (საიტის დიზაინით, `shop/base.html`-ს აფართოებენ და იგივე `includes/form_fields.html`-ს იყენებენ) და წერილის ორი ტექსტური ფაილი: `password_reset_subject.txt` (თემა), `password_reset_email.txt` (ტექსტი). შაბლონებს განზრახ `users/...` სახელები აქვთ და არა Django-ს სტანდარტული `registration/...`: admin-საც ასეთი სახელის შაბლონები აქვს და `INSTALLED_APPS`-ში ის წინ დგას, ამიტომ ჩვენი შაბლონები საერთოდ არ გამოჩნდებოდა.
- **წერილი** (`config/settings.py`): `MAILERS` უკვე იყენებს `console` backend-ს, ამიტომ წერილი ტერმინალში იბეჭდება (რეალური SMTP სერვერი არ გვჭირდება). დაემატა `DEFAULT_FROM_EMAIL` ("From" მისამართი) და `PASSWORD_RESET_TIMEOUT` (ბმულის ვადა, 3 დღე). წერილის ყველა ხაზი 78 სიმბოლოზე მოკლეა: გრძელ ხაზებს Django quoted-printable-ით აკოდირებს და ტერმინალში ბმული "="-ებით დაიჭრებოდა. `MAILERS` Django 6.1+ -ის პარამეტრია (პროექტი 6.1-ზეა შექმნილი).
- **შესვლის გვერდი** (`users/templates/users/login.html`): დაემატა ბმული "Forgot your password?".

### უსაფრთხოება

- **ბმული ერთჯერადია**: ტოკენი პაროლის ჰეშისგან და დროისგან გამოითვლება, ამიტომ პაროლის შეცვლისთანავე (ამ ბმულით ან სხვაგვარად) ყველა ძველი ბმული ძალას კარგავს. გამოყენებულ ბმულზე ჩანს "Reset link is invalid" და ღილაკი ახალი ბმულის მოთხოვნისთვის. ბმულს ვადაც აქვს (`PASSWORD_RESET_TIMEOUT`).
- **email-ის არსებობა არ ჩანს**: ცნობილი და უცნობი email-ისას ზუსტად ერთი და იგივე გვერდი იხსნება ("If an account exists..."), უცნობზე წერილი უბრალოდ არ იგზავნება. ამით უცხო ვერ გაიგებს, ვინ არის დარეგისტრირებული.
- **ტოკენი მისამართიდან ქრება**: ბმულზე პირველად გადასვლისას Django ტოკენს სესიაში ინახავს და მისამართს `.../set-password/`-ზე ცვლის, რომ ტოკენი HTTP `Referer`-ით სხვა საიტზე არ გაჟონოს.
- წერილი **არააქტიურ** მომხმარებელს და მომხმარებელს **გამოუსადეგარი პაროლით** არ ეგზავნება. email-ის შედარებისას დიდი/პატარა ასო არ ითვლება (`Tester@Example.com` = `tester@example.com`).
- ყველა ფორმა დაცულია `{% csrf_token %}`-ით; პაროლის ველები დაცულია `sensitive_post_parameters`-ით (პაროლი შეცდომის ლოგებში არ ხვდება).
- პაროლის აღდგენის გვერდებზე ტექნიკური სამუშაოების რეჟიმიც (HW42) მოქმედებს: `MAINTENANCE_MODE = True`-ზე ისინიც იკეტება.

## დავალება 45: REST API (Django REST Framework)

პროექტს დაემატა REST API: კატეგორიებისა და პროდუქტების მონაცემები JSON-ის სახით მიიღება და პროდუქტი API-დანაც შეიძლება შეიქმნას. ახალი მოდელი და მიგრაცია არ გვჭირდება: API იმავე `Category` და `Product` მოდელებზე მუშაობს, რაც საიტს აქვს.

### დავალების პუნქტები და სად არის შესრულებული

| # | პუნქტი | სად |
|---|---|---|
| 1 | პროექტში გამოიყენეთ Django Rest Framework | `requirements.txt` (`djangorestframework`); `config/settings.py`: `"rest_framework"` `INSTALLED_APPS`-ში და `REST_FRAMEWORK` პარამეტრები |
| 2 | დაამატეთ `api` აპლიკაცია | საქაღალდე `api/`; `"api"` `INSTALLED_APPS`-ში; `config/urls.py`-ში `path("api/", include("api.urls"))` |
| 3 | შექმენით კატეგორიებისა და პროდუქტების ლისტინგის API | `GET /api/categories/` და `GET /api/products/` |
| 4 | ასევე შექმენით პროდუქტის დეტალური ინფორმაციის API | `GET /api/products/<id>/` |
| 5 | დაამატეთ პროდუქტის შექმნის API | `POST /api/products/create/` |
| 6 | გამოიყენეთ შესაბამისი სერიალიზატორები | `api/serializers.py`: ყოველ endpoint-ს თავისი სერიალიზატორი აქვს (იხ. ქვემოთ) |

### Endpoint-ები

| მისამართი | მეთოდი | view (`api/views.py`) | სერიალიზატორი | ვის შეუძლია |
|---|---|---|---|---|
| `/api/` | GET | `api_root` | — | ყველას |
| `/api/categories/` | GET | `CategoryListAPIView` (`ListAPIView`) | `CategoryListSerializer` | ყველას |
| `/api/products/` | GET | `ProductListAPIView` (`ListAPIView`) | `ProductListSerializer` | ყველას |
| `/api/products/<id>/` | GET | `ProductDetailAPIView` (`RetrieveAPIView`) | `ProductDetailSerializer` | ყველას |
| `/api/products/create/` | POST | `ProductCreateAPIView` (`CreateAPIView`) | `ProductCreateSerializer` | **მხოლოდ ავტორიზებულს** |

`api/urls.py`-ში მისამართებს `api:` სახელთა სივრცე აქვს (`reverse("api:product-list")`), ამიტომ საიტის სახელებს (`home`, `product_detail`, ...) არ ეჯახება.

### სერიალიზატორები (`api/serializers.py`)

სერიალიზატორი მოდელის ობიექტს JSON-ად აქცევს (პასუხი) და პირიქით: გამოგზავნილ JSON-ს ამოწმებს (მოთხოვნა). ყოველ endpoint-ს მისთვის შესაფერისი სერიალიზატორი აქვს და არა ერთი საერთო:

| სერიალიზატორი | ველები | რატომ ასეა |
|---|---|---|
| `CategorySerializer` | `id`, `name`, `description` | კატეგორიის ძირითადი ველები; პროდუქტის დეტალებში ჩადგმულია |
| `CategoryListSerializer` | იგივე + `product_count` | სიაში ჩანს, რამდენი პროდუქტია კატეგორიაში (ბაზიდან ერთი მოთხოვნით: `annotate(Count)`) |
| `ProductListSerializer` | `id`, `url`, `name`, `price`, `has_discount`, `category` (id), `category_name`, `image` | მოკლე ინფორმაცია: სია მსუბუქია (აღწერა და მფლობელი არ არის); `url` ამ პროდუქტის დეტალურ API-ზე მიდის |
| `ProductDetailSerializer` | `id`, `name`, `description`, `price`, `has_discount`, `image`, `category` (მთლიანი ობიექტი), `owner` | სრული ინფორმაცია: კატეგორია ჩადგმულია (`CategorySerializer`), `owner` მომხმარებლის სახელია |
| `ProductCreateSerializer` | `name`, `description`, `price`, `category` (id), `has_discount`, `image` | მხოლოდ ის ველები, რომლებსაც კლიენტი წერს. `id` და `user` აქ არ არის: მფლობელს view წერს, ამიტომ გამოგზავნილი `"user": 5` იგნორირდება |

### როგორ გამოვცადოთ

**1. ბრაუზერში** (ყველაზე მარტივი). `python manage.py runserver`, შემდეგ:

- <http://127.0.0.1:8000/api/>: ბმულები ყველა endpoint-ზე (DRF-ის ბრაუზერული ინტერფეისი, ბმულებზე დაწკაპუნებით გადადიხართ);
- <http://127.0.0.1:8000/api/categories/>, <http://127.0.0.1:8000/api/products/>, <http://127.0.0.1:8000/api/products/1/>: სია და დეტალები (შესვლა არ სჭირდება);
- **შექმნა**: შედით <http://127.0.0.1:8000/api-auth/login/> გვერდზე (იგივე username/პაროლით, რაც საიტზე გაქვთ; თუ არა გაქვთ, ჯერ დარეგისტრირდით `/users/register/`-ზე), შემდეგ გახსენით <http://127.0.0.1:8000/api/products/create/>. ზედა ნაწილში "Method GET not allowed" ჩვეულებრივია (შექმნა POST-ია), გვერდის ბოლოს კი ფორმაა: შეავსეთ და დააჭირეთ **POST**. წარმატებისას პასუხი `201 Created`-ია.

**2. curl-ით** (Windows 10/11-ში `curl.exe` ჩაშენებულია; PowerShell-ში აუცილებლად `curl.exe` დაწერეთ და არა `curl`). `-F` ფორმატი cmd-შიც და PowerShell-შიც ერთნაირად მუშაობს:

```
curl.exe http://127.0.0.1:8000/api/products/
curl.exe http://127.0.0.1:8000/api/products/1/
curl.exe -u "USERNAME:PASSWORD" -F "name=Lenovo IdeaPad 3" -F "price=899.90" -F "category=1" -F "has_discount=on" http://127.0.0.1:8000/api/products/create/
curl.exe -u "USERNAME:PASSWORD" -F "name=Photo product" -F "price=120" -F "category=4" -F "image=@C:\Users\me\photo.png" http://127.0.0.1:8000/api/products/create/
```

`USERNAME:PASSWORD` საიტის მომხმარებელია. კატეგორიის id-ები `/api/categories/`-იდან იღება (მაგ. Laptops = 1). პროდუქტი JSON-ითაც იქმნება (`Content-Type: application/json`), ოღონდ სურათი მხოლოდ `multipart/form-data`-თი იგზავნება: JSON-ში ფაილი არ ჩადის.

### პასუხების მაგალითები

`GET /api/products/` (`ProductListSerializer`):

```json
[
  {
    "id": 11,
    "url": "http://127.0.0.1:8000/api/products/11/",
    "name": "USB-C Cable 1m",
    "price": "19.90",
    "has_discount": false,
    "category": 4,
    "category_name": "Accessories",
    "image": "http://127.0.0.1:8000/static/shop/img/product-6.png"
  }
]
```

`GET /api/products/1/` (`ProductDetailSerializer`):

```json
{
  "id": 1,
  "name": "ASUS VivoBook 15",
  "description": "15.6\" FHD display, Intel Core i5, 16GB RAM, 512GB SSD.",
  "price": "1299.00",
  "has_discount": false,
  "image": "http://127.0.0.1:8000/static/shop/img/product-11.png",
  "category": {
    "id": 1,
    "name": "Laptops",
    "description": "Laptops for work, study and everyday use."
  },
  "owner": null
}
```

`POST /api/products/create/`: `201 Created`, `Location: http://127.0.0.1:8000/api/products/15/` და პასუხში ახალი პროდუქტის სრული ინფორმაცია (როგორც დეტალურ API-ში, `"owner"` კი ის მომხმარებელია, ვინც მოთხოვნა გამოაგზავნა).

არასწორი მონაცემების დროს (`400 Bad Request`) პასუხი ველების მიხედვით ჩამოთვლის შეცდომებს, პროდუქტი კი არ ინახება:

```json
{
  "name": ["Product name must contain at least 2 characters."],
  "price": ["Price must be greater than zero."],
  "category": ["Invalid pk \"999\" - object does not exist."]
}
```

ანონიმურს `POST`-ზე `403 Forbidden` უბრუნდება: `{"detail": "Authentication credentials were not provided."}`.

### უფლებები და ავტორიზაცია

| მოქმედება | ანონიმური | ავტორიზებული |
|---|---|---|
| სიები და დეტალები (GET) | **200** | **200** |
| პროდუქტის შექმნა (POST `/api/products/create/`) | **403**, არაფერი ინახება | **201** |
| განახლება/წაშლა API-დან | არ არის (დავალებაში არ არის) | `405 Method Not Allowed` |

- წაკითხვა ყველას შეუძლია, შექმნა მხოლოდ ავტორიზებულს: საიტზეც ასეა (HW41). წესი `settings.py`-ში `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = IsAuthenticatedOrReadOnly`-ითაა, შექმნის view-ზე კი დამატებით `permission_classes = [IsAuthenticated]` წერია.
- ავტორიზაცია ორნაირია (`DEFAULT_AUTHENTICATION_CLASSES`): **სესია** (ბრაუზერში `/api-auth/login/`-ით შესული მომხმარებელი; POST-ს CSRF ტოკენი სჭირდება, ბრაუზერული ფორმა მას თვითონ აგზავნის) და **Basic** (`username:password`, მაგ. `curl -u`).
- **მფლობელი**: პროდუქტს ეწერება ის მომხმარებელი, ვინც მოთხოვნა გამოაგზავნა (`serializer.save(user=request.user)`), ე.ი. API-დან შექმნილ პროდუქტს საიტზე ისევე შეუძლია შეცვლა/წაშლა მხოლოდ მფლობელს, როგორც საიტიდან დამატებულს (HW41).

### როგორ მუშაობს

- **generic view-ები**: `ListAPIView`, `RetrieveAPIView`, `CreateAPIView` queryset-ს იღებს, `serializer_class`-ით JSON-ად აქცევს და 404/400-ს თვითონ აბრუნებს. ჩვენ მხოლოდ ვწერთ, რომელი მონაცემი და რომელი სერიალიზატორი.
- **ბაზის მოთხოვნები**: სია და დეტალები ბაზაში **ერთ მოთხოვნას** ასრულებს (`select_related("category")`, კატეგორიებში `annotate(Count)`), ამიტომ პროდუქტების რაოდენობა მოთხოვნებს არ ზრდის. ტესტები ამას `assertNumQueries(1)`-ით ამოწმებს.
- **კატეგორიების სია** აბრუნებს **ყველა** კატეგორიას, ცარიელებსაც (საიტის მენიუში ცარიელი არ ჩანს): პროდუქტის შესაქმნელად კატეგორიის id აუცილებელია, ამიტომ კლიენტს ყველა უნდა ხედავდეს. სორტირება `order_by("name")`-ით ცალსახადაა მითითებული: `annotate`-ის შემდეგ `Meta.ordering` აღარ მოქმედებს.
- **პროდუქტების სია** ფასის ზრდადობითაა (ისევე, როგორც საიტის მთავარ გვერდზე); თანაბარი ფასის დროს `pk` ამყარებს რიგს.
- **შექმნის წესები საიტის ფორმის იგივეა** (`shop.forms.ProductForm`): სახელი მინიმუმ 2 სიმბოლო (ზედმეტი გამოტოვებები იჭრება), ფასი ნულზე მეტი და `Product.price`-ის ფარგლებში (10 ციფრი, 2 ათწილადი), კატეგორია უნდა არსებობდეს, სურათი ნამდვილი სურათი უნდა იყოს (Pillow), ფორმატი JPG/PNG/GIF/WEBP და მაქსიმუმ 5 MB. სურათის ლიმიტებს `shop.forms`-იდან ვკითხულობთ (`MAX_IMAGE_SIZE`, `ALLOWED_IMAGE_TYPES`), ერთ ადგილას წერია და სხვაგან არ მეორდება.
- **პასუხი შექმნის შემდეგ**: `CreateAPIView`-ის სტანდარტული ქცევა მხოლოდ გამოგზავნილ ველებს დააბრუნებდა; ჩვენ `create()`-ში პასუხს `ProductDetailSerializer`-ით ვაგებთ, ამიტომ კლიენტი ახალ `id`-ს, ჩადგმულ კატეგორიას და `owner`-ს მაშინვე იღებს. `Location` თავსართში ახალი პროდუქტის მისამართია.
- **ფასი სტრიქონია** (`"price": "899.90"`): DRF-ის სტანდარტია `DecimalField`-ისთვის, რომ ფულის სიზუსტე JSON-ის რიცხვებში არ დაიკარგოს.
- **სურათი** ყოველთვის სრული მისამართია (`http://127.0.0.1:8000/media/products/...`). თუ პროდუქტს სურათი არ აქვს ატვირთული (მაგ. 14 საწყისი პროდუქტი), იგივე მზა სურათი ბრუნდება, რასაც საიტი აჩვენებს (`Product.image_url`).
- **მფლობელი**: 14 საწყის პროდუქტს მფლობელი არ ჰყავს (HW41-მდე დაემატა), ამიტომ მათთვის `"owner": null`.
- **ტექნიკური სამუშაოები** (HW42): `MAINTENANCE_MODE = True`-ზე `/api/...` იკეტება ისევე, როგორც საიტის ყველა გვერდი (`/admin/`-ის გარდა).

### ახალი და შეცვლილი ფაილები

```
api/                       ახალი აპლიკაცია (მოდელი და მიგრაცია არ აქვს)
    apps.py
    serializers.py         CategorySerializer, CategoryListSerializer, ProductListSerializer,
                           ProductDetailSerializer, ProductCreateSerializer
    views.py               api_root, CategoryListAPIView, ProductListAPIView,
                           ProductDetailAPIView, ProductCreateAPIView
    urls.py                /api/... მისამართები (app_name = "api")
    tests.py               84 ტესტი
config/settings.py         "rest_framework" და "api" INSTALLED_APPS-ში, REST_FRAMEWORK პარამეტრები
config/urls.py             path("api/", ...) და path("api-auth/", ...)
requirements.txt           + djangorestframework
```

## პროდუქტის დამატება, განახლება, წაშლა

- **დამატება**: `ProductCreateView` (`CreateView`) + `ProductForm` (`shop/forms.py`). ფორმა ამოწმებს მონაცემებს: სახელი მინიმუმ 2 სიმბოლო, კატეგორია აუცილებელია, ფასი ნულზე მეტი, სურათი (თუ არის) ნამდვილი სურათი უნდა იყოს. შენახვის შემდეგ ხსნის ახალი პროდუქტის გვერდს (`get_absolute_url`) და აჩვენებს შეტყობინებას.
- **განახლება**: `product_update` view იგივე ფორმით, ოღონდ `instance=product`, ამიტომ ფორმა არსებული მონაცემებით ივსება და ახალი ჩანაწერი არ იქმნება.
- **წაშლა**: `product_delete` view. `GET` მხოლოდ დადასტურების გვერდს აჩვენებს, პროდუქტი იშლება მხოლოდ `POST`-ზე (ღილაკი "Yes, delete"). ასე ბმულზე შემთხვევით გადასვლა არაფერს წაშლის.
- ყველა ფორმა დაცულია `{% csrf_token %}`-ით.
- ღილაკები ჩანს: ზედა მენიუში ("Add Product"), პროდუქტის ბარათზე მაუსის მიტანისას (Edit / Delete, მხოლოდ მფლობელისთვის) და პროდუქტის გვერდზე (Edit / Delete, მხოლოდ მფლობელისთვის).

## შაბლონების სტრუქტურა

Electro-ს 5 HTML ფაილი ლოგიკურ ნაწილებად დავჭერი (`shop/templates/shop/`):

```
base.html                    საერთო ჩარჩო: <head>, ზედა ზოლი, მენიუ, footer, სკრიპტები
maintenance.html             "Site is under maintenance" გვერდი (დამოუკიდებელია, base.html-ს არ აფართოებს)
shop_layout.html             ორი სვეტის განლაგება (shop.html-იდან): გვერდითი პანელი + ბადე
includes/
    topbar.html              ლოგო, ძიების ფორმა, ხატულები
    navbar.html              "All Categories" + მენიუ + "Add Product" ღილაკი
    messages.html            შეტყობინებები ("Product ... was added")
    category_list.html       კატეგორიების სია რაოდენობებით
    services.html            სერვისების ზოლი
    sidebar.html             გვერდითი პანელი (კატეგორიები, ფასდაკლებული პროდუქტები)
    product_card.html        ერთი პროდუქტის ბარათი
    pagination.html          გვერდების ნავიგაცია (იძახება {% pagination page_obj %} ტეგით)
    footer.html              footer + copyright
    filter_bar.html          ძებნის, ფილტრებისა და სორტირების პანელი (HW43; მთავარი, კატეგორია, sale)
home.html                    მთავარი (index.html-იდან)
category_detail.html         კატეგორიის გვერდი  (აფართოებს shop_layout.html-ს)
sale.html                    ფასდაკლება          (აფართოებს shop_layout.html-ს)
product_detail.html          პროდუქტის გვერდი
product_form.html            დამატება და რედაქტირება (ერთი შაბლონი ორივესთვის, სურათის ველით)
product_confirm_delete.html  წაშლის დადასტურება
cart.html, checkout.html, contact.html   შაბლონის დანარჩენი გვერდები
```

`users/templates/users/`: `login.html`, `register.html`, `includes/form_fields.html` (ყველა ფორმის საერთო ველები), HW44: `password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, `password_reset_subject.txt`, `password_reset_email.txt`. `shop/templates/403.html` — "არ გაქვთ უფლება" გვერდი.

სტატიკური ფაილები (`shop/static/shop/`): `css/` (Electro + `custom.css`), `js/`, `lib/`, `img/`.

კატეგორიების სია და ფასდაკლებული პროდუქტები თითქმის ყველა გვერდზე გვჭირდება (მენიუ, გვერდითი პანელი, footer), ამიტომ ისინი ყოველ view-ში ცალკე არ გადაეცემა. მათ ყველა შაბლონს აძლევს `shop/context_processors.py` (დარეგისტრირებულია `config/settings.py`-ში).

## რა უნდა იცოდეთ

- თუ პროდუქტს თავისი სურათი არ აქვს ატვირთული (მაგ. ძველი 14 პროდუქტი), ბარათებზე შაბლონის მზა სურათები ჩანს. სურათი კატეგორიისა და პროდუქტის id-ის მიხედვით ირჩევა (`Product.placeholder_image`, `shop/models.py`).
- ძველი 14 პროდუქტი HW41-მდე დაემატა, ამიტომ მფლობელი არ ჰყავთ და საიტიდან არავის შეუძლია მათი შეცვლა/წაშლა (admin-იდან შეიძლება). ახალ პროდუქტს მფლობელი ავტომატურად ეწერება.
- ბაზაში მომხმარებლები წინასწარ არ არის: გამოსაცდელად `/users/register/`-ზე დარეგისტრირდით (თუ უფლებების შესამოწმებლად ორი მომხმარებელი გჭირდებათ, გასვლის შემდეგ მეორეც შექმენით).
- `cart`, `checkout` და `contact` გვერდები შაბლონიდან გადმოტანილი დემო გვერდებია: მათში მონაცემები სტატიკურია და ლოგიკა დავალების ნაწილი არ არის.
- ძებნა, ფილტრები და სორტირება (HW43) მუშაობს მთავარ, კატეგორიის და sale გვერდზე; ძველი ბმულები (`/?q=sony&category=3`) ისევ მუშაობს.

## ტესტები

```
python manage.py test
```

368 ტესტი (`shop/tests.py`, `users/tests.py` და `api/tests.py`). ტესტების გაშვებამდე `MAINTENANCE_MODE` უნდა იყოს `False` (ტესტები ამას ამოწმებს):

- HW36–HW39: მთავარი გვერდი, კატეგორიები, ფასდაკლება, ძიება, დამატება (სწორი და არასწორი მონაცემებით), განახლება, წაშლა (დადასტურება, POST, 404, CSRF), view-ები მართლა Class-Based-ია (update და delete კი function-based). ეს ტესტები ახლა შესული მფლობელის სახელით სრულდება.
- HW41, `users`: რეგისტრაცია (დაჰეშილი პაროლი, ავტომატური შესვლა, სუსტი/განსხვავებული პაროლი, განმეორებადი username/email), შესვლა (სწორი/არასწორი მონაცემები, `?next=`, უსაფრთხო გადამისამართება), გასვლა (მხოლოდ POST), მენიუ ანონიმურისა და შესულისთვის.
- HW41, `shop`: მფლობელის ველი და ჩაწერა (ფორმიდან მოსული `user` იგნორირდება), დამატება მხოლოდ შესულისთვის, განახლება/წაშლა მხოლოდ მფლობელისთვის (ანონიმური, სხვა მომხმარებელი, უმფლობელო პროდუქტი), Edit/Delete ღილაკების ხილვადობა, სურათი (ატვირთვა, ჩვენება, შეცვლა, "Clear", არასწორი ფაილი/ფორმატი/ზომა, ფაილების წაშლა დისკიდან).
- ერთი სრული სცენარი: ორი მომხმარებელი რეგისტრირდება და ერთმანეთის პროდუქტს ვერ ეხება.
- HW42, პაგინაცია: გვერდების ზომა (8/6/6), ბოლო გვერდზე დარჩენილი პროდუქტები, ფასის რიგი გვერდებს შორის, გამეორებების გარეშე, სათაურში ჯამური რაოდენობა, ნავიგაციის ბმულები და აქტიური გვერდი, ძიების პარამეტრების შენახვა ბმულებში, არასწორი გვერდი = 404, ერთგვერდიან სიაზე ნავიგაცია არ ჩანს, ბევრი გვერდის შემოკლება "…"-ით.
- HW42, maintenance: ჩართვა/გამორთვა, ყველა გვერდი და POST იკეტება (503 + ტექსტი), ავტორიზებულიც კი, `/admin/` (ანონიმურისთვის და ადმინისტრატორისთვის) მუშაობს, `/admin` და `/administrator/` სწორად მუშაობს, ბაზის მოთხოვნები 0-ია, პარამეტრის არარსებობა, middleware-ის რიგი `MIDDLEWARE`-ში.
- HW42, signal: განახლებაზე ზუსტი ტექსტი (ქართული სახელითაც), დამატებაზე და წაშლაზე არაფერი, Edit ფორმა ბეჭდავს ზუსტად ერთხელ, არასწორ ფორმაზე არაფერი.
- HW43, ძებნა/ფილტრაცია/სორტირება (70 ტესტი): ძებნა სახელში და აღწერაში, სიტყვების რიგი, ზედმეტი გამოტოვებები, XSS-ისგან დაცვა; კატეგორია, ფასი (ზღვრები ჩართულია, ათწილადები, `min > max`, არასწორი და ძალიან დიდი მნიშვნელობები), sale; ყველა სორტირება (დიდი/პატარა ასო, თანაბარი ფასის სტაბილური რიგი, უცნობი `sort`); **ყველაფერი ერთად** სამივე გვერდზე; არასწორი მნიშვნელობა სხვა ფილტრებს არ აუქმებს; ბმულები (სორტირება, ჩიპები, "Clear filters") ინახავს დანარჩენ პარამეტრებს და `page`-ს შლის; პაგინაციისას ფილტრები და სორტირება არ იკარგება და პროდუქტი არ მეორდება; ზედა ზოლის ძებნა სორტირებას ინახავს.
- HW44, პაროლის აღდგენა (39 ტესტი, `users/tests.py`): ოთხივე გვერდი ანონიმურისთვის იხსნება და ჩვენს შაბლონებს იყენებს, ბმული "Forgot your password?" შესვლის გვერდზე; წერილი (მიმღები, თემა, "From", მომხმარებლის სახელი, მოკლე ხაზები, ბმული მუშაობს); email-ის ძებნა დიდი/პატარა ასოს გარეშე; უცნობი email არაფერს აგზავნის და ცნობილისგან გვერდით ვერ გაირჩევა; არასწორი ფორმატი, არააქტიური მომხმარებელი, გამოუსადეგარი პაროლი; ბმული: ტოკენი მისამართიდან ქრება, ახალი პაროლი ინახება დაჰეშილი, ძველი პაროლი აღარ მუშაობს, ავტომატური შესვლა არ ხდება; ბმული მხოლოდ ერთხელ მუშაობს, გაყალბებული/ვადაგასული/პაროლის შეცვლის შემდეგ ძველი ბმული არასწორია; სუსტი, განსხვავებული და ცარიელი პაროლი; CSRF; სხვა მომხმარებელი არ ზიანდება; ტექნიკური სამუშაოები (503); ერთი სრული სცენარი: რეგისტრაცია → წერილი → ახალი პაროლი → შესვლა.
- HW45, REST API (84 ტესტი, `api/tests.py`): ოთხივე endpoint-ის მისამართები და view-ები; კატეგორიების სია (ცარიელებიც, სახელის რიგი, `product_count`); პროდუქტების სია (ფასის რიგი, მოკლე ველები, სრული `url` და სურათის მისამართი, მზა სურათი და ატვირთული სურათი); დეტალები (ჩადგმული კატეგორია, `owner`, უმფლობელო პროდუქტი, 404); სია და დეტალები ბაზაში ზუსტად 1 მოთხოვნით; შექმნა: ანონიმური 403, მფლობელი = ავტორიზებული მომხმარებელი, გამოგზავნილი `user` და `id` იგნორირდება, JSON და form-data, `201` + `Location` + სრული პასუხი, ახალი პროდუქტი სიაშიც და საიტზეც ჩანს; 14 არასწორი შემთხვევა (სახელი, ფასი, კატეგორია) = `400` ზუსტი ველით და არაფერი ინახება, შეცდომის ტექსტები საიტის ფორმის იგივეა; სურათი (ატვირთვა, 4 ფორმატი, ყალბი ფაილი, BMP, ზომა, JSON-ში ფაილი); Basic და სესიით ავტორიზაცია, არასწორი პაროლი, CSRF; სწორი სერიალიზატორი თითოეულ view-ზე; ბრაუზერული API იხსნება; ტექნიკური სამუშაოების რეჟიმი.

ტესტების დროს signal-ის ტექსტი (`Product "..." was updated.`) დამალულია (`SilentStdoutMixin`), რომ ტესტების წერტილებს არ ერეოდეს.

ატვირთული ფაილები ტესტებში დროებით საქაღალდეში ინახება, ამიტომ პროექტის `media/` საქაღალდე არ ივსება.

შაბლონი: [Electro](https://htmlcodex.com/electronics-website-template) (HTML Codex), ლიცენზია: `shop/static/shop/TEMPLATE_LICENSE.txt`.
