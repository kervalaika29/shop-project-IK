"""
REST API-ის ტესტები (HW45).

    python manage.py test api          მხოლოდ API-ის ტესტები
    python manage.py test              ყველა ტესტი (shop, users, api)
"""

import base64
import io
import os
import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import resolve, reverse
from PIL import Image
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIClient, APITestCase

from shop import forms as shop_forms
from shop.models import Category, Product

from .serializers import (
    CategoryListSerializer,
    CategorySerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)
from .views import (
    CategoryListAPIView,
    ProductCreateAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
)

User = get_user_model()

CATEGORY_LIST_KEYS = {"id", "name", "description", "product_count"}
PRODUCT_LIST_KEYS = {"id", "url", "name", "price", "has_discount", "category", "category_name", "image"}
PRODUCT_DETAIL_KEYS = {"id", "name", "description", "price", "has_discount", "image", "category", "owner"}


def make_image(name="photo.png", image_format="PNG", size=(30, 20)):
    """ტესტისთვის ნამდვილ (Pillow-ით შექმნილ) სურათს აბრუნებს ატვირთვისთვის."""
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=Image.MIME[image_format])


class ApiTestCase(APITestCase):
    """
    საერთო საწყისი მონაცემები: ორი მომხმარებელი, სამი კატეგორია (ერთი ცარიელი) და ოთხი პროდუქტი,
    მათგან ერთი უმფლობელო ("ძველი", HW41-მდე დამატებულის მსგავსი).

    ატვირთული სურათები დროებით საქაღალდეში ინახება და ტესტების შემდეგ იშლება, ამიტომ
    პროექტის media/ საქაღალდე არ ივსება.
    """

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="api-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="owner", email="owner@example.com")
        cls.other = User.objects.create(username="other", email="other@example.com")

        cls.laptops = Category.objects.create(name="Laptops", description="Notebook computers")
        cls.phones = Category.objects.create(name="Phones")
        cls.empty = Category.objects.create(name="Empty category")

        cls.cheap = Product.objects.create(
            name="Cheap laptop", price="500.00", category=cls.laptops,
            description="Light and cheap", has_discount=True, user=cls.owner,
        )
        cls.mid = Product.objects.create(
            name="Mid phone", price="800.00", category=cls.phones, user=cls.owner
        )
        cls.expensive = Product.objects.create(
            name="Expensive laptop", price="2500.00", category=cls.laptops, user=cls.owner
        )
        # უმფლობელო პროდუქტი (ასეთია საიტის 14 საწყისი პროდუქტი)
        cls.legacy = Product.objects.create(
            name="Legacy tablet", price="1500.00", category=cls.phones
        )

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


# ---------------------------------------------------------------------------
# მისამართები
# ---------------------------------------------------------------------------

class ApiUrlsTests(ApiTestCase):
    def test_url_names_and_paths(self):
        self.assertEqual(reverse("api:category-list"), "/api/categories/")
        self.assertEqual(reverse("api:product-list"), "/api/products/")
        self.assertEqual(reverse("api:product-create"), "/api/products/create/")
        self.assertEqual(reverse("api:product-detail", args=[7]), "/api/products/7/")

    def test_each_url_leads_to_its_view(self):
        expected = {
            "/api/categories/": CategoryListAPIView,
            "/api/products/": ProductListAPIView,
            "/api/products/create/": ProductCreateAPIView,
            f"/api/products/{self.cheap.pk}/": ProductDetailAPIView,
        }
        for path, view_class in expected.items():
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class, view_class)

    def test_create_url_is_not_mistaken_for_a_product_id(self):
        """"/api/products/create/" ახალი პროდუქტის შექმნაა და არა პროდუქტი "create"-ის სახელით."""
        self.assertIs(resolve("/api/products/create/").func.view_class, ProductCreateAPIView)

    def test_api_root_lists_all_endpoints(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "categories": "http://testserver/api/categories/",
                "products": "http://testserver/api/products/",
                "product_create": "http://testserver/api/products/create/",
            },
        )

    def test_site_urls_are_not_affected(self):
        self.assertEqual(reverse("home"), "/")
        self.assertEqual(reverse("product_detail", args=[self.cheap.pk]), f"/product/{self.cheap.pk}/")
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)


