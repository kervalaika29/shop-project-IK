import contextlib
import io
import os
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Paginator
from django.db.models.signals import post_save
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from PIL import Image

from .middleware import MaintenanceModeMiddleware
from .models import CATEGORY_IMAGES, DEFAULT_IMAGES, Category, Product
from .templatetags.shop_tags import pagination
from .views import CategoryDetailView, HomeView, SaleView

User = get_user_model()


class SilentStdoutMixin:
    """
    HW42-ის სიგნალი პროდუქტის ყოველ განახლებაზე ტერმინალში წერს: Product "..." was updated.
    ტესტებში ეს ტექსტი ტესტების წერტილებს ერეოდა, ამიტომ კლასის ტესტების დროს stdout
    დუმდება. სიგნალის ტესტები თავიანთ ტექსტს ცალკე იჭერენ (redirect_stdout).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        redirect = contextlib.redirect_stdout(io.StringIO())
        redirect.__enter__()
        cls.addClassCleanup(redirect.__exit__, None, None, None)


class ShopTestCase(SilentStdoutMixin, TestCase):
    """
    საერთო საწყისი მონაცემები ყველა ტესტისთვის: ორი მომხმარებელი (owner და other)
    და სამი პროდუქტი, რომელიც owner-ს ეკუთვნის.
    """

    @classmethod
    def setUpTestData(cls):
        # პაროლის გარეშე (ჰეშირება ნელია): ტესტებში force_login გამოიყენება
        cls.owner = User.objects.create(username="owner", email="owner@example.com")
        cls.other = User.objects.create(username="other", email="other@example.com")

        cls.laptops = Category.objects.create(name="Laptops")
        cls.phones = Category.objects.create(name="Phones")
        cls.empty = Category.objects.create(name="Empty category")

        cls.cheap = Product.objects.create(
            name="Cheap laptop", price="500.00", category=cls.laptops,
            has_discount=True, user=cls.owner,
        )
        cls.mid = Product.objects.create(
            name="Mid phone", price="800.00", category=cls.phones, user=cls.owner
        )
        cls.expensive = Product.objects.create(
            name="Expensive laptop", price="2500.00", category=cls.laptops, user=cls.owner
        )


def make_image(name="photo.png", image_format="PNG", size=(30, 20)):
    """ტესტისთვის ნამდვილ (Pillow-ით შექმნილ) სურათს აბრუნებს ატვირთვისთვის."""
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, format=image_format)
    content_type = Image.MIME[image_format]
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class TempMediaMixin:
    """ატვირთული ფაილები დროებით საქაღალდეში ინახება და ტესტების შემდეგ იშლება."""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="shop-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    def setUp(self):
        super().setUp()
        # ბაზას TestCase ყოველი ტესტის შემდეგ აბრუნებს, ფაილებს კი არა: ხელით ვასუფთავებთ
        for entry in os.listdir(self._media_root):
            shutil.rmtree(os.path.join(self._media_root, entry), ignore_errors=True)

    def media_files(self):
        """ყველა ფაილი media საქაღალდეში (გზები MEDIA_ROOT-ის მიმართ)."""
        found = []
        for folder, _, files in os.walk(self._media_root):
            for file in files:
                found.append(os.path.relpath(os.path.join(folder, file), self._media_root))
        return sorted(found)


class ShopViewsTests(ShopTestCase):
    """HW36-ის ფუნქციონალი ახალ (Electro) შაბლონებზეც უნდა მუშაობდეს."""

    def test_model_defaults(self):
        mid = Product.objects.get(pk=self.mid.pk)
        self.assertFalse(mid.has_discount)
        self.assertEqual(mid.category, self.phones)
        self.assertEqual(mid.price, Decimal("800.00"))

    def test_home_products_sorted_by_price_ascending(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        prices = [p.price for p in response.context["products"]]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(len(prices), 3)

    def test_home_shows_sale_badge_only_for_discounted_products(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="product-sale"', count=1)

    def test_categories_list_has_only_non_empty_categories(self):
        response = self.client.get(reverse("home"))
        names = [c.name for c in response.context["categories"]]
        self.assertEqual(names, ["Laptops", "Phones"])
        self.assertNotContains(response, "Empty category")

    def test_categories_show_product_count_in_brackets(self):
        response = self.client.get(reverse("home"))
        counts = {c.name: c.product_count for c in response.context["categories"]}
        self.assertEqual(counts, {"Laptops": 2, "Phones": 1})
        self.assertContains(response, "(2)")
        self.assertContains(response, "(1)")

    def test_category_page_lists_only_its_products(self):
        response = self.client.get(reverse("category_detail", args=[self.laptops.pk]))
        self.assertEqual(response.status_code, 200)
        products = list(response.context["products"])
        self.assertEqual(products, [self.cheap, self.expensive])
        self.assertNotContains(response, "Mid phone")

    def test_category_link_leads_to_category_page(self):
        response = self.client.get(reverse("home"))
        self.assertContains(
            response, reverse("category_detail", args=[self.laptops.pk])
        )

    def test_sale_page_has_only_discounted_products(self):
        response = self.client.get(reverse("sale"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [self.cheap])

    def test_product_detail_page(self):
        response = self.client.get(reverse("product_detail", args=[self.cheap.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cheap laptop")
        self.assertContains(response, "SALE")

    def test_product_detail_shows_other_products_of_same_category(self):
        response = self.client.get(reverse("product_detail", args=[self.cheap.pk]))
        self.assertEqual(list(response.context["related_products"]), [self.expensive])

    def test_product_detail_without_discount_has_no_sale_badge(self):
        response = self.client.get(reverse("product_detail", args=[self.mid.pk]))
        self.assertNotContains(response, "SALE")

    def test_missing_product_and_category_return_404(self):
        self.assertEqual(self.client.get(reverse("product_detail", args=[9999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("category_detail", args=[9999])).status_code, 404)

    def test_template_pages_open(self):
        for name in ("cart", "checkout", "contact"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_cards_have_edit_and_delete_links_for_the_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("product_update", args=[self.mid.pk]))
        self.assertContains(response, reverse("product_delete", args=[self.mid.pk]))


class ProductSearchTests(ShopTestCase):
    def test_search_by_name_is_case_insensitive(self):
        response = self.client.get(reverse("home"), {"q": "LAPTOP"})
        self.assertEqual(
            list(response.context["products"]), [self.cheap, self.expensive]
        )
        self.assertContains(response, "Search Results")

    def test_search_by_category(self):
        response = self.client.get(reverse("home"), {"category": self.phones.pk})
        self.assertEqual(list(response.context["products"]), [self.mid])

    def test_search_by_name_and_category(self):
        response = self.client.get(
            reverse("home"), {"q": "laptop", "category": self.phones.pk}
        )
        self.assertEqual(list(response.context["products"]), [])
        self.assertContains(response, "No products match your search.")

    def test_garbage_category_value_is_ignored(self):
        response = self.client.get(reverse("home"), {"category": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 3)


class ProductCreateTests(ShopTestCase):
    url = "/product/add/"

    def setUp(self):
        # პროდუქტის დამატება მხოლოდ შესულ მომხმარებელს შეუძლია
        self.client.force_login(self.owner)

    def valid_data(self, **extra):
        data = {
            "name": "New tablet",
            "category": self.phones.pk,
            "price": "999.90",
            "description": "10 inch tablet",
            "has_discount": "on",
        }
        data.update(extra)
        return data

    def test_url_name(self):
        self.assertEqual(reverse("product_create"), self.url)

    def test_get_shows_empty_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_bound)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_category_select_contains_all_categories_even_empty_ones(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Empty category")

    def test_valid_post_creates_product_and_redirects_to_its_page(self):
        response = self.client.post(self.url, self.valid_data())
        product = Product.objects.get(name="New tablet")
        self.assertRedirects(response, reverse("product_detail", args=[product.pk]))
        self.assertEqual(product.price, Decimal("999.90"))
        self.assertEqual(product.category, self.phones)
        self.assertTrue(product.has_discount)
        self.assertEqual(Product.objects.count(), 4)

    def test_checkbox_is_optional(self):
        data = self.valid_data()
        del data["has_discount"]
        self.client.post(self.url, data)
        self.assertFalse(Product.objects.get(name="New tablet").has_discount)

    def test_description_is_optional(self):
        self.client.post(self.url, self.valid_data(description=""))
        self.assertEqual(Product.objects.get(name="New tablet").description, "")

    def test_success_message_is_shown_after_redirect(self):
        response = self.client.post(self.url, self.valid_data(), follow=True)
        self.assertContains(response, "was added")
        self.assertContains(response, "New tablet")

    def test_new_product_appears_on_home_and_in_category_count(self):
        self.client.post(self.url, self.valid_data())
        response = self.client.get(reverse("home"))
        self.assertContains(response, "New tablet")
        counts = {c.name: c.product_count for c in response.context["categories"]}
        self.assertEqual(counts["Phones"], 2)

    def test_adding_first_product_to_empty_category_shows_the_category(self):
        self.client.post(self.url, self.valid_data(category=self.empty.pk))
        response = self.client.get(reverse("home"))
        names = [c.name for c in response.context["categories"]]
        self.assertIn("Empty category", names)

    def test_name_is_stripped(self):
        self.client.post(self.url, self.valid_data(name="   Spaced name   "))
        self.assertTrue(Product.objects.filter(name="Spaced name").exists())

    def test_invalid_data_is_not_saved_and_form_shows_errors(self):
        bad_cases = {
            "empty name": {"name": ""},
            "one letter name": {"name": "A"},
            "spaces only": {"name": "   "},
            "no category": {"category": ""},
            "unknown category": {"category": 9999},
            "empty price": {"price": ""},
            "zero price": {"price": "0"},
            "negative price": {"price": "-5"},
            "text price": {"price": "abc"},
            "too many digits": {"price": "12345678901"},
        }
        for label, change in bad_cases.items():
            with self.subTest(case=label):
                response = self.client.post(self.url, self.valid_data(**change))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(Product.objects.count(), 3)

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.force_login(self.owner)
        response = strict_client.post(self.url, self.valid_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 3)


class ProductUpdateTests(ShopTestCase):
    def setUp(self):
        # განახლება მხოლოდ მფლობელს შეუძლია (ყველა პროდუქტი owner-ს ეკუთვნის)
        self.client.force_login(self.owner)

    def url(self, product):
        return reverse("product_update", args=[product.pk])

    def test_url_pattern(self):
        self.assertEqual(self.url(self.mid), f"/product/{self.mid.pk}/edit/")

    def test_get_shows_form_filled_with_current_data(self):
        response = self.client.get(self.url(self.mid))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.instance, self.mid)
        self.assertEqual(form["name"].value(), "Mid phone")
        self.assertEqual(form["category"].value(), self.phones.pk)
        self.assertContains(response, 'value="Mid phone"')

    def test_valid_post_updates_same_record(self):
        response = self.client.post(
            self.url(self.mid),
            {
                "name": "Mid phone PRO",
                "category": self.laptops.pk,
                "price": "850.50",
                "description": "updated",
                "has_discount": "on",
            },
        )
        self.assertRedirects(response, reverse("product_detail", args=[self.mid.pk]))
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.name, "Mid phone PRO")
        self.assertEqual(self.mid.category, self.laptops)
        self.assertEqual(self.mid.price, Decimal("850.50"))
        self.assertTrue(self.mid.has_discount)
        # ახალი ჩანაწერი არ შექმნილა
        self.assertEqual(Product.objects.count(), 3)

    def test_unchecking_discount_removes_product_from_sale_page(self):
        self.client.post(
            self.url(self.cheap),
            {"name": "Cheap laptop", "category": self.laptops.pk, "price": "500.00"},
        )
        self.cheap.refresh_from_db()
        self.assertFalse(self.cheap.has_discount)
        response = self.client.get(reverse("sale"))
        self.assertEqual(list(response.context["products"]), [])

    def test_price_change_changes_order_on_home_page(self):
        self.client.post(
            self.url(self.expensive),
            {"name": "Expensive laptop", "category": self.laptops.pk, "price": "100"},
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["products"][0], self.expensive)

    def test_success_message(self):
        response = self.client.post(
            self.url(self.mid),
            {"name": "Mid phone 2", "category": self.phones.pk, "price": "801"},
            follow=True,
        )
        self.assertContains(response, "was updated")

    def test_invalid_post_does_not_change_product(self):
        response = self.client.post(
            self.url(self.mid),
            {"name": "Changed", "category": self.phones.pk, "price": "-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.name, "Mid phone")
        self.assertEqual(self.mid.price, Decimal("800.00"))

    def test_missing_product_returns_404(self):
        self.assertEqual(self.client.get("/product/9999/edit/").status_code, 404)
        self.assertEqual(self.client.post("/product/9999/edit/", {}).status_code, 404)


class ProductDeleteTests(ShopTestCase):
    def setUp(self):
        # წაშლა მხოლოდ მფლობელს შეუძლია (ყველა პროდუქტი owner-ს ეკუთვნის)
        self.client.force_login(self.owner)

    def url(self, product):
        return reverse("product_delete", args=[product.pk])

    def test_url_pattern(self):
        self.assertEqual(self.url(self.mid), f"/product/{self.mid.pk}/delete/")

    def test_get_shows_confirmation_and_does_not_delete(self):
        response = self.client.get(self.url(self.mid))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete this product?")
        self.assertContains(response, "Mid phone")
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())

    def test_post_deletes_product_and_redirects_home(self):
        response = self.client.post(self.url(self.mid))
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Product.objects.filter(pk=self.mid.pk).exists())
        self.assertEqual(Product.objects.count(), 2)

    def test_only_selected_product_is_deleted(self):
        self.client.post(self.url(self.cheap))
        self.assertEqual(
            set(Product.objects.values_list("name", flat=True)),
            {"Mid phone", "Expensive laptop"},
        )

    def test_success_message_and_product_is_gone_from_pages(self):
        response = self.client.post(self.url(self.mid), follow=True)
        self.assertContains(response, "was deleted")
        self.assertNotContains(response, reverse("product_detail", args=[self.mid.pk]))

    def test_deleted_product_page_returns_404(self):
        self.client.post(self.url(self.mid))
        self.assertEqual(
            self.client.get(reverse("product_detail", args=[self.mid.pk])).status_code, 404
        )

    def test_category_without_products_disappears_from_list(self):
        self.client.post(self.url(self.mid))
        response = self.client.get(reverse("home"))
        names = [c.name for c in response.context["categories"]]
        self.assertEqual(names, ["Laptops"])
        # თვითონ კატეგორია ბაზაში რჩება
        self.assertTrue(Category.objects.filter(pk=self.phones.pk).exists())

    def test_missing_product_returns_404(self):
        self.assertEqual(self.client.get("/product/9999/delete/").status_code, 404)
        self.assertEqual(self.client.post("/product/9999/delete/").status_code, 404)

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.force_login(self.owner)
        response = strict_client.post(self.url(self.mid))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())


class ClassBasedViewsTests(ShopTestCase):
    """HW39: view-ები Class-Based View-ებია, გარდა update-ისა და delete-ისა."""

    def view_of(self, name, *args):
        return resolve(reverse(name, args=args)).func

    def test_converted_views_use_expected_generic_classes(self):
        expected = {
            "home": (ListView, []),
            "sale": (ListView, []),
            "category_detail": (DetailView, [self.laptops.pk]),
            "product_detail": (DetailView, [self.cheap.pk]),
            "product_create": (CreateView, []),
            "cart": (TemplateView, []),
            "checkout": (TemplateView, []),
            "contact": (TemplateView, []),
        }
        for name, (base_class, args) in expected.items():
            with self.subTest(view=name):
                view_class = getattr(self.view_of(name, *args), "view_class", None)
                self.assertIsNotNone(view_class, f"{name} is not a class-based view")
                self.assertTrue(issubclass(view_class, base_class))

    def test_create_view_is_protected_by_login_required_mixin(self):
        view_class = self.view_of("product_create").view_class
        self.assertTrue(issubclass(view_class, LoginRequiredMixin))

    def test_update_and_delete_stay_function_based(self):
        for name in ("product_update", "product_delete"):
            with self.subTest(view=name):
                view = self.view_of(name, self.mid.pk)
                self.assertFalse(hasattr(view, "view_class"))

    def test_read_only_pages_do_not_accept_post(self):
        urls = [
            reverse("home"),
            reverse("sale"),
            reverse("category_detail", args=[self.laptops.pk]),
            reverse("product_detail", args=[self.cheap.pk]),
            reverse("cart"),
            reverse("checkout"),
            reverse("contact"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 405)

    def test_non_ascii_digit_in_category_parameter_is_ignored(self):
        response = self.client.get(reverse("home"), {"category": "²"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 3)


class PlaceholderImageTests(ShopTestCase):
    def test_all_possible_images_exist_in_static_files(self):
        numbers = set(DEFAULT_IMAGES)
        for category_numbers in CATEGORY_IMAGES.values():
            numbers.update(category_numbers)
        for number in sorted(numbers):
            with self.subTest(image=number):
                self.assertIsNotNone(finders.find(f"shop/img/product-{number}.png"))

    def test_image_is_stable_for_same_product(self):
        self.assertEqual(self.cheap.placeholder_image, self.cheap.placeholder_image)

    def test_image_for_known_and_unknown_category(self):
        self.assertEqual(self.cheap.placeholder_image, "shop/img/product-11.png")
        self.assertTrue(self.mid.placeholder_image.startswith("shop/img/product-"))


# ===========================================================================
# HW41: მომხმარებლები, პროდუქტის მფლობელი, სურათი და უფლებები
# ===========================================================================

class ProductOwnerFieldTests(ShopTestCase):
    """Product.user: პროდუქტი მიბმულია მომხმარებელზე (ForeignKey)."""

    def test_product_belongs_to_user_and_reverse_relation_works(self):
        self.assertEqual(self.mid.user, self.owner)
        self.assertEqual(self.owner.products.count(), 3)
        self.assertEqual(self.other.products.count(), 0)

    def test_deleting_user_deletes_his_products(self):
        self.other_product = Product.objects.create(
            name="Other's phone", price="10", category=self.phones, user=self.other
        )
        self.other.delete()
        self.assertFalse(Product.objects.filter(name="Other's phone").exists())
        self.assertEqual(Product.objects.count(), 3)

    def test_is_owned_by(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertTrue(self.mid.is_owned_by(self.owner))
        self.assertFalse(self.mid.is_owned_by(self.other))
        self.assertFalse(self.mid.is_owned_by(AnonymousUser()))

    def test_product_without_owner_belongs_to_nobody(self):
        from django.contrib.auth.models import AnonymousUser

        legacy = Product.objects.create(name="Legacy", price="5", category=self.phones)
        self.assertIsNone(legacy.user)
        self.assertFalse(legacy.is_owned_by(self.owner))
        # ანონიმურ მომხმარებელს (id=None) უმფლობელო პროდუქტთან არასდროს უნდა დაემთხვეს
        self.assertFalse(legacy.is_owned_by(AnonymousUser()))


class ProductCreatePermissionTests(ShopTestCase):
    """პროდუქტის დამატება მხოლოდ შესულ მომხმარებელს შეუძლია; მფლობელი ავტომატურად ეწერება."""

    url = "/product/add/"

    def valid_data(self, **extra):
        data = {"name": "Owner test", "category": self.phones.pk, "price": "10.00"}
        data.update(extra)
        return data

    def test_anonymous_get_redirects_to_login_with_next(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_anonymous_post_is_redirected_and_nothing_is_saved(self):
        response = self.client.post(self.url, self.valid_data())
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")
        self.assertEqual(Product.objects.count(), 3)
        self.assertFalse(Product.objects.filter(name="Owner test").exists())

    def test_login_page_explains_why_user_was_redirected(self):
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "Please log in to add a product.")

    def test_after_login_user_returns_to_add_page(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_logged_in_user_is_saved_as_owner(self):
        self.client.force_login(self.other)
        self.client.post(self.url, self.valid_data())
        self.assertEqual(Product.objects.get(name="Owner test").user, self.other)

    def test_owner_is_the_currently_logged_in_user_each_time(self):
        for user in (self.owner, self.other):
            self.client.force_login(user)
            self.client.post(self.url, self.valid_data(name=f"By {user.username}"))
        self.assertEqual(Product.objects.get(name="By owner").user, self.owner)
        self.assertEqual(Product.objects.get(name="By other").user, self.other)

    def test_form_has_no_user_field(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertNotIn("user", response.context["form"].fields)
        self.assertNotContains(response, 'name="user"')

    def test_user_value_sent_in_post_is_ignored(self):
        """ვინმემ ხელით რომ გაგზავნოს user=<სხვა id>, მაინც შესული მომხმარებელი ჩაიწერება."""
        self.client.force_login(self.owner)
        self.client.post(self.url, self.valid_data(user=self.other.pk))
        self.assertEqual(Product.objects.get(name="Owner test").user, self.owner)


class ProductUpdatePermissionTests(ShopTestCase):
    """განახლება მხოლოდ მფლობელს შეუძლია."""

    def url(self, product):
        return reverse("product_update", args=[product.pk])

    def data(self, **extra):
        data = {"name": "Hacked", "category": self.phones.pk, "price": "1.00"}
        data.update(extra)
        return data

    def test_anonymous_is_redirected_to_login(self):
        url = self.url(self.mid)
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")
        self.assertRedirects(self.client.post(url, self.data()), f"{reverse('login')}?next={url}")
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.name, "Mid phone")

    def test_other_user_gets_403_on_get_and_post(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url(self.mid)).status_code, 403)
        self.assertEqual(self.client.post(self.url(self.mid), self.data()).status_code, 403)
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.name, "Mid phone")
        self.assertEqual(self.mid.price, Decimal("800.00"))

    def test_403_page_is_our_template_with_explanation(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url(self.mid))
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "You don't have permission", status_code=403)
        self.assertContains(response, "Only the user who added a product", status_code=403)

    def test_owner_can_update(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url(self.mid), self.data(name="Mine now"))
        self.assertRedirects(response, reverse("product_detail", args=[self.mid.pk]))
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.name, "Mine now")

    def test_update_keeps_the_owner(self):
        self.client.force_login(self.owner)
        self.client.post(self.url(self.mid), self.data(user=self.other.pk))
        self.mid.refresh_from_db()
        self.assertEqual(self.mid.user, self.owner)

    def test_product_without_owner_cannot_be_updated_from_the_site(self):
        legacy = Product.objects.create(name="Legacy", price="5", category=self.phones)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url(legacy)).status_code, 403)

    def test_missing_product_is_404_for_logged_in_user(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/product/9999/edit/").status_code, 404)


class ProductDeletePermissionTests(ShopTestCase):
    """წაშლა მხოლოდ მფლობელს შეუძლია."""

    def url(self, product):
        return reverse("product_delete", args=[product.pk])

    def test_anonymous_is_redirected_to_login_and_nothing_is_deleted(self):
        url = self.url(self.mid)
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")
        self.assertRedirects(self.client.post(url), f"{reverse('login')}?next={url}")
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())

    def test_other_user_gets_403_and_product_stays(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url(self.mid)).status_code, 403)
        self.assertEqual(self.client.post(self.url(self.mid)).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())
        self.assertEqual(Product.objects.count(), 3)

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url(self.mid))
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Product.objects.filter(pk=self.mid.pk).exists())

    def test_each_user_deletes_only_own_product(self):
        theirs = Product.objects.create(
            name="Other's phone", price="10", category=self.phones, user=self.other
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url(self.mid)).status_code, 403)
        self.assertEqual(self.client.post(self.url(theirs)).status_code, 302)
        self.assertFalse(Product.objects.filter(pk=theirs.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())

    def test_product_without_owner_cannot_be_deleted_from_the_site(self):
        legacy = Product.objects.create(name="Legacy", price="5", category=self.phones)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.url(legacy)).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=legacy.pk).exists())

    def test_missing_product_is_404_for_logged_in_user(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post("/product/9999/delete/").status_code, 404)


class OwnerOnlyButtonsTests(ShopTestCase):
    """Edit/Delete ღილაკები და Add Product მხოლოდ იმას ჩანს, ვისაც შესაბამისი უფლება აქვს."""

    def edit_link(self, product):
        return reverse("product_update", args=[product.pk])

    def delete_link(self, product):
        return reverse("product_delete", args=[product.pk])

    def pages(self):
        return [
            reverse("home"),
            reverse("sale"),
            reverse("category_detail", args=[self.laptops.pk]),
            reverse("product_detail", args=[self.cheap.pk]),
        ]

    def test_anonymous_sees_no_edit_or_delete_buttons(self):
        for url in self.pages():
            with self.subTest(page=url):
                response = self.client.get(url)
                for product in (self.cheap, self.mid, self.expensive):
                    self.assertNotContains(response, self.edit_link(product))
                    self.assertNotContains(response, self.delete_link(product))

    def test_anonymous_add_product_link_leads_to_login_page(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("product_create"))
        response = self.client.get(reverse("product_create"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], f"{reverse('login')}?next=/product/add/")

    def test_other_user_sees_no_edit_or_delete_buttons_but_can_add(self):
        self.client.force_login(self.other)
        for url in self.pages():
            with self.subTest(page=url):
                response = self.client.get(url)
                for product in (self.cheap, self.mid, self.expensive):
                    self.assertNotContains(response, self.edit_link(product))
                    self.assertNotContains(response, self.delete_link(product))
                self.assertContains(response, reverse("product_create"))

    def test_owner_sees_edit_and_delete_buttons_on_cards_and_detail_page(self):
        self.client.force_login(self.owner)
        for url in self.pages():
            with self.subTest(page=url):
                response = self.client.get(url)
                self.assertContains(response, self.edit_link(self.cheap))
                self.assertContains(response, self.delete_link(self.cheap))

    def test_only_own_products_get_buttons(self):
        theirs = Product.objects.create(
            name="Other's phone", price="10", category=self.phones, user=self.other
        )
        self.client.force_login(self.other)
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.edit_link(theirs))
        self.assertNotContains(response, self.edit_link(self.mid))

    def test_product_without_owner_has_no_buttons_for_anyone(self):
        legacy = Product.objects.create(name="Legacy", price="5", category=self.phones)
        for user in (None, self.owner):
            if user:
                self.client.force_login(user)
            with self.subTest(user=user):
                response = self.client.get(reverse("product_detail", args=[legacy.pk]))
                self.assertNotContains(response, self.edit_link(legacy))
                self.assertNotContains(response, self.delete_link(legacy))
                self.assertContains(response, "Mini Shop catalog")

    def test_detail_page_shows_who_added_the_product(self):
        response = self.client.get(reverse("product_detail", args=[self.mid.pk]))
        self.assertContains(response, "Added by")
        self.assertContains(response, "owner")


class ProductImageTests(TempMediaMixin, ShopTestCase):
    """image ველი: ატვირთვა, ჩვენება, შეცვლა, წაშლა და შემოწმება."""

    create_url = "/product/add/"

    def post_data(self, **extra):
        data = {"name": "With photo", "category": self.phones.pk, "price": "10.00"}
        data.update(extra)
        return data

    def create_with_image(self, **extra):
        self.client.force_login(self.owner)
        self.client.post(self.create_url, self.post_data(image=make_image(**extra)))
        return Product.objects.get(name="With photo")

    def test_form_is_multipart_and_has_image_field(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.create_url)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'type="file"')
        self.assertIn("image", response.context["form"].fields)

    def test_image_is_optional(self):
        self.client.force_login(self.owner)
        self.client.post(self.create_url, self.post_data())
        product = Product.objects.get(name="With photo")
        self.assertFalse(product.image)
        self.assertEqual(self.media_files(), [])

    def test_uploaded_image_is_saved_in_products_folder(self):
        product = self.create_with_image()
        self.assertTrue(product.image.name.startswith("products/"))
        self.assertEqual(self.media_files(), [product.image.name.replace("/", os.sep)])
        self.assertEqual(product.user, self.owner)

    def test_uploaded_image_is_shown_on_pages(self):
        product = self.create_with_image()
        for url in (reverse("home"), reverse("product_detail", args=[product.pk])):
            with self.subTest(page=url):
                self.assertContains(self.client.get(url), product.image.url)

    def test_product_without_image_uses_template_placeholder(self):
        self.assertEqual(self.mid.image_url, f"/static/{self.mid.placeholder_image}")
        self.assertContains(
            self.client.get(reverse("product_detail", args=[self.mid.pk])),
            self.mid.image_url,
        )

    def test_not_an_image_is_rejected(self):
        self.client.force_login(self.owner)
        fake = SimpleUploadedFile("evil.png", b"this is not an image", content_type="image/png")
        response = self.client.post(self.create_url, self.post_data(image=fake))
        self.assertEqual(response.status_code, 200)
        self.assertIn("image", response.context["form"].errors)
        self.assertFalse(Product.objects.filter(name="With photo").exists())
        self.assertEqual(self.media_files(), [])

    def test_unsupported_format_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.create_url, self.post_data(image=make_image("scan.bmp", "BMP"))
        )
        self.assertIn("JPG, PNG, GIF or WEBP", str(response.context["form"].errors["image"]))
        self.assertFalse(Product.objects.filter(name="With photo").exists())

    def test_supported_formats_are_accepted(self):
        self.client.force_login(self.owner)
        for index, (file_name, image_format) in enumerate(
            [("a.jpg", "JPEG"), ("b.png", "PNG"), ("c.gif", "GIF"), ("d.webp", "WEBP")]
        ):
            with self.subTest(format=image_format):
                response = self.client.post(
                    self.create_url,
                    self.post_data(name=f"Photo {index}", image=make_image(file_name, image_format)),
                )
                self.assertEqual(response.status_code, 302)

    def test_too_large_image_is_rejected(self):
        from . import forms

        self.client.force_login(self.owner)
        original = forms.MAX_IMAGE_SIZE
        forms.MAX_IMAGE_SIZE = 10  # ბაიტი: ნებისმიერი რეალური სურათი დიდია
        try:
            response = self.client.post(self.create_url, self.post_data(image=make_image()))
        finally:
            forms.MAX_IMAGE_SIZE = original
        self.assertIn("too large", str(response.context["form"].errors["image"]))
        self.assertFalse(Product.objects.filter(name="With photo").exists())

    def test_edit_page_shows_current_image(self):
        product = self.create_with_image()
        response = self.client.get(reverse("product_update", args=[product.pk]))
        self.assertContains(response, product.image.url)

    def test_update_without_new_file_keeps_old_image(self):
        product = self.create_with_image()
        old_name = product.image.name
        self.client.post(
            reverse("product_update", args=[product.pk]),
            self.post_data(name="Renamed"),
        )
        product.refresh_from_db()
        self.assertEqual(product.name, "Renamed")
        self.assertEqual(product.image.name, old_name)
        self.assertEqual(len(self.media_files()), 1)

    def test_update_with_new_file_replaces_image_and_removes_old_file(self):
        product = self.create_with_image()
        old_name = product.image.name
        self.client.post(
            reverse("product_update", args=[product.pk]),
            self.post_data(image=make_image("second.png")),
        )
        product.refresh_from_db()
        self.assertNotEqual(product.image.name, old_name)
        self.assertEqual(self.media_files(), [product.image.name.replace("/", os.sep)])

    def test_clear_checkbox_removes_image_and_file(self):
        product = self.create_with_image()
        self.client.post(
            reverse("product_update", args=[product.pk]),
            self.post_data(**{"image-clear": "on"}),
        )
        product.refresh_from_db()
        self.assertFalse(product.image)
        self.assertEqual(self.media_files(), [])

    def test_deleting_product_removes_its_image_file(self):
        product = self.create_with_image()
        self.assertEqual(len(self.media_files()), 1)
        self.client.post(reverse("product_delete", args=[product.pk]))
        self.assertEqual(self.media_files(), [])

    def test_deleting_category_removes_image_files_of_its_products(self):
        self.create_with_image()
        self.phones.delete()
        self.assertEqual(self.media_files(), [])

    def test_other_user_cannot_replace_image(self):
        product = self.create_with_image()
        old_name = product.image.name
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("product_update", args=[product.pk]),
            self.post_data(image=make_image("hijack.png")),
        )
        self.assertEqual(response.status_code, 403)
        product.refresh_from_db()
        self.assertEqual(product.image.name, old_name)
        self.assertEqual(len(self.media_files()), 1)


class UrlsAndSettingsTests(ShopTestCase):
    def test_media_settings_exist(self):
        from django.conf import settings

        self.assertEqual(settings.MEDIA_URL, "/media/")
        self.assertTrue(str(settings.MEDIA_ROOT).endswith("media"))

    def test_auth_settings_exist(self):
        from django.conf import settings

        self.assertEqual(settings.LOGIN_URL, "login")
        self.assertEqual(settings.LOGIN_REDIRECT_URL, "home")
        self.assertEqual(settings.LOGOUT_REDIRECT_URL, "home")

    def test_builtin_user_model_is_used(self):
        from django.conf import settings

        self.assertEqual(settings.AUTH_USER_MODEL, "auth.User")


# ---------------------------------------------------------------------------
# HW42: პაგინაცია, ტექნიკური სამუშაოების middleware, პროდუქტის განახლების სიგნალი
# ---------------------------------------------------------------------------


class PaginationTests(ShopTestCase):
    """
    პაგინაცია მთავარ (8 პროდუქტი გვერდზე), კატეგორიის და sale (6 პროდუქტი) გვერდებზე.

    საწყისი 3 პროდუქტის გარდა ვამატებთ კატეგორიას "Many" 15 ფასდაკლებული პროდუქტით:
    - მთავარი: 3 + 15 = 18 პროდუქტი = 3 გვერდი (8 + 8 + 2),
    - "Many" კატეგორია: 15 პროდუქტი = 3 გვერდი (6 + 6 + 3),
    - sale: 1 + 15 = 16 პროდუქტი = 3 გვერდი (6 + 6 + 4).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.many = Category.objects.create(name="Many")
        Product.objects.bulk_create(
            Product(
                name=f"Many {i:02d}",
                price=Decimal(1000 + i),
                category=cls.many,
                has_discount=True,
                user=cls.owner,
            )
            for i in range(1, 16)
        )

    def names(self, response):
        return [product.name for product in response.context["products"]]

    def category_url(self):
        return reverse("category_detail", args=[self.many.pk])

    def test_page_sizes(self):
        self.assertEqual(HomeView.paginate_by, 8)
        self.assertEqual(CategoryDetailView.paginate_by, 6)
        self.assertEqual(SaleView.paginate_by, 6)

    # --- მთავარი გვერდი -------------------------------------------------

    def test_home_first_page_has_8_products(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["paginator"].count, 18)
        self.assertEqual(response.context["paginator"].num_pages, 3)

    def test_home_last_page_has_the_rest(self):
        response = self.client.get(reverse("home"), {"page": 3})
        self.assertEqual(self.names(response), ["Many 15", "Expensive laptop"])

    def test_home_pages_together_show_every_product_once_in_price_order(self):
        products = []
        for number in (1, 2, 3):
            response = self.client.get(reverse("home"), {"page": number})
            products += list(response.context["products"])
        self.assertEqual(len(products), 18)
        self.assertEqual(len({p.pk for p in products}), 18)  # გამეორებების გარეშე
        prices = [p.price for p in products]
        self.assertEqual(prices, sorted(prices))  # ფასის ზრდადობა გვერდებს შორისაც ნარჩუნდება

    def test_home_heading_shows_total_not_page_size(self):
        for page in (1, 3):
            with self.subTest(page=page):
                response = self.client.get(reverse("home"), {"page": page})
                self.assertContains(response, "· 18 products")

    def test_pagination_links_on_first_middle_and_last_page(self):
        first = self.client.get(reverse("home"))
        self.assertContains(first, 'href="?page=2"')
        self.assertContains(first, 'aria-label="Next page"')
        self.assertNotContains(first, 'aria-label="Previous page"')
        self.assertContains(first, '<a class="active rounded" aria-current="page">1</a>')
        self.assertContains(first, "Showing 1–8 of 18 products")

        middle = self.client.get(reverse("home"), {"page": 2})
        self.assertContains(middle, 'aria-label="Previous page"')
        self.assertContains(middle, 'aria-label="Next page"')
        self.assertContains(middle, 'href="?page=1"')
        self.assertContains(middle, 'href="?page=3"')
        self.assertContains(middle, '<a class="active rounded" aria-current="page">2</a>')
        self.assertContains(middle, "Showing 9–16 of 18 products")

        last = self.client.get(reverse("home"), {"page": 3})
        self.assertContains(last, 'aria-label="Previous page"')
        self.assertNotContains(last, 'aria-label="Next page"')
        self.assertContains(last, "Showing 17–18 of 18 products")

    def test_search_parameters_survive_page_links(self):
        response = self.client.get(reverse("home"), {"q": "Many", "page": 1})
        self.assertEqual(response.context["paginator"].count, 15)
        self.assertContains(response, "15 products found")
        self.assertContains(response, 'href="?q=Many&amp;page=2"')

        response = self.client.get(
            reverse("home"), {"q": "Many", "category": self.many.pk, "page": 2}
        )
        self.assertEqual(len(response.context["products"]), 7)
        # page არ მეორდება: ძველი მნიშვნელობა იცვლება ახლით
        self.assertContains(
            response, f'href="?q=Many&amp;category={self.many.pk}&amp;page=1"'
        )
        self.assertNotContains(response, "page=2&amp;page=")

    def test_search_with_no_results_has_no_pagination(self):
        response = self.client.get(reverse("home"), {"q": "zzz-nothing"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 0)
        self.assertContains(response, "No products match your search.")
        self.assertNotContains(response, 'class="pagination')

    # --- კატეგორიის გვერდი ---------------------------------------------

    def test_category_page_is_paginated(self):
        first = self.client.get(self.category_url())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.context["products"]), 6)
        self.assertEqual(self.names(first)[0], "Many 01")
        self.assertTrue(first.context["is_paginated"])
        self.assertEqual(first.context["paginator"].count, 15)
        self.assertContains(first, "· 15 products")
        self.assertContains(first, 'href="?page=2"')

        last = self.client.get(self.category_url(), {"page": 3})
        self.assertEqual(self.names(last), ["Many 13", "Many 14", "Many 15"])
        self.assertContains(last, "Showing 13–15 of 15 products")

    def test_category_pages_contain_only_this_category(self):
        for number in (1, 2, 3):
            response = self.client.get(self.category_url(), {"page": number})
            for product in response.context["products"]:
                self.assertEqual(product.category, self.many)

    # --- sale გვერდი ---------------------------------------------------

    def test_sale_page_is_paginated(self):
        first = self.client.get(reverse("sale"))
        self.assertEqual(len(first.context["products"]), 6)
        self.assertEqual(first.context["paginator"].count, 16)
        self.assertContains(first, "· 16 products")

        last = self.client.get(reverse("sale"), {"page": 3})
        self.assertEqual(len(last.context["products"]), 4)
        for product in last.context["products"]:
            self.assertTrue(product.has_discount)

    # --- შეცდომები და განსაკუთრებული შემთხვევები -----------------------

    def test_invalid_page_returns_404_everywhere(self):
        for url in (reverse("home"), self.category_url(), reverse("sale")):
            for bad_page in ("99", "0", "-1", "abc"):
                with self.subTest(url=url, page=bad_page):
                    response = self.client.get(url, {"page": bad_page})
                    self.assertEqual(response.status_code, 404)

    def test_empty_page_parameter_means_first_page(self):
        for url in (reverse("home"), self.category_url(), reverse("sale")):
            with self.subTest(url=url):
                response = self.client.get(url, {"page": ""})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["page_obj"].number, 1)

    def test_page_with_a_single_page_of_products_has_no_pagination_block(self):
        # "Laptops" კატეგორიაში მხოლოდ 2 პროდუქტია
        response = self.client.get(reverse("category_detail", args=[self.laptops.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_paginated"])
        self.assertEqual(len(response.context["products"]), 2)
        self.assertNotContains(response, 'class="pagination')
        self.assertNotContains(response, "Showing ")

    def test_page_numbers_are_shortened_with_dots_when_there_are_many_pages(self):
        page = Paginator(range(200), 8).page(13)  # 25 გვერდი, ვართ მე-13-ზე
        request = RequestFactory().get("/", {"q": "x", "page": 13})
        context = pagination({"request": request}, page)
        shown = ["..." if item.get("gap") else item["number"] for item in context["pages"]]
        self.assertEqual(shown, [1, "...", 11, 12, 13, 14, 15, "...", 25])
        self.assertEqual(context["querystring"], "q=x")


class MaintenanceModeTests(ShopTestCase):
    """MAINTENANCE_MODE = True-ზე ყველაფერი იკეტება, გარდა /admin/-ისა."""

    MESSAGE = "Site is under maintenance"

    def test_shipped_default_is_off(self):
        # პროექტის settings.py-ში (override_settings-ის გარეშე) რეჟიმი გამორთული უნდა იყოს
        from config import settings as project_settings

        self.assertIs(project_settings.MAINTENANCE_MODE, False)

    def test_middleware_is_registered_in_settings(self):
        from django.conf import settings

        middleware = settings.MIDDLEWARE
        name = "shop.middleware.MaintenanceModeMiddleware"
        self.assertIn(name, middleware)
        # CommonMiddleware-ის შემდეგ ("/admin" -> "/admin/"), CSRF/Auth-ის წინ (ბაზას არ ვეხებით)
        self.assertGreater(middleware.index(name), middleware.index("django.middleware.common.CommonMiddleware"))
        self.assertLess(middleware.index(name), middleware.index("django.middleware.csrf.CsrfViewMiddleware"))
        self.assertLess(
            middleware.index(name),
            middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"),
        )

    def test_site_works_normally_when_mode_is_off(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.MESSAGE)

    @override_settings(MAINTENANCE_MODE=True)
    def test_every_page_shows_the_maintenance_message(self):
        urls = [
            reverse("home"),
            reverse("sale"),
            reverse("category_detail", args=[self.laptops.pk]),
            reverse("product_detail", args=[self.cheap.pk]),
            reverse("product_create"),
            reverse("product_update", args=[self.cheap.pk]),
            reverse("cart"),
            reverse("checkout"),
            reverse("contact"),
            reverse("login"),
            reverse("register"),
            "/no/such/page/",  # არარსებული გვერდიც
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                # 503 Service Unavailable: "დროებით მიუწვდომელია"
                self.assertContains(response, self.MESSAGE, status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_post_requests_are_blocked_too(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("product_create"),
            {"name": "Sneaky", "category": self.laptops.pk, "price": "10"},
        )
        self.assertContains(response, self.MESSAGE, status_code=503)
        self.assertFalse(Product.objects.filter(name="Sneaky").exists())

    @override_settings(MAINTENANCE_MODE=True)
    def test_logged_in_users_see_maintenance_too(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.MESSAGE, status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_admin_keeps_working(self):
        # ანონიმურს admin-ის შესვლის გვერდი უხსნება და არა "maintenance"
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.MESSAGE)
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/")

        # შესული ადმინისტრატორი admin-ის გვერდებს ჩვეულებრივ ხედავს
        boss = User.objects.create(username="boss", is_staff=True, is_superuser=True)
        self.client.force_login(boss)
        for url in (
            "/admin/",
            "/admin/shop/product/",
            f"/admin/shop/product/{self.cheap.pk}/change/",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, self.MESSAGE)

    @override_settings(MAINTENANCE_MODE=True)
    def test_admin_url_without_trailing_slash_is_not_blocked(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 301)  # /admin/-ზე გადამისამართება
        self.assertEqual(response["Location"], "/admin/")

    @override_settings(MAINTENANCE_MODE=True)
    def test_urls_that_only_look_like_admin_are_blocked(self):
        for url in ("/administrator/", "/admin-panel/", "/shop/admin/"):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), self.MESSAGE, status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_maintenance_page_does_not_touch_the_database(self):
        # context processor-ებისა და სესიის გარეშე: ბაზა არ გვჭირდება
        with self.assertNumQueries(0):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 503)

    @override_settings()
    def test_missing_setting_means_the_site_is_on(self):
        from django.conf import settings

        del settings.MAINTENANCE_MODE
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_mode_can_be_switched_on_and_off(self):
        with override_settings(MAINTENANCE_MODE=True):
            self.assertEqual(self.client.get(reverse("home")).status_code, 503)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_middleware_passes_request_on_only_when_allowed(self):
        passed_on = []

        def get_response(request):
            passed_on.append(request.path)
            return HttpResponse("real page")

        middleware = MaintenanceModeMiddleware(get_response)
        factory = RequestFactory()

        with override_settings(MAINTENANCE_MODE=False):
            self.assertEqual(middleware(factory.get("/sale/")).content, b"real page")
        with override_settings(MAINTENANCE_MODE=True):
            blocked = middleware(factory.get("/sale/"))
            allowed = middleware(factory.get("/admin/shop/product/"))

        self.assertEqual(blocked.status_code, 503)
        self.assertIn(self.MESSAGE.encode(), blocked.content)
        self.assertEqual(allowed.content, b"real page")
        # დაბლოკილი request შემდეგ ფენამდე (view-მდე) საერთოდ არ მისულა
        self.assertEqual(passed_on, ["/sale/", "/admin/shop/product/"])


class ProductUpdatedSignalTests(ShopTestCase):
    """post_save signal: განახლებულ პროდუქტზე ტერმინალში იბეჭდება Product "..." was updated."""

    def capture(self):
        """print-ის ტექსტს იჭერს (ტერმინალის ნაცვლად StringIO-ში ჩაწერს)."""
        return contextlib.redirect_stdout(io.StringIO())

    def test_signal_is_connected(self):
        self.assertTrue(post_save.has_listeners(Product))

    def test_saving_existing_product_prints_the_message(self):
        product = Product.objects.get(pk=self.cheap.pk)
        product.name = "Asus Laptop"
        with self.capture() as output:
            product.save()
        self.assertEqual(output.getvalue(), 'Product "Asus Laptop" was updated.\n')

    def test_message_works_with_georgian_names(self):
        product = Product.objects.get(pk=self.cheap.pk)
        product.name = "ლეპტოპი"
        with self.capture() as output:
            product.save()
        self.assertEqual(output.getvalue(), 'Product "ლეპტოპი" was updated.\n')

    def test_creating_a_product_prints_nothing(self):
        with self.capture() as output:
            Product.objects.create(
                name="Brand new", price="10", category=self.laptops, user=self.owner
            )
        self.assertEqual(output.getvalue(), "")

    def test_deleting_a_product_prints_nothing(self):
        with self.capture() as output:
            self.cheap.delete()
        self.assertEqual(output.getvalue(), "")

    def test_edit_form_prints_the_message_once(self):
        self.client.force_login(self.owner)
        with self.capture() as output:
            response = self.client.post(
                reverse("product_update", args=[self.mid.pk]),
                {"name": "Asus Laptop", "category": self.laptops.pk, "price": "999"},
            )
        self.assertRedirects(response, reverse("product_detail", args=[self.mid.pk]))
        self.assertEqual(output.getvalue(), 'Product "Asus Laptop" was updated.\n')

    def test_invalid_edit_form_prints_nothing(self):
        self.client.force_login(self.owner)
        with self.capture() as output:
            response = self.client.post(
                reverse("product_update", args=[self.mid.pk]),
                {"name": "Asus Laptop", "category": self.laptops.pk, "price": "not a number"},
            )
        self.assertEqual(response.status_code, 200)  # ფორმა შეცდომებით ისევ გამოჩნდა
        self.assertEqual(output.getvalue(), "")

    def test_add_form_prints_nothing(self):
        self.client.force_login(self.owner)
        with self.capture() as output:
            response = self.client.post(
                reverse("product_create"),
                {"name": "Asus Laptop", "category": self.laptops.pk, "price": "999"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(output.getvalue(), "")
