from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from .models import CATEGORY_IMAGES, DEFAULT_IMAGES, Category, Product


class ShopTestCase(TestCase):
    """საერთო საწყისი მონაცემები ყველა ტესტისთვის."""

    @classmethod
    def setUpTestData(cls):
        cls.laptops = Category.objects.create(name="Laptops")
        cls.phones = Category.objects.create(name="Phones")
        cls.empty = Category.objects.create(name="Empty category")

        cls.cheap = Product.objects.create(
            name="Cheap laptop", price="500.00", category=cls.laptops, has_discount=True
        )
        cls.mid = Product.objects.create(
            name="Mid phone", price="800.00", category=cls.phones
        )
        cls.expensive = Product.objects.create(
            name="Expensive laptop", price="2500.00", category=cls.laptops
        )


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

    def test_cards_have_edit_and_delete_links(self):
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
        response = strict_client.post(self.url, self.valid_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 3)


class ProductUpdateTests(ShopTestCase):
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
        response = strict_client.post(self.url(self.mid))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.mid.pk).exists())


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
