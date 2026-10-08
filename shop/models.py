from django.db import models


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
