from django.db import models
from django.urls import reverse

# პროდუქტს სურათის ველი არ აქვს, ამიტომ ბარათზე ვაჩვენებთ Electro შაბლონის
# მზა სურათებს (static/shop/img/product-N.png). კატეგორიის მიხედვით ვირჩევთ
# შესაბამის სურათებს, უცნობი კატეგორიისთვის კი ყველა სურათს.
CATEGORY_IMAGES = {
    "laptops": [11],
    "smartphones": [3, 15, 16, 17, 18, 10],
    "headphones": [8],
    "accessories": [9, 12, 13, 6],
}
DEFAULT_IMAGES = list(range(3, 19))


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # ForeignKey: ერთ კატეგორიას ბევრი პროდუქტი შეიძლება ჰქონდეს
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    # ველი, რომელიც აჩვენებს ფასდაკლება აქვს თუ არა პროდუქტს
    has_discount = models.BooleanField(default=False)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """პროდუქტის გვერდის მისამართი (გამოიყენება შენახვის შემდეგ გადასამისამართებლად)."""
        return reverse("product_detail", args=[self.pk])

    @property
    def placeholder_image(self):
        """
        სურათის გზა static-ში. არჩევა დამოკიდებულია კატეგორიაზე და პროდუქტის
        id-ზე, ამიტომ ერთი და იგივე პროდუქტს ყველა გვერდზე ერთი სურათი ექნება.
        """
        numbers = CATEGORY_IMAGES.get(self.category.name.lower(), DEFAULT_IMAGES)
        number = numbers[(self.pk or 0) % len(numbers)]
        return f"shop/img/product-{number}.png"
