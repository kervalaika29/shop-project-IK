# Mini Shop — Django Homework 39

Django პროექტი პროდუქტებითა და კატეგორიებით (ბაზა: **sqlite3**).

- დავალება 37: პროდუქტის **დამატების, განახლების და წაშლის** ლოგიკა + **Electro HTML შაბლონების** მორგება პროექტზე.
- **დავალება 39: აქამდე არსებული ყველა view გადაკეთებულია Class-Based-View-ებად (update-ისა და delete-ის გარდა).**

## გაშვება (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

შემდეგ ბრაუზერში გახსენით <http://127.0.0.1:8000/>.

ბაზა (`db.sqlite3`) უკვე შევსებულია: 5 კატეგორია, 14 პროდუქტი.
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
| `/` | მთავარი: ყველა პროდუქტი ფასის ზრდადობით + კატეგორიების სია (რაოდენობა ფრჩხილებში). ძიება: `/?q=sony&category=3` |
| `/category/<id>/` | კონკრეტული კატეგორიის პროდუქტები |
| `/sale/` | ფასდაკლებული პროდუქტები |
| `/product/<id>/` | პროდუქტის დეტალური გვერდი |
| `/product/add/` | **პროდუქტის დამატება** (`ProductCreateView`) |
| `/product/<id>/edit/` | **პროდუქტის განახლება** |
| `/product/<id>/delete/` | **პროდუქტის წაშლა** (ჯერ დადასტურების გვერდი) |
| `/cart/`, `/checkout/`, `/contact/` | Electro შაბლონის დანარჩენი გვერდები (დემო, ლოგიკის გარეშე) |

## Class-Based Views (HW39)

`shop/views.py`-ში ყველა view კლასია, გარდა `product_update`-ისა და `product_delete`-ისა (დავალების პირობით ისინი ჩვეულებრივი function-based view-ები რჩება). `shop/urls.py`-ში კლასები `.as_view()`-ით ერთვება. URL-ების სახელები (`name=...`) არ შეცვლილა, ამიტომ შაბლონებს არაფერი შეცვლია.

| ძველი view (ფუნქცია) | ახალი view (კლასი) | საბაზო კლასი | რას აკეთებს |
|---|---|---|---|
| `home` | `HomeView` | `ListView` | პროდუქტების სია ფასის ზრდადობით; `get_queryset`-ში ძიება (`?q=`, `?category=`), `get_context_data`-ში სარეკლამო ბლოკები |
| `category_detail` | `CategoryDetailView` | `DetailView` | კატეგორია (`product_count`-ით) + მისი პროდუქტები |
| `sale` | `SaleView` | `ListView` | მხოლოდ ფასდაკლებული პროდუქტები |
| `product_detail` | `ProductDetailView` | `DetailView` | პროდუქტი + იმავე კატეგორიის სხვა პროდუქტები (`related_products`) |
| `product_create` | `ProductCreateView` | `CreateView` | დამატების ფორმა (`ProductForm`), შენახვის შემდეგ გადადის პროდუქტის გვერდზე + შეტყობინება `form_valid`-ში |
| `cart` | `CartView` | `TemplateView` | დემო გვერდი |
| `checkout` | `CheckoutView` | `TemplateView` | დემო გვერდი |
| `contact` | `ContactView` | `TemplateView` | დემო გვერდი |
| `product_update` | *უცვლელია (function-based)* | — | განახლება |
| `product_delete` | *უცვლელია (function-based)* | — | წაშლა |

## პროდუქტის დამატება, განახლება, წაშლა