# ---------------------------------------------------------------------------
# კატეგორიების სია
# ---------------------------------------------------------------------------

class CategoryListApiTests(ApiTestCase):
    url = "/api/categories/"

    def test_anonymous_can_read_the_list_as_json(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIsInstance(response.json(), list)
        self.assertEqual(len(response.json()), 3)

    def test_all_categories_are_listed_in_name_order_including_empty_ones(self):
        names = [item["name"] for item in self.client.get(self.url).json()]
        self.assertEqual(names, ["Empty category", "Laptops", "Phones"])

    def test_item_fields(self):
        for item in self.client.get(self.url).json():
            self.assertEqual(set(item), CATEGORY_LIST_KEYS)

    def test_item_values(self):
        laptops = next(i for i in self.client.get(self.url).json() if i["name"] == "Laptops")
        self.assertEqual(
            laptops,
            {"id": self.laptops.pk, "name": "Laptops", "description": "Notebook computers", "product_count": 2},
        )

    def test_product_count_per_category(self):
        counts = {i["name"]: i["product_count"] for i in self.client.get(self.url).json()}
        self.assertEqual(counts, {"Empty category": 0, "Laptops": 2, "Phones": 2})

    def test_list_needs_one_database_query(self):
        with self.assertNumQueries(1):
            self.client.get(self.url)

    def test_new_product_changes_the_count(self):
        Product.objects.create(name="Another phone", price="10", category=self.phones)
        counts = {i["name"]: i["product_count"] for i in self.client.get(self.url).json()}
        self.assertEqual(counts["Phones"], 3)

    def test_list_is_read_only(self):
        self.assertEqual(self.client.post(self.url, {"name": "Hack"}, format="json").status_code, 403)
        self.client.force_authenticate(self.owner)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.url).status_code, 405)
        self.assertEqual(Category.objects.count(), 3)


# ---------------------------------------------------------------------------
# პროდუქტების სია
# ---------------------------------------------------------------------------

class ProductListApiTests(ApiTestCase):
    url = "/api/products/"

    def test_anonymous_can_read_the_list_as_json(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(len(response.json()), 4)

    def test_products_are_sorted_by_price_ascending(self):
        names = [item["name"] for item in self.client.get(self.url).json()]
        self.assertEqual(names, ["Cheap laptop", "Mid phone", "Legacy tablet", "Expensive laptop"])

    def test_item_has_short_info_only(self):
        for item in self.client.get(self.url).json():
            self.assertEqual(set(item), PRODUCT_LIST_KEYS)
        item = self.client.get(self.url).json()[0]
        self.assertNotIn("description", item)
        self.assertNotIn("owner", item)

    def test_item_values(self):
        item = self.client.get(self.url).json()[0]
        self.assertEqual(item["id"], self.cheap.pk)
        self.assertEqual(item["name"], "Cheap laptop")
        self.assertEqual(item["price"], "500.00")  # DRF Decimal-ს სტრიქონად აბრუნებს: სიზუსტე არ იკარგება
        self.assertIs(item["has_discount"], True)
        self.assertEqual(item["category"], self.laptops.pk)
        self.assertEqual(item["category_name"], "Laptops")
        self.assertEqual(item["url"], f"http://testserver/api/products/{self.cheap.pk}/")

    def test_discount_flag_is_per_product(self):
        flags = {i["name"]: i["has_discount"] for i in self.client.get(self.url).json()}
        self.assertEqual(
            flags,
            {"Cheap laptop": True, "Mid phone": False, "Legacy tablet": False, "Expensive laptop": False},
        )

    def test_product_without_image_gets_the_same_placeholder_as_the_site(self):
        item = next(i for i in self.client.get(self.url).json() if i["id"] == self.mid.pk)
        self.assertEqual(item["image"], f"http://testserver/static/{self.mid.placeholder_image}")

    def test_uploaded_image_is_returned_as_full_media_url(self):
        product = Product.objects.create(
            name="With photo", price="1", category=self.phones, image=make_image()
        )
        item = next(i for i in self.client.get(self.url).json() if i["id"] == product.pk)
        self.assertEqual(item["image"], "http://testserver" + product.image.url)
        self.assertTrue(item["image"].startswith("http://testserver/media/products/"))

    def test_list_needs_one_database_query(self):
        """select_related: კატეგორია პროდუქტებთან ერთად იკითხება (1 მოთხოვნა და არა 1 + N)."""
        with self.assertNumQueries(1):
            self.client.get(self.url)

    def test_empty_database_returns_empty_list(self):
        Product.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_is_read_only(self):
        self.assertEqual(self.client.post(self.url, {"name": "Hack"}, format="json").status_code, 403)
        self.client.force_authenticate(self.owner)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.url).status_code, 405)
        self.assertEqual(Product.objects.count(), 4)


