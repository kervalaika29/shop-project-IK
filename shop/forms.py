from django import forms
from django.core.exceptions import ValidationError

from .models import Product


class ProductForm(forms.ModelForm):
    """
    პროდუქტის დამატებისა და რედაქტირების ფორმა.
    ერთი და იგივე ფორმა გამოიყენება ორივე შემთხვევაში: დამატებისას ცარიელია,
    რედაქტირებისას კი არსებული პროდუქტის მონაცემებით ივსება (instance=product).
    """

    class Meta:
        model = Product
        fields = ["name", "category", "price", "description", "has_discount"]
        labels = {
            "name": "Product name",
            "category": "Category",
            "price": "Price (₾)",
            "description": "Description",
            "has_discount": "This product is on sale (discount)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Lenovo IdeaPad 3"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "0.00"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Short description (optional)"}),
            "has_discount": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # select-ის პირველი (ცარიელი) ვარიანტის ტექსტი
        self.fields["category"].empty_label = "— Select a category —"

    def clean_name(self):
        """სახელი: ზედმეტი გამოტოვებები იჭრება და მინიმუმ 2 სიმბოლო უნდა იყოს."""
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise ValidationError("Product name must contain at least 2 characters.")
        return name

    def clean_price(self):
        """ფასი ნულზე მეტი უნდა იყოს."""
        price = self.cleaned_data["price"]
        if price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price
