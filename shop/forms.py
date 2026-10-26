from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import Product

# სურათის მაქსიმალური ზომა (5 MB) და დაშვებული ფორმატები
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class ProductForm(forms.ModelForm):
    """
    პროდუქტის დამატებისა და რედაქტირების ფორმა.
    ერთი და იგივე ფორმა გამოიყენება ორივე შემთხვევაში: დამატებისას ცარიელია,
    რედაქტირებისას კი არსებული პროდუქტის მონაცემებით ივსება (instance=product).

    user ველი ფორმაში განზრახ არ არის: მფლობელს მომხმარებელი ფორმიდან კი არ ირჩევს,
    view-ში ავტომატურად ვწერთ იმ მომხმარებელს, ვინც ამ მომენტში შესულია სისტემაში.
    """

    class Meta:
        model = Product
        fields = ["name", "category", "price", "image", "description", "has_discount"]
        labels = {
            "name": "Product name",
            "category": "Category",
            "price": "Price (₾)",
            "image": "Product image",
            "description": "Description",
            "has_discount": "This product is on sale (discount)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Lenovo IdeaPad 3"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "0.00"}),
            # ClearableFileInput: რედაქტირებისას აჩვენებს მიმდინარე სურათს და "Clear" ღილაკს
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
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

    def clean_image(self):
        """
        სურათის შემოწმება. ImageField თვითონ ამოწმებს, რომ ფაილი მართლა სურათია (Pillow-ით).
        აქ ვამატებთ ფორმატისა და ზომის შეზღუდვას. შემოწმება მხოლოდ ახლად ატვირთულ
        ფაილზე ხდება (UploadedFile): არსებული სურათი ან "Clear" (False) ამას არ სჭირდება.
        """
        image = self.cleaned_data.get("image")
        if isinstance(image, UploadedFile):
            if image.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError("Please upload a JPG, PNG, GIF or WEBP image.")
            if image.size > MAX_IMAGE_SIZE:
                raise ValidationError("The image is too large (maximum size is 5 MB).")
        return image