# ---------------------------------------------------------------------------
# პროდუქტის დეტალური ინფორმაცია
# ---------------------------------------------------------------------------

class ProductDetailApiTests(ApiTestCase):
    def url(self, product):
        return f"/api/products/{product.pk}/"

    def test_anonymous_can_read_a_product(self):
        response = self.client.get(self.url(self.cheap))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_full_info(self):
        data = self.client.get(self.url(self.cheap)).json()
        self.assertEqual(set(data), PRODUCT_DETAIL_KEYS)
        self.assertEqual(
            data,
            {
                "id": self.cheap.pk,
                "name": "Cheap laptop",
                "description": "Light and cheap",
                "price": "500.00",
                "has_discount": True,
                "image": f"http://testserver/static/{self.cheap.placeholder_image}",
                "category": {"id": self.laptops.pk, "name": "Laptops", "description": "Notebook computers"},
                "owner": "owner",
            },
        )

    def test_category_is_a_nested_object_not_just_an_id(self):
        category = self.client.get(self.url(self.mid)).json()["category"]
        self.assertEqual(set(category), {"id", "name", "description"})
        self.assertEqual(category["name"], "Phones")

    def test_product_without_owner_has_null_owner(self):
        self.assertIsNone(self.client.get(self.url(self.legacy)).json()["owner"])

    def test_each_product_returns_its_own_data(self):
        for product in (self.cheap, self.mid, self.expensive, self.legacy):
            with self.subTest(product=product.name):
                data = self.client.get(self.url(product)).json()
                self.assertEqual(data["id"], product.pk)
                self.assertEqual(data["name"], product.name)
                # product.price setUpTestData-ში სტრიქონად იყო გადაცემული, ამიტომ ბაზიდან ვკითხულობთ
                self.assertEqual(Decimal(data["price"]), Product.objects.get(pk=product.pk).price)

    def test_uploaded_image_is_returned(self):
        product = Product.objects.create(
            name="With photo", price="1", category=self.phones, image=make_image()
        )
        data = self.client.get(self.url(product)).json()
        self.assertEqual(data["image"], "http://testserver" + product.image.url)

    def test_detail_needs_one_database_query(self):
        with self.assertNumQueries(1):
            self.client.get(self.url(self.cheap))

    def test_missing_product_returns_404_json(self):
        response = self.client.get("/api/products/9999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "No Product matches the given query."})

    def test_non_numeric_id_returns_404(self):
        self.assertEqual(self.client.get("/api/products/abc/").status_code, 404)

    def test_detail_is_read_only(self):
        """API-ს ცვლილების სხვა ოპერაციები (განახლება, წაშლა) არ აქვს: დავალებაში მხოლოდ შექმნაა."""
        url = self.url(self.cheap)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_authenticate(self.owner)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(url).status_code, 405)
        self.cheap.refresh_from_db()
        self.assertEqual(self.cheap.name, "Cheap laptop")


# ---------------------------------------------------------------------------
# პროდუქტის შექმნა
# ---------------------------------------------------------------------------

