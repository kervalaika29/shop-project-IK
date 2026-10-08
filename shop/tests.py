from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ShopViewsTests(TestCase):
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

    def test_home_shows_sale_only_for_discounted_products(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "SALE", count=1)

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

    def test_product_detail_without_discount_has_no_sale_badge(self):
        response = self.client.get(reverse("product_detail", args=[self.mid.pk]))
        self.assertNotContains(response, "SALE")

    def test_missing_product_and_category_return_404(self):
        self.assertEqual(self.client.get(reverse("product_detail", args=[9999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("category_detail", args=[9999])).status_code, 404)