- **დამატება**: `ProductCreateView` (`CreateView`) + `ProductForm` (`shop/forms.py`). ფორმა ამოწმებს მონაცემებს: სახელი მინიმუმ 2 სიმბოლო, კატეგორია აუცილებელია, ფასი ნულზე მეტი. შენახვის შემდეგ ხსნის ახალი პროდუქტის გვერდს (`get_absolute_url`) და აჩვენებს შეტყობინებას.
- **განახლება**: `product_update` view იგივე ფორმით, ოღონდ `instance=product`, ამიტომ ფორმა არსებული მონაცემებით ივსება და ახალი ჩანაწერი არ იქმნება.
- **წაშლა**: `product_delete` view. `GET` მხოლოდ დადასტურების გვერდს აჩვენებს, პროდუქტი იშლება მხოლოდ `POST`-ზე (ღილაკი "Yes, delete"). ასე ბმულზე შემთხვევით გადასვლა არაფერს წაშლის.
- ყველა ფორმა დაცულია `{% csrf_token %}`-ით.
- ღილაკები ჩანს: ზედა მენიუში ("Add Product"), პროდუქტის ბარათზე მაუსის მიტანისას (Edit / Delete) და პროდუქტის გვერდზე.

## შაბლონების სტრუქტურა

Electro-ს 5 HTML ფაილი ლოგიკურ ნაწილებად დავჭერი (`shop/templates/shop/`):

```
base.html                    საერთო ჩარჩო: <head>, ზედა ზოლი, მენიუ, footer, სკრიპტები
shop_layout.html             ორი სვეტის განლაგება (shop.html-იდან): გვერდითი პანელი + ბადე
includes/
    topbar.html              ლოგო, ძიების ფორმა, ხატულები
    navbar.html              "All Categories" + მენიუ + "Add Product" ღილაკი
    messages.html            შეტყობინებები ("Product ... was added")
    category_list.html       კატეგორიების სია რაოდენობებით
    services.html            სერვისების ზოლი
    sidebar.html             გვერდითი პანელი (კატეგორიები, ფასდაკლებული პროდუქტები)
    product_card.html        ერთი პროდუქტის ბარათი
    footer.html              footer + copyright
home.html                    მთავარი (index.html-იდან)
category_detail.html         კატეგორიის გვერდი  (აფართოებს shop_layout.html-ს)
sale.html                    ფასდაკლება          (აფართოებს shop_layout.html-ს)
product_detail.html          პროდუქტის გვერდი
product_form.html            დამატება და რედაქტირება (ერთი შაბლონი ორივესთვის)
product_confirm_delete.html  წაშლის დადასტურება
cart.html, checkout.html, contact.html   შაბლონის დანარჩენი გვერდები
```

სტატიკური ფაილები (`shop/static/shop/`): `css/` (Electro + `custom.css`), `js/`, `lib/`, `img/`.

კატეგორიების სია და ფასდაკლებული პროდუქტები თითქმის ყველა გვერდზე გვჭირდება (მენიუ, გვერდითი პანელი, footer), ამიტომ ისინი ყოველ view-ში ცალკე არ გადაეცემა. მათ ყველა შაბლონს აძლევს `shop/context_processors.py` (დარეგისტრირებულია `config/settings.py`-ში).

## რა უნდა იცოდეთ

- პროდუქტს სურათის ველი არ აქვს (დავალებაში არ მოითხოვებოდა), ამიტომ ბარათებზე შაბლონის მზა სურათები ჩანს. სურათი კატეგორიისა და პროდუქტის id-ის მიხედვით ირჩევა (`Product.placeholder_image`, `shop/models.py`).
- `cart`, `checkout` და `contact` გვერდები შაბლონიდან გადმოტანილი დემო გვერდებია: მათში მონაცემები სტატიკურია და ლოგიკა დავალების ნაწილი არ არის.
- ჩაშენებული ძიება (`?q=`, `?category=`) მთავარ გვერდზე მუშაობს: პროდუქტის სახელით და/ან კატეგორიით.

## ტესტები

```
python manage.py test shop
```

54 ტესტი ფარავს მთავარ გვერდს, კატეგორიებს, ფასდაკლებას, ძიებას, დამატებას (სწორი და არასწორი მონაცემებით), განახლებას, წაშლას (დადასტურება, POST, 404, CSRF). HW39-ის ტესტები ამოწმებს, რომ view-ები მართლა Class-Based-ია (`ListView`, `DetailView`, `CreateView`, `TemplateView`), update და delete კი ისევ function-based.

შაბლონი: [Electro](https://htmlcodex.com/electronics-website-template) (HTML Codex), ლიცენზია: `shop/static/shop/TEMPLATE_LICENSE.txt`.