class ProductCreateApiTests(ApiTestCase):
    url = "/api/products/create/"

    def valid_data(self, **extra):
        data = {
            "name": "New tablet",
            "description": "10 inch tablet",
            "price": "999.90",
            "category": self.phones.pk,
            "has_discount": True,
        }
        data.update(extra)
        return data

    # --- ვის შეუძლია --------------------------------------------------------

    def test_anonymous_cannot_create(self):
        response = self.client.post(self.url, self.valid_data(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})
        self.assertEqual(Product.objects.count(), 4)

    def test_anonymous_get_is_also_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_logged_in_user_cannot_use_get(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    # --- წარმატებული შექმნა -------------------------------------------------

    def test_valid_json_creates_product(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, self.valid_data(), format="json")
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="New tablet")
        self.assertEqual(Product.objects.count(), 5)
        self.assertEqual(product.price, Decimal("999.90"))
        self.assertEqual(product.category, self.phones)
        self.assertEqual(product.description, "10 inch tablet")
        self.assertTrue(product.has_discount)

    def test_response_has_full_product_info(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, self.valid_data(), format="json")
        product = Product.objects.get(name="New tablet")
        data = response.json()
        self.assertEqual(set(data), PRODUCT_DETAIL_KEYS)
        self.assertEqual(data["id"], product.pk)
        self.assertEqual(data["price"], "999.90")
        self.assertEqual(data["category"], {"id": self.phones.pk, "name": "Phones", "description": ""})
        self.assertEqual(data["owner"], "owner")
        self.assertIs(data["has_discount"], True)

    def test_response_has_location_header_of_the_new_product(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, self.valid_data(), format="json")
        product = Product.objects.get(name="New tablet")
        self.assertEqual(response["Location"], f"http://testserver/api/products/{product.pk}/")
        self.assertEqual(self.client.get(response["Location"]).json()["name"], "New tablet")

    def test_owner_is_the_authenticated_user(self):
        for user in (self.owner, self.other):
            self.client.force_authenticate(user)
            self.client.post(self.url, self.valid_data(name=f"By {user.username}"), format="json")
        self.assertEqual(Product.objects.get(name="By owner").user, self.owner)
        self.assertEqual(Product.objects.get(name="By other").user, self.other)

    def test_owner_can_manage_the_product_on_the_site(self):
        """API-დან შექმნილი პროდუქტი საიტზე ისევე ეკუთვნის მომხმარებელს, როგორც საიტიდან დამატებული."""
        self.client.force_authenticate(self.other)
        self.client.post(self.url, self.valid_data(), format="json")
        product = Product.objects.get(name="New tablet")
        self.assertTrue(product.is_owned_by(self.other))
        self.assertFalse(product.is_owned_by(self.owner))

    def test_user_sent_in_the_request_is_ignored(self):
        """ხელით გამოგზავნილი "user": <სხვა id> მაინც ავტორიზებულ მომხმარებელს ჩაწერს."""
        self.client.force_authenticate(self.owner)
        self.client.post(self.url, self.valid_data(user=self.other.pk), format="json")
        self.assertEqual(Product.objects.get(name="New tablet").user, self.owner)

    def test_id_sent_in_the_request_is_ignored(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, self.valid_data(id=99999), format="json")
        self.assertNotEqual(response.json()["id"], 99999)

    def test_only_required_fields(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url, {"name": "Minimal", "price": "10", "category": self.phones.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="Minimal")
        self.assertEqual(product.description, "")
        self.assertFalse(product.has_discount)
        self.assertFalse(product.image)

    def test_name_is_stripped(self):
        self.client.force_authenticate(self.owner)
        self.client.post(self.url, self.valid_data(name="   Spaced name   "), format="json")
        self.assertTrue(Product.objects.filter(name="Spaced name").exists())

    def test_form_data_works_like_the_site_form(self):
        """multipart/form-data (HTML ფორმისა და curl -F-ის ფორმატი); ჩეკბოქსი "on"-ია."""
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url,
            {"name": "From form", "price": "45.50", "category": self.laptops.pk, "has_discount": "on"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="From form")
        self.assertEqual(product.price, Decimal("45.50"))
        self.assertTrue(product.has_discount)

    def test_unchecked_discount_in_form_data_is_false(self):
        self.client.force_authenticate(self.owner)
        self.client.post(
            self.url,
            {"name": "No discount", "price": "5", "category": self.phones.pk},
            format="multipart",
        )
        self.assertFalse(Product.objects.get(name="No discount").has_discount)

    def test_created_product_appears_in_api_and_on_the_site(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(self.url, self.valid_data(), format="json").json()
        self.client.force_authenticate(None)

        listed = [i["id"] for i in self.client.get("/api/products/").json()]
        self.assertIn(created["id"], listed)
        counts = {i["name"]: i["product_count"] for i in self.client.get("/api/categories/").json()}
        self.assertEqual(counts["Phones"], 3)
        self.assertContains(self.client.get(reverse("product_detail", args=[created["id"]])), "New tablet")

    def test_product_can_be_created_in_an_empty_category(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, self.valid_data(category=self.empty.pk), format="json")
        self.assertEqual(response.status_code, 201)
        counts = {i["name"]: i["product_count"] for i in self.client.get("/api/categories/").json()}
        self.assertEqual(counts["Empty category"], 1)

    # --- არასწორი მონაცემები ---------------------------------------------

    def test_empty_request_reports_every_required_field(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"name", "price", "category"})
        self.assertEqual(Product.objects.count(), 4)

    def test_invalid_data_is_rejected_with_error_on_the_right_field(self):
        bad_cases = {
            "empty name": ({"name": ""}, "name"),
            "one letter name": ({"name": "A"}, "name"),
            "spaces only": ({"name": "   "}, "name"),
            "too long name": ({"name": "x" * 201}, "name"),
            "no category": ({"category": None}, "category"),
            "unknown category": ({"category": 9999}, "category"),
            "text category": ({"category": "abc"}, "category"),
            "empty price": ({"price": ""}, "price"),
            "zero price": ({"price": "0"}, "price"),
            "negative price": ({"price": "-5"}, "price"),
            "text price": ({"price": "abc"}, "price"),
            "NaN price": ({"price": "NaN"}, "price"),
            "too many digits": ({"price": "12345678901"}, "price"),
            "too many decimals": ({"price": "10.999"}, "price"),
        }
        self.client.force_authenticate(self.owner)
        for label, (change, field) in bad_cases.items():
            with self.subTest(case=label):
                response = self.client.post(self.url, self.valid_data(**change), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
                self.assertEqual(Product.objects.count(), 4)

    def test_error_messages_are_the_same_as_on_the_site_form(self):
        self.client.force_authenticate(self.owner)
        short = self.client.post(self.url, self.valid_data(name="A"), format="json").json()
        self.assertEqual(short["name"], ["Product name must contain at least 2 characters."])
        zero = self.client.post(self.url, self.valid_data(price="0"), format="json").json()
        self.assertEqual(zero["price"], ["Price must be greater than zero."])

    def test_invalid_data_does_not_change_existing_products(self):
        self.client.force_authenticate(self.owner)
        self.client.post(self.url, self.valid_data(name="Cheap laptop", price="-1"), format="json")
        self.cheap.refresh_from_db()
        self.assertEqual(self.cheap.price, Decimal("500.00"))
        self.assertEqual(Product.objects.count(), 4)


# ---------------------------------------------------------------------------
# სურათის ატვირთვა
# ---------------------------------------------------------------------------

class ProductCreateImageApiTests(ApiTestCase):
    url = "/api/products/create/"

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.owner)

    def post_data(self, **extra):
        data = {"name": "With photo", "category": self.phones.pk, "price": "10.00"}
        data.update(extra)
        return data

    def post(self, **extra):
        return self.client.post(self.url, self.post_data(**extra), format="multipart")

    def test_image_is_optional(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="With photo")
        self.assertFalse(product.image)
        self.assertEqual(self.media_files(), [])
        # სურათის გარეშე იგივე მზა სურათი ჩანს, რაც საიტზე
        self.assertEqual(response.json()["image"], f"http://testserver/static/{product.placeholder_image}")

    def test_uploaded_image_is_saved_in_products_folder(self):
        response = self.post(image=make_image())
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="With photo")
        self.assertTrue(product.image.name.startswith("products/"))
        self.assertEqual(self.media_files(), [product.image.name.replace("/", os.sep)])
        self.assertEqual(product.user, self.owner)

    def test_response_contains_full_image_url(self):
        response = self.post(image=make_image())
        product = Product.objects.get(name="With photo")
        self.assertEqual(response.json()["image"], "http://testserver" + product.image.url)
        self.assertTrue(response.json()["image"].startswith("http://testserver/media/products/"))

    def test_supported_formats_are_accepted(self):
        for index, (file_name, image_format) in enumerate(
            [("a.jpg", "JPEG"), ("b.png", "PNG"), ("c.gif", "GIF"), ("d.webp", "WEBP")]
        ):
            with self.subTest(format=image_format):
                response = self.post(name=f"Photo {index}", image=make_image(file_name, image_format))
                self.assertEqual(response.status_code, 201)

    def test_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile("evil.png", b"this is not an image", content_type="image/png")
        response = self.post(image=fake)
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.json())
        self.assertFalse(Product.objects.filter(name="With photo").exists())
        self.assertEqual(self.media_files(), [])

    def test_unsupported_format_is_rejected(self):
        response = self.post(image=make_image("scan.bmp", "BMP"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["image"], ["Please upload a JPG, PNG, GIF or WEBP image."])
        self.assertFalse(Product.objects.filter(name="With photo").exists())
        self.assertEqual(self.media_files(), [])

    def test_too_large_image_is_rejected(self):
        with mock.patch.object(shop_forms, "MAX_IMAGE_SIZE", 10):  # ბაიტი: ნებისმიერი რეალური სურათი დიდია
            response = self.post(image=make_image())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["image"], ["The image is too large (maximum size is 5 MB)."])
        self.assertFalse(Product.objects.filter(name="With photo").exists())
        self.assertEqual(self.media_files(), [])

    def test_limits_are_the_same_as_on_the_site(self):
        self.assertEqual(shop_forms.MAX_IMAGE_SIZE, 5 * 1024 * 1024)
        self.assertEqual(
            shop_forms.ALLOWED_IMAGE_TYPES, {"image/jpeg", "image/png", "image/gif", "image/webp"}
        )

    def test_json_cannot_carry_a_file(self):
        response = self.client.post(self.url, self.post_data(image="photo.png"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.json())
        self.assertFalse(Product.objects.filter(name="With photo").exists())


# ---------------------------------------------------------------------------
# ავტორიზაცია
# ---------------------------------------------------------------------------

class AuthenticationApiTests(ApiTestCase):
    url = "/api/products/create/"
    payload = {"name": "Authenticated", "price": "10", "category": None}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.member = User.objects.create_user(username="member", password="correct-horse-9")

    def data(self):
        return {**self.payload, "category": self.phones.pk}

    def basic(self, username, password):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"HTTP_AUTHORIZATION": f"Basic {token}"}

    def test_basic_authentication_with_username_and_password(self):
        response = self.client.post(self.url, self.data(), format="json", **self.basic("member", "correct-horse-9"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.get(name="Authenticated").user, self.member)
        self.assertEqual(response.json()["owner"], "member")

    def test_wrong_password_is_refused(self):
        response = self.client.post(self.url, self.data(), format="json", **self.basic("member", "wrong"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Authenticated").exists())

    def test_unknown_user_is_refused(self):
        response = self.client.post(self.url, self.data(), format="json", **self.basic("nobody", "x"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Authenticated").exists())

    def test_inactive_user_is_refused(self):
        User.objects.filter(pk=self.member.pk).update(is_active=False)
        response = self.client.post(self.url, self.data(), format="json", **self.basic("member", "correct-horse-9"))
        self.assertEqual(response.status_code, 403)

    def test_session_login_works_when_csrf_token_is_sent(self):
        """ბრაუზერიდან შესული მომხმარებელი (სესია) იყენებს CSRF-ს: ტოკენის გარეშე 403."""
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.member)
        response = strict.post(self.url, self.data(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])
        self.assertFalse(Product.objects.filter(name="Authenticated").exists())

    def test_session_login_without_csrf_enforcement_creates_product(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url, self.data(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.get(name="Authenticated").user, self.member)

    def test_reading_does_not_need_login(self):
        for url in ("/api/categories/", "/api/products/", f"/api/products/{self.cheap.pk}/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


# ---------------------------------------------------------------------------
# სერიალიზატორები, view-ები, პარამეტრები
# ---------------------------------------------------------------------------

class SerializersAndSettingsTests(ApiTestCase):
    def test_each_view_uses_its_own_serializer(self):
        self.assertIs(CategoryListAPIView.serializer_class, CategoryListSerializer)
        self.assertIs(ProductListAPIView.serializer_class, ProductListSerializer)
        self.assertIs(ProductDetailAPIView.serializer_class, ProductDetailSerializer)
        self.assertIs(ProductCreateAPIView.serializer_class, ProductCreateSerializer)

    def test_views_are_drf_generic_views(self):
        self.assertTrue(issubclass(CategoryListAPIView, generics.ListAPIView))
        self.assertTrue(issubclass(ProductListAPIView, generics.ListAPIView))
        self.assertTrue(issubclass(ProductDetailAPIView, generics.RetrieveAPIView))
        self.assertTrue(issubclass(ProductCreateAPIView, generics.CreateAPIView))

    def test_serializer_fields(self):
        self.assertEqual(set(CategorySerializer().fields), {"id", "name", "description"})
        self.assertEqual(set(CategoryListSerializer().fields), CATEGORY_LIST_KEYS)
        self.assertEqual(set(ProductListSerializer().fields), PRODUCT_LIST_KEYS)
        self.assertEqual(set(ProductDetailSerializer().fields), PRODUCT_DETAIL_KEYS)
        self.assertEqual(
            set(ProductCreateSerializer().fields),
            {"name", "description", "price", "category", "has_discount", "image"},
        )

    def test_create_serializer_has_no_user_or_id(self):
        fields = ProductCreateSerializer().fields
        self.assertNotIn("user", fields)
        self.assertNotIn("id", fields)

    def test_read_serializers_cannot_write(self):
        for serializer in (ProductListSerializer(), ProductDetailSerializer()):
            for name, field in serializer.fields.items():
                with self.subTest(serializer=type(serializer).__name__, field=name):
                    self.assertTrue(field.read_only)

    def test_serializer_validates_without_a_view(self):
        serializer = ProductCreateSerializer(
            data={"name": "X", "price": "1", "category": self.phones.pk}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_create_view_requires_authentication_explicitly(self):
        self.assertEqual(ProductCreateAPIView.permission_classes, [IsAuthenticated])

    def test_drf_is_installed_and_configured(self):
        self.assertIn("rest_framework", settings.INSTALLED_APPS)
        self.assertIn("api", settings.INSTALLED_APPS)
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"],
            ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
        )


# ---------------------------------------------------------------------------
# ბრაუზერული API და ტექნიკური სამუშაოები
# ---------------------------------------------------------------------------

class BrowsableApiTests(ApiTestCase):
    """ბრაუზერში API-ს გვერდი იხსნება (DRF-ის ბრაუზერული ინტერფეისი), ე.ი. ხელით გამოსაცდელადაც მუშაობს."""

    def test_pages_open_in_the_browser(self):
        urls = ["/api/", "/api/categories/", "/api/products/", f"/api/products/{self.cheap.pk}/"]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url, HTTP_ACCEPT="text/html")
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response["Content-Type"])
                self.assertContains(response, "Django REST framework")

    def test_anonymous_sees_login_link(self):
        response = self.client.get("/api/products/", HTTP_ACCEPT="text/html")
        self.assertContains(response, "/api-auth/login/")

    def test_login_page_opens(self):
        self.assertEqual(self.client.get("/api-auth/login/").status_code, 200)

    def test_logged_in_user_sees_the_create_form(self):
        self.client.force_login(self.owner)
        response = self.client.get("/api/products/create/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 405)  # GET არ ეთქმის, მაგრამ POST ფორმა გვერდზე ჩანს
        self.assertContains(response, 'name="name"', status_code=405)
        self.assertContains(response, 'name="price"', status_code=405)
        self.assertContains(response, 'name="category"', status_code=405)

    def test_json_is_default_for_api_clients(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response["Content-Type"], "application/json")


class MaintenanceModeApiTests(ApiTestCase):
    """HW42-ის ტექნიკური სამუშაოების რეჟიმი API-ზეც მოქმედებს (ყველა გვერდი იკეტება, /admin/-ის გარდა)."""

    @override_settings(MAINTENANCE_MODE=True)
    def test_api_is_closed_during_maintenance(self):
        for url in ("/api/", "/api/categories/", "/api/products/", f"/api/products/{self.cheap.pk}/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_create_is_closed_during_maintenance(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/products/create/",
            {"name": "Closed", "price": "10", "category": self.phones.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Product.objects.filter(name="Closed").exists())
